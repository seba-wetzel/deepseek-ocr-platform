#!/bin/bash
set -e

echo "=== DeepSeek OCR Platform Installer ==="

# 1. System Dependencies (Debian/Ubuntu)
echo "[1/3] Checking system dependencies..."
if command -v apt-get &> /dev/null; then
    echo "Detected apt-based system. Installing poppler-utils and python3-venv..."
    # sudo is required for apt-get, assuming user has sudo access or runs as root specific parts if needed
    # We use sudo here assuming standard user setup.
    sudo apt-get update
    sudo apt-get install -y poppler-utils python3-venv python3-pip git
else
    echo "⚠️  Warning: 'apt-get' not found. Please ensure 'poppler-utils' and 'python3-venv' are installed manually for your distribution."
fi

# 2. Backend Setup
echo "[2/3] Setting up Backend..."
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
pip install git+https://github.com/deepseek-ai/DeepSeek-VL.git
pip install huggingface_hub

echo "Downloading Model (this may take a while)..."
python3 download_model.py

# 3. Frontend Setup
echo "[3/3] Setting up Frontend..."
if [ -d "frontend" ]; then
    cd frontend
    echo "Installing Node.js dependencies..."
    npm install
    cd ..
else
    echo "❌ Error: 'frontend' directory not found."
    exit 1
fi

echo ""
echo "✅ Installation Complete!"
echo "You can now run the platform using: ./start.sh"
