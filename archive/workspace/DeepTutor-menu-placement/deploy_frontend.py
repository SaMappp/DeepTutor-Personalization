# SPDX-License-Identifier: Apache-2.0
# Historical local customization; publication paths sanitized. Review docs before running.
"""Deploy the reading-composer placement fix to the active desktop frontend."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import socket
import sys

import httpx

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
RUNTIME = Path(r'C:\Users\YOUR_NAME\AppData\Local\Open DeepTutor\runtimes\1.7.1-f7aed0744-x64')
CACHE = Path(r'C:\Users\YOUR_NAME\AppData\Local\Open DeepTutor\cache\1.7.1-f7aed0744-x64')
BUILT = PROJECT / 'DeepTutor-local-ui/web/.next/standalone'
STAGED = ROOT / 'bundle'
sys.path.insert(0, str(PROJECT / 'DeepTutor-native-ocr'))
from deploy import snapshot
from verify_live import stable


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, data):
    (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def current():
    with httpx.Client(trust_env=False, timeout=20) as client:
        return snapshot(client)


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'prepare':
        assert (BUILT / 'server.js').is_file()
        assert (BUILT / '.next/static').is_dir()
        before = current()
        before['ocr_log_sha256'] = sha(PROJECT / 'DeepTutor-native-ocr/logs/page-ocr.jsonl')
        before['desktop_shell_sha256'] = sha(PROJECT / 'Open DeepTutor-win32-x64/resources/app/src/main.mjs')
        write('before.json', before)
        assert not STAGED.exists(), 'A staged bundle already exists; inspect before replacing.'
        shutil.copytree(BUILT, STAGED)
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        write('deployment.json', {
            'change': 'ReadingComposer enables the existing docked layout; model and reasoning menus always open upward.',
            'source_file': str(PROJECT / 'DeepTutor-local-ui/web/components/reading/workspace/ReadingComposer.tsx'),
            'build_id': (STAGED / '.next/BUILD_ID').read_text().strip(),
            'old_build_id': (CACHE / 'web/.next/BUILD_ID').read_text().strip(),
            'runtime_frontend': str(RUNTIME / 'web'),
            'actual_frontend': str(CACHE / 'web'),
            'backups': {str(parent / 'web'): str(parent / ('web.before-menu-up-' + stamp)) for parent in [RUNTIME, CACHE]},
            'status': 'prepared',
        })
        print('Prepared frontend bundle and current reading/model baseline.')
    elif action == 'install':
        record = json.loads((ROOT / 'deployment.json').read_text(encoding='utf-8'))
        assert record['status'] == 'prepared'
        targets = []
        for parent in [RUNTIME, CACHE]:
            target = parent / 'web'
            backup = Path(record['backups'][str(target)])
            # Both resolved paths must remain immediate children of the named runtime/cache.
            assert target.resolve().parent == parent.resolve()
            assert backup.resolve().parent == parent.resolve()
            assert target.is_dir() and not backup.exists()
            targets.append((target, backup))
        try:
            for target, backup in targets:
                target.rename(backup)
            shutil.copytree(STAGED, RUNTIME / 'web')
        except Exception:
            # Keep an incomplete copy for diagnosis, then restore only our moved frontend directories.
            if targets[0][1].exists() and (RUNTIME / 'web').exists():
                (RUNTIME / 'web').rename(RUNTIME / ('web.failed-menu-up-' + str(int(datetime.datetime.now().timestamp()))))
            for target, backup in targets:
                if backup.exists() and not target.exists():
                    backup.rename(target)
            raise
        record['status'] = 'installed'
        write('deployment.json', record)
        print('Installed frontend; prior runtime/cache frontends retained as backups.')
    elif action == 'audit':
        before = json.loads((ROOT / 'before.json').read_text(encoding='utf-8'))
        after = current()
        assert stable(before['workspaces']) == stable(after['workspaces']), 'Reading state differs; inspect before concluding.'
        assert before['model'] == after['model']
        assert before['active_runtime'] == after['active_runtime']
        assert before['ocr_log_sha256'] == sha(PROJECT / 'DeepTutor-native-ocr/logs/page-ocr.jsonl')
        assert before['desktop_shell_sha256'] == sha(PROJECT / 'Open DeepTutor-win32-x64/resources/app/src/main.mjs')
        record = json.loads((ROOT / 'deployment.json').read_text(encoding='utf-8'))
        for parent in [RUNTIME, CACHE]:
            assert (parent / 'web/.next/BUILD_ID').read_text().strip() == record['build_id']
        native = json.loads((PROJECT / 'DeepTutor-native-ocr/deployment.json').read_text(encoding='utf-8'))
        for row in native['files']:
            assert sha(RUNTIME / 'core' / row['file']) == row['after_sha256']
        ui = []
        for name in ['empty-model-menu', 'empty-effort-menu', 'existing-model-menu', 'existing-effort-menu', 'last-model-option']:
            payload = json.loads((ROOT / (name + '.json')).read_text(encoding='utf-8-sig'))
            assert payload['success'], payload
            row = payload['data']['result']
            if name == 'last-model-option':
                assert row['fully_visible'] and row['hit_target_is_option'] and row['not_covered_by_window_edge']
            else:
                assert row['opens_up'] and row['inside_viewport']
            ui.append(row)
        with socket.socket() as probe:
            probe.settimeout(1)
            assert probe.connect_ex(('127.0.0.1', 19474)) != 0, 'Temporary debugging port still open'
        result = {
            'checked_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'build_id': record['build_id'],
            'actual_frontend': record['actual_frontend'],
            'reading_data_preserved': True, 'model_settings_preserved': after['model'],
            'ocr_patch_and_cache_log_preserved': True, 'desktop_restore_fix_preserved': True,
            'no_ocr_or_model_turns_for_ui_verification': True,
            'ui_verification': ui,
            'temporary_debug_port_closed': True,
        }
        write('final-audit.json', result)
        record['status'] = 'verified'
        write('deployment.json', record)
        print(json.dumps(result, ensure_ascii=False))
    else:
        raise ValueError(action)
