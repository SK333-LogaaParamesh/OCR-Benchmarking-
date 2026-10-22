@echo off
rem Rebuild the local dashboard from results\raw\*.json and open it.
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
envs\env-torch\Scripts\python.exe bench\build_dashboard_data.py || exit /b 1
envs\env-torch\Scripts\python.exe bench\render_dashboard.py || exit /b 1
start "" "%~dp0dashboard\index.html"
