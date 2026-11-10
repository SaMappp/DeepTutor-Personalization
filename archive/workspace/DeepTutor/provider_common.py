# SPDX-License-Identifier: Apache-2.0
"""Public support for the historical account adapter; explicit targets only."""
import json
import os
from pathlib import Path
import shutil
from datetime import datetime, timezone
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None

def _targets():
    path = os.environ.get('DEEPTUTOR_ACCOUNT_TARGETS_CONFIG')
    if not path: return []
    config = json.loads(Path(path).read_text(encoding='utf-8'))
    from urllib.parse import urlparse
    rows=[]
    for item in config['targets']:
        parsed=urlparse(item['api'])
        if parsed.scheme!='http' or parsed.hostname not in {'localhost','127.0.0.1','::1'} or parsed.username or parsed.password:
            raise RuntimeError('Only explicitly configured loopback targets are supported.')
        rows.append((item['name'],item['api'].rstrip('/'),Path(item['settings_dir'])))
    return rows

TARGETS=_targets()

def request(url,data=None):
    opener=build_opener(ProxyHandler({}),NoRedirect())
    req=Request(url,headers={'Content-Type':'application/json'},data=json.dumps(data).encode() if data is not None else None)
    with opener.open(req,timeout=60) as response:return json.load(response)

def backup(settings):
    folder=settings/'backups'/('account-import-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    folder.mkdir(parents=True,exist_ok=False)
    for name in ['model_catalog.json','settings_draft.json']:
        if (settings/name).is_file():shutil.copy2(settings/name,folder/name)
    return str(folder)
