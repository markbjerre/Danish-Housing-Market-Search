#!/bin/bash
# Automated test runner for Danish Housing Market Search
# Run: ./scripts/run-tests-ci.sh or from project root: bash scripts/run-tests-ci.sh

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

echo "==============================================="
echo "Danish Housing Market Search - Automated Tests"
echo "==============================================="
echo ""
echo "Starting at: $(date)"
echo "Project: $PROJECT_DIR"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Step 1: Check prerequisites
print_step "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi
print_success "Python 3 found: $(python3 --version)"

if ! command -v node &> /dev/null; then
    print_error "Node.js is not installed"
    exit 1
fi
print_success "Node.js found: $(node --version)"

if ! command -v npm &> /dev/null; then
    print_error "npm is not installed"
    exit 1
fi
print_success "npm found: $(npm --version)"

if ! command -v docker &> /dev/null; then
    print_warning "Docker not found - will run tests without containers"
    USE_DOCKER=false
else
    print_success "Docker found: $(docker --version)"
    USE_DOCKER=true
fi

echo ""

# Step 2: Install Python dependencies
print_step "Installing Python dependencies..."
python3 -m pip install -q -r requirements.txt 2>/dev/null || {
    print_error "Failed to install Python dependencies"
    exit 1
}
print_success "Python dependencies installed"

echo ""

# Step 3: Install npm dependencies
print_step "Installing npm dependencies..."
npm install --silent 2>/dev/null || {
    print_error "Failed to install npm dependencies"
    exit 1
}
print_success "npm dependencies installed"

echo ""

# Step 4: Install Playwright browsers
print_step "Installing Playwright browsers..."
npx playwright install --with-deps > /dev/null 2>&1 || {
    print_error "Failed to install Playwright browsers"
    exit 1
}
print_success "Playwright browsers installed"

echo ""

# Step 5: Start services (Docker or local)
print_step "Starting services..."

if [ "$USE_DOCKER" = true ]; then
    print_step "Using Docker Compose..."
    docker-compose -f docker-compose.test.yml down 2>/dev/null || true
    docker-compose -f docker-compose.test.yml up -d
    sleep 10  # Wait for services to start
    print_success "Docker services started"
else
    print_step "Starting Flask server locally..."
    export DATABASE_URL="sqlite:///housing_test.db"
    export FLASK_ENV="testing"

    # Start Flask in background
    cd webapp
    python3 app.py > ../flask.log 2>&1 &
    FLASK_PID=$!
    cd ..

    sleep 5  # Wait for Flask to start

    # Check if Flask is running
    if ! kill -0 $FLASK_PID 2>/dev/null; then
        print_error "Failed to start Flask server"
        cat flask.log
        exit 1
    fi
    print_success "Flask server started (PID: $FLASK_PID)"
fi

echo ""

# Step 6: Run tests
print_step "Running Playwright tests..."
echo ""

if npm test; then
    TEST_RESULT=$?
    echo ""
    print_success "All tests passed!"
else
    TEST_RESULT=$?
    echo ""
    print_error "Some tests failed"
fi

echo ""

# Step 7: Generate report
print_step "Test Summary"
if [ -f "playwright-report/index.html" ]; then
    print_success "Test report generated: playwright-report/index.html"
    TEST_COUNT=$(grep -o '"test"' "playwright-report/index.html" | wc -l)
    echo "  Test count: ~$TEST_COUNT"
fi

echo ""

# Step 8: Cleanup
print_step "Cleaning up..."

if [ "$USE_DOCKER" = true ]; then
    docker-compose -f docker-compose.test.yml down 2>/dev/null
    print_success "Docker services stopped"
else
    if [ ! -z "$FLASK_PID" ] && kill -0 $FLASK_PID 2>/dev/null; then
        kill $FLASK_PID
        print_success "Flask server stopped"
    fi
fi

echo ""

# Step 9: Final summary
print_step "Test Run Complete"
echo "Finished at: $(date)"
echo ""

if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review test report: playwright-report/index.html"
    echo "  2. Deploy to production if all tests pass"
    echo "  3. Check logs: flask.log (if using local mode)"
    exit 0
else
    echo -e "${RED}✗ Tests failed - see details above${NC}"
    echo ""
    echo "Debugging:"
    echo "  1. Check test output above for specific failures"
    echo "  2. Review test-results/ folder for screenshots"
    echo "  3. Run: npm run test:debug for interactive debugging"
    exit 1
fi
