#!/bin/bash
# FPL Assistant Startup Script

echo "🚀 Starting FPL Assistant Pro..."
echo "=================================="

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Error: app.py not found. Please run this script from the fpl-assistant directory."
    exit 1
fi

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not installed."
    exit 1
fi

# Check if dependencies are installed
echo "🔍 Checking dependencies..."
python3 -c "import streamlit, pandas, plotly" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Dependencies not found. Installing..."
    pip install -r requirements.txt
fi

# Run tests
echo "🧪 Running quick tests..."
python3 run_tests.py
if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Please check the output above."
    exit 1
fi

echo ""
echo "✅ All tests passed!"
echo ""
echo "🌟 Starting FPL Assistant Pro..."
echo "💻 Open your browser and go to: http://localhost:8501"
echo ""
echo "📋 Quick Setup Instructions:"
echo "1. Enter your FPL team URL in the sidebar"
echo "2. Add your mini league URL: https://fantasy.premierleague.com/leagues/37044/standings/c"
echo "3. Configure your strategy preferences"
echo "4. Explore the different tabs for analysis and recommendations"
echo ""
echo "🛑 To stop the application, press Ctrl+C"
echo ""

# Launch Streamlit
streamlit run app.py
