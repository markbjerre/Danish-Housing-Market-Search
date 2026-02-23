# Testing Quick Start Guide

Complete guide to running the scoring system tests locally with Playwright.

## 30-Second Setup

```bash
# 1. Navigate to project
cd "Danish Housing Market Search"

# 2. Install test dependencies
npm install

# 3. Run tests (automatically starts Flask server)
npm test
```

## What Gets Tested?

✅ **API Endpoints** (7 tests)
- GET /api/personas - all 4 personas
- GET /api/property/<id>/score - with all persona types
- Weight validation and structure

✅ **Frontend UI** (9 tests)
- Score badges (colors and labels)
- Persona selector dropdown
- Factor breakdown visualization
- Score modals (open/close)
- Score interpretation text

✅ **Responsive Design** (5 tests)
- Mobile (375px)
- Tablet (768px)
- Desktop (1920px)
- Factor grid layouts

✅ **Performance** (3 tests)
- API <500ms
- Score endpoint <2s
- Page load <5s

✅ **Error Handling** (4 tests)
- Invalid personas
- Missing properties
- Missing data gracefully
- No JavaScript errors

## Running Tests

### All Tests
```bash
npm test
```

### By Category
```bash
npm run test:api          # API endpoints only
npm run test:ui           # UI components only
npm run test:mobile       # Mobile devices only
```

### By Browser
```bash
npm run test:chrome       # Chromium
npm run test:firefox      # Firefox
npm run test:webkit       # Safari
npm run test:mobile       # iPhone 12 + Pixel 5
npm run test:all-browsers # All browsers
```

### Debug Mode
```bash
npm run test:debug        # Interactive debugging
npm run test:headed       # Browser window visible
```

### View Results
```bash
npm run test:report       # Open HTML report
```

## What You'll See

### Successful Test Run
```
✓ GET /api/personas - Returns all 4 personas
✓ GET /api/personas - Personas have correct structure
✓ Score badge displays with correct color for excellent score
✓ Persona selector dropdown is present and functional
✓ Score modal opens when clicking score badge
...

50 passed (2m 15s)
```

### Test Report
After tests complete, open the interactive HTML report:
```bash
npm run test:report
```

This shows:
- All test results
- Screenshots on failure
- Execution timeline
- Network requests
- Console logs

## Prerequisites Checklist

Before running tests, verify:

- [ ] Node.js 16+ installed (`node --version`)
- [ ] npm installed (`npm --version`)
- [ ] Python 3.8+ available
- [ ] Flask dependencies installed (`pip list | grep flask`)
- [ ] PostgreSQL running (if using production database)

## Troubleshooting

### Tests Won't Start
```bash
# Check if npm is installed
npm --version

# Install dependencies
npm install

# Install Playwright browsers
npx playwright install
```

### Flask Server Won't Start
```bash
# Check if port 5000 is available
lsof -i :5000

# Or manually start Flask
cd webapp
python app.py
# In another terminal, run tests in different session
npm test
```

### Database Connection Error
Tests run against localhost:5000. Ensure:
- Flask app has database configured
- PostgreSQL is running
- .env file has correct credentials

### Tests Timeout
Tests have generous timeouts (10s per test). If timing out:
- Check Flask server logs for errors
- Verify database is responding
- Check network connectivity
- Increase timeout in playwright.config.ts

### Port 5000 Already in Use
```bash
# Find what's using port 5000
lsof -i :5000

# Kill the process
kill -9 <PID>

# Or use different port
export PORT=5001
npm test
```

## Test File Locations

| File | Purpose |
|------|---------|
| `tests/scoring_system.spec.ts` | Main test suite (850 lines) |
| `playwright.config.ts` | Browser and device config |
| `package.json` | Test scripts and dependencies |
| `tests/README.md` | Detailed test documentation |
| `test-results/` | Screenshots, traces, reports |

## Common Commands

```bash
# Run all tests
npm test

# Run tests in specific file
npx playwright test tests/scoring_system.spec.ts

# Run tests matching pattern
npx playwright test --grep "API Tests"

# Run single test
npx playwright test --grep "GET /api/personas"

# Run with tracing (detailed execution log)
npx playwright test --trace on

# Run with screenshots
npx playwright test --screenshot on

# Run in specific browser
npx playwright test --project=chromium

# Run tests serially (one at a time)
npx playwright test --workers=1

# List available tests without running
npx playwright test --list
```

## CI/CD Integration

Tests are designed to run in GitHub Actions or similar CI systems:

```yaml
# Example GitHub Actions workflow
- name: Install dependencies
  run: npm ci

- name: Run tests
  run: npm test

- name: Upload test results
  uses: actions/upload-artifact@v2
  with:
    name: playwright-report
    path: playwright-report/
```

## Performance Expectations

Expected timing for local tests:
- API tests: 5-10 seconds
- UI tests: 30-45 seconds
- Responsive tests: 20-30 seconds
- Total: 2-3 minutes for full suite

Factors affecting performance:
- Computer speed (faster CPU = faster tests)
- Database size (more properties = slower scores)
- Network latency
- Disk I/O speed

## Next Steps

### After Tests Pass
1. Review test results in HTML report
2. Check coverage of scoring features
3. Add tests for new features
4. Run before each commit

### If Tests Fail
1. Check Flask server logs
2. Verify database has test data
3. Review test output for specifics
4. Check `test-results/` for screenshots
5. Run `npm run test:debug` for interactive debugging

### Expanding Tests
Add more tests by:
1. Editing `tests/scoring_system.spec.ts`
2. Adding new test cases
3. Running `npm test` to verify
4. Committing changes

## Resources

- **Playwright Docs**: https://playwright.dev
- **Test File**: `tests/scoring_system.spec.ts`
- **Test README**: `tests/README.md`
- **Configuration**: `playwright.config.ts`

## Support

For test issues:
1. **Check logs**: `npm run test:debug`
2. **View report**: `npm run test:report`
3. **Check server**: `curl http://localhost:5000`
4. **Read docs**: `tests/README.md`

---

**Happy testing! 🎭**

Created: November 2025
Scoring System Status: Phase 4 (Testing) Complete
