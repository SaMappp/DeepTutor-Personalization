# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Deploy only the reviewed reading patch into the verified desktop runtime."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil
import httpx

ROOT=Path(__file__).resolve().parent
ACTUAL=Path(r'C:\Users\YOUR_NAME\AppData\Local\Open DeepTutor\runtimes\1.7.1-f7aed0744-x64\core')
BASE='http://127.0.0.1:18801'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(client):
    def get(path,workspace=''):
        r=client.get(BASE+path,params={'dt_workspace':workspace} if workspace else {});r.raise_for_status();return r.json()
    runtime=get('/api/system/runtime')
    if runtime['owner_turn_count']!=0:raise RuntimeError('桌面版有正在执行的对话，暂不部署或重启，请等它完成。')
    workspaces=get('/api/settings/workspace/registrations')
    llm=get('/api/settings/catalog')['catalog']['services']['llm']
    p=next(x for x in llm['profiles'] if x['id']==llm['active_profile_id'])
    m=next(x for x in p['models'] if x['id']==llm['active_model_id'])
    result={'runtime':runtime,'active_runtime':json.loads(Path(r'C:\Users\YOUR_NAME\AppData\Local\Open DeepTutor\active.json').read_text()),
            'model':{'profile_id':p['id'],'model':m['model'],'reasoning_effort':m.get('reasoning_effort')},'workspaces':{}}
    for workspace in workspaces['workspaces']:
        if workspace.get('kind')=='system' or workspace.get('archived'):
            continue
        wid=workspace['workspace_id'];materials=get('/api/reading/materials',wid)
        result['workspaces'][wid]={'name':workspace['display_name'],'path':workspace['path'],
            'collections':get('/api/reading/workspaces',wid),'materials':{}}
        for material in materials:
            mid=material['material_id']
            result['workspaces'][wid]['materials'][mid]={'info':material,**{
                endpoint:get(f'/api/reading/materials/{mid}/{endpoint}',wid)
                for endpoint in ['position','annotations','bookmarks']}}
    return result


def main():
    with httpx.Client(trust_env=False,timeout=30) as client:
        before=snapshot(client)
        path=ROOT/'verification'/'desktop-before.json';path.parent.mkdir(exist_ok=True)
        if not path.exists():path.write_text(json.dumps(before,ensure_ascii=False,indent=2),encoding='utf-8')
        files=list((ROOT/'patch').rglob('*.py'))
        files=[p for p in files if '__pycache__' not in str(p)]
        backup=ROOT/'backups'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        rows=[]
        for source in files:
            relative=source.relative_to(ROOT/'patch');target=ACTUAL/relative
            old_hash=sha(target) if target.exists() else None
            if target.exists():
                saved=backup/relative;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
            rows.append({'file':str(relative),'before_sha256':old_hash,'after_sha256':sha(target)})
        record={'actual_core':str(ACTUAL),'actual_web':r'C:\Users\YOUR_NAME\AppData\Local\Open DeepTutor\cache\1.7.1-f7aed0744-x64\web',
                'runtime_home':r'C:\Users\YOUR_NAME\AppData\Local\Open DeepTutor\workspace','backup':str(backup),'files':rows,
                'model_before':before['model'],'frontend_rebuild_required':False}
        (ROOT/'deployment.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(record,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
