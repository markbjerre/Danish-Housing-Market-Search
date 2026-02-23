# Automated CI/CD Testing Guide

Complete automation setup for running the scoring system tests without manual intervention.

## Overview

Three automated testing methods are now available:

1. **GitHub Actions** - Automatic on every push/PR (cloud-based)
2. **Docker Compose** - Local/VPS containerized testing
3. **Shell Script** - VPS automated runner

---

## Option 1: GitHub Actions (Recommended - Fully Automatic)

### How It Works

Tests run **automatically** on:
- Every `git push` to `main` or `develop` branches
- Every pull request
- Daily at 2 AM UTC (scheduled)

No manual action needed!

### Setup

1. Push code to GitHub:
```bash
git push origin main
```

2. Tests start automatically in GitHub Actions
3. View results:
   - Go to: https://github.com/YOUR_USERNAME/Danish-Housing-Market-Search
   - Click: "Actions" tab
   - See test results, logs, and artifacts

### Features

✅ PostgreSQL database service
✅ Python 3.12 and Node.js 18
✅ Playwright browser installation
✅ 50+ tests execution
✅ HTML report generation
✅ Artifact upload (30 days retention)
✅ PR comments with results
✅ Test report publishing
✅ Failure notifications

### View Test Results

1. **GitHub Actions UI**
   - Go to Actions tab
   - Click the test run
   - See detailed logs and artifacts

2. **Download Report**
   - Click "Artifacts" section
   - Download `playwright-report`
   - Open `index.html` in browser

3. **PR Comments**
   - GitHub automatically comments on PRs
   - Shows test status and results link

---

## Option 2: Docker Compose (Local or VPS)

### Quick Start

```bash
# Run tests in isolated Docker environment
docker-compose -f docker-compose.test.yml up

# Wait for services to start and tests to complete
# View results in playwright-report/ folder
```

### Services Included

- **PostgreSQL 15** - Test database (port 5433)
- **Flask API** - Test server (port 5000)
- **Playwright** - Test runner (runs automatically)

### Manual Service Control

```bash
# Start services
docker-compose -f docker-compose.test.yml up -d

# Check status
docker-compose -f docker-compose.test.yml ps

# View logs
docker-compose -f docker-compose.test.yml logs -f

# Run tests only (services already running)
docker run -it --network housing-test-network \
  -v $(pwd):/app \
  mcr.microsoft.com/playwright:v1.40.0-focal \
  npm test

# Stop services
docker-compose -f docker-compose.test.yml down

# Full cleanup
docker-compose -f docker-compose.test.yml down -v
```

### Advantages

- ✅ Isolated environment (no system dependencies)
- ✅ Reproducible across machines
- ✅ No local database conflicts
- ✅ Fast setup and teardown
- ✅ Works on Windows, Mac, Linux

### Requirements

- Docker installed
- Docker Compose (usually included with Docker Desktop)
- 2GB free disk space

---

## Option 3: Shell Script Runner (VPS Recommended)

### Quick Start

```bash
# Make script executable (first time only)
chmod +x scripts/run-tests-ci.sh

# Run tests (from project root)
./scripts/run-tests-ci.sh
```

### What It Does

1. ✅ Checks prerequisites (Python, Node, npm)
2. ✅ Installs Python dependencies (pip)
3. ✅ Installs npm dependencies
4. ✅ Installs Playwright browsers
5. ✅ Detects Docker availability
6. ✅ Starts services (Docker or local Flask)
7. ✅ Runs 50+ Playwright tests
8. ✅ Generates HTML report
9. ✅ Cleans up services
10. ✅ Shows summary with pass/fail status

### Output Example

```
===============================================
Danish Housing Market Search - Automated Tests
===============================================

Starting at: 2025-11-16 14:32:15

✓ Python 3 found: Python 3.12.3
✓ Node.js found: v18.20.8
✓ npm found: 10.8.2
✓ Docker found: Docker version 24.0.0

✓ Python dependencies installed
✓ npm dependencies installed
✓ Playwright browsers installed

[2025-11-16 14:32:45] Starting services...
✓ Docker services started

[2025-11-16 14:32:50] Running Playwright tests...

✓ GET /api/personas - Returns all 4 personas
✓ GET /api/personas - Personas have correct structure
✓ Score badge displays with correct color
✓ Persona selector dropdown is present
...

50 passed (2m 15s)

✓ Test report generated: playwright-report/index.html

✓ Docker services stopped

Test Run Complete
Finished at: 2025-11-16 14:35:30

✓ All tests passed!

Next steps:
  1. Review test report: playwright-report/index.html
  2. Deploy to production if all tests pass
  3. Check logs: flask.log (if using local mode)
```

### Error Handling

If tests fail:
- Colored output shows ✗ (red)
- Detailed error messages
- Suggestions for debugging
- Automatic cleanup on failure

### Exit Codes

- `0` - All tests passed
- `1` - Tests failed or prerequisite missing

Perfect for scripting:
```bash
./scripts/run-tests-ci.sh
if [ $? -eq 0 ]; then
    echo "Tests passed - deploying..."
    ./deploy.sh
else
    echo "Tests failed - aborting deploy"
    exit 1
fi
```

### Running on VPS

Add to cron for automated daily testing:

```bash
# Edit crontab
crontab -e

# Add this line to run tests daily at 2 AM
0 2 * * * cd /opt/ai-vaerksted/Danish-Housing-Market-Search && ./scripts/run-tests-ci.sh >> /var/log/housing-tests.log 2>&1
```

