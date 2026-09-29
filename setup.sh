#!/bin/bash
set -e

echo "--- Starting Project Setup (pyenv) ---"

# Ensure we are in the correct directory
cd "$(dirname "$0")"

# Reuse an existing environment and preserve the tracked dependency list.
if [ ! -d ".venv" ]; then
    echo "🐍 Creating new virtual environment..."
    python -m venv .venv
fi

# Activate and install
source .venv/bin/activate
echo "⚡ Environment activated."
echo "📦 Installing packages..."
pip install -r requirements.txt
echo "✅ Packages installed."

echo ""
echo "--- 🎉 Setup Complete! ---"
echo "The environment is ready. Run the GUI with:"
echo "python \"Gemini wav_TO_XpmV2.py\""
