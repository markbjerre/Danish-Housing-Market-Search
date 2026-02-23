@echo off
REM Start local development environment with SSH tunnel and Flask
REM Run from project root: scripts\start_local_dev.bat

setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║  Danish Housing Market Search - Local Development Environment  ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found! Please install Python 3.x first.
    echo    Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Change to project root (parent of scripts/)
cd /d "%~dp0.."
set "PROJECT_DIR=%cd%"

echo 📁 Project directory: %PROJECT_DIR%
echo.

REM Create or activate virtual environment
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo ✅ Virtual environment ready
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

echo ✅ Virtual environment activated
echo.

REM Install requirements
echo 📦 Installing dependencies (this may take a minute)...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo ✅ Dependencies installed
echo.

REM Create .env file
echo 🔧 Setting up environment variables...
(
    echo DATABASE_URL=postgresql://housing:housing_password@localhost:5432/housing
    echo FLASK_ENV=development
    echo FLASK_DEBUG=True
) > .env

echo ✅ .env file created
echo.

REM Check if SSH tunnel is already running
echo 🔍 Checking for existing SSH tunnel...
netstat -ano | findstr ":5432" >nul 2>&1
if errorlevel 1 (
    echo 📡 Starting SSH tunnel to VPS database...
    REM Start SSH tunnel in background
    start "" ssh -L 5432:housing-db:5432 root@72.61.179.126 -N
    timeout /t 2 /nobreak
    echo ✅ SSH tunnel started
) else (
    echo ✅ SSH tunnel already running
)

echo.
echo ════════════════════════════════════════════════════════════════
echo 🚀 Starting Flask development server...
echo ════════════════════════════════════════════════════════════════
echo.
echo 🌐 Access at: http://localhost:5000/housing
echo.
echo 💡 Tips:
echo    • Edit files and refresh browser to see changes
echo    • Press Ctrl+C to stop the server
echo    • SSH tunnel will keep running in background
echo.
echo ════════════════════════════════════════════════════════════════
echo.

cd /d "%PROJECT_DIR%\webapp"
python app.py

pause
