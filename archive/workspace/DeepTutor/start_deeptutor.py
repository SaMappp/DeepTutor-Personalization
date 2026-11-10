# SPDX-License-Identifier: Apache-2.0
# Historical local customization; publication paths sanitized. Review docs before running.
"""Start the local DeepTutor app and wait until its web UI is usable."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

import psutil

HOME = Path(__file__).resolve().parent
LOG = HOME / 'data/user/runtime/launcher.log'
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def message(text: str) -> None:
    print(text, flush=True)


def ports() -> tuple[int, int]:
    settings = json.loads((HOME / 'data/user/settings/system.json').read_text(encoding='utf-8-sig'))
    backend = int(settings.get('backend_port', 8001))
    frontend = int(settings.get('frontend_port', 3782))
    if not (0 < backend < 65536 and 0 < frontend < 65536 and backend != frontend):
        raise RuntimeError('设置中的前后端端口无效。')
    return backend, frontend


def owned_listeners(wanted: set[int]) -> set[int]:
    found: set[int] = set()
    prefix = str(HOME).casefold() + os.sep
    for connection in psutil.net_connections(kind='tcp'):
        if connection.status != psutil.CONN_LISTEN or not connection.laddr:
            continue
        port = connection.laddr.port
        if port not in wanted:
            continue
        try:
            process = psutil.Process(connection.pid)
            args = process.cmdline()
            command = ' '.join(args).casefold()
            owned = prefix in command and process.name().lower() in {'python.exe', 'pythonw.exe', 'node.exe'}
        except (psutil.Error, TypeError):
            owned = False
        if not owned:
            raise RuntimeError(f'端口 {port} 正被其他程序占用。请先修改 DeepTutor 设置或关闭对应程序。')
        found.add(port)
    return found


def ready(backend: int, frontend: int) -> bool:
    try:
        with HTTP.open(f'http://127.0.0.1:{backend}/health/ready', timeout=2) as response:
            if response.status != 200 or json.load(response).get('status') != 'ready':
                return False
        with HTTP.open(f'http://127.0.0.1:{frontend}/', timeout=2) as response:
            return response.status == 200
    except (OSError, ValueError):
        return False


def open_page(frontend: int) -> None:
    url = f'http://127.0.0.1:{frontend}/'
    message(f'DeepTutor 已就绪，正在打开浏览器：{url}')
    os.startfile(url)


def main() -> int:
    os.chdir(HOME)
    support = HOME.parent / 'DeepTutor-learning-support'
    if (support / 'ensure_support.py').is_file():
        result = subprocess.run([str(support / '.venv/Scripts/python.exe'), str(support / 'ensure_support.py')], cwd=support, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError('本地学习辅助服务启动失败，请查看 DeepTutor-learning-support/runtime/service.log。')
    os.environ['DEEPTUTOR_HOME'] = str(HOME)
    os.environ['PYTHONUTF8'] = '1'
    backend, frontend = ports()
    listening = owned_listeners({backend, frontend})
    if listening == {backend, frontend} and ready(backend, frontend):
        message('DeepTutor 已在运行，无需重复启动。')
        open_page(frontend)
        return 0
    if listening:
        message('检测到 DeepTutor 正在启动，等待网页就绪……')
    else:
        message('正在启动 DeepTutor，请稍候……')
        cli = HOME / '.venv/Scripts/deeptutor.exe'
        result = subprocess.run([str(cli), 'start', '--home', str(HOME), '--detach', '--no-browser'], cwd=HOME)
        if result.returncode:
            raise RuntimeError(f'启动命令返回错误码 {result.returncode}。')
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if owned_listeners({backend, frontend}) == {backend, frontend} and ready(backend, frontend):
            open_page(frontend)
            return 0
        time.sleep(1)
    raise RuntimeError('等待 60 秒后，前后端仍未全部就绪。请使用停止脚本后重试，并查看启动日志。')


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        message(f'\nDeepTutor 启动未完成：{error}')
        message(f'日志位置：{LOG}')
        raise SystemExit(1)
