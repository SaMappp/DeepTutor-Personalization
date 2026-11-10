# SPDX-License-Identifier: Apache-2.0
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import httpx,json,time
R=Path(__file__).resolve().parent;before=json.loads((R/'verification/before.json').read_text(encoding='utf-8'));results={}
c=httpx.Client(trust_env=False,timeout=240)
for label in ['desktop','cli']:
 base=before[label]['base']
 for _ in range(60):
  try:
   if c.get(base+'/health/ready',timeout=3).status_code==200:break
  except Exception:pass
  time.sleep(1)
 results[label]={}
 for wid,workspace in before[label]['workspaces'].items():
  r=c.post(base+'/api/reading/knowledge-sync',params={'dt_workspace':wid});r.raise_for_status();result=r.json();results[label][wid]=result;print(label,workspace['name'],json.dumps(result,ensure_ascii=False),flush=True)
(R/'verification/backfill.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
