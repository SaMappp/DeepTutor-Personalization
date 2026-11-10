# SPDX-License-Identifier: Apache-2.0
"""Check exported source hashes, syntax and patches against a clean upstream tree."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(upstream=None):
    manifest = json.loads((ROOT / 'upstream/manifest.json').read_text(encoding='utf-8'))
    source_count = 0
    for path in ROOT.rglob('*.py'):
        if '.git' not in path.parts:
            ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path.relative_to(ROOT)))
            source_count += 1
    for target in manifest['targets'].values():
        for entry in target['files']:
            assert digest(ROOT / entry['source']) == entry['sha256'], entry['source']
    checked = []
    if upstream is not None:
        upstream = Path(upstream).resolve()
        for name, target in manifest['targets'].items():
            with tempfile.TemporaryDirectory(prefix='deeptutor-patch-check-') as tmp:
                folder = Path(tmp)
                for entry in target['files']:
                    if entry['base_sha256']:
                        original = upstream / entry['path']
                        assert digest(original) == entry['base_sha256'], entry['path']
                        dest = folder / entry['path']
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(original, dest)
                subprocess.run(['git', 'init', '--quiet', str(folder)], check=True)
                patch = str(ROOT / target['patch'])
                subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', '--check', patch], cwd=folder, check=True, capture_output=True)
                subprocess.run(['git', '-c', 'core.autocrlf=false', 'apply', patch], cwd=folder, check=True, capture_output=True)
                for entry in target['files']:
                    assert digest(folder / entry['path']) == entry['sha256'], entry['path']
                checked.append(name)
    result = {'python_sources_parsed': source_count, 'override_hashes_valid': True, 'patch_targets_reproduced': checked}
    print(json.dumps(result))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', type=Path)
    args = parser.parse_args()
    verify(args.upstream)
