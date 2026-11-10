# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import json,httpx
R=Path(r'C:\Users\YOUR_NAME\Documents\ChatGPT\Academic learning\DeepTutor-conversion-tools');p=R/'verification/pdf-reading-import.json';s=json.loads(p.read_text(encoding='utf-8'));files=[Path(f) for f in json.loads((R/'primary-pdfs.json').read_text(encoding='utf-8'))];c=httpx.Client(trust_env=False,timeout=30)
def call(row,path,method='GET',**kw):
 r=c.request(method,row['base']+path,params={'dt_workspace':row['workspace_id']},**kw);r.raise_for_status();return r.json()
for label,row in s['targets'].items():
 primary=[next(m for m in row['materials'] if m['filename']==f.name) for f in files]
 ids=[m['material_id'] for m in primary];collection=call(row,'/api/reading/workspaces/'+row['collection_id'])['workspace']
 for tab in collection['tabs']:
  m=tab['material']
  if m['material_id'] not in ids:
   assert m['filename']=='ENG2002_Lecture02_Python_Basics_Types_Variables_Operators(1).pdf'
   row['faithful_export_material']=next(x for x in row['materials'] if x['material_id']==m['material_id'])
   call(row,'/api/reading/workspaces/'+row['collection_id']+'/materials/'+m['material_id'],'DELETE')
   assert call(row,'/api/reading/materials/'+m['material_id'])['material_id']==m['material_id']
 call(row,'/api/reading/workspaces/'+row['collection_id']+'/materials/order','PUT',json={'material_ids':ids})
 call(row,'/api/reading/workspaces/'+row['collection_id'],'PATCH',json={'description':'英文 Lecture01–06 完整页面 PDF，374页，可搜索文字。Lecture02 使用仅修复原第65页越界卡片的阅读修正版（忠实导出另存保留）；Lecture03 包含隐藏第45页。旧PPT阅读组、进度、批注及知识库均保留。'})
 row['materials']=primary
 if label=='cli':
  m=primary[2]
  call(row,'/api/reading/workspaces/'+row['collection_id']+'/materials/'+m['material_id']+'/active','PUT')
  if not row.get('verification_session'):
   row['verification_session']=call(row,'/api/reading/workspaces/'+row['collection_id']+'/sessions','POST',json={'title':'PDF阅读验证 · Euclid循环','active_material_id':m['material_id']})['session']
 print(label,'six PDFs ready',row['url'],flush=True)
p.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8')
print('CLI_SESSION_URL=http://127.0.0.1:3782/learning/reading/'+row['collection_id']+'/sessions/'+row['verification_session']['session_id']+'?dt_workspace='+row['workspace_id'])
