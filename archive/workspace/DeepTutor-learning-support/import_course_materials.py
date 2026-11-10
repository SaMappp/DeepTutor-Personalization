# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Import only the audited original-English lectures into independent course workspaces."""
from pathlib import Path
import json,requests,time,hashlib
SUPPORT=Path(__file__).resolve().parent
BASES=[("desktop","http://127.0.0.1:18801"),("cli","http://127.0.0.1:8001")]
ACADEMIC=SUPPORT.parent
s=requests.Session();s.trust_env=False
sources=json.loads((SUPPORT/"course-source-manifest.json").read_text(encoding="utf-8"))
assert len(sources)==11 and all(x["english_source_verified"] for x in sources)
COMMON="我是计算机专业大一学生，课程全英文授课。中文解释，保留英文术语，最后练习英文作答。优先使用当前课程的原始英文讲义；AI改写的中文课件不作为课程原始依据。区分来源明确内容与辅助解释，标注可核对的位置。不编造考试范围、考试日期或我的掌握程度。先让我尝试，按需逐级提示，再用变式题检查。默认模型保持 GPT-6.1-Sol，high。"
COURSES=[
("linear-algebra","Linear Algebra · 期末备考","Linear Algebra","LA-English-Lectures","核对矩阵维度、定理条件与行变换；计算、概念解释和英文论证分别练习。"),
("python","Computer Programming (Python) · 期末备考","Computer Programming","Python-English-Lectures","先让我预测、设计或编写代码；按本课已介绍的方法辅导；使用正常与边界输入验证，并明确区分静态检查和实际运行。"),
("calculus","Calculus · 期末备考",None,None,"手写材料尚未导入。先依据用户实际提供的题目或材料学习，不编造课程章节。"),
("cet4","CET-4 · 一个月备考",None,None,"以用户提供的真题、原音频、原文和答案为准。先诊断听力、阅读、写作、翻译；隐藏答案后作答，错因分析后再做新题。"),
("ielts","IELTS · 长期积累",None,None,"目前以英语能力积累为主。雅思类别、目标分数和考试日期待用户确定；不把AI反馈当作正式考试成绩。")]
state={"targets":{},"source_manifest":"course-source-manifest.json","excluded":"Chinese rewrites, textbooks, solutions and homework are not imported in this initial lecture set."}
state_file=SUPPORT/"verification/course-import-state.json"
if state_file.exists(): state=json.loads(state_file.read_text(encoding="utf-8"))
def save():
    state_file.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
def call(base,path,method="GET",**kwargs):
    r=s.request(method,base+path,timeout=kwargs.pop("timeout",180),**kwargs)
    if not r.ok: raise RuntimeError(f"{method} {path.split('?')[0]} returned {r.status_code}: {r.text[:250]}")
    return r.json()
def scoped(path,w): return path+("&" if "?" in path else "?")+"dt_workspace="+w
for label,base in BASES:
    if call(base,"/api/system/runtime").get("owner_turn_count"): raise RuntimeError(label+" is busy.")
    state["targets"].setdefault(label,{"base":base,"courses":{}})
    catalog=call(base,"/api/settings/workspace/registrations")
    for slug,title,source_course,kb_name,extra in COURSES:
        row=state["targets"][label]["courses"].setdefault(slug,{})
        path=ACADEMIC/"DeepTutor-study"/label/slug
        path.mkdir(parents=True,exist_ok=True)
        existing=next((w for w in catalog["workspaces"] if w["display_name"]==title),None)
        if existing:
            if Path(existing["path"]).resolve()!=path.resolve(): raise RuntimeError("A same-name user workspace already exists; refusing to overwrite it.")
            w=existing
        else:
            w=call(base,"/api/settings/workspace/registrations","POST",json={"name":title,"path":str(path),"instructions":COMMON+extra,"resources":{"skills":None,"mcp":None,"knowledge_bases":None}})["workspace"]
            catalog["workspaces"].append(w)
        assert w["status"]=="ready"
        ws=w["workspace_id"]
        row.update({"title":title,"workspace_id":ws,"path":str(path)})
        save()
        print(json.dumps({"target":label,"workspace":title,"ready":True},ensure_ascii=False),flush=True)
        if not source_course: continue
        selected=[x for x in sources if x["course"]==source_course]
        row["original_files"]=[x["path"] for x in selected]
        # The KB and the reader are separate official data surfaces.
        kbs=call(base,scoped("/api/knowledge-bases",ws))
        kb=next((x for x in kbs if x["name"]==kb_name),None)
        if not kb and not row.get("kb_task"):
            handles=[]
            try:
                multipart=[]
                for item in selected:
                    p=Path(item["path"]);f=p.open("rb");handles.append(f)
                    multipart.append(("files",(p.name,f,"application/pdf" if p.suffix.lower()==".pdf" else "application/vnd.openxmlformats-officedocument.presentationml.presentation")))
                payload={"name":kb_name,"rag_provider":"llamaindex","storage_workspace_id":ws,
                         "embedding_model":json.dumps({"profile_id":"embedding-profile-local-learning","model_id":"embedding-model-local-jina-zh"})}
                task=call(base,scoped("/api/knowledge-bases",ws),"POST",data=payload,files=multipart)
                row["kb_task"]=task
                print(json.dumps({"target":label,"kb_submitted":kb_name,"response":task},ensure_ascii=False),flush=True)
            finally:
                for f in handles:f.close()
        if kb: row["kb_info"]={k:kb.get(k) for k in ("id","name","status","path")}
        row["kb_name"]=kb_name;save()
        materials=row.setdefault("reading_materials",[])
        known={x["source_path"] for x in materials}
        for item in selected:
            if item["path"] in known:continue
            p=Path(item["path"])
            with p.open("rb") as f:
                m=call(base,scoped("/api/reading/materials?reuse=true",ws),"POST",files={"file":(p.name,f,"application/pdf" if p.suffix.lower()==".pdf" else "application/vnd.openxmlformats-officedocument.presentationml.presentation")})
            if m["unit_count"]<=0: raise RuntimeError("Empty material extraction for "+p.name)
            materials.append({"source_path":str(p),"material_id":m["material_id"],"unit":m["unit"],"unit_count":m["unit_count"],"char_count":m.get("char_count"),"extractor":m.get("extractor")})
            save()
            print(json.dumps({"target":label,"reading_imported":p.name,"units":m["unit_count"]},ensure_ascii=False),flush=True)
        collections=call(base,scoped("/api/reading/workspaces",ws)).get("workspaces",[])
        collection_title="原始英文课件 · "+source_course
        collection=next((x for x in collections if x["title"]==collection_title),None)
        if not collection:
            collection=call(base,scoped("/api/reading/workspaces",ws),"POST",json={"title":collection_title,"description":"仅已核对的英文原始讲课资料；未导入AI中文改写、教材或答案。","material_ids":[x["material_id"] for x in materials]})["workspace"]
        row["reading_collection_id"]=collection["workspace_id"]
        save()
print("Course workspaces, original-English reading collections and KB tasks have been prepared.")
