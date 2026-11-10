# SPDX-License-Identifier: Apache-2.0
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import json,httpx,hashlib,sqlite3,time
ROOT=Path(__file__).resolve().parent
c=httpx.Client(trust_env=False,timeout=120)
report={}
for label,base in [('desktop','http://127.0.0.1:18801'),('cli','http://127.0.0.1:8001')]:
 for _ in range(60):
  try:
   if c.get(base+'/health/ready').status_code==200:break
  except Exception:pass
  time.sleep(1)
 regs=c.get(base+'/api/settings/workspace/registrations').json()['workspaces'];llm=c.get(base+'/api/settings/catalog').json()['catalog']['services']['llm'];p=next(p for p in llm['profiles'] if p['id']==llm['active_profile_id']);m=next(m for m in p['models'] if m['id']==llm['active_model_id'])
 data={'base':base,'model':{k:m.get(k) for k in ['model','reasoning_effort']},'workspaces':{}}
 for w in regs:
  if w['kind']=='system' or w.get('archived'):continue
  wid=w['workspace_id'];q={'dt_workspace':wid}
  def get(p):
   r=c.get(base+p,params=q);r.raise_for_status();return r.json()
  row={'name':w['display_name'],'path':w['path'],'reading':get('/api/reading/workspaces'),'materials':get('/api/reading/materials'),'kbs':get('/api/knowledge-bases'),'material_state':{}}
  for material in row['materials']:
   mid=material['material_id'];row['material_state'][mid]={ep:get('/api/reading/materials/'+mid+'/'+ep) for ep in ['position','annotations','bookmarks']}
  data['workspaces'][wid]=row
  print(label,w['display_name'],'KBs',len(row['kbs']),'reader',len(row['materials']),flush=True)
 report[label]=data
ocr=ROOT.parent/'DeepTutor-native-ocr/cache';report['ocr_cache']={str(p.relative_to(ocr)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ocr.rglob('*') if p.is_file()};report['ocr_log']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT.parent/'DeepTutor-native-ocr/logs').glob('*') if p.is_file()}
(ROOT/'verification/before.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Baseline saved; OCR cached files',len(report['ocr_cache']))
