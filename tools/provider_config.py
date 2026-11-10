# SPDX-License-Identifier: Apache-2.0
"""Import an explicitly authorized custom API profile without changing LLM defaults."""
import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
from urllib.parse import urlparse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def local_url(value):
    parsed = urlparse(value)
    if parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost', '::1'} or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {'', '/'}:
        raise ValueError('Target must be an explicit loopback HTTP service origin.')
    return value.rstrip('/')


def call(base, path, payload=None):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    req = urllib.request.Request(local_url(base) + path, headers={'Content-Type': 'application/json'},
                                 data=json.dumps(payload).encode() if payload is not None else None)
    with opener.open(req, timeout=30) as response:
        return json.load(response)


def selection(catalog):
    bucket = catalog['services']['llm']
    return bucket['active_profile_id'], bucket['active_model_id']


def configure(config, apply=False):
    provider = urlparse(config['base_url'])
    if provider.scheme != 'https' or not provider.hostname or provider.username or provider.password or provider.query or provider.fragment:
        raise ValueError('Provider base_url must be an HTTPS endpoint without embedded credentials.')
    if not config['profile_id'] or not config['models'] or not config['targets']:
        raise ValueError('Explicit profile, model list and targets are required.')
    model_ids = [m['id'] for m in config['models']]
    if len(model_ids) != len(set(model_ids)) or any(not m.get('model') or not m.get('id') for m in config['models']):
        raise ValueError('Models require unique ids and explicit API model names.')
    env_name = config['api_key_env']
    if not env_name or not env_name.replace('_', '').isalnum():
        raise ValueError('api_key_env must name a process environment variable.')
    credential = os.environ.get(env_name)
    if not credential:
        raise ValueError('Set the named credential environment variable; do not paste keys into configuration.')
    targets = []
    for target in config['targets']:
        base = local_url(target['api'])
        runtime = call(base, '/api/system/runtime')
        if runtime.get('owner_turn_count', 0):
            raise RuntimeError('A target has an active learning turn; no settings were changed.')
        before = call(base, '/api/settings/catalog')['catalog']
        if config['profile_id'] == selection(before)[0]:
            raise ValueError('Use a separate profile id; replacing the active default provider is not supported.')
        settings = Path(target['settings_dir']).expanduser().resolve()
        if not (settings / 'model_catalog.json').is_file():
            raise ValueError('Each target needs its own existing private settings directory.')
        targets.append((target, base, settings, before))
    if not apply:
        return {'checked_targets': len(targets), 'models': len(model_ids), 'writes': 0}
    profile = {'id': config['profile_id'], 'name': config['name'], 'binding': 'custom',
               'base_url': config['base_url'].rstrip('/'), 'api_key': credential,
               'api_format': 'openai_chat', 'wire_api': 'chat_completions', 'models': copy.deepcopy(config['models'])}
    for target, base, settings, before in targets:
        # Recheck immediately before each mutation. Backups contain secrets and remain private.
        if call(base, '/api/system/runtime').get('owner_turn_count', 0):
            raise RuntimeError('A learning turn started; remaining targets were not changed.')
        current = call(base, '/api/settings/catalog')['catalog']
        if selection(current) != selection(before):
            raise RuntimeError('Default selection changed during preflight; retry after reviewing settings.')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        folder = settings / 'backups' / ('explicit-provider-' + stamp)
        folder.mkdir(parents=True, exist_ok=False)
        shutil.copy2(settings / 'model_catalog.json', folder / 'model_catalog.json')
        after = call(base, '/api/settings/apply/provider', {'service': 'llm', 'profile': profile, 'activate': False})['catalog']
        if selection(after) != selection(before):
            raise RuntimeError('Server unexpectedly changed the default. Review the private backup before continuing.')
    return {'configured_targets': len(targets), 'models': len(model_ids), 'default_selection_preserved': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('--apply', action='store_true', help='Write profiles; default is a read-only preflight.')
    args = parser.parse_args()
    result = configure(json.loads(args.config.read_text(encoding='utf-8-sig')), args.apply)
    print(json.dumps(result))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Provider responses, config contents and exception strings may contain secrets.
        print('Provider configuration failed (' + type(exc).__name__ + '); no credentials were printed.', file=sys.stderr)
        raise SystemExit(1)
