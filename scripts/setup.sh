#!/usr/bin/env bash
set -euo pipefail

echo "=== NexusOS Setup ==="

# Check Python version
python3 -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ required'" || {
    echo "ERROR: Python 3.11+ is required"
    exit 1
}

# Copy env file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env from .env.example — please add your API keys"
fi

# Install core dependencies
cd core
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium || echo "Playwright install skipped (run manually if needed)"

# Create data directory
mkdir -p ../data

echo ""
echo "=== Setup Complete ==="
echo "Start with: docker-compose up --build"
echo "Or locally: cd core && uvicorn main:app --reload"
