# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import json,time
import httpx
import pymupdf

ROOT=Path(__file__).resolve().parent
W='REDACTED_WORKSPACE_ID'
path=ROOT/'verification'/'桌面验收_混合教材.pdf'
state=ROOT/'verification'/'ui-state.json'
if state.exists():
    print(state.read_text(encoding='utf-8'))
else:
    with pymupdf.open(ROOT/'verification'/'原生按需OCR验证 混合.pdf') as doc:
        meta=dict(doc.metadata);meta['subject']='desktop-ui-demand-ocr-'+str(time.time());doc.set_metadata(meta);doc.save(path)
    with httpx.Client(trust_env=False,timeout=20) as c:
        r=c.post('http://127.0.0.1:18801/api/reading/workspaces',params={'dt_workspace':W},
                 json={'title':'按页 OCR · 隔离验收','description':'本次原生按需 OCR 功能的隔离验收材料，原有教材和记录不变。','material_ids':[]})
        r.raise_for_status();collection=r.json()['workspace']
    result={'workspace_id':W,'collection_id':collection['workspace_id'],'file':str(path),
            'url':'http://127.0.0.1:18802/learning/reading/'+collection['workspace_id']+'?dt_workspace='+W}
    state.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False),flush=True)
