@rem SPDX-License-Identifier: Apache-2.0
@rem Historical local customization; publication paths sanitized. Review docs before running.
@echo off
setlocal
chcp 65001 >nul
set "PYTHONUTF8=1"
set "DEEPTUTOR_HOME=%~dp0"
cd /d "%~dp0"
"%~dp0.venv\Scripts\python.exe" "%~dp0start_deeptutor.py"
if errorlevel 1 (
    echo.
    echo Startup failed. Please keep this window open and check the error above.
    pause
    exit /b 1
)
endlocal
