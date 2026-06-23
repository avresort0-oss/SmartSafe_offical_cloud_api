@echo off
echo ==========================================
echo    SmartSafe Enterprise - Cleanup Script
echo ==========================================
echo.

echo [1/2] Deleting virtual environment (venv)...
if exist "venv\" (
    rmdir /s /q "venv"
    echo venv folder deleted successfully.
) else (
    echo venv folder not found. Skipping.
)

echo.
echo [2/2] Deleting __pycache__ folders recursively...
FOR /d /r . %%d IN ("__pycache__") DO (
    IF EXIST "%%d" (
        echo Deleting: %%d
        rmdir /s /q "%%d"
    )
)
echo All __pycache__ folders cleaned up.

echo.
echo ==========================================
echo Cleanup Complete! Your project is ready to copy.
echo ==========================================
pause