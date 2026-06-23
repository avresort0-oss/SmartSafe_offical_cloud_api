@echo off
SETLOCAL EnableDelayedExpansion
cd /d "%~dp0"

echo ===================================================
echo SmartSafe Enterprise: ONE-CLICK SETUP ^& LAUNCH
echo ===================================================
echo.

REM --- Configuration ---
SET VENV_DIR=venv
SET REQUIREMENTS_FILE=requirements.txt
SET PYTHON_EXE=%VENV_DIR%\Scripts\python.exe
SET API_PORT=8000

REM --- 1. Python Environment Check ---
python --version >NUL 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

IF NOT EXIST %VENV_DIR%\ (
    echo [1/6] Creating virtual environment...
    python -m venv %VENV_DIR%
) ELSE (
    echo [1/6] Virtual environment found.
)

REM --- 2. Dependency Management ---
echo [2/6] Updating dependencies (this may take a moment)...
call %VENV_DIR%\Scripts\activate.bat
python -m pip install --upgrade pip >NUL
pip install -r %REQUIREMENTS_FILE%
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

REM --- 3. Database Migrations ---
echo [3/6] Running database migrations...
%PYTHON_EXE% utils/check_db.py
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Database is not reachable. Please check your POSTGRES_URL in .env.
    pause
    exit /b 1
)
alembic upgrade head
IF %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Alembic migrations encountered an issue. Continuing anyway...
)

REM --- 4. Portfolio Cleanup ---
echo [4/6] Cleaning up orphaned processes on port %API_PORT%...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :%API_PORT% ^| findstr LISTENING') do taskkill /F /PID %%a > nul 2>&1

REM --- 5. Launch Cloud API Server ---
echo [5/6] Starting Cloud API Server (Background)...
start "SmartSafe Cloud API" /min cmd /c "set API_PORT=%API_PORT% && %PYTHON_EXE% api_main.py"
start "" "http://localhost:%API_PORT%/docs"

REM --- 6. Launch Desktop Application ---
echo [6/6] Starting SmartSafe Desktop Application...
timeout /t 2 /nobreak > nul
%PYTHON_EXE% main.py

echo.
echo ===================================================
echo SmartSafe Session Ended.
echo Cleaning up background API...
echo ===================================================
taskkill /FI "WINDOWTITLE eq SmartSafe Cloud API*" /T /F > nul 2>&1

ENDLOCAL
pause
