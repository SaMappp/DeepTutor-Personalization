@rem SPDX-License-Identifier: AGPL-3.0-or-later
@rem Historical local customization; publication paths sanitized. Review docs before running.
@echo off
chcp 65001 >nul
set PYTHONUTF8=1
"%~dp0..\DeepTutor-learning-support\.venv\Scripts\python.exe" "%~dp0import_python_pdfs.py" %*
echo.
pause
