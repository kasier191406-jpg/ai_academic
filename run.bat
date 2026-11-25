@echo off
setlocal
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" -c "import fastapi, uvicorn, multipart" >nul 2>nul
if errorlevel 1 (
    echo Backend dependencies are missing.
    echo Install them once with: "%PYTHON_EXE%" -m pip install -r requirements.txt
    exit /b 1
)

if not exist "frontend\node_modules\vite\bin\vite.js" (
    echo Frontend dependencies are missing.
    echo Install them once with: cd frontend ^&^& npm install
    exit /b 1
)

start "MARIS API" powershell -NoExit -Command "& '%PYTHON_EXE%' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000"
start "MARIS Frontend" powershell -NoExit -Command "Set-Location '%CD%\frontend'; npm run dev -- --host 127.0.0.1"
echo.
echo MARIS is starting.
echo Frontend: http://127.0.0.1:5173
echo API docs: http://127.0.0.1:8000/docs
echo Close both MARIS PowerShell windows to stop the application.
