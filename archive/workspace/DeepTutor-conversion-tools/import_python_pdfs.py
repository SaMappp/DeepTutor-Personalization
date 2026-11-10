# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import json,sys,time,subprocess,argparse,hashlib
import httpx
ROOT=Path(__file__).resolve().parent
ACADEMIC=ROOT.parent
HOME=ACADEMIC/'DeepTutor'
SUPPORT=ACADEMIC/'DeepTutor-learning-support'
statefile=ROOT/'verification/pdf-reading-import.json'
state=json.loads(statefile.read_text(encoding='utf-8')) if statefile.exists() else {'targets':{}}
previous=json.loads((SUPPORT/'verification/course-import-state.json').read_text(encoding='utf-8'))
client=httpx.Client(trust_env=False,timeout=180)
def call(base,path,method='GET',**kw):
 r=client.request(method,base+path,**kw);r.raise_for_status();return r.json()
def scope(path,w):return path+('&' if '?' in path else '?')+'dt_workspace='+w
def save():statefile.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
def selection(base):
 llm=call(base,'/api/settings/catalog')['catalog']['services']['llm']
 p=next(x for x in llm['profiles'] if x['id']==llm['active_profile_id']);m=next(x for x in p['models'] if x['id']==llm['active_model_id'])
 return {'profile':p['id'],'model':m['model'],'reasoning_effort':m.get('reasoning_effort')}
def snapshot(base,course):
 w=course['workspace_id'];old=course['reading_collection_id']
 value={'model':selection(base),'old_collection':call(base,scope('/api/reading/workspaces/'+old,w)),'old_materials':{},'knowledge_bases':call(base,scope('/api/knowledge-bases',w))}
 for m in course['reading_materials']:
  mid=m['material_id'];value['old_materials'][mid]={}
  for endpoint in ['position','annotations','bookmarks']:
   value['old_materials'][mid][endpoint]=call(base,scope('/api/reading/materials/'+mid+'/'+endpoint,w))
 return value
ap=argparse.ArgumentParser();ap.add_argument('files',nargs='*');a=ap.parse_args()
if a.files:files=[Path(x).resolve(strict=True) for x in a.files]
else:
 from convert_materials import pick
 files=[Path(x).resolve(strict=True) for x in pick('pdf')]
if not files:sys.exit('未选择 PDF，已取消。')
if not all(f.suffix.lower()=='.pdf' for f in files):sys.exit('只接受 PDF。')
started=False
try:
 try:call('http://127.0.0.1:8001','/health/ready')
 except Exception:
  import os
  env=os.environ.copy();env['DEEPTUTOR_HOME']=str(HOME);env['PYTHONUTF8']='1'
  subprocess.run([str(HOME/'.venv/Scripts/deeptutor.exe'),'start','--detach','--no-browser'],env=env,check=True)
  started=True
  for _ in range(90):
   try:
    if call('http://127.0.0.1:8001','/health/ready').get('status')=='ready':break
   except Exception:pass
   time.sleep(1)
  else:raise RuntimeError('CLI/PyPI service did not become ready')
 for label,base in [('desktop','http://127.0.0.1:18801'),('cli','http://127.0.0.1:8001')]:
  course=previous['targets'][label]['courses']['python'];w=course['workspace_id']
  before_path=ROOT/'verification'/('before-reading-import-'+label+'.json')
  if not before_path.exists():before_path.write_text(json.dumps(snapshot(base,course),ensure_ascii=False,indent=2),encoding='utf-8')
  selected=selection(base);assert selected['model']=='gpt-6.1-sol' and selected['reasoning_effort']=='high',selected
  row=state['targets'].setdefault(label,{'workspace_id':w,'base':base,'materials':[]})
  for f in files:
   with f.open('rb') as h:m=call(base,scope('/api/reading/materials?reuse=true',w),'POST',files={'file':(f.name,h,'application/pdf')})
   assert m['unit_count']>0 and m['has_raw_view'] and m['render_mode']=='pdf',m
   if m['material_id'] not in [x['material_id'] for x in row['materials']]:
    row['materials'].append({'source_pdf':str(f),**{k:m.get(k) for k in ['material_id','filename','unit_count','render_mode','has_raw_view','char_count']}});save()
   print(label,'PDF ready',f.name,m['unit_count'],flush=True)
  title='英文原版 PDF 课件 · Computer Programming'
  collections=call(base,scope('/api/reading/workspaces',w))['workspaces']
  collection=next((x for x in collections if x['title']==title),None)
  if not collection:collection=call(base,scope('/api/reading/workspaces',w),'POST',json={'title':title,'description':'由原始英文 Lecture01–06 PPTX 转出的完整页面 PDF。保留代码、图片、流程图及可搜索文字；Lecture03 包含原 PPT 的隐藏第45页。旧 PPT 阅读组及知识库保留。','material_ids':[x['material_id'] for x in row['materials']]})['workspace']
  else:
   known={x['material']['material_id'] for x in collection['tabs']}
   for m in row['materials']:
    if m['material_id'] not in known:call(base,scope('/api/reading/workspaces/'+collection['workspace_id']+'/materials',w),'POST',json={'material_id':m['material_id'],'make_active':False})
  row['collection_id']=collection['workspace_id'];row['url']=('http://127.0.0.1:18802' if label=='desktop' else 'http://127.0.0.1:3782')+'/learning/reading/'+row['collection_id']+'?dt_workspace='+w
  save()
  before=json.loads(before_path.read_text(encoding='utf-8'));after=snapshot(base,course)
  def stable(v):
   if isinstance(v,dict):return {k:stable(x) for k,x in v.items() if k!='updated_at'}
   if isinstance(v,list):return [stable(x) for x in v]
   return v
  assert stable(before)==stable(after), 'Existing reader data, KB metadata or model selection changed; inspect before continuing.'
  row['old_reading_and_kb_unchanged']=True;row['model']=selected;save()
  print(label,'collection',row['collection_id'],'old data preserved',flush=True)
finally:
 if started:
  if call('http://127.0.0.1:8001','/api/system/runtime').get('owner_turn_count',0)==0:
   subprocess.run([str(HOME/'.venv/Scripts/python.exe'),str(HOME/'stop_deeptutor.py')],check=True)
  else:print('CLI/PyPI 当前有任务，已保留运行，避免中断。')
 client.close()
