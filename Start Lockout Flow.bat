@echo off
cd /d "%~dp0"
start "Lockout Flow Server" cmd /k ""%~dp0.venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000"
timeout /t 3 /nobreak >nul
start "" http://localhost:8000
