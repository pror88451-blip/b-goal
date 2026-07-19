@echo off
cd /d "%~dp0"
python bgoal_app.py
if not errorlevel 1 exit /b 0
py bgoal_app.py
if errorlevel 1 pause
