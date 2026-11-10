@rem SPDX-License-Identifier: Apache-2.0
@rem Historical local customization; publication paths sanitized. Review docs before running.
@echo off
set "PYTHONUTF8=1"
set "DEEPTUTOR_HOME=%~dp0"
cd /d "%~dp0"
"%~dp0.venv\Scripts\deeptutor.exe" provider login openai-codex
pause