---

## Choosing the Right Option

### Use GitHub Actions If:
- You want fully automatic testing
- Tests should run on every push
- You need cloud-based CI/CD
- You want PR integration
- Team collaboration is important

### Use Docker Compose If:
- You want isolated testing environment
- You don't want system dependencies
- You're testing locally before pushing
- Reproducibility is critical
- You use Windows/Mac/Linux

### Use Shell Script If:
- You're testing on VPS
- You want direct control
- You need custom logging
- You prefer simplicity
- You want to chain with other scripts

---

## Full Automation Workflow

Recommended: Combine all three!

### Developer Workflow
```bash
# 1. Make changes
git add .
git commit -m "Add feature"

# 2. Test locally with Docker
./scripts/run-tests-ci.sh

# 3. Push to GitHub (if local tests pass)
git push origin main

# 4. GitHub Actions tests automatically
# (View results in Actions tab)

# 5. VPS runs daily scheduled tests
# (Setup via cron job)
```

### VPS Deployment Workflow
```bash
# 1. Pull latest code
git pull origin main

# 2. Run tests automatically
./scripts/run-tests-ci.sh

# 3. If tests pass, deploy
if [ $? -eq 0 ]; then
    docker-compose up -d
    echo "Deployment successful"
else
    echo "Tests failed - deployment aborted"
fi
```

---

## Monitoring Test Results

### GitHub Actions
- **Dashboard**: Actions tab in repository
- **Real-time**: Click running test to see live logs
- **Artifacts**: Test reports and videos
- **History**: All previous test runs

### Docker Compose
- **Logs**: `docker-compose logs -f test-runner`
- **Report**: `playwright-report/index.html`
- **Screenshots**: `test-results/` folder

### Shell Script
- **Console**: Colored output in terminal
- **Report**: `playwright-report/index.html`
- **Logs**: `flask.log` (if local mode)
- **Cron**: Check `/var/log/housing-tests.log`

---

## Troubleshooting

### GitHub Actions Failures

**Check logs:**
1. Go to Actions tab
2. Click failed workflow run
3. Expand job logs
4. Look for error messages

**Common issues:**
- Database not starting: Check PostgreSQL health check in workflow
- Playwright timeout: Increase timeout in playwright.config.ts
- Import errors: Verify all requirements.txt dependencies

### Docker Issues

**Port already in use:**
```bash
# Stop other containers using ports
docker stop $(docker ps -q)

# Or use different ports in docker-compose.test.yml
```

**Out of disk space:**
```bash
# Clean up Docker
docker system prune -a

# Remove old test databases
docker volume rm housing-test-db
```

**Playwright not installing:**
```bash
# Force reinstall
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up --build
```

### Shell Script Issues

**Permission denied:**
```bash
chmod +x scripts/run-tests-ci.sh
```

**Python not found:**
```bash
# Check Python version
python3 --version

# If not installed
sudo apt-get install python3 python3-pip
```

**Port 5000 in use:**
```bash
# Kill process using port
lsof -i :5000
kill -9 <PID>

# Or let script use different port
export FLASK_PORT=5001
./scripts/run-tests-ci.sh
```

---

## Integration Examples

### GitHub Actions + Deployment

```yaml
# After tests pass
- name: Deploy if tests pass
  if: success()
  run: |
    ssh user@vps "cd /app && docker-compose up -d"
```

### Slack Notifications

```yaml
# Notify Slack of test results
- name: Notify Slack
  if: always()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {"text": "Tests: ${{ job.status }}"}
```

### VPS Deployment Script

```bash
#!/bin/bash
# deploy.sh

# Run tests first
./scripts/run-tests-ci.sh || exit 1

# If tests pass, deploy
git pull origin main
docker-compose down
docker build -t housing:latest .
docker-compose up -d

echo "Deployment complete"
```

---

## Performance Metrics

### Typical Execution Times

| Method | Setup | Tests | Cleanup | Total |
|--------|-------|-------|---------|-------|
| GitHub Actions | 2-3 min | 2-3 min | 1 min | 5-7 min |
| Docker Compose | 1-2 min | 2-3 min | 30 sec | 4-6 min |
| Shell Script (Docker) | 1-2 min | 2-3 min | 30 sec | 4-6 min |
| Shell Script (Local) | 30 sec | 2-3 min | 10 sec | 3-4 min |

---

## Next Steps

1. **Immediate**: Push code to GitHub
   - GitHub Actions will run automatically
   - View results in Actions tab

2. **Test Locally**: Run Docker setup
   ```bash
   docker-compose -f docker-compose.test.yml up
   ```

3. **VPS Setup**: Add cron job
   ```bash
   crontab -e
   # Add: 0 2 * * * cd /path && ./scripts/run-tests-ci.sh >> /var/log/housing-tests.log 2>&1
   ```

4. **Monitor Results**: Check dashboards
   - GitHub Actions for cloud tests
   - Cron logs for VPS tests
   - Local reports for development

---

## Summary

✅ **Fully Automated** - No manual test running
✅ **Multiple Options** - Cloud, Docker, or Shell
✅ **Well-Documented** - Clear instructions
✅ **Easy Monitoring** - View results everywhere
✅ **Production-Ready** - Error handling and logging

**Status**: Tests now run automatically across all environments!

---

**Created**: November 2025
**Scoring System Version**: 1.0.0
**Test Coverage**: 50+ cases
**Automation**: 3 methods (GitHub Actions, Docker, Shell)
