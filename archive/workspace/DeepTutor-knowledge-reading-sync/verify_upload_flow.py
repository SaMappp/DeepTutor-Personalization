# SPDX-License-Identifier: Apache-2.0
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import httpx,json,time,hashlib
ROOT=Path(__file__).resolve().parent
c=httpx.Client(trust_env=False,timeout=180)
report={}
def call(base,path,method='GET',workspace=None,**kw):
 r=c.request(method,base+path,params={'dt_workspace':workspace} if workspace else None,**kw)
 if not r.is_success:raise RuntimeError(str(r.status_code)+' '+r.text[:600])
 return r.json()
for label,base in [('desktop','http://127.0.0.1:18801'),('cli','http://127.0.0.1:8001')]:
 folder=ROOT/'verification'/('flow-'+label);folder.mkdir(exist_ok=True)
 registered=call(base,'/api/settings/workspace/registrations')['workspaces']
 existing=next((w for w in registered if Path(w['path'])==folder),None)
 w=existing or call(base,'/api/settings/workspace/registrations','POST',json={'name':'资料同步功能验收（非课程）','path':str(folder),'resources':{'skills':None,'mcp':None,'knowledge_bases':None}})['workspace']
 wid=w['workspace_id'];name='Knowledge-Reading-Sync-Verification'
 initial='# 创建知识库时同步验证\n\nThis document tests the original knowledge-center upload path.\nA parameter is a placeholder; an argument supplies a value.\n此文档仅用于验证同步，不属于课程资料。\n'.encode()
 kbs=call(base,'/api/knowledge-bases',workspace=wid)
 if not any(k['name']==name for k in kbs):
  created=call(base,'/api/knowledge-bases','POST',workspace=wid,data={'name':name,'rag_provider':'llamaindex','storage_workspace_id':wid,'embedding_model':json.dumps({'profile_id':'embedding-profile-local-learning','model_id':'embedding-model-local-jina-zh'})},files={'files':('创建时同步验证.md',initial,'text/markdown')})
 else:created={'reused_test_kb':True}
 # Observe catalog SQLite immediately, before any reading route can backfill.
 db=folder/'.deeptutor/data/user/workspace/reading/_catalog.sqlite3'
 import sqlite3
 if not db.exists():
  candidates=list(folder.rglob('_catalog.sqlite3'));assert candidates,candidates;db=candidates[0]
 mid=hashlib.sha256(initial).hexdigest()[:16]
 with sqlite3.connect(db) as con:
  assert con.execute('SELECT COUNT(*) FROM reading_materials WHERE material_id=?',(mid,)).fetchone()[0]==1,'Creation hook did not sync'
 for _ in range(90):
  k=call(base,'/api/knowledge-bases',workspace=wid)[0]
  if k.get('status')=='ready':break
  if k.get('status')=='failed':raise RuntimeError('Test indexing failed')
  time.sleep(1)
 else:raise RuntimeError('Test KB not ready')
 additional='# 追加知识中心文档验证\n\nThe reading collection must receive a new document immediately after upload.\n同一份文档重复上传不能产生重复资料。\n'.encode()
 uploaded=call(base,'/api/knowledge-bases/'+name+'/upload','POST',workspace=wid,data={'image_analysis':'false'},files={'files':('追加同步验证.md',additional,'text/markdown')})
 amid=hashlib.sha256(additional).hexdigest()[:16]
 with sqlite3.connect(db) as con:
  assert con.execute('SELECT COUNT(*) FROM reading_materials WHERE material_id=?',(amid,)).fetchone()[0]==1,'Append upload hook did not sync'
  before_count=con.execute('SELECT COUNT(*) FROM reading_materials').fetchone()[0]
  before_tabs=con.execute('SELECT COUNT(*) FROM reading_workspace_materials').fetchone()[0]
 # Wait for the append lock before repeating the same content in a subfolder.
 for _ in range(90):
  if call(base,'/api/knowledge-bases',workspace=wid)[0].get('status')=='ready':break
  time.sleep(1)
 duplicate=call(base,'/api/knowledge-bases/'+name+'/upload','POST',workspace=wid,data={'image_analysis':'false','dest_subdir':'中文 子目录'},files={'files':('追加同步验证.md',additional,'text/markdown')})
 with sqlite3.connect(db) as con:
  assert con.execute('SELECT COUNT(*) FROM reading_materials').fetchone()[0]==before_count==2
  assert con.execute('SELECT COUNT(*) FROM reading_workspace_materials').fetchone()[0]==before_tabs==2
 collections=call(base,'/api/reading/workspaces',workspace=wid)['workspaces'];assert len(collections)==1 and len(collections[0]['tabs'])==2
 collection=collections[0]
 report[label]={'workspace_id':wid,'folder':str(folder),'collection_id':collection['workspace_id'],'collection_title':collection['title'],'create_upload_hook_verified_without_reader_backfill':True,'append_upload_hook_verified_without_reader_backfill':True,'duplicate_subfolder_upload_deduplicated':True,'material_count':2,'materials':[mid,amid],'db':str(db),'created':created,'uploaded':uploaded,'duplicate':duplicate,'reader_url':('http://127.0.0.1:18802' if label=='desktop' else 'http://127.0.0.1:3782')+'/learning/reading/'+collection['workspace_id']+'?dt_workspace='+wid}
 (ROOT/'verification/live-upload-flow.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(label,'create/add/repeat sync verified',report[label]['reader_url'],flush=True)
print('Both actual API upload paths passed. Test workspaces will be archived after UI inspection.')
