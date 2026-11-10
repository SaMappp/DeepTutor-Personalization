# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Use only existing loopback DeepTutor services and reading collections."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse
import hashlib
import json
import re
import httpx
import pymupdf
import engine
from pipeline import atomic_json, meaningful

DESKTOP = 'http://127.0.0.1:18801'
CLI = 'http://127.0.0.1:8001'


class DeepTutorClient:
    def __init__(self, base=DESKTOP):
        url = urlparse(base)
        if url.scheme != 'http' or url.hostname not in ['127.0.0.1', 'localhost', '::1'] or url.username or url.password:
            raise ValueError('只允许连接本机现有 DeepTutor 服务。')
        self.base = base.rstrip('/')
        self.client = httpx.Client(trust_env=False, timeout=300)

    def close(self):
        self.client.close()

    def call(self, path, workspace='', method='GET', params=None, **kwargs):
        query = dict(params or {})
        if workspace:
            query['dt_workspace'] = workspace
        try:
            response = self.client.request(method, self.base + path, params=query, **kwargs)
        except httpx.ConnectError as exc:
            raise RuntimeError('无法连接 DeepTutor。请先打开所选桌面版/CLI 服务；工具不会擅自启动另一套服务。') from exc
        if response.status_code in [401, 403]:
            raise RuntimeError('DeepTutor 拒绝访问，请在应用中登录或检查权限，然后重试。')
        if response.is_error:
            try:
                detail = response.json().get('detail', '')
            except ValueError:
                detail = response.text[:300]
            raise RuntimeError(f'DeepTutor 接口失败 {response.status_code}：{detail}')
        return response.json()

    def workspaces(self):
        return [w for w in self.call('/api/settings/workspace/registrations')['workspaces']
                if not w.get('archived') and w.get('status') == 'ready']

    def collections(self, workspace):
        return self.call('/api/reading/workspaces', workspace)['workspaces']

    def selection(self, workspace):
        llm = self.call('/api/settings/catalog', workspace)['catalog']['services']['llm']
        profile = next(x for x in llm['profiles'] if x['id'] == llm['active_profile_id'])
        model = next(x for x in profile['models'] if x['id'] == llm['active_model_id'])
        return {'profile_id': profile['id'], 'model_id': model['id'], 'model': model['model'],
                'reasoning_effort': model.get('reasoning_effort')}

    def import_pdf(self, result, workspace, collection, log=print, make_active=True):
        output = Path(result['output'])
        output_hash = engine.file_hash(output)
        if output_hash != result['output_sha256']:
            raise RuntimeError('输出文件已被修改，请重新处理后再导入。')
        existing = self.call('/api/reading/materials', workspace)
        before_collection = self.call('/api/reading/workspaces/' + collection, workspace)['workspace']
        old_ids = [tab['material']['material_id'] for tab in before_collection['tabs']]
        selected = self.selection(workspace)
        state = {mid: {name: self.call(f'/api/reading/materials/{mid}/{name}', workspace)
                       for name in ['position', 'annotations', 'bookmarks']}
                 for mid in old_ids}
        expected_id = output_hash[:16]
        match = next((m for m in existing if m['material_id'] == expected_id), None)
        if match is not None:
            # Verify full bytes before trusting a shortened content ID from another import.
            h = hashlib.sha256()
            with self.client.stream('GET', self.base + f'/api/reading/materials/{expected_id}/raw',
                                    params={'dt_workspace': workspace}) as response:
                response.raise_for_status()
                for chunk in response.iter_bytes():
                    h.update(chunk)
            if h.hexdigest() != output_hash:
                raise RuntimeError('已有材料的完整内容哈希不匹配，停止导入。')
            material = match
            log('相同内容的材料已存在，复用材料，不重复上传。')
        else:
            log('正在上传到本机 DeepTutor 并提取页面文字……')
            with output.open('rb') as stream:
                material = self.call('/api/reading/materials', workspace, method='POST',
                                     params={'reuse': 'true'},
                                     files={'file': (output.name, stream, 'application/pdf')})
        mid = material['material_id']
        if material['unit_count'] != result['source_pages'] or not material['has_raw_view']:
            raise RuntimeError('DeepTutor 导入后的页数或原图视图不符合预期；未加入阅读组。')
        if material.get('render_mode') != 'pdf':
            raise RuntimeError('DeepTutor 未保留 PDF 原图模式。')
        if match is None and mid != result['source_sha256'][:16]:
            source = next((m for m in existing if m['material_id'] == result['source_sha256'][:16]), None)
            if source:
                pos = self.call(f'/api/reading/materials/{source["material_id"]}/position', workspace)
                self.call(f'/api/reading/materials/{mid}/position', workspace, method='PUT',
                          json={k: pos[k] for k in ['locator', 'source_anchor', 'percentage']})
        with pymupdf.open(output) as document:
            expected = {n+1: document[n].get_text() for n in range(len(document))}
        def verify(number):
            actual = self.call(f'/api/reading/materials/{mid}/units/{number}', workspace)['text']
            want = meaningful(expected[number])
            got = meaningful(actual)
            # Ignore image markers and whitespace; PDF text must survive page-by-page ingestion.
            if want and want not in got:
                raise RuntimeError(f'DeepTutor 第 {number} 页正文提取不一致。')
            return {'page': number, 'expected_chars': len(expected[number]), 'actual_chars': len(actual)}
        log(f'正在通过 DeepTutor 接口逐页检查 {result["source_pages"]} 页文字……')
        with ThreadPoolExecutor(max_workers=4) as pool:
            pages = list(pool.map(verify, expected))
        if mid not in old_ids:
            active = make_active and self.call('/api/system/runtime', workspace).get('owner_turn_count') == 0
            self.call('/api/reading/workspaces/' + collection + '/materials', workspace, method='POST',
                      json={'material_id': mid, 'make_active': active})
        after = self.call('/api/reading/workspaces/' + collection, workspace)['workspace']
        after_ids = [tab['material']['material_id'] for tab in after['tabs']]
        if [i for i in after_ids if i != mid] != [i for i in old_ids if i != mid]:
            raise RuntimeError('阅读组原有材料顺序发生变化，请检查。')
        differences = []
        for old_id, endpoints in state.items():
            for name, original in endpoints.items():
                actual = self.call(f'/api/reading/materials/{old_id}/{name}', workspace)
                def stable(v):
                    if isinstance(v, dict):
                        return {k:stable(x) for k,x in v.items() if k != 'updated_at'}
                    if isinstance(v, list):
                        return [stable(x) for x in v]
                    return v
                if stable(actual) != stable(original):
                    differences.append({'material_id': old_id, 'state': name})
        if differences:
            log('检测期间原材料状态有变化（可能同时在应用中阅读）；工具未写入原材料状态。')
        frontend = 18802 if self.base == DESKTOP else 3782
        record = {'base': self.base, 'workspace_id': workspace, 'collection_id': collection,
                  'collection_title': after['title'], 'material': material,
                  'output_sha256': output_hash, 'reused_material': match is not None,
                  'source_materials_retained': True, 'source_state_differences': differences,
                  'model_selection_before': selected, 'model_selection_after': self.selection(workspace),
                  'verified_pages': pages, 'partial': result['partial'], 'processed_pdf_pages': result['range'],
                  'url': f'http://127.0.0.1:{frontend}/learning/reading/{collection}?dt_workspace={workspace}'}
        atomic_json(output.with_suffix('.DeepTutor导入.json'), record)
        log('导入并验证成功：' + after['title'])
        return record
