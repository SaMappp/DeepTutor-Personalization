# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import httpx
import json

ROOT = Path(__file__).resolve().parent


def request(port):
    base = f'http://127.0.0.1:{port}'
    out = {'port': port, 'base': base}
    with httpx.Client(trust_env=False, timeout=6) as client:
        for path in ['/health/ready', '/api/settings/workspace/registrations',
                     '/api/reading/materials', '/api/reading/workspaces']:
            try:
                response = client.get(base + path)
                if response.status_code == 200:
                    out[path] = response.json()
                else:
                    out[path] = {'status': response.status_code}
            except Exception as exc:
                out[path] = {'error': str(exc)}
    print(json.dumps(out, ensure_ascii=False), flush=True)
    return out


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=2) as pool:
        data = list(pool.map(request, [18801, 8001]))
    (ROOT / 'reading-before.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
