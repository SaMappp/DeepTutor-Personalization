# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import httpx
import json

ROOT = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:18801'
WORKSPACE = 'REDACTED_WORKSPACE_ID'


def get(client, path):
    response = client.get(BASE + path, params={'dt_workspace': WORKSPACE})
    response.raise_for_status()
    return response.json()


if __name__ == '__main__':
    with httpx.Client(trust_env=False, timeout=30) as client:
        materials = get(client, '/api/reading/materials')
        collections = get(client, '/api/reading/workspaces')
        llm = get(client, '/api/settings/catalog')['catalog']['services']['llm']
        profile = next(x for x in llm['profiles'] if x['id'] == llm['active_profile_id'])
        model = next(x for x in profile['models'] if x['id'] == llm['active_model_id'])
        selection = {'profile_id': profile['id'], 'model': model['model'],
                     'reasoning_effort': model.get('reasoning_effort')}
        snapshot = {'base': BASE, 'workspace_id': WORKSPACE, 'materials': materials,
                    'collections': collections, 'selection': selection,
                    'runtime': get(client, '/api/system/runtime'), 'original_state': {}}
        for material in materials:
            if '高等数学' in material.get('filename', ''):
                mid = material['material_id']
                snapshot['original_state'][mid] = {
                    endpoint: get(client, '/api/reading/materials/' + mid + '/' + endpoint)
                    for endpoint in ['position', 'annotations', 'bookmarks']}
        (ROOT / 'calculus-before.json').write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({k:v for k,v in snapshot.items() if k not in ['runtime','original_state']},
                         ensure_ascii=False), flush=True)
        print('active_turn_count:', snapshot['runtime'].get('owner_turn_count'))
