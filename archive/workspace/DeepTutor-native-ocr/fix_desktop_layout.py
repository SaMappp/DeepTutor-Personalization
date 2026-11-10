# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Refresh the desktop content bounds when restoring a minimized window."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parent
TARGET = ROOT.parent / 'Open DeepTutor-win32-x64/resources/app/src/main.mjs'
RECORD = ROOT / 'desktop-layout-fix.json'
OLD = "  window.on('resize', layout);"
NEW = """  window.on('resize', layout);
  // A minimized Windows window can provide stale content bounds at startup.
  window.on('restore', layout);
  window.on('show', layout);"""


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == '__main__':
    source = TARGET.read_text(encoding='utf-8')
    if NEW in source:
        print('Desktop layout fix already present.')
    else:
        assert source.count(OLD) == 1, 'Unexpected desktop source; no changes made.'
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup = ROOT / 'backups' / stamp / 'desktop/main.mjs'
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TARGET, backup)
        before = sha(TARGET)
        TARGET.write_text(source.replace(OLD, NEW), encoding='utf-8')
        record = {
            'target': str(TARGET), 'backup': str(backup),
            'before_sha256': before, 'after_sha256': sha(TARGET),
            'reason': 'Refresh WebContentsView bounds on Windows restore/show, in addition to resize.',
            'scope': 'Desktop layout only; no model, OCR, or reading-data changes.',
        }
        RECORD.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(record, ensure_ascii=False))
