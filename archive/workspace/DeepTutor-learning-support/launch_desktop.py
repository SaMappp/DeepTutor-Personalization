# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Launch local learning services, then the existing official desktop app."""
from pathlib import Path
import ctypes,subprocess
from ensure_support import ensure_support
ROOT=Path(__file__).resolve().parent
APP=ROOT.parent/"Open DeepTutor-win32-x64/Open DeepTutor.exe"
def main():
    ensure_support()
    if not APP.is_file(): raise RuntimeError("The original Open DeepTutor executable is missing.")
    subprocess.Popen([str(APP)],cwd=APP.parent)
if __name__=="__main__":
    try: main()
    except Exception as exc:
        ctypes.windll.user32.MessageBoxW(None,f"DeepTutor 启动未完成：{exc}\n日志：{ROOT/'runtime/service.log'}","DeepTutor",0x10)
