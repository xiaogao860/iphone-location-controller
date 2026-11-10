@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3.11 -m venv .venv
    if errorlevel 1 goto fail
    .venv\Scripts\python.exe -m pip install -r requirements.txt
    if errorlevel 1 goto fail
)
.venv\Scripts\python.exe launcher.py
if errorlevel 1 goto fail
exit /b 0
:fail
echo Startup failed. Install Python 3.11 x64 and see README.md.
pause
exit /b 1
