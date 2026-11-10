# SPDX-License-Identifier: Apache-2.0
# Historical local customization; publication paths sanitized. Review docs before running.
"""Stop this installation, including verified orphaned server processes."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import psutil

HOME=Path(__file__).resolve().parent

def owned_processes():
    prefix=str(HOME).casefold()+os.sep
    result=[]
    for process in psutil.process_iter(['name','cmdline']):
        command=' '.join(process.info.get('cmdline') or [])
        if prefix not in command.casefold():continue
        if str(process.info.get('name')).lower() not in {'python.exe','pythonw.exe','node.exe'}:continue
        if '-m uvicorn deeptutor.api.main:app' in command or 'runtime\\web\\server.js' in command or '-m deeptutor_cli.main start' in command:
            result.append(process)
    return result

def main():
    os.environ['DEEPTUTOR_HOME']=str(HOME)
    os.environ['PYTHONUTF8']='1'
    os.chdir(HOME)
    print('正在停止 DeepTutor……',flush=True)
    try:
        subprocess.run([str(HOME/'.venv/Scripts/deeptutor.exe'),'stop'],cwd=HOME,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20)
    except subprocess.TimeoutExpired:
        pass
    processes=owned_processes()
    for process in reversed(processes):
        try:process.terminate()
        except psutil.NoSuchProcess:pass
    _,alive=psutil.wait_procs(processes,timeout=5)
    if alive:raise RuntimeError('部分 DeepTutor 进程仍未退出，请保留此窗口。')
    runtime=HOME/'data/user/runtime'
    state=runtime/'launcher.json'
    if state.exists():
        saved=json.loads(state.read_text(encoding='utf-8-sig'))
        if Path(saved.get('home','')).resolve()!=HOME:raise RuntimeError('启动器状态属于其他目录，未修改。')
        state.unlink()
    (runtime/'launcher.stop').unlink(missing_ok=True)
    print('DeepTutor 已停止。',flush=True)
    return 0

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        print(f'DeepTutor 停止未完成：{error}',flush=True)
        raise SystemExit(1)
