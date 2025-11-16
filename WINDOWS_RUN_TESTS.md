# Running Tests on Windows

## Quick Start (2 Options)

### Option 1: Using PowerShell (Recommended)
```powershell
.\RUN_TESTS.ps1
```

This script will automatically:
1. Install npm dependencies
2. Install Playwright browsers
3. Run all 50+ tests
4. Display results

### Option 2: Using Command Prompt (cmd.exe)
```cmd
cmd /c RUN_TESTS.bat
```

### Option 3: Manual Commands
If the scripts don't work, run these commands manually:

```powershell
# Install dependencies
npm install

# Install Playwright browsers
npx playwright install

# Run all tests
npm test

# View results
npm run test:report
```

## Fixing PowerShell Execution Policy Error

If you get "running scripts is disabled on this system" error:

### Quick Fix (Temporary - Current Session Only)
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

Then run:
```powershell
.\RUN_TESTS.ps1
```

### Permanent Fix (All Sessions)
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## What Gets Tested

✅ **50+ Test Cases** covering:
- API endpoints (personas, property scores)
- UI components (badges, modals, selectors)
- Responsive design (mobile/tablet/desktop)
- Performance metrics
- Error handling

## Expected Results

When tests complete, you'll see:
```
✓ GET /api/personas - Returns all 4 personas
✓ GET /api/personas - Personas have correct structure
✓ Score badge displays with correct color
✓ Persona selector dropdown is present
...

50 passed (2m 15s)
```

## View HTML Report

After tests complete:
```powershell
npm run test:report
```

This opens an interactive HTML report with:
- All test results
- Screenshots on failure
- Detailed execution timeline
- Network requests
- Console logs

## Run Specific Tests

```powershell
# API tests only
npm run test:api

# UI tests only
npm run test:ui

# Mobile device tests
npm run test:mobile

# Debug mode (interactive)
npm run test:debug

# Browser visible while running
npm run test:headed
```

## Troubleshooting

### npm not found
- Ensure Node.js is installed: `node --version`
- Restart PowerShell/cmd after installing Node.js
- Or use `npx` instead: `npx npm install`

### Port 5000 already in use
- Flask server will use another port automatically
- Or kill process using port 5000: `netstat -ano | findstr :5000`

### Tests timeout
- Flask may be slow to start
- Increase timeout in `playwright.config.ts`
- Or run `npm run test:debug` for interactive debugging

### Playwright browser installation fails
```powershell
# Reinstall browsers
npx playwright install
```

## Manual Test Execution

### Terminal 1: Start Flask Server
```powershell
python webapp/app.py
```
Server runs on http://localhost:5000

### Terminal 2: Run Tests
```powershell
npm install
npm test
```

## Files Created for Easy Testing

- **RUN_TESTS.ps1** - PowerShell script (recommended)
- **RUN_TESTS.bat** - Command Prompt script
- **WINDOWS_RUN_TESTS.md** - This file

## Support

If tests fail:
1. Check Flask server logs
2. Verify http://localhost:5000 is accessible
3. Check `test-results/` folder for screenshots
4. Run `npm run test:debug` for interactive debugging

---

**Status:** Complete implementation ready for testing
**Next:** Run tests to validate scoring system
