# FPL Assistant Pro ⚽

A professional-grade Fantasy Premier League analysis application that provides real-time player analytics, AI-powered transfer recommendations, and strategic chip planning to help you dominate your mini league.

## 🌟 Features

### 📊 Advanced Analytics
- **Real-time Player Analysis**: Live stats, form analysis, and performance metrics
- **Predictive Modeling**: AI-powered points predictions considering fixtures and form
- **Value Analysis**: Identify undervalued players and optimal price points
- **Differential Picks**: Find low-ownership gems with high potential

### 🔄 Transfer Optimization
- **Smart Transfer Recommendations**: Multi-gameweek optimization considering future fixtures
- **Risk Assessment**: Analyze when point hits are worthwhile
- **Position-Specific Analysis**: Tailored recommendations for each position
- **Budget Management**: Optimize transfers within your budget constraints

### 🎯 Chip Strategy Planning
- **Season-Long Planning**: Optimal timing for all chip usage
- **Fixture Analysis**: Identify double gameweeks and blank gameweeks
- **Bookmark System**: Mark specific gameweeks for chip usage
- **Strategic Insights**: Professional-grade chip timing recommendations

### 🏆 Mini League Intelligence
- **Competitor Tracking**: Monitor your league rivals' strategies
- **Gap Analysis**: Track points needed to climb rankings
- **Popular Picks**: Identify template players vs differentials
- **Strategic Advice**: Personalized tips based on your league position

### 📈 Professional Dashboard
- **Interactive Visualizations**: Beautiful charts and graphs
- **Real-time Updates**: Live data from the official FPL API
- **Mobile-Friendly**: Access from any device
- **Export Capabilities**: Save your analysis and recommendations

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ installed on your system
- Internet connection for FPL API access

### Installation

1. **Clone or download this repository**
   ```bash
   cd fpl-assistant
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Test the installation**
   ```bash
   python run_tests.py
   ```

4. **Launch the application**
   ```bash
   ./start_app.sh
   ```
   Or manually:
   ```bash
   streamlit run app.py
   ```

5. **Open your browser** and navigate to `http://localhost:8501`

## 📱 Usage Guide

### Initial Setup
1. **Enter Your Team Details**
   - Paste your FPL team URL (e.g., `https://fantasy.premierleague.com/entry/123456/`)
   - Or manually enter your Manager ID
   - Add your mini league URL: `https://fantasy.premierleague.com/leagues/37044/standings/c`

2. **Configure Strategy Preferences**
   - Set your risk appetite (Conservative/Balanced/Aggressive)
   - Choose whether to allow point hits
   - Set maximum transfers per week

### Main Features

#### 📊 Dashboard Tab
- **Team Overview**: Current squad, team value, and free transfers
- **Performance Tracking**: Gameweek points and rank progression
- **Key Metrics**: Overall rank, league position, and recent form

#### 🔄 Transfer Analysis Tab
- **AI Recommendations**: Get optimal transfer suggestions
- **Cost-Benefit Analysis**: See expected points vs transfer costs
- **Alternative Players**: Browse options by position
- **Transfer Summary**: Complete impact analysis

#### 🎯 Chip Strategy Tab
- **Season Planning**: Optimal timing for all chips
- **Fixture Analysis**: Upcoming gameweek difficulties
- **Bookmarking**: Mark preferred gameweeks for chip usage
- **Strategic Insights**: Professional timing recommendations

#### 🏆 League Analysis Tab
- **Live Standings**: Real-time league table
- **Gap Analysis**: Points needed for rank improvements
- **Competitor Tracking**: Monitor rival strategies
- **Strategic Advice**: Position-specific recommendations

#### 📈 Player Analytics Tab
- **Advanced Filtering**: Search by position, team, price
- **Value Analysis**: Price vs points visualization
- **Differential Picks**: Low-ownership, high-potential players
- **Form Analysis**: Recent performance trends

## 🎯 Pro Tips

### Transfer Strategy
- **Use the 6-week lookahead**: The system analyzes fixtures up to 6 gameweeks ahead
- **Consider chip timing**: Plan transfers around your chip strategy
- **Monitor value changes**: Act before price rises/falls
- **Balance template vs differentials**: Mix popular picks with unique choices

### Chip Usage
- **Wildcard**: Use before good fixture runs, typically GW8-12 or GW20-25
- **Bench Boost**: Save for double gameweeks when your bench will play
- **Triple Captain**: Use on premium players during double gameweeks or easy fixtures
- **Free Hit**: Perfect for blank gameweeks or unique fixture scenarios

### League Strategy
- **Track competitors**: Monitor what successful rivals are doing
- **Time differentials**: Use unique picks when you need to catch up
- **Play it safe when ahead**: Stick to template when protecting a lead
- **Plan for the endgame**: Have a strategy for the final 6-8 gameweeks

## 🔧 Advanced Configuration

### API Rate Limiting
The application includes intelligent caching to respect FPL API limits:
- Bootstrap data cached for 10 minutes
- Player data refreshed every 5 minutes during active hours
- Automatic retry logic for failed requests

### Data Sources
- **Official FPL API**: All player and team data
- **Real-time Updates**: Live gameweek information
- **Historical Analysis**: Season-long performance tracking

## 🐛 Troubleshooting

### Common Issues

**"Failed to load FPL data"**
- Check your internet connection
- The FPL API may be temporarily down (especially during gameweeks)
- Try refreshing the page

**"Invalid team URL format"**
- Ensure your URL follows the format: `https://fantasy.premierleague.com/entry/123456/`
- Try entering your Manager ID manually

**"Could not load current team data"**
- Your team/league may be private
- Check that your Manager ID is correct
- Some features require public league access

### Performance Tips
- **Use filtering**: Narrow down player searches to improve performance
- **Cache clearing**: Refresh data if you see outdated information
- **Browser compatibility**: Works best in Chrome, Firefox, Safari

## 📊 System Architecture

The FPL Assistant Pro is built with:
- **Backend**: Python with pandas, numpy, scikit-learn
- **Frontend**: Streamlit with plotly visualizations
- **Data Source**: Official FPL API
- **Analytics**: Custom algorithms for player scoring and predictions
- **Optimization**: Mathematical models for transfer recommendations

## 🔮 Future Enhancements

Planned features for future releases:
- **Machine Learning Models**: Enhanced prediction accuracy
- **Captaincy Analysis**: Advanced captain selection algorithms
- **Set Piece Specialists**: Corner/free kick takers analysis
- **Injury Tracking**: Real-time injury news integration
- **Price Change Predictions**: Forecast player price movements
- **Mobile App**: Native iOS/Android applications

## 💡 Contributing

This is a personal project, but suggestions and feedback are welcome! If you find bugs or have feature requests, please let me know.

## 📄 License

This project is for educational and personal use only. Please respect the FPL API terms of service.

---

**Ready to dominate your mini league? Let's get started! 🏆**

Your League: https://fantasy.premierleague.com/leagues/37044/standings/c
