# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import json,hashlib,re,httpx
import pymupdf as f
R=Path(__file__).resolve().parent;V=R/'verification';files=[Path(p) for p in json.loads((R/'primary-pdfs.json').read_text(encoding='utf-8'))];audit=[]
for p in files:
 d=f.open(p);bad=[];chars=[];sizes=set();unembedded=set()
 for i,pg in enumerate(d,1):
  text=pg.get_text();chars.append(len(text));sizes.add((round(pg.rect.width,2),round(pg.rect.height,2)))
  if not text.strip() or '\ufffd' in text:bad.append(i)
  for ft in pg.get_fonts():
   if not d.extract_font(ft[0])[3]:unembedded.add(ft[3])
 assert not bad and len(sizes)==1 and min(chars)>0
 audit.append({'pdf':str(p),'pages':len(d),'size_pt':list(sizes)[0],'minimum_chars_per_page':min(chars),'empty_or_replacement_character_pages':bad,'unembedded_fonts':sorted(unembedded),'sha256':hashlib.file_digest(p.open('rb'),'sha256').hexdigest()})
original=f.open(files[1].parent/'ENG2002_Lecture02_Python_Basics_Types_Variables_Operators(1).pdf');fixed=f.open(files[1]);different=[]
for i in range(70):
 if original[i].get_pixmap(matrix=f.Matrix(.5,.5)).samples!=fixed[i].get_pixmap(matrix=f.Matrix(.5,.5)).samples:different.append(i+1)
assert different==[65],different
state=json.loads((V/'pdf-reading-import.json').read_text(encoding='utf-8'));c=httpx.Client(trust_env=False,timeout=45);targets={}
def stable(v):
 if isinstance(v,dict):return {k:stable(x) for k,x in v.items() if k!='updated_at'}
 if isinstance(v,list):return [stable(x) for x in v]
 return v
for label,row in state['targets'].items():
 def get(path):
  rr=c.get(row['base']+path,params={'dt_workspace':row['workspace_id']});rr.raise_for_status();return rr.json()
 collection=get('/api/reading/workspaces/'+row['collection_id'])['workspace'];assert len(collection['tabs'])==6
 for m in row['materials']:
  rr=c.get(row['base']+'/api/reading/materials/'+m['material_id']+'/raw',params={'dt_workspace':row['workspace_id']});rr.raise_for_status();assert hashlib.sha256(rr.content).hexdigest()==next(x['sha256'] for x in audit if Path(x['pdf']).name==m['filename'])
 before=json.loads((V/('before-reading-import-'+label+'.json')).read_text(encoding='utf-8'))
 oldid=before['old_collection']['workspace']['workspace_id'];assert stable(before['old_collection'])==stable(get('/api/reading/workspaces/'+oldid))
 assert stable(before['knowledge_bases'])==stable(get('/api/knowledge-bases'))
 for mid,values in before['old_materials'].items():
  for ep,value in values.items():assert stable(value)==stable(get('/api/reading/materials/'+mid+'/'+ep))
 llm=c.get(row['base']+'/api/settings/catalog').json()['catalog']['services']['llm'];profile=next(p for p in llm['profiles'] if p['id']==llm['active_profile_id']);m=next(m for m in profile['models'] if m['id']==llm['active_model_id']);assert m['model']=='gpt-6.1-sol' and m['reasoning_effort']=='high'
 targets[label]={'six_pdfs_ready':True,'raw_pdf_hashes_match':True,'old_ppt_reading_progress_annotations_bookmarks_unchanged':True,'existing_kb_metadata_unchanged':True,'default_model':m['model'],'reasoning_effort':m['reasoning_effort'],'owner_turn_count':get('/api/system/runtime')['owner_turn_count']}
report={'pdfs':audit,'total_pages':sum(x['pages'] for x in audit),'lecture02_changed_rendered_pages':different,'targets':targets,'visual_review':{'all_page_contact_sheets':True,'full_resolution_pages':{'1':[6,9,13],'2':[8,28,44,65],'3':[4,45],'4':[11,23,43],'5':[16,31],'6':[13,58]}},'reader_qa':{'desktop':{'request':'parameter versus argument, Lecture04','page':11,'read_material':True,'reader_goto':True,'clicked_citation_after_returning_to_page1':True},'cli':{'request':'Euclid loop trace 48 and18, Lecture03','page':45,'read_material':True,'reader_goto':True,'clicked_citation_after_returning_to_page1':True}},'limitations':['Static PDF does not retain animations or interactive multimedia.','Only representative pages were reviewed at full resolution; no complete pixel comparison against PowerPoint.','Lecture02 page65 uses a clearly labelled layout repair; faithful export retained.']}
(V/'final-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False,indent=2))
