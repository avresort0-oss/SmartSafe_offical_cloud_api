@echo off
echo ====================================================
echo Starting SmartSafe Cloud Services (FastAPI + Celery)
echo ====================================================

REM Ensure dependencies are met
echo 1. Starting FastAPI Server...
start "SmartSafe FastAPI" cmd /k "venv\Scripts\activate && uvicorn api_main:app --host 0.0.0.0 --port 8000 --reload"

echo 2. Starting Celery Worker...
start "SmartSafe Celery Worker" cmd /k "venv\Scripts\activate && celery -A workers.celery_app worker --loglevel=info -P solo"

echo Services started in separate windows!
echo - API Docs available at: http://localhost:8000/docs
pause
