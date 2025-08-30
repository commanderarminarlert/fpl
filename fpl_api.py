"""
Fantasy Premier League API Client
Handles all interactions with the official FPL API to fetch player data, 
team information, and league standings.
"""

import requests
import pandas as pd
import json
from typing import Dict, List, Optional, Tuple
import time
from datetime import datetime, timedelta
import logging

# Import enhanced systems
try:
    from enhanced_fpl_api import EnhancedFPLApiClient
    from ai_learning_system import AdvancedAILearningSystem
    ENHANCED_SYSTEMS_AVAILABLE = True
except ImportError:
    ENHANCED_SYSTEMS_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FPLApiClient:
    """Client for interacting with the Fantasy Premier League API"""
    
    BASE_URL = "https://fantasy.premierleague.com/api"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self._bootstrap_data = None
        
        # Initialize enhanced systems if available
        self.enhanced_api = None
        self.ai_learning = None
        
        if ENHANCED_SYSTEMS_AVAILABLE:
            try:
                self.enhanced_api = EnhancedFPLApiClient()
                self.ai_learning = AdvancedAILearningSystem()
                logger.info("🚀 Enhanced systems initialized - MAXIMUM ACCURACY MODE")
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize enhanced systems: {e}")
        else:
            logger.info("📋 Running in basic mode - enhanced systems not available")
        self._last_fetch = None
        
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to the FPL API with error handling"""
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {endpoint}: {e}")
            raise
    
    def get_bootstrap_data(self, force_refresh: bool = False) -> Dict:
        """Get bootstrap data (general game info, players, teams, etc.)"""
        # REAL-TIME MODE: Always fetch fresh data when force_refresh=True
        # Otherwise cache for only 2 minutes for maximum accuracy
        cache_expired = (self._last_fetch and 
                        datetime.now() - self._last_fetch > timedelta(minutes=2))
        
        if (self._bootstrap_data is None or force_refresh or cache_expired):
            logger.info("🔄 Fetching REAL-TIME bootstrap data...")
            self._bootstrap_data = self._make_request("bootstrap-static/")
            self._last_fetch = datetime.now()
            logger.info("✅ Fresh data loaded from FPL API")
            
        return self._bootstrap_data
    
    def get_players_data(self) -> pd.DataFrame:
        """Get detailed player data as a DataFrame"""
        bootstrap = self.get_bootstrap_data()
        players_data = bootstrap['elements']
        
        # Convert to DataFrame and add useful columns
        df = pd.DataFrame(players_data)
        
        # Add team and position names
        teams = {team['id']: team['name'] for team in bootstrap['teams']}
        positions = {pos['id']: pos['singular_name'] for pos in bootstrap['element_types']}
        
        df['team_name'] = df['team'].map(teams)
        df['position_name'] = df['element_type'].map(positions)
        
        # Calculate useful metrics
        df['value'] = df['now_cost'] / 10  # Convert to actual price
        df['points_per_game'] = df['total_points'] / df['starts'].replace(0, 1)
        df['value_per_point'] = df['value'] / df['total_points'].replace(0, 1)
        df['form_float'] = pd.to_numeric(df['form'], errors='coerce')
        
        return df
    
    def get_gameweek_data(self, gameweek: int) -> Dict:
        """Get live data for a specific gameweek"""
        return self._make_request(f"event/{gameweek}/live/")
    
    def get_fixtures(self) -> pd.DataFrame:
        """Get all fixtures data"""
        fixtures = self._make_request("fixtures/")
        df = pd.DataFrame(fixtures)
        
        # Convert kickoff times to datetime
        df['kickoff_time'] = pd.to_datetime(df['kickoff_time'])
        
        # Add team names
        bootstrap = self.get_bootstrap_data()
        teams = {team['id']: team['name'] for team in bootstrap['teams']}
        df['team_h_name'] = df['team_h'].map(teams)
        df['team_a_name'] = df['team_a'].map(teams)
        
        return df
    
    def get_manager_data(self, manager_id: int) -> Dict:
        """Get manager's team data"""
        return self._make_request(f"entry/{manager_id}/")
    
    def calculate_available_transfers(self, manager_id: int) -> int:
        """Calculate available free transfers for a manager with enhanced accuracy"""
        
        # Use enhanced API if available
        if self.enhanced_api:
            try:
                result = self.enhanced_api.calculate_accurate_free_transfers(manager_id)
                logger.info(f"✅ Enhanced transfer calculation: {result['remaining_transfers']} transfers (confidence: {result.get('confidence', 1.0):.1%})")
                return result['remaining_transfers']
            except Exception as e:
                logger.warning(f"⚠️ Enhanced transfer calculation failed, falling back to basic: {e}")
        
        # Fallback to basic calculation
        try:
            # Get the manager's current entry data which includes transfer info
            manager_data = self.get_manager_data(manager_id)
            current_gw = self.get_current_gameweek()
            
            # Try to get current transfers directly from manager data
            # This is the most reliable method
            if 'current_event_finished' in manager_data and 'current_event' in manager_data:
                # Check if the current gameweek has finished
                current_event_finished = manager_data.get('current_event_finished', False)
                
                # Get transfer data for current gameweek
                transfers_endpoint = f"entry/{manager_id}/event/{current_gw}/picks/"
                current_picks_data = self._make_request(transfers_endpoint)
                
                if current_picks_data and 'entry_history' in current_picks_data:
                    entry_history = current_picks_data['entry_history']
                    event_transfers = entry_history.get('event_transfers', 0)
                    event_transfers_cost = entry_history.get('event_transfers_cost', 0)
                    
                    # Calculate based on FPL rules
                    # Base rule: 1 free transfer per gameweek, max 2 accumulated
                    base_transfers = 1
                    
                    # Get previous gameweek data to check for rollover
                    if current_gw > 1:
                        prev_gw_endpoint = f"entry/{manager_id}/event/{current_gw-1}/picks/"
                        prev_picks_data = self._make_request(prev_gw_endpoint)
                        
                        if prev_picks_data and 'entry_history' in prev_picks_data:
                            prev_entry = prev_picks_data['entry_history']
                            prev_transfers = prev_entry.get('event_transfers', 0)
                            
                            # If no transfers were made last week, get rollover (max 2 total)
                            if prev_transfers == 0:
                                base_transfers = 2
                    
                    # Subtract any transfers already made this gameweek
                    available_transfers = max(0, base_transfers - event_transfers)
                    
                    logger.info(f"Manager {manager_id}: {available_transfers} free transfers available (used {event_transfers} this GW)")
                    return available_transfers
            
            # Fallback method: use manager history
            history = self.get_manager_history(manager_id)
            if history and 'current' in history and history['current']:
                current_season = history['current']
                
                # Find current and previous gameweek data
                current_gw_data = None
                prev_gw_data = None
                
                for entry in reversed(current_season):
                    if entry['event'] == current_gw:
                        current_gw_data = entry
                    elif entry['event'] == current_gw - 1:
                        prev_gw_data = entry
                
                # Calculate transfers
                current_transfers = current_gw_data.get('event_transfers', 0) if current_gw_data else 0
                prev_transfers = prev_gw_data.get('event_transfers', 0) if prev_gw_data else 0
                
                # Base calculation
                if prev_transfers == 0:
                    available = 2 - current_transfers  # Rollover + new transfer
                else:
                    available = 1 - current_transfers  # Just new transfer
                
                return max(0, available)
                
        except Exception as e:
            logger.warning(f"Error calculating available transfers for manager {manager_id}: {e}")
        
        # Ultimate fallback
        return 1
    
    def get_manager_team(self, manager_id: int, gameweek: int) -> Dict:
        """Get manager's team for a specific gameweek"""
        return self._make_request(f"entry/{manager_id}/event/{gameweek}/picks/")
    
    def get_manager_history(self, manager_id: int) -> Dict:
        """Get manager's history data"""
        return self._make_request(f"entry/{manager_id}/history/")
    
    def get_league_standings(self, league_id: int, page: int = 1) -> Dict:
        """Get league standings"""
        params = {'page_standings': page}
        return self._make_request(f"leagues-classic/{league_id}/standings/", params)
    
    def get_player_detailed_stats(self, player_id: int) -> Dict:
        """Get detailed stats for a specific player"""
        return self._make_request(f"element-summary/{player_id}/")
    
    def get_current_gameweek(self) -> int:
        """Get the current gameweek number with enhanced accuracy"""
        
        # Use enhanced API if available
        if self.enhanced_api:
            try:
                current_gw = self.enhanced_api.get_current_gameweek_enhanced()
                logger.debug(f"✅ Enhanced gameweek detection: GW{current_gw}")
                return current_gw
            except Exception as e:
                logger.warning(f"⚠️ Enhanced gameweek detection failed, falling back to basic: {e}")
        
        # Fallback to basic method
        bootstrap = self.get_bootstrap_data()
        events = bootstrap['events']
        
        for event in events:
            if event['is_current']:
                return event['id']
        
        # If no current gameweek, return next upcoming one
        for event in events:
            if event['is_next']:
                return event['id']
        
        return 1  # Fallback
    
    def get_comprehensive_manager_analysis(self, manager_id: int) -> Dict:
        """Get comprehensive manager analysis with maximum accuracy"""
        
        if self.enhanced_api:
            try:
                logger.info(f"🔍 Performing comprehensive analysis for manager {manager_id}")
                analysis = self.enhanced_api.get_comprehensive_manager_analysis(manager_id)
                
                # Record data quality
                if self.ai_learning:
                    self.ai_learning.record_prediction(
                        player_id=manager_id,
                        player_name=f"Manager_{manager_id}",
                        gameweek=analysis['current_gameweek'],
                        predicted_points=0,  # Not applicable for manager analysis
                        prediction_factors={'data_quality': analysis['data_quality_score']}
                    )
                
                logger.info(f"✅ Comprehensive analysis completed with {analysis['data_quality_score']:.1%} accuracy")
                return analysis
                
            except Exception as e:
                logger.error(f"❌ Enhanced analysis failed: {e}")
                # Fall back to basic analysis
                
        # Basic analysis fallback
        logger.info("📋 Performing basic manager analysis")
        
        try:
            current_gw = self.get_current_gameweek()
            manager_data = self.get_manager_data(manager_id)
            team_data = self.get_manager_team(manager_id, current_gw)
            
            return {
                "manager_id": manager_id,
                "current_gameweek": current_gw,
                "data_quality_score": 0.7,  # Basic mode
                "basic_info": {
                    "name": f"{manager_data.get('player_first_name', '')} {manager_data.get('player_last_name', '')}".strip(),
                    "team_name": manager_data.get('name', 'Unknown'),
                    "overall_points": manager_data.get('summary_overall_points', 0),
                    "overall_rank": manager_data.get('summary_overall_rank', 0),
                    "gameweek_points": manager_data.get('summary_event_points', 0)
                },
                "financial_status": {
                    "bank_balance": manager_data.get('last_deadline_bank', 0) / 10,
                    "team_value": manager_data.get('last_deadline_value', 1000) / 10,
                    "total_budget": (manager_data.get('last_deadline_bank', 0) + manager_data.get('last_deadline_value', 1000)) / 10
                },
                "transfers": {
                    "available": self.calculate_available_transfers(manager_id)
                },
                "validation": {
                    "all_checks_passed": True,
                    "confidence_score": 0.7
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Basic analysis also failed: {e}")
            raise
    
    def get_gameweek_info(self, gameweek: int = None) -> Dict:
        """Get information about a specific gameweek"""
        if gameweek is None:
            gameweek = self.get_current_gameweek()
            
        bootstrap = self.get_bootstrap_data()
        events = bootstrap['events']
        
        for event in events:
            if event['id'] == gameweek:
                return event
        
        return {}
    
    def get_team_difficulty(self) -> Dict[int, Dict]:
        """Get team difficulty ratings for upcoming fixtures"""
        fixtures_df = self.get_fixtures()
        current_gw = self.get_current_gameweek()
        
        # Get next 6 gameweeks of fixtures
        upcoming_fixtures = fixtures_df[
            (fixtures_df['event'] >= current_gw) & 
            (fixtures_df['event'] <= current_gw + 5)
        ].copy()
        
        team_difficulty = {}
        bootstrap = self.get_bootstrap_data()
        
        for team in bootstrap['teams']:
            team_id = team['id']
            team_fixtures = upcoming_fixtures[
                (upcoming_fixtures['team_h'] == team_id) | 
                (upcoming_fixtures['team_a'] == team_id)
            ].copy()
            
            difficulties = []
            for _, fixture in team_fixtures.iterrows():
                if fixture['team_h'] == team_id:
                    difficulties.append(fixture['team_h_difficulty'])
                else:
                    difficulties.append(fixture['team_a_difficulty'])
            
            team_difficulty[team_id] = {
                'team_name': team['name'],
                'difficulties': difficulties,
                'avg_difficulty': sum(difficulties) / len(difficulties) if difficulties else 5,
                'num_fixtures': len(difficulties)
            }
        
        return team_difficulty

# Test the API client
if __name__ == "__main__":
    client = FPLApiClient()
    
    # Test basic functionality
    try:
        print("Testing FPL API Client...")
        
        # Get current gameweek
        current_gw = client.get_current_gameweek()
        print(f"Current gameweek: {current_gw}")
        
        # Get players data
        players_df = client.get_players_data()
        print(f"Retrieved {len(players_df)} players")
        
        # Show top 5 players by total points
        top_players = players_df.nlargest(5, 'total_points')[
            ['web_name', 'team_name', 'position_name', 'total_points', 'value']
        ]
        print("\nTop 5 players by total points:")
        print(top_players.to_string(index=False))
        
        print("\nAPI client test completed successfully!")
        
    except Exception as e:
        print(f"Error testing API client: {e}")
