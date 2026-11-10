# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Start and check only this installation's local learning service."""
from pathlib import Path
import json,os,socket,subprocess,time,urllib.request
ROOT=Path(__file__).resolve().parent
ID="deeptutor-local-learning-support-v1"
HTTP=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def health():
    try:
        with HTTP.open("http://127.0.0.1:18810/health",timeout=2) as r:
            value=json.load(r)
            return value if value.get("service_id")==ID else None
    except (OSError,ValueError): return None

def ensure_support():
    import msvcrt
    runtime=ROOT/"runtime"
    runtime.mkdir(exist_ok=True)
    with (runtime/"start.lock").open("a+b") as lock:
        lock.seek(0); lock.write(b"0"); lock.flush(); lock.seek(0)
        msvcrt.locking(lock.fileno(),msvcrt.LK_LOCK,1)
        try:
            status=health()
            if status: return status
            with socket.socket() as s:
                if s.connect_ex(("127.0.0.1",18810))==0:
                    raise RuntimeError("Port 18810 belongs to a different service; no process was stopped.")
            env=os.environ.copy()
            env.pop("PYTHONPATH",None)
            env["PYTHONUTF8"]="1"
            env["HF_HOME"]=str(ROOT/"models/huggingface")
            env["HF_HUB_DISABLE_SYMLINKS_WARNING"]="1"
            log=(runtime/"service.log").open("a",encoding="utf-8")
            try:
                subprocess.Popen([str(ROOT/".venv/Scripts/pythonw.exe"),str(ROOT/"server.py")],cwd=ROOT,env=env,
                                 stdin=subprocess.DEVNULL,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
            finally: log.close()
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                status=health()
                if status: return status
                time.sleep(0.5)
            raise RuntimeError("Local learning support did not start. See runtime/service.log.")
        finally:
            lock.seek(0); msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
if __name__=="__main__":
    print(json.dumps(ensure_support(),ensure_ascii=False))
