# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Add local study services through the official incremental settings API."""
from pathlib import Path
import json,shutil,time,requests
ROOT=Path(__file__).resolve().parent
SUPPORT=Path(r"C:\Users\YOUR_NAME\Documents\ChatGPT\Academic learning\DeepTutor-learning-support")
s=requests.Session();s.trust_env=False
key=(SUPPORT/"private/service-key.txt").read_text().strip()
targets=[
 ("desktop","http://127.0.0.1:18801",Path.home()/"AppData/Local/Open DeepTutor/workspace/data/user/settings"),
 ("cli","http://127.0.0.1:8001",Path.home()/"Documents/ChatGPT/Academic learning/DeepTutor/data/user/settings")]
def call(base,path,payload=None):
    r=s.get(base+path,timeout=30) if payload is None else s.post(base+path,json=payload,timeout=30)
    r.raise_for_status();return r.json()
def default(c):
    b=c["services"]["llm"];p=next(x for x in b["profiles"] if x["id"]==b["active_profile_id"]);m=next(x for x in p["models"] if x["id"]==b["active_model_id"])
    return (p["id"],m["id"],m["model"],m.get("reasoning_effort"))
profiles=[
("embedding",{"id":"embedding-profile-local-learning","name":"本机中英课件检索（Jina，免API）","binding":"custom","base_url":"http://127.0.0.1:18810/v1/embeddings","api_key":key,"batch_size":10,"models":[{"id":"embedding-model-local-jina-zh","name":"Jina v2 中英双语 · 768维 · 本机","model":"jinaai/jina-embeddings-v2-base-zh","dimension":768,"send_dimensions":False}]},"embedding-model-local-jina-zh"),
("stt",{"id":"stt-profile-local-learning","name":"本机 Whisper 离线转写（免API）","binding":"custom","base_url":"http://127.0.0.1:18810/v1","api_key":key,"models":[{"id":"stt-model-local-whisper-small","name":"Whisper small · 本机CPU · 中英转写","model":"faster-whisper-small","language":"auto"}]},"stt-model-local-whisper-small"),
("tts",{"id":"tts-profile-local-learning","name":"本机语音转接 · Edge 免费在线朗读","binding":"custom","base_url":"http://127.0.0.1:18810/v1","api_key":key,"models":[
 {"id":"tts-model-local-emma","name":"Emma · 英语/中文多语种朗读","model":"edge-tts","voice":"en-US-EmmaMultilingualNeural","response_format":"mp3","speed":1.0,"request_timeout":120},
 {"id":"tts-model-local-sonia","name":"Sonia · 英式英语朗读","model":"edge-tts","voice":"en-GB-SoniaNeural","response_format":"mp3","speed":1.0,"request_timeout":120},
 {"id":"tts-model-local-xiaoxiao","name":"晓晓 · 中文讲解朗读","model":"edge-tts","voice":"zh-CN-XiaoxiaoNeural","response_format":"mp3","speed":1.0,"request_timeout":120}]},"tts-model-local-emma")]
report=[]
# Preflight every target before applying any service profile.
for label,base,settings in targets:
    deadline=time.monotonic()+60
    while True:
        try:
            ready=call(base,"/health/ready")
            if ready.get("status")=="ready": break
        except requests.RequestException:
            pass
        if time.monotonic()>deadline: raise RuntimeError(label+" is not ready; no profiles were applied.")
        time.sleep(1)
for label,base,settings in targets:
    runtime=call(base,"/api/system/runtime")
    if runtime.get("owner_turn_count"): raise RuntimeError(label+" has an active turn; no settings were changed.")
    before=call(base,"/api/settings/catalog")["catalog"]
    original=default(before)
    if original[2:]!=("gpt-6.1-sol","high"): raise RuntimeError("Unexpected default selection. No silent model change allowed.")
    backup=settings/f"model_catalog.json.before-local-learning-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(settings/"model_catalog.json",backup)
    for service,profile,model_id in profiles:
        after=call(base,"/api/settings/apply/provider",{"service":service,"profile":profile,"activate":True,"active_model_id":model_id})["catalog"]
        if default(after)!=original: raise RuntimeError("Default LLM changed unexpectedly; review private backup.")
        print(json.dumps({"target":label,"service":service,"configured":True,"default_unchanged":True},ensure_ascii=False),flush=True)
    report.append({"target":label,"default_model":original[2],"reasoning":original[3],"backup":str(backup),"services":["embedding","stt","tts"]})
(SUPPORT/"verification/configured-services.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
