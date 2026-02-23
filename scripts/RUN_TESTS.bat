@echo off
REM Installation and Test Runner for Danish Housing Market Search Scoring System
REM Run from project root: scripts\RUN_TESTS.bat

cd /d "%~dp0.."

echo.
echo ========================================
echo Danish Housing Market Search - Test Suite
echo ========================================
echo.

REM Step 1: Install dependencies
echo [1/3] Installing npm dependencies...
call npm install

if errorlevel 1 (
    echo ERROR: npm install failed
    pause
    exit /b 1
)

echo.
echo [2/3] Installing Playwright browsers...
call npx playwright install

if errorlevel 1 (
    echo ERROR: Playwright install failed
    pause
    exit /b 1
)

echo.
echo [3/3] Running test suite...
call npm test

if errorlevel 1 (
    echo WARNING: Some tests failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Tests completed successfully!
echo ========================================
echo.
echo To view the HTML report, run:
echo   npm run test:report
echo.
pause
