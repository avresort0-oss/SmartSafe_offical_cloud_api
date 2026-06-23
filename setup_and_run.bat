@echo off
cd /d "%~dp0"
SETLOCAL

REM --- Configuration ---
SET VENV_DIR=venv
SET REQUIREMENTS_FILE=requirements.txt
SET MAIN_APP_FILE=main.py
SET DOTENV_FILE=.env

REM --- Check for Python ---
python --version >NUL 2>&1
IF %ERRORLEVEL% NEQ 0 (
    ECHO Python is not installed or not in PATH. Please install Python 3.8+ and try again.
    GOTO :END_PROCESS
)

REM --- Create Virtual Environment ---
IF NOT EXIST %VENV_DIR%\ (
    ECHO Creating virtual environment...
    python -m venv %VENV_DIR%
    IF %ERRORLEVEL% NEQ 0 (
        ECHO Failed to create virtual environment.
        GOTO :END_PROCESS
    )
)

REM --- Activate Virtual Environment ---
CALL %VENV_DIR%\Scripts\activate.bat
IF %ERRORLEVEL% NEQ 0 (
    ECHO Failed to activate virtual environment.
    GOTO :END_PROCESS
)

REM --- Install Dependencies ---
IF NOT EXIST %REQUIREMENTS_FILE% (
    ECHO.
    ECHO Creating %REQUIREMENTS_FILE%...
    ECHO customtkinter > %REQUIREMENTS_FILE%
    ECHO SQLAlchemy >> %REQUIREMENTS_FILE%
    ECHO alembic >> %REQUIREMENTS_FILE%
    ECHO cryptography >> %REQUIREMENTS_FILE%
    ECHO bcrypt >> %REQUIREMENTS_FILE%
    ECHO PyInstaller >> %REQUIREMENTS_FILE%
    ECHO psycopg2-binary >> %REQUIREMENTS_FILE%
    ECHO python-dotenv >> %REQUIREMENTS_FILE%
)
ECHO Installing/Updating dependencies...
pip install -r %REQUIREMENTS_FILE%
IF %ERRORLEVEL% NEQ 0 (
    ECHO Failed to install dependencies.
    GOTO :END_PROCESS
)

REM --- Setup .env file ---
IF NOT EXIST %DOTENV_FILE% (
    ECHO.
    ECHO =================================================================================
    ECHO CRITICAL: .env file not found. Setting up database and E2EE key.
    ECHO =================================================================================
    ECHO.
    
    REM Use a default if user just presses enter, or capture their input.
    SET "DATABASE_URL_INPUT=sqlite:///./smartsafe.db"
    SET /P "DATABASE_URL_INPUT_TEMP=Enter your DATABASE_URL (e.g., postgresql://user:pass@host:port/db or sqlite:///./smartsafe.db) [Default: sqlite:///./smartsafe.db]: "
    IF NOT "%DATABASE_URL_INPUT_TEMP%"=="" SET "DATABASE_URL_INPUT=%DATABASE_URL_INPUT_TEMP%"
    (
        ECHO DATABASE_URL="%DATABASE_URL_INPUT%"
    ) > %DOTENV_FILE%
    
    ECHO Generating a secure E2EE_MASTER_KEY...
    FOR /F "delims=" %%i IN ('python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"') DO (
        ECHO E2EE_MASTER_KEY="%%i" >> %DOTENV_FILE%
    )

    ECHO.
    ECHO .env file created. Please review it for correctness.
    ECHO =================================================================================
    ECHO.
)

REM --- Run Alembic Migrations ---
ECHO Running Alembic database migrations...
alembic upgrade head
IF %ERRORLEVEL% NEQ 0 (
    ECHO Alembic migrations failed. Check your DATABASE_URL and database connectivity.
    GOTO :END_PROCESS
)

REM --- Run the Main Application ---
ECHO Starting SmartSafe v28 application...
python %MAIN_APP_FILE%
IF %ERRORLEVEL% NEQ 0 (
    ECHO SmartSafe v28 application encountered an error.
    GOTO :END_PROCESS
)

ENDLOCAL
:END_PROCESS
PAUSE