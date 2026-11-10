# SPDX-License-Identifier: Apache-2.0
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import ast,json,hashlib,shutil,datetime
ROOT=Path(__file__).resolve().parent
TARGETS={'desktop':Path(r'C:\Users\YOUR_NAME\AppData\Local\Open DeepTutor\runtimes\1.7.1-f7aed0744-x64\core'), 'cli':ROOT.parent/'DeepTutor/.venv/Lib/site-packages'}
def once(s,old,new):
 assert s.count(old)==1,('Unexpected patch anchor',old[:100],s.count(old))
 return s.replace(old,new,1)
changes=[]
for label,core in TARGETS.items():
 paths=['deeptutor/api/routers/reading.py','deeptutor/api/routers/knowledge.py','deeptutor/knowledge/initializer.py','deeptutor/knowledge/add_documents.py']
 for rel in paths:
  target=core/rel;s=target.read_text(encoding='utf-8-sig');before=hashlib.sha256(target.read_bytes()).hexdigest()
  if rel.endswith('routers/knowledge.py'):
   s=once(s,'    return uploaded_files, uploaded_file_paths','    # Local additive bridge: reading receives the same saved original files.\n    from deeptutor.reading.knowledge_sync import sync_saved_documents\n\n    sync_saved_documents(target_dir)\n    return uploaded_files, uploaded_file_paths')
  elif rel.endswith('initializer.py'):
   s=once(s,'        return copied_files','        from deeptutor.reading.knowledge_sync import sync_saved_documents\n\n        sync_saved_documents(self.raw_dir)\n        return copied_files')
  elif rel.endswith('add_documents.py'):
   s=once(s,'        return files_to_process','        from deeptutor.reading.knowledge_sync import sync_saved_documents\n\n        sync_saved_documents(self.raw_dir)\n        return files_to_process')
  else:
   helper='''async def _sync_knowledge_for_reading(*, force: bool = False) -> dict[str, Any]:
    from deeptutor.modules.catalog import module_enabled
    if not module_enabled("knowledge"):
        return {"knowledge_bases": []}
    from deeptutor.reading.knowledge_sync import sync_visible_knowledge
    return await asyncio.to_thread(sync_visible_knowledge, force=force)


@router.post("/knowledge-sync")
async def reconcile_knowledge_documents() -> dict[str, Any]:
    """Retry missing KB documents without rebuilding indexes or changing old reader data."""
    return await _sync_knowledge_for_reading(force=True)


'''
   s=once(s,'def _new_material_id() -> str:',helper+'def _new_material_id() -> str:')
   s=once(s,'    catalog = _catalog()\n    store = _store()\n    try:\n        for manifest in store.list_materials():','    await _sync_knowledge_for_reading()\n    catalog = _catalog()\n    store = _store()\n    try:\n        for manifest in store.list_materials():')
   s=once(s,'        rows = _catalog().list_workspaces(search=search)','        await _sync_knowledge_for_reading()\n        rows = _catalog().list_workspaces(search=search)')
   start=s.index('async def list_workspace_index()');end=s.index('@router.post("/workspaces"',start);chunk=s[start:end]
   chunk=once(chunk,'    try:\n        return {','    try:\n        await _sync_knowledge_for_reading()\n        return {');s=s[:start]+chunk+s[end:]
   s=once(s,'async def list_materials() -> list[MaterialInfo]:\n    store = _store()','async def list_materials() -> list[MaterialInfo]:\n    await _sync_knowledge_for_reading()\n    store = _store()')
  ast.parse(s);staged=ROOT/'staged'/label/rel;staged.parent.mkdir(parents=True,exist_ok=True);staged.write_text(s,encoding='utf-8');changes.append({'label':label,'target':str(target),'staged':str(staged),'before_sha256':before})
 source=ROOT/'patch/knowledge_sync.py';ast.parse(source.read_text(encoding='utf-8-sig'));changes.append({'label':label,'target':str(core/'deeptutor/reading/knowledge_sync.py'),'staged':str(source),'before_sha256':None})
(ROOT/'prepared-patches.json').write_text(json.dumps(changes,indent=2),encoding='utf-8');print('Prepared and syntax checked',len(changes),'patch files; production unchanged')
