@echo off
SETLOCAL
cd /d "%~dp0"

echo ===================================================
echo SmartSafe Hybrid System: Unified Launcher
echo ===================================================
echo.

if not exist venv goto NO_VENV

REM Use explicit venv python for reliability
set PYTHON_EXE=venv\Scripts\python.exe

echo [0/2] Cleaning up orphaned processes on port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a > nul 2>&1

echo [1/4] Starting Cloud API Server on port 8000...
start "SmartSafe Cloud API" /min cmd /c "set API_PORT=8000 && %PYTHON_EXE% api_main.py"

echo [2/4] Starting Celery Worker...
start "SmartSafe Celery Worker" /min cmd /c "venv\Scripts\activate && celery -A workers.celery_app worker --loglevel=info -P solo"

echo [3/4] Starting Celery Beat Scheduler...
start "SmartSafe Celery Beat" /min cmd /c "venv\Scripts\activate && celery -A workers.celery_app beat --loglevel=info"

echo [4/4] Opening API Documentation...
start "" "http://localhost:8000/docs"

timeout /t 3 /nobreak > nul

echo.
echo Starting SmartSafe Desktop Application...
echo.
%PYTHON_EXE% main.py

echo.
echo ===================================================
echo System shutdown. Closing background processes...
echo ===================================================
taskkill /FI "WINDOWTITLE eq SmartSafe Cloud API*" /T /F > nul 2>&1
taskkill /FI "WINDOWTITLE eq SmartSafe Celery Worker*" /T /F > nul 2>&1
taskkill /FI "WINDOWTITLE eq SmartSafe Celery Beat*" /T /F > nul 2>&1
goto END

:NO_VENV
echo Virtual environment (venv) not found.
echo Please run setup_and_run.bat first to initialize the project.
pause
goto END

:END
ENDLOCAL
