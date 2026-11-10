# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import httpx

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'tessdata_best'


def download(language):
    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA / (language + '.traineddata')
    url = 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/main/' + path.name
    if not path.exists():
        with httpx.Client(follow_redirects=True, timeout=120) as client:
            response = client.get(url)
            response.raise_for_status()
            if len(response.content) < 1_000_000:
                raise ValueError('Unexpected model size')
            path.write_bytes(response.content)
    row = {'language': language, 'source': url, 'bytes': path.stat().st_size,
           'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    print(json.dumps(row), flush=True)
    return row


if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = list(pool.map(download, ['chi_sim', 'eng']))
    (ROOT / 'model-sources.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
