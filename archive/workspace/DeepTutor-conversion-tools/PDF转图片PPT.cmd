@rem SPDX-License-Identifier: AGPL-3.0-or-later
@rem Historical local customization; publication paths sanitized. Review docs before running.
@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
"%~dp0.venv\Scripts\python.exe" "%~dp0convert_materials.py" pdf %*
set "conversion_exit=%errorlevel%"
echo.
pause
exit /b %conversion_exit%

