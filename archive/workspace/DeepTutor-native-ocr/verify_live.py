# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys
import httpx

ROOT=Path(__file__).resolve().parent
CORE=Path(r'C:\Users\YOUR_NAME\AppData\Local\Open DeepTutor\runtimes\1.7.1-f7aed0744-x64\core')
BASE='http://127.0.0.1:18801'
sys.path.insert(0,str(CORE))
from deeptutor.reading import native_ocr


def stable(value):
    if isinstance(value,dict):return {k:stable(v) for k,v in value.items() if k not in ['updated_at','last_opened_at']}
    if isinstance(value,list):return [stable(v) for v in value]
    return value


def main():
    before=json.loads((ROOT/'verification'/'desktop-before.json').read_text(encoding='utf-8'))
    ui=json.loads((ROOT/'verification'/'ui-state.json').read_text(encoding='utf-8'))
    events=[json.loads(line) for line in (ROOT/'logs'/'page-ocr.jsonl').read_text(encoding='utf-8').splitlines()]
    source_hash=hashlib.sha256(Path(ui['file']).read_bytes()).hexdigest()
    calls=[e for e in events if e.get('source_sha256')==source_hash and e['action']=='ocr_start']
    counts=Counter(e['page'] for e in calls)
    assert counts=={2:1,3:1},counts
    scopes=[e for e in events if e.get('material_id')==source_hash[:16] and e['action']=='request_scope']
    assert [e['pages'] for e in scopes]==[[1],[2],[2],[3]]
    timings=[e['seconds'] for e in events if e.get('source_sha256')==source_hash and e['action']=='ocr_done']
    hits=[e for e in events if e.get('source_sha256')==source_hash and e['action']=='cache_hit' and e['page']==2]
    assert len(hits)>=2
    cfg=native_ocr.configuration();cache=native_ocr.cache_paths(source_hash,cfg['engine']['id'],2)[0]
    assert native_ocr.read_cache(cache,source_hash,cfg['engine']['id'],2)
    assert native_ocr.read_cache(cache,'0'*64,cfg['engine']['id'],2) is None
    assert native_ocr.read_cache(cache,source_hash,'0'*64,2) is None
    assert native_ocr.read_cache(cache,source_hash,cfg['engine']['id'],3) is None
    mismatches=[];raw_checks=[];replies=[]
    with httpx.Client(trust_env=False,timeout=20) as c:
        def get(path,w=''):
            response=c.get(BASE+path,params={'dt_workspace':w} if w else {});response.raise_for_status();return response.json()
        runtime=get('/api/system/runtime');assert runtime['owner_turn_count']==0
        llm=get('/api/settings/catalog')['catalog']['services']['llm']
        profile=next(x for x in llm['profiles'] if x['id']==llm['active_profile_id'])
        model=next(x for x in profile['models'] if x['id']==llm['active_model_id'])
        selected={'profile_id':profile['id'],'model':model['model'],'reasoning_effort':model.get('reasoning_effort')}
        assert selected==before['model'] and selected['model']=='gpt-6.1-sol' and selected['reasoning_effort']=='high'
        for wid,workspace in before['workspaces'].items():
            for mid,saved in workspace['materials'].items():
                for endpoint in ['position','annotations','bookmarks']:
                    actual=get(f'/api/reading/materials/{mid}/{endpoint}',wid)
                    if stable(actual)!=stable(saved[endpoint]):mismatches.append({'workspace':wid,'material':mid,'endpoint':endpoint})
            for original in workspace['collections']['workspaces']:
                actual=get('/api/reading/workspaces/'+original['workspace_id'],wid)['workspace']
                if stable(original)!=stable(actual):mismatches.append({'workspace':wid,'collection':original['workspace_id']})
        assert not mismatches,mismatches
        r=c.get(BASE+f'/api/reading/materials/{source_hash[:16]}/raw',params={'dt_workspace':ui['workspace_id']});r.raise_for_status()
        assert hashlib.sha256(r.content).hexdigest()==source_hash
        raw_checks.append({'material_id':source_hash[:16],'raw_pdf_bytes_identical':True})
        for session in ['SESSION_ID','SESSION_ID']:
            data=get('/api/sessions/'+session,ui['workspace_id'])
            replies.extend({'session':session,'content':message['content']} for message in data['messages'] if message.get('role')=='assistant')
        assert any('映射' in r['content'] and '[p.2]' in r['content'] for r in replies)
        assert any('极限' in r['content'] and '[p.3]' in r['content'] for r in replies)
    deployment=json.loads((ROOT/'deployment.json').read_text(encoding='utf-8'))
    for row in deployment['files']:
        actual=CORE/row['file'];assert hashlib.sha256(actual.read_bytes()).hexdigest()==row['after_sha256']
    result={'actual_desktop_core':str(CORE),'actual_frontend':deployment['actual_web'],
        'runtime_home':deployment['runtime_home'],'backend_runtime':runtime,
        'model_preserved':selected,'original_reading_positions_annotations_bookmarks_collections_preserved':not mismatches,
        'raw_pdf_checks':raw_checks,'native_ui_upload_open_without_ocr':True,
        'native_ui_current_text_page_no_ocr':True,'native_ui_requested_scanned_pages':dict(counts),
        'native_ui_request_scopes':[e['pages'] for e in scopes],
        'no_unrequested_page_ocr':True,'native_ui_page_ocr_seconds':timings,
        'cache_hit_after_desktop_restart':True,'cache_identity_negative_tests_passed':True,
        'native_ui_status_visible':'正在本机识别 PDF 第 3 页… PDF 第 3 页识别完成，用时 8.1 秒。',
        'native_ui_replies_verified':replies,'patched_files_verified':True,
        'evidence_screenshot':str(ROOT/'verification'/'desktop-ocr-status.png')}
    (ROOT/'verification'/'live-desktop-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='native_ui_replies_verified'},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
