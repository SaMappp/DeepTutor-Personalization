# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Local OpenAI-compatible learning services; no paid API and no LLM routing."""
from __future__ import annotations
import asyncio, base64, hashlib, io, json, os, re, shutil, subprocess, tempfile, threading, time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parent
os.environ.setdefault("HF_HOME",str(ROOT/"models/huggingface"))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING","1")
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
import psutil
ID="deeptutor-local-learning-support-v1"
EMBED_MODEL="jinaai/jina-embeddings-v2-base-zh"
STT_MODEL="faster-whisper-small"
KEY_FILE=ROOT/"private/service-key.txt"
RUNTIME=ROOT/"runtime"
RUNTIME.mkdir(exist_ok=True)
KEY=KEY_FILE.read_text(encoding="utf-8").strip()
embed_lock=threading.Lock()
speech_lock=threading.Lock()
embed_model=None
speech_model=None
active=0
app_server=None

def get_embedder():
    global embed_model
    if embed_model is None:
        from fastembed import TextEmbedding
        embed_model=TextEmbedding(model_name=EMBED_MODEL,cache_dir=str(ROOT/"models/fastembed"),threads=4,providers=["CPUExecutionProvider"],local_files_only=True)
    return embed_model

def get_transcriber():
    global speech_model
    if speech_model is None:
        from faster_whisper import WhisperModel
        speech_model=WhisperModel("small",device="cpu",compute_type="int8",cpu_threads=4,num_workers=1,download_root=str(ROOT/"models/whisper"),local_files_only=True)
    return speech_model

def owner_present():
    desktop=Path.home()/"Documents/ChatGPT/Academic learning/Open DeepTutor-win32-x64/Open DeepTutor.exe"
    pypi=Path.home()/"Documents/ChatGPT/Academic learning/DeepTutor"
    prefix=str(pypi).casefold()+os.sep
    for p in psutil.process_iter(["exe","cmdline"]):
        try:
            exe=p.info.get("exe") or ""
            if exe.casefold()==str(desktop).casefold(): return True
            command=" ".join(p.info.get("cmdline") or []).casefold()
            if prefix in command and any(k in command for k in ("deeptutor.exe","deeptutor_cli","deeptutor.api.main")): return True
        except (psutil.Error,OSError): pass
    return False

def watch_owners():
    missing=None
    while app_server is not None and not app_server.should_exit:
        if owner_present() or active:
            missing=None
        elif missing is None:
            missing=time.monotonic()
        elif time.monotonic()-missing>120:
            app_server.should_exit=True
            return
        time.sleep(10)

app=FastAPI(title="DeepTutor local learning support",version="1.0",docs_url=None,redoc_url=None)
@app.middleware("http")
async def protect(request:Request,call_next):
    global active
    if request.url.path.startswith("/v1/"):
        import hmac
        if not hmac.compare_digest(request.headers.get("authorization",""),"Bearer "+KEY):
            return JSONResponse({"detail":"Local service authorization required."},status_code=401)
    active+=1
    try: return await call_next(request)
    finally: active-=1

@app.get("/health")
def health():
    return {"service_id":ID,"status":"ready","pid":os.getpid(),"embedding_model":EMBED_MODEL,
            "embedding_loaded":embed_model is not None,"stt_model":STT_MODEL,"stt_loaded":speech_model is not None,
            "bind":"127.0.0.1","port":18810,"billing":"local CPU; Edge speech has no API subscription"}

@app.get("/v1/models")
def models():
    return {"object":"list","data":[{"id":m,"object":"model","owned_by":"local-learning-support"} for m in (EMBED_MODEL,STT_MODEL,"edge-tts")]}

class EmbeddingBody(BaseModel):
    model:str=EMBED_MODEL
    input:Any
    dimensions:int|None=None
    encoding_format:str="float"

@app.post("/v1/embeddings")
def embeddings(body:EmbeddingBody):
    if body.model!=EMBED_MODEL: raise HTTPException(400,"Unknown embedding model.")
    if body.dimensions not in (None,768): raise HTTPException(400,"This embedding model uses 768 dimensions.")
    texts=[body.input] if isinstance(body.input,str) else body.input
    if not isinstance(texts,list) or not 1<=len(texts)<=256 or not all(isinstance(t,str) and len(t)<=100000 for t in texts):
        raise HTTPException(400,"Input must be a string or at most 256 text strings.")
    if body.encoding_format not in ("float","base64"): raise HTTPException(400,"Unsupported encoding format.")
    with embed_lock:
        vectors=list(get_embedder().embed(texts,batch_size=16))
    values=[]
    for i,v in enumerate(vectors):
        value=base64.b64encode(v.astype("<f4").tobytes()).decode() if body.encoding_format=="base64" else v.tolist()
        values.append({"object":"embedding","index":i,"embedding":value})
    return {"object":"list","model":EMBED_MODEL,"data":values}

