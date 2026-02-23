#!/bin/bash
# Danish Housing Market Search — run Playwright tests
# Usage: ./scripts/test.sh

set -e
cd "$(dirname "$0")/.."
npm test
