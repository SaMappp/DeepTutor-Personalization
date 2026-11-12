# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local validation/deployment script; configure your runtime paths before use.
"""Deploy only the verified document-scope fix to the current desktop core."""
from pathlib import Path
import ast
import datetime
import hashlib
import json
import shutil
import sys
import httpx

from deploy import snapshot

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'verification/full-document-fix'
CORE = Path(r'C:\Users\YOUR_NAME\AppData\Local\Open DeepTutor\runtimes\1.7.1-f7aed0744-x64\core')
FILES = ['deeptutor/reading/native_ocr.py', 'deeptutor/reading/page_scope.py', 'deeptutor/capabilities/reading/tools.py']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'prepare':
        with httpx.Client(trust_env=False, timeout=20) as client:
            before = snapshot(client)
        write(OUT / 'desktop-before-private.json', before)
        record = json.loads((ROOT/'deployment.json').read_text(encoding='utf-8'))
        known = {str(Path(row['file'])):row['after_sha256'] for row in record['files']}
        rows = []
        for rel in FILES:
            path = CORE/rel
            old = digest(path) if path.exists() else None
            assert old == known.get(str(Path(rel))), f'Unexpected deployed changes: {rel}'
            ast.parse((ROOT/'patch'/rel).read_text(encoding='utf-8'))
            rows.append({'file':rel,'before_sha256':old,'after_sha256':digest(ROOT/'patch'/rel)})
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        write(OUT/'deployment.json', {'backup':str(ROOT/'backups'/stamp/'document-scope'), 'files':rows, 'status':'prepared'})
        print('Current reading/model baseline saved; three-file patch prepared.')
    elif action == 'install':
        plan = json.loads((OUT/'deployment.json').read_text(encoding='utf-8'))
        assert plan['status'] == 'prepared'
        for row in plan['files']:
            target = CORE/row['file'];old = digest(target) if target.exists() else None
            assert old == row['before_sha256']
            if target.exists():
                saved = Path(plan['backup'])/row['file'];saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
            shutil.copy2(ROOT/'patch'/row['file'],target)
            assert digest(target) == row['after_sha256']
        record = json.loads((ROOT/'deployment.json').read_text(encoding='utf-8'))
        for row in plan['files']:
            matches = [r for r in record['files'] if Path(r['file']) == Path(row['file'])]
            if matches:matches[0]['after_sha256'] = row['after_sha256']
            else:record['files'].append(row)
        record['latest_document_scope_fix'] = str(OUT/'deployment.json')
        write(ROOT/'deployment.json',record)
        plan['status']='installed';write(OUT/'deployment.json',plan)
        print('Document-scope fix installed; original files backed up.')
    else:
        raise ValueError(action)
