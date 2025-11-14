#!/bin/bash

# Start local development environment with SSH tunnel and Flask

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  Danish Housing Market Search - Local Development Environment  ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found! Please install Python 3.x first."
    echo "   Download from: https://www.python.org/downloads/"
    exit 1
fi

# Get the directory where this script is located
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "📁 Project directory: $PROJECT_DIR"
echo ""

# Create or activate virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
fi

echo "✅ Virtual environment ready"
echo ""

# Activate virtual environment
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "❌ Failed to activate virtual environment"
    exit 1
fi

echo "✅ Virtual environment activated"
echo ""

# Install requirements
echo "📦 Installing dependencies (this may take a minute)..."
pip install -r requirements.txt -q
if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed"
echo ""

# Create .env file
echo "🔧 Setting up environment variables..."
cat > .env << EOF
DATABASE_URL=postgresql://housing:housing_password@localhost:5432/housing
FLASK_ENV=development
FLASK_DEBUG=True
EOF

echo "✅ .env file created"
echo ""

# Check if SSH tunnel is already running
echo "🔍 Checking for existing SSH tunnel..."
if lsof -Pi :5432 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "✅ SSH tunnel already running"
else
    echo "📡 Starting SSH tunnel to VPS database..."
    # Start SSH tunnel in background
    ssh -L 5432:housing-db:5432 root@72.61.179.126 -N &
    SSH_PID=$!
    sleep 2
    echo "✅ SSH tunnel started (PID: $SSH_PID)"
    echo "   To stop tunnel later: kill $SSH_PID"
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "🚀 Starting Flask development server..."
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "🌐 Access at: http://localhost:5000/housing"
echo ""
echo "💡 Tips:"
echo "   • Edit files and refresh browser to see changes"
echo "   • Press Ctrl+C to stop the server"
echo "   • SSH tunnel will keep running in background"
echo ""
echo "════════════════════════════════════════════════════════════════"
echo ""

cd "$PROJECT_DIR/webapp"
python3 app.py
