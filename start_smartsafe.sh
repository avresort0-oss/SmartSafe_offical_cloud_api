#!/usr/bin/env bash
# Linux/Codespaces equivalent of START_SMARTSAFE.bat (Windows-only).
# Starts the Cloud API, Celery worker, Celery beat, then the desktop app.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")"

echo "==================================================="
echo "SmartSafe Hybrid System: Unified Launcher (Linux)"
echo "==================================================="
echo

if [ -d venv ]; then
    PYTHON_EXE="venv/bin/python"
else
    PYTHON_EXE="python"
fi

echo "[0/4] Cleaning up orphaned processes on port 8000..."
fuser -k 8000/tcp 2>/dev/null || true

echo "[1/4] Starting Cloud API Server on port 8000..."
API_PORT=8000 "$PYTHON_EXE" api_main.py > /tmp/smartsafe_api.log 2>&1 &
API_PID=$!

echo "[2/4] Starting Celery Worker..."
"$PYTHON_EXE" -m celery -A workers.celery_app worker --loglevel=info -P solo > /tmp/smartsafe_celery_worker.log 2>&1 &
WORKER_PID=$!

echo "[3/4] Starting Celery Beat Scheduler..."
"$PYTHON_EXE" -m celery -A workers.celery_app beat --loglevel=info > /tmp/smartsafe_celery_beat.log 2>&1 &
BEAT_PID=$!

echo "[4/4] API docs available at http://localhost:8000/docs"
echo "      (logs: /tmp/smartsafe_api.log, /tmp/smartsafe_celery_worker.log, /tmp/smartsafe_celery_beat.log)"

sleep 3

cleanup() {
    echo
    echo "==================================================="
    echo "System shutdown. Closing background processes..."
    echo "==================================================="
    kill "$API_PID" "$WORKER_PID" "$BEAT_PID" 2>/dev/null
}
trap cleanup EXIT

echo
echo "Starting SmartSafe Desktop Application..."
echo
"$PYTHON_EXE" main.py