@app.post("/v1/audio/transcriptions")
def transcribe(file:UploadFile=File(...),model:str=Form(STT_MODEL),language:str|None=Form(None),
               response_format:str=Form("json"),timestamp_granularities:list[str]=Form(default=[])):
    if model not in (STT_MODEL,"small","whisper-1"): raise HTTPException(400,"Unknown local speech model.")
    if language in ("","auto"): language=None
    if language is not None and not re.fullmatch(r"[a-z]{2,3}",language): raise HTTPException(400,"Use an ISO language code.")
    suffix=Path(file.filename or "audio.webm").suffix.lower()
    if suffix not in (".wav",".mp3",".mp4",".webm",".m4a",".ogg",".flac",".aac"): suffix=".audio"
    tmp=ROOT/"runtime/uploads"
    tmp.mkdir(exist_ok=True)
    fd,path=tempfile.mkstemp(suffix=suffix,dir=tmp)
    try:
        total=0
        with os.fdopen(fd,"wb") as f:
            while chunk:=file.file.read(1024*1024):
                total+=len(chunk)
                if total>25*1024*1024: raise HTTPException(413,"Audio exceeds 25 MB.")
                f.write(chunk)
        if not total: raise HTTPException(400,"Empty audio.")
        with speech_lock:
            segments,info=get_transcriber().transcribe(path,language=language,beam_size=3,vad_filter=True)
            rows=[{"id":i,"start":float(s.start),"end":float(s.end),"text":s.text.strip()} for i,s in enumerate(segments)]
        text=" ".join(s["text"] for s in rows)
        if response_format=="text": return Response(text,media_type="text/plain")
        return {"text":text,"language":info.language,"duration":float(info.duration),"segments":rows}
    finally:
        Path(path).unlink(missing_ok=True)

class SpeechBody(BaseModel):
    model:str="edge-tts"
    input:str=Field(min_length=1,max_length=12000)
    voice:str="en-GB-SoniaNeural"
    response_format:str="mp3"
    speed:float=Field(default=1.0,ge=0.5,le=2.0)

@app.post("/v1/audio/speech")
async def speech(body:SpeechBody):
    if body.model!="edge-tts": raise HTTPException(400,"Unknown speech model.")
    voices={"sonia":"en-GB-SoniaNeural","jenny":"en-US-JennyNeural","xiaoxiao":"zh-CN-XiaoxiaoNeural"}
    voice=voices.get(body.voice,body.voice)
    if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}-[A-Za-z0-9]+Neural",voice): raise HTTPException(400,"Invalid Edge voice ID.")
    if body.response_format not in ("mp3","wav"): raise HTTPException(400,"Use MP3 or WAV for local speech.")
    import edge_tts
    rate=f"{round((body.speed-1)*100):+d}%"
    chunks=[]
    try:
        async for part in edge_tts.Communicate(body.input,voice,rate=rate).stream():
            if part["type"]=="audio": chunks.append(part["data"])
    except Exception as e:
        raise HTTPException(502,"Edge speech is temporarily unavailable; retry or use original audio.") from e
    audio=b"".join(chunks)
    if not audio: raise HTTPException(502,"No speech audio received.")
    if body.response_format=="wav":
        ffmpeg=shutil.which("ffmpeg")
        if not ffmpeg: raise HTTPException(503,"FFmpeg is not available for WAV conversion.")
        p=await asyncio.to_thread(subprocess.run,[ffmpeg,"-hide_banner","-loglevel","error","-i","pipe:0","-f","wav","pipe:1"],input=audio,capture_output=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        if p.returncode: raise HTTPException(502,"Audio format conversion failed.")
        audio=p.stdout
    return Response(audio,media_type="audio/wav" if body.response_format=="wav" else "audio/mpeg",headers={"Cache-Control":"no-store"})

if __name__=="__main__":
    import uvicorn
    (RUNTIME/"server.json").write_text(json.dumps({"service_id":ID,"pid":os.getpid(),"created":psutil.Process().create_time(),"executable":str(Path(os.sys.executable).resolve())}),encoding="utf-8")
    app_server=uvicorn.Server(uvicorn.Config(app,host="127.0.0.1",port=18810,access_log=False,log_level="info"))
    threading.Thread(target=watch_owners,daemon=True).start()
    app_server.run()
