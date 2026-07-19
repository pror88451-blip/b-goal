@echo off
cd /d "%~dp0"
python check_openai_key.py
if not errorlevel 1 goto done
py check_openai_key.py
:done
pause
