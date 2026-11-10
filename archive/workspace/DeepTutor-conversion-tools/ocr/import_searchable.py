# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Append the reviewed OCR copy to the existing desktop Calculus collection."""
from pathlib import Path
import json
import re
import httpx
from make_searchable_rapid import OUTPUT, OUTDIR, WORK, digest

ROOT = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:18801'
WORKSPACE = 'REDACTED_WORKSPACE_ID'
ORIGINAL_ID = '965af5862119fc49'
COLLECTION = 'REDACTED_WORKSPACE_ID'


def normalize(text):
    return re.sub(r'\s+', '', text)


def main():
    verified = json.loads((OUTDIR / 'OCR验证报告.json').read_text(encoding='utf-8'))
    assert verified['output_sha256'] == digest(OUTPUT)
    assert verified['visual_pages_identical'] == 349
    before = json.loads((ROOT / 'calculus-before.json').read_text(encoding='utf-8'))
    with httpx.Client(trust_env=False, timeout=300) as client:
        def call(path, method='GET', **kwargs):
            response = client.request(method, BASE + path,
                                      params={'dt_workspace': WORKSPACE}, **kwargs)
            response.raise_for_status()
            return response.json()

        def selection():
            llm = call('/api/settings/catalog')['catalog']['services']['llm']
            profile = next(x for x in llm['profiles'] if x['id'] == llm['active_profile_id'])
            model = next(x for x in profile['models'] if x['id'] == llm['active_model_id'])
            return {'profile_id': profile['id'], 'model': model['model'],
                    'reasoning_effort': model.get('reasoning_effort')}

        selected = selection()
        original_collection = call('/api/reading/workspaces/' + COLLECTION)['workspace']
        assert ORIGINAL_ID in [tab['material']['material_id'] for tab in original_collection['tabs']]
        old_materials = call('/api/reading/materials')
        source_position = call('/api/reading/materials/' + ORIGINAL_ID + '/position')
        original_state = {
            old_id: {endpoint: call('/api/reading/materials/' + old_id + '/' + endpoint)
                     for endpoint in ['position', 'annotations', 'bookmarks']}
            for old_id in before['original_state']}
        # Reuse is based on content. Do not replace/delete the source material or its marks.
        with OUTPUT.open('rb') as file:
            material = call('/api/reading/materials?reuse=true', 'POST',
                            files={'file': (OUTPUT.name, file, 'application/pdf')})
        mid = material['material_id']
        (ROOT / 'uploaded-ocr-material.json').write_text(json.dumps(material, ensure_ascii=False, indent=2), encoding='utf-8')
        assert mid != ORIGINAL_ID
        assert material['unit_count'] == 349 and material['char_count'] > 100_000
        assert material['has_raw_view'] and material['render_mode'] == 'pdf'
        already_present = mid in [item['material_id'] for item in old_materials]
        if not already_present:
            call('/api/reading/materials/' + mid + '/position', 'PUT',
                 json={key: source_position[key] for key in ['locator', 'source_anchor', 'percentage']})
        probes = {13: ['函数与极限', '映射与函数'],
                  30: ['收敛数列的性质', '极限的唯一性'],
                  150: ['函数图像的描绘', '渐近线'], 280: ['伯努利方程', '通解']}
        units = {}
        for number, phrases in probes.items():
            unit = call('/api/reading/materials/' + mid + '/units/' + str(number))
            assert all(phrase in normalize(unit['text']) for phrase in phrases)
            units[str(number)] = {'chars': len(unit['text']), 'phrases_verified': phrases}
        current = call('/api/reading/workspaces/' + COLLECTION)['workspace']
        if mid not in [tab['material']['material_id'] for tab in current['tabs']]:
            # Keep an active conversation's source untouched; otherwise open the fixed copy.
            make_active = call('/api/system/runtime').get('owner_turn_count') == 0
            call('/api/reading/workspaces/' + COLLECTION + '/materials', 'POST',
                 json={'material_id': mid, 'make_active': make_active})
        after_collection = call('/api/reading/workspaces/' + COLLECTION)['workspace']
        old_ids = [tab['material']['material_id'] for tab in original_collection['tabs']]
        new_ids = [tab['material']['material_id'] for tab in after_collection['tabs']]
        assert [m for m in new_ids if m != mid] == old_ids
        assert selection() == selected
        for old_id, state in original_state.items():
            for endpoint, saved in state.items():
                actual = call('/api/reading/materials/' + old_id + '/' + endpoint)
                if isinstance(saved, dict):
                    saved = {k:v for k,v in saved.items() if k != 'updated_at'}
                    actual = {k:v for k,v in actual.items() if k != 'updated_at'}
                assert actual == saved, ('Existing source data changed', old_id, endpoint)
        saved_path = OUTDIR / 'DeepTutor导入记录.json'
        result = {'base': BASE, 'workspace_id': WORKSPACE, 'collection_id': COLLECTION,
                  'collection_title': after_collection['title'], 'material': material,
                  'url': 'http://127.0.0.1:18802/learning/reading/' + COLLECTION + '?dt_workspace=' + WORKSPACE,
                  'verified_units': units, 'original_materials_preserved': True,
                  'original_positions_annotations_bookmarks_preserved': True,
                  'model_selection_unchanged': selected,
                  'new_material_position': call('/api/reading/materials/' + mid + '/position'),
                  'active_material_id': after_collection['active_material_id']}
        saved_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
