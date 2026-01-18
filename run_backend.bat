@echo off
echo ========================================
echo Starting Reinforcement Signal Optimizer Backend
echo ========================================
echo.

cd /d "%~dp0backend"

echo Activating virtual environment...
call venv\Scripts\activate.bat

if errorlevel 1 (
    echo.
    echo ERROR: Failed to activate virtual environment!
    echo Please ensure venv exists in the backend folder.
    echo.
    pause
    exit /b 1
)

echo.
echo Virtual environment activated!
echo Python location: 
where python

echo.
echo Starting FastAPI backend server...
echo Server will be available at: http://localhost:8000
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start backend server!
    echo Check the error message above.
    echo.
    pause
)
