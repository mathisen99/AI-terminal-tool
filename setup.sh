#!/bin/bash
# Setup script for Lolo AI Terminal Assistant
# This script sets up the Python virtual environment and installs dependencies

set -e  # Exit on error

echo "=========================================="
echo "  Lolo AI Terminal Assistant - Setup"
echo "=========================================="
echo ""

# Check if uv is installed
echo "Checking for UV package manager..."
if ! command -v uv &> /dev/null; then
    echo "❌ Error: UV is not installed"
    echo ""
    echo "UV is required for package management in this project."
    echo "Install UV with one of these methods:"
    echo ""
    echo "  1. Using the official installer (recommended):"
    echo "     curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    echo "  2. Using pip:"
    echo "     pip install uv"
    echo ""
    echo "  3. Using Homebrew (macOS/Linux):"
    echo "     brew install uv"
    echo ""
    echo "After installation, restart your terminal and run this script again."
    exit 1
fi

echo "✓ UV is installed"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo ""
    echo "Creating .env file from template..."
    echo "OPENAI_API_KEY=your_api_key_here" > .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your OpenAI API key before running the assistant!"
    echo ""
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
    echo "✓ Virtual environment created"
    echo ""
else
    echo "✓ Virtual environment already exists"
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "Installing dependencies..."
uv pip install -r requirements.txt
echo "✓ Dependencies installed"
echo ""

# Create .lolo directory for memory storage
LOLO_DIR="$HOME/.lolo"
if [ ! -d "$LOLO_DIR" ]; then
    echo "Creating .lolo directory for memory storage..."
    mkdir -p "$LOLO_DIR"
    echo "✓ Created $LOLO_DIR"
    echo ""
fi

echo "=========================================="
echo "  Setup Complete! ✓"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "  1. Activate the virtual environment:"
echo "     source .venv/bin/activate"
echo ""
echo "  2. Make sure your OpenAI API key is set in .env"
echo ""
echo "  3. Run the assistant:"
echo "     python main.py \"Your question here\""
echo ""
echo "  Or use uv run (auto-activates venv):"
echo "     uv run main.py \"Your question here\""
echo ""
echo "For more information, see README.md"
echo ""
