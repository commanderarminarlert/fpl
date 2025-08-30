# 🔥 FPL Assistant Pro - Easy Setup

Hey! Your friend sent you this awesome FPL analysis tool. Here's how to get it running:

## 🚀 Quick Start (5 minutes)

### Option 1: One-Click Installer (Mac/Linux)
1. **Download** the `FPL_Assistant_Pro.zip` file
2. **Unzip** it to a folder
3. **Open Terminal** and navigate to that folder:
   ```bash
   cd ~/Downloads/fpl-assistant  # or wherever you unzipped it
   ```
4. **Run the installer**:
   ```bash
   ./install_fpl_assistant.sh
   ```
5. **Start the app**:
   ```bash
   ./run_fpl_assistant.sh
   ```

### Option 2: Manual Setup (Windows/Mac/Linux)

#### Step 1: Install Python
- Download Python 3.8+ from [python.org](https://www.python.org/downloads/)
- ✅ Make sure to check "Add Python to PATH" during installation

#### Step 2: Install Dependencies
Open Command Prompt/Terminal and run:
```bash
pip install streamlit pandas requests numpy scikit-learn
```

#### Step 3: Run the App
1. Navigate to the unzipped folder
2. Run: `streamlit run app.py`
3. The app opens automatically in your browser at `http://localhost:8501`

## 🎯 How to Use

1. **Enter your FPL Manager ID** (found in your FPL URL)
2. **Add your Mini League URL** (optional)
3. **Explore the 6 tabs**:
   - 📊 **Dashboard**: Team overview
   - 🔄 **Transfer Analysis**: Smart fixture-aware recommendations
   - 🎯 **Chip Strategy**: Optimal timing for your chips
   - 🏆 **League Analysis**: Compare with mini league
   - 📈 **Player Analytics**: Deep player statistics
   - 🧠 **AI Learning**: System performance and insights

## 🔥 Features You'll Love

- **Smart Transfer Recommendations** (avoids bad fixture timing)
- **Chip Planning** for all 8 chips (2 of each type)
- **AI Learning System** (gets better over time)
- **Fixture Analysis** (15 gameweeks ahead)
- **League Comparison** tools
- **Alternative Player Suggestions**

## 🆘 Need Help?

**Can't find your Manager ID?**
- Go to fantasy.premierleague.com
- Click "Points" → your team name
- Your ID is the number in the URL: `/entry/YOUR_ID_HERE/`

**App won't start?**
- Make sure Python 3.8+ is installed
- Try: `python3 -m streamlit run app.py`
- Check you're in the right folder with the app files

**Still stuck?**
- Ask your friend who sent this to you!
- All the code is included so it runs offline

## 🎉 Enjoy!

This tool uses the same advanced analytics that top FPL players use. Have fun climbing those rankings! 🚀

---
*Created by your friend who clearly knows what they're doing with FPL! 😄*
