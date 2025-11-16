# Installation and Test Runner for Danish Housing Market Search Scoring System
# Run this file from PowerShell: .\RUN_TESTS.ps1

Write-Host ""
Write-Host "========================================"
Write-Host "Danish Housing Market Search - Test Suite"
Write-Host "========================================"
Write-Host ""

# Step 1: Install dependencies
Write-Host "[1/3] Installing npm dependencies..."
npm install

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: npm install failed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "[2/3] Installing Playwright browsers..."
npx playwright install

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Playwright install failed" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "[3/3] Running test suite..."
npm test

if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Some tests failed" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "========================================"
    Write-Host "Tests completed successfully!" -ForegroundColor Green
    Write-Host "========================================"
}

Write-Host ""
Write-Host "To view the HTML report, run:"
Write-Host "  npm run test:report" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to exit"
