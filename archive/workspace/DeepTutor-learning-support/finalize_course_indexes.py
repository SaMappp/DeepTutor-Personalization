# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import requests,json,time,urllib.parse
root=Path(__file__).resolve().parent
state_file=root/"verification/course-import-state.json"
state=json.loads(state_file.read_text(encoding="utf-8"))
s=requests.Session();s.trust_env=False
def call(base,path,method="GET",**kw):
    r=s.request(method,base+path,timeout=30,**kw);r.raise_for_status();return r.json()
pending=[(label,t,slug,row) for label,t in state["targets"].items() for slug,row in t["courses"].items() if row.get("kb_task")]
deadline=time.monotonic()+1200
last={}
while pending:
    remaining=[]
    for label,target,slug,row in pending:
        key=(label,slug)
        p=call(target["base"],"/api/knowledge-bases/"+urllib.parse.quote(row["kb_task"]["id"],safe="")+"/progress",params={"dt_workspace":row["workspace_id"]})
        stage=p.get("stage","")
        if stage=="error": raise RuntimeError(label+"/"+slug+": "+str(p.get("error") or p.get("message")))
        if stage!="completed": remaining.append((label,target,slug,row))
        text=(stage,p.get("message"))
        if last.get(key)!=text:
            print(json.dumps({"target":label,"course":slug,"stage":stage,"message":p.get("message")},ensure_ascii=False),flush=True)
            last[key]=text
    if not remaining:break
    if time.monotonic()>deadline: raise RuntimeError("Indexing is still running; existing imported sources were preserved.")
    pending=remaining;time.sleep(10)
for label,target in state["targets"].items():
    for slug,row in target["courses"].items():
        if not row.get("kb_task"):continue
        base=target["base"];ws=row["workspace_id"];kb_id=row["kb_task"]["id"]
        items=call(base,"/api/knowledge-bases",params={"dt_workspace":ws})
        kb=next(x for x in items if x["name"]==row["kb_name"] and Path(x["path"]).resolve().is_relative_to(Path(row["path"]).resolve()))
        row["kb_info"]={k:kb.get(k) for k in ("id","name","path","status","statistics")}
        r=call(base,"/api/settings/workspace/registrations/"+ws,"PATCH",
               json={"resources":{"skills":None,"mcp":None,"knowledge_bases":[kb_id]}})["workspace"]
        assert r.get("resources",{}).get("knowledge_bases")==[kb_id]
        row["knowledge_resource_assignment"]=[kb_id]
        print(json.dumps({"target":label,"course":slug,"statistics":kb.get("statistics"),"scope":"only this course KB"},ensure_ascii=False),flush=True)
state_file.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
print("All four independent indexes completed; course resource scopes saved.")
