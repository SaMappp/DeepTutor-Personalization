@rem SPDX-License-Identifier: AGPL-3.0-or-later
@rem Historical local customization; publication paths sanitized. Review docs before running.
@echo off
setlocal
set "TEXTBOOK_TOOL=%~dp0pdf-textbook-tool\gui.py"
set "TEXTBOOK_PYTHON=%~dp0..\DeepTutor\.venv\Scripts\pythonw.exe"
if not exist "%TEXTBOOK_PYTHON%" (
  echo DeepTutor Python environment was not found.
  pause
  exit /b 1
)
powershell.exe -NoProfile -WindowStyle Hidden -Command "Start-Process -FilePath $env:TEXTBOOK_PYTHON -ArgumentList ('{0}{1}{0}' -f [char]34,$env:TEXTBOOK_TOOL) -WorkingDirectory ([System.IO.Path]::GetDirectoryName($env:TEXTBOOK_TOOL)) -WindowStyle Normal"
endlocal
