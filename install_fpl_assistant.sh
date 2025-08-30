#!/bin/bash

# FPL Assistant Pro - Easy Installer
# No GitHub account required!

echo "🔥 Installing FPL Assistant Pro..."
echo "=================================="

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required. Please install Python 3 first."
    echo "   Download from: https://www.python.org/downloads/"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required. Please install pip first."
    exit 1
fi

echo "✅ Python 3 found"

# Create project directory
PROJECT_DIR="$HOME/fpl-assistant-pro"
echo "📁 Creating project directory at $PROJECT_DIR"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Create virtual environment
echo "🔧 Setting up virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install required packages
echo "📦 Installing packages..."
pip install streamlit pandas requests numpy scikit-learn

# Download the app files (you would need to provide these)
echo "⬇️  Downloading FPL Assistant files..."
echo "Note: You'll need to get the app files from your friend who has the code."

# Create a simple requirements file
cat > requirements.txt << EOF
streamlit>=1.28.0
pandas>=2.0.0
requests>=2.28.0
numpy>=1.24.0
scikit-learn>=1.3.0
EOF

# Create run script
cat > run_fpl_assistant.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
streamlit run app.py --server.port 8501
EOF

chmod +x run_fpl_assistant.sh

echo ""
echo "🎉 Installation setup complete!"
echo ""
echo "Next steps:"
echo "1. Get the app files from your friend"
echo "2. Place them in: $PROJECT_DIR"
echo "3. Run: ./run_fpl_assistant.sh"
echo ""
echo "The app will open in your browser at http://localhost:8501"
