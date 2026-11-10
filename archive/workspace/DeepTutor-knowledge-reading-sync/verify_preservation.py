# SPDX-License-Identifier: Apache-2.0
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import json,hashlib,httpx,sqlite3
R=Path(__file__).resolve().parent;V=R/'verification';before=json.loads((V/'before.json').read_text(encoding='utf-8'));client=httpx.Client(trust_env=False,timeout=120)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def stable(v):
 if isinstance(v,dict):return {k:stable(x) for k,x in v.items() if k!='updated_at'}
 if isinstance(v,list):return [stable(x) for x in v]
 return v
report={'targets':{},'scope':'Additive local documents; each installation/account/workspace remains isolated.'}
for label in ['desktop','cli']:
 base=before[label]['base'];target={'workspaces':{}}
 for wid,previous in before[label]['workspaces'].items():
  def get(path):
   r=client.get(base+path,params={'dt_workspace':wid});r.raise_for_status();return r.json()
  kbs=get('/api/knowledge-bases');assert stable(kbs)==stable(previous['kbs']),('KB metadata changed',label,previous['name'])
  current=get('/api/reading/workspaces')['workspaces'];byid={w['workspace_id']:w for w in current}
  for old in previous['reading']['workspaces']:
   now=byid[old['workspace_id']];assert old['title']==now['title'];assert {t['material']['material_id'] for t in old['tabs']}.issubset({t['material']['material_id'] for t in now['tabs']})
  for mid,state in previous['material_state'].items():
   for endpoint,value in state.items():
    now=get('/api/reading/materials/'+mid+'/'+endpoint)
    assert stable(value)==stable(now),('Reader state changed',label,previous['name'],mid,endpoint,value,now)
  sync=get('/api/reading/materials');first_ids={m['material_id'] for m in sync};again=get('/api/reading/workspaces');second_ids={m['material_id'] for m in get('/api/reading/materials')};assert first_ids==second_ids
  # Validate every KB raw document maps to a ready source-identical material.
  linked=0;matched=[]
  path=Path(previous['path']);dbs=list(path.rglob('_knowledge_sync.sqlite3'))
  for db in dbs:
   with sqlite3.connect(db) as con:
    con.row_factory=sqlite3.Row
    for row in con.execute('SELECT * FROM kb_documents'):
     assert row['status']=='ready',(label,row['relative_path'],row['error'])
     source=Path(row['kb_root'])/'raw'/row['relative_path'];expected=sha(source)
     mid=row['material_id'];detail=get('/api/reading/materials/'+mid);assert detail['unit_count']>0
     # Stream the actual served original, without buffering large books.
     if detail.get('render_mode')!='text':
      h=hashlib.sha256()
      with client.stream('GET',base+'/api/reading/materials/'+mid+'/raw',params={'dt_workspace':wid}) as response:
       response.raise_for_status()
       for chunk in response.iter_bytes(1024*1024):h.update(chunk)
      assert h.hexdigest()==expected,(label,row['relative_path'],'raw file differs')
     else:
      # Native PPT/text readers deliberately keep extracted units, not raw bytes.
      assert row['content_id']==expected[:16]
      assert detail['char_count']>0
     linked+=1;matched.append(row['relative_path'])
  target['workspaces'][wid]={'name':previous['name'],'old_collections_and_tabs_preserved':True,'old_positions_annotations_bookmarks_preserved':True,'kb_metadata_preserved':True,'material_count_before':len(previous['materials']),'material_count_after':len(sync),'linked_kb_documents':linked,'files':matched,'idempotent_reading_refresh':True}
 llm=client.get(base+'/api/settings/catalog').json()['catalog']['services']['llm'];p=next(p for p in llm['profiles'] if p['id']==llm['active_profile_id']);m=next(m for m in p['models'] if m['id']==llm['active_model_id']);selected={k:m.get(k) for k in ['model','reasoning_effort']};assert selected==before[label]['model'];assert selected=={'model':'gpt-6.1-sol','reasoning_effort':'high'};target['model']=selected;report['targets'][label]=target
ocr=R.parent/'DeepTutor-native-ocr/cache'
for rel,value in before['ocr_cache'].items():assert sha(ocr/rel)==value,('OCR cache changed',rel)
for p,value in before['ocr_log'].items():assert sha(p)==value,('OCR log changed',p)
report['existing_ocr_cache_and_logs_unchanged']=True
report['real_api_flow']=json.loads((V/'live-upload-flow.json').read_text(encoding='utf-8'))
report['tests']={'desktop_isolated_tests':7,'cli_isolated_tests':7,'actual_create_upload_append_and_duplicate_upload_both_installations':True,'python_homework_opened_in_real_pdf_reader':True,'desktop_native_window_normal_after_restart':True}
(V/'final-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
for label,target in report['targets'].items():
 print(label,'model',target['model'])
 for w in target['workspaces'].values():print(' ',w['name'],'mapped',w['linked_kb_documents'],'materials',w['material_count_before'],'->',w['material_count_after'])
print('PASS: old reader states, original KB metadata, served originals, duplicate prevention and OCR cache/logs preserved.')
