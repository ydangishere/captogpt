@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" goto no_venv

if not defined OPENAI_API_KEY goto no_key

".venv\Scripts\python.exe" -u live_caption_enter_toggle.py
if errorlevel 1 goto run_error
exit /b 0

:no_venv
echo [Error] .venv is missing for fast start.
echo Run one-time setup in PowerShell:
echo   cd "D:\captogpt-enter" ^& python -m venv .venv ^& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
echo.
pause
exit /b 1

:no_key
echo.
echo [Error] OPENAI_API_KEY is missing.
echo Set it one-time in PowerShell:
echo   cd "D:\captogpt-enter" ^& setx OPENAI_API_KEY "your_real_openai_api_key"
echo Then close and reopen terminal.
echo.
pause
exit /b 1

:run_error
echo.
echo [Error] App stopped unexpectedly.
pause
exit /b 1
