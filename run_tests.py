#!/usr/bin/env python3
"""
Test runner for FPL Assistant
Validates all components are working correctly
"""

import sys
import traceback
from datetime import datetime

def test_api_client():
    """Test the FPL API client"""
    print("🔌 Testing FPL API Client...")
    
    try:
        from fpl_api import FPLApiClient
        
        client = FPLApiClient()
        
        # Test basic data fetching
        print("  - Fetching bootstrap data...")
        bootstrap = client.get_bootstrap_data()
        assert 'elements' in bootstrap, "Bootstrap data missing elements"
        assert 'teams' in bootstrap, "Bootstrap data missing teams"
        print(f"  ✅ Retrieved data for {len(bootstrap['elements'])} players")
        
        # Test players dataframe
        print("  - Creating players DataFrame...")
        players_df = client.get_players_data()
        assert len(players_df) > 500, "Not enough players in DataFrame"
        print(f"  ✅ Created DataFrame with {len(players_df)} players")
        
        # Test current gameweek
        print("  - Getting current gameweek...")
        current_gw = client.get_current_gameweek()
        assert 1 <= current_gw <= 38, "Invalid gameweek number"
        print(f"  ✅ Current gameweek: {current_gw}")
        
        # Test fixtures
        print("  - Fetching fixtures...")
        fixtures_df = client.get_fixtures()
        assert len(fixtures_df) > 0, "No fixtures found"
        print(f"  ✅ Retrieved {len(fixtures_df)} fixtures")
        
        print("✅ FPL API Client - All tests passed!\n")
        return True
        
    except Exception as e:
        print(f"❌ FPL API Client test failed: {e}")
        traceback.print_exc()
        return False

def test_analysis_engine():
    """Test the analysis engine"""
    print("🧠 Testing Analysis Engine...")
    
    try:
        from fpl_api import FPLApiClient
        from analysis_engine import AnalysisEngine
        
        api = FPLApiClient()
        engine = AnalysisEngine(api)
        
        # Test data update
        print("  - Updating analysis data...")
        engine.update_data()
        assert engine.players_df is not None, "Players data not loaded"
        assert len(engine.players_df) > 500, "Not enough players loaded"
        print(f"  ✅ Loaded {len(engine.players_df)} players for analysis")
        
        # Test player scoring
        print("  - Calculating player scores...")
        scored_players = engine.calculate_player_scores()
        assert 'total_score' in scored_players.columns, "Player scores not calculated"
        assert not scored_players['total_score'].isna().all(), "All scores are NaN"
        print("  ✅ Player scoring system working")
        
        # Test predictions
        print("  - Testing player predictions...")
        top_player_id = scored_players.iloc[0]['id']
        predicted_points = engine.predict_player_points(top_player_id, 6)
        assert predicted_points >= 0, "Negative prediction"
        assert predicted_points < 200, "Unrealistic prediction"
        print(f"  ✅ Prediction for top player: {predicted_points:.1f} points")
        
        # Test captain recommendations
        print("  - Testing captain recommendations...")
        mock_team = scored_players.head(15)['id'].tolist()
        captains = engine.get_captain_recommendations(mock_team)
        assert len(captains) > 0, "No captain recommendations"
        print(f"  ✅ Generated {len(captains)} captain recommendations")
        
        print("✅ Analysis Engine - All tests passed!\n")
        return True
        
    except Exception as e:
        print(f"❌ Analysis Engine test failed: {e}")
        traceback.print_exc()
        return False

def test_transfer_optimizer():
    """Test the transfer optimizer"""
    print("🔄 Testing Transfer Optimizer...")
    
    try:
        from fpl_api import FPLApiClient
        from analysis_engine import AnalysisEngine
        from transfer_optimizer import TransferOptimizer, ChipPlanner
        from models import UserStrategy, ChipType
        
        api = FPLApiClient()
        analysis = AnalysisEngine(api)
        optimizer = TransferOptimizer(api, analysis)
        
        # Update data
        print("  - Updating optimizer data...")
        optimizer.update_data()
        print("  ✅ Data updated successfully")
        
        # Create mock user strategy
        print("  - Creating mock user strategy...")
        user_strategy = UserStrategy(
            manager_id=123456,
            team_name="Test Team",
            current_team_value=100.0,
            free_transfers=1,
            bank=2.5,
            total_points=500,
            overall_rank=100000,
            league_rank=5,
            chips_remaining=[ChipType.WILDCARD, ChipType.BENCH_BOOST],
            planned_chips=[]
        )
        print("  ✅ Mock strategy created")
        
        # Test transfer optimization with mock team
        print("  - Testing transfer optimization...")
        scored_players = analysis.calculate_player_scores()
        mock_team = scored_players.head(15)['id'].tolist()
        
        transfers = optimizer.optimize_transfers(
            user_strategy, mock_team, max_transfers=2, allow_hits=True
        )
        
        print(f"  ✅ Generated {len(transfers)} transfer recommendations")
        
        # Test chip planner
        print("  - Testing chip planner...")
        planner = ChipPlanner(api, analysis)
        chip_strategies = planner.create_chip_strategy(user_strategy)
        assert len(chip_strategies) > 0, "No chip strategies generated"
        print(f"  ✅ Generated {len(chip_strategies)} chip strategies")
        
        print("✅ Transfer Optimizer - All tests passed!\n")
        return True
        
    except Exception as e:
        print(f"❌ Transfer Optimizer test failed: {e}")
        traceback.print_exc()
        return False

def test_app_components():
    """Test app components"""
    print("🖥️  Testing App Components...")
    
    try:
        # Test imports
        print("  - Testing imports...")
        import streamlit as st
        import pandas as pd
        import plotly.express as px
        import plotly.graph_objects as go
        print("  ✅ All dependencies imported successfully")
        
        # Test our modules
        print("  - Testing module imports...")
        from app import extract_manager_id_from_url, extract_league_id_from_url
        print("  ✅ App utility functions imported")
        
        # Test URL extraction
        print("  - Testing URL extraction...")
        test_team_url = "https://fantasy.premierleague.com/entry/123456/"
        manager_id = extract_manager_id_from_url(test_team_url)
        assert manager_id == 123456, f"Expected 123456, got {manager_id}"
        
        test_league_url = "https://fantasy.premierleague.com/leagues/37044/standings/c"
        league_id = extract_league_id_from_url(test_league_url)
        assert league_id == 37044, f"Expected 37044, got {league_id}"
        print("  ✅ URL extraction working correctly")
        
        print("✅ App Components - All tests passed!\n")
        return True
        
    except Exception as e:
        print(f"❌ App Components test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 FPL Assistant - Test Suite")
    print("=" * 50)
    print(f"Starting tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        test_api_client,
        test_analysis_engine,
        test_transfer_optimizer,
        test_app_components
    ]
    
    results = []
    
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    # Summary
    print("=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED! ({passed}/{total})")
        print("\n✅ Your FPL Assistant is ready to use!")
        print("Run: streamlit run app.py")
    else:
        print(f"⚠️  SOME TESTS FAILED ({passed}/{total})")
        print("\n❌ Please check the errors above before running the app.")
        
    print(f"\nTest completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
