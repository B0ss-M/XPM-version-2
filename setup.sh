#!/bin/bash
set -e

echo "--- Starting Project Setup (pyenv) ---"

# Ensure we are in the correct directory
cd "$(dirname "$0")"

# Create requirements.txt
echo "📄 Creating requirements.txt..."
cat > requirements.txt << EOL
Pillow
numpy
scipy
librosa
EOL

# Remove old virtual environment if it exists
if [ -d ".venv" ]; then
    echo "🗑️  Removing old virtual environment..."
    rm -rf .venv
fi

# Create new virtual environment.
# 'python' will now automatically be the pyenv version (3.12.4)
echo "🐍 Creating new virtual environment..."
python -m venv .venv
echo "✅ Virtual environment created."

# Activate and install
source .venv/bin/activate
echo "⚡ Environment activated."
echo "📦 Installing packages..."
pip install -r requirements.txt
echo "✅ Packages installed."

echo ""
echo "--- 🎉 Setup Complete! ---"
echo "The environment is ready. Run your app with:"
echo "python \"Gemini wav_TO_XpmV2.py\""