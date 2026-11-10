# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Read-only closure audit. Never launches OCR or an LLM request."""
from pathlib import Path
from collections import Counter
import datetime
import hashlib
import json
import socket
import subprocess
import sys

import httpx

ROOT = Path(__file__).resolve().parent
CORE = Path(r'C:\Users\YOUR_NAME\AppData\Local\Open DeepTutor\runtimes\1.7.1-f7aed0744-x64\core')
sys.path.insert(0, str(CORE))
from deeptutor.reading import native_ocr
from deploy import snapshot
from verify_live import stable, main as verify_live


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == '__main__':
    verify_live()
    before = json.loads((ROOT / 'verification/resume-before.json').read_text(encoding='utf-8'))
    with httpx.Client(trust_env=False, timeout=20) as client:
        after = snapshot(client)
        assert client.get('http://127.0.0.1:18801/health/ready').status_code == 200
        assert client.get('http://127.0.0.1:18802/chat').status_code == 200
    assert stable(before['workspaces']) == stable(after['workspaces']), 'Reading data changed during final restart'
    assert before['model'] == after['model']
    assert before['active_runtime'] == after['active_runtime']
    log = ROOT / 'logs/page-ocr.jsonl'
    assert sha(log) == before['ocr_log_sha256'], 'Unexpected OCR/preparation activity during closure'
    with socket.socket() as probe:
        probe.settimeout(1)
        assert probe.connect_ex(('127.0.0.1', 19473)) != 0, 'Temporary debugging port still open'

    shell = json.loads((ROOT / 'desktop-layout-fix.json').read_text(encoding='utf-8'))
    assert sha(Path(shell['target'])) == shell['after_sha256']
    node = CORE.parent / 'node/node.exe'
    subprocess.run([str(node), '--check', shell['target']], check=True, capture_output=True)
    processes = json.loads(subprocess.check_output([
        'powershell.exe', '-NoProfile', '-Command',
        "Get-CimInstance Win32_Process -Filter \"Name='Open DeepTutor.exe'\" | "
        "Where-Object {$_.CommandLine -notlike '*--type=*'} | "
        "Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress"
    ], encoding='utf-8'))
    if isinstance(processes, dict):
        processes = [processes]
    assert len(processes) == 1
    assert '--remote-debugging' not in processes[0]['CommandLine']

    source = Path(r'authorized-source.pdf')
    searchable = ROOT.parent / 'Course materials/Calculus/OCR可搜索教材/高等数学（上册）天津大学_OCR可搜索版.pdf'
    source_hash = '965af5862119fc49e7d63eede9942c0cec653fb360bbbd9fb19ec8b06aae4ae6'
    assert sha(source) == source_hash
    assert sha(searchable) == 'e353bbbe43b4e7f9d30e21730bea28dbda3f89f236aeaffab40a471da582449a'
    cfg = native_ocr.configuration()
    shared_page = native_ocr.cache_paths(source_hash, cfg['engine']['id'], 167)[1]
    legacy_pages = list(shared_page.parent.glob('*.json'))
    assert len(legacy_pages) == 349
    page167 = native_ocr.read_cache(shared_page, source_hash, cfg['engine']['id'], 167)
    assert page167 and len(page167) > 100
    assert sha(log) == before['ocr_log_sha256']

    events = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()]
    starts = Counter((row['source_sha256'], row['page']) for row in events if row['action'] == 'ocr_start')
    result = {
        'checked_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'complete',
        'backend_and_frontend_ready': True,
        'desktop_process': processes[0],
        'normal_start_without_debug_flags': True,
        'temporary_debug_port_19473_closed': True,
        'native_core_patch_hashes_verified': True,
        'desktop_layout_restore_fix_verified_in_real_window': True,
        'desktop_layout_syntax_check_passed': True,
        'desktop_layout_fix': shell,
        'desktop_normal_window_screenshot': str(ROOT / 'verification/desktop-normal-start-verified.png'),
        'reading_data_unchanged_during_closure': True,
        'original_reading_data_matches_predeployment': True,
        'model_preserved': after['model'],
        'runtime_preserved': after['active_runtime']['runtimeId'],
        'no_ocr_or_model_turns_during_closure': True,
        'ocr_log_sha256': sha(log),
        'native_ui_total_ocr_calls': [
            {'source_sha256': source_hash, 'page': page, 'count': count}
            for (source_hash, page), count in starts.items()
        ],
        'original_calculus_pdf_hash_preserved': True,
        'previous_searchable_pdf_hash_preserved': True,
        'previous_shared_cache_pages_preserved': len(legacy_pages),
        'previous_page167_cache_readable': True,
        'previous_page167_cached_characters': len(page167),
        'whole_calculus_ocr_rerun': False,
        'verification_scope': 'Prior actual desktop reading UI evidence rechecked; fresh normal startup and restore verified; no new OCR run.',
    }
    (ROOT / 'verification/resume-final-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False), flush=True)
