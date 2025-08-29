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
        # Cache bootstrap data for 10 minutes to avoid excessive API calls
        if (self._bootstrap_data is None or force_refresh or 
            (self._last_fetch and datetime.now() - self._last_fetch > timedelta(minutes=10))):
            
            logger.info("Fetching bootstrap data...")
            self._bootstrap_data = self._make_request("bootstrap-static/")
            self._last_fetch = datetime.now()
            
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
        """Calculate available free transfers for a manager"""
        try:
            current_gw = self.get_current_gameweek()
            
            # Get manager's transfer history
            history = self.get_manager_history(manager_id)
            if not history or 'current' not in history:
                return 1  # Default to 1 free transfer
            
            current_season = history['current']
            if not current_season:
                return 1
            
            # Get the last gameweek's transfer data
            last_gw_data = None
            for entry in reversed(current_season):
                if entry['event'] < current_gw:
                    last_gw_data = entry
                    break
            
            if not last_gw_data:
                return 1  # No previous gameweek data, default to 1
            
            # Calculate available transfers based on FPL rules:
            # - 1 free transfer per gameweek
            # - Unused transfers accumulate (max 2 total)
            # - Used transfers reduce available count
            
            transfers_used_last_gw = last_gw_data.get('event_transfers', 0)
            
            if transfers_used_last_gw == 0:
                # No transfers used last week, accumulate (max 2)
                return min(2, 2)  # 1 from last week + 1 new = 2 (capped at 2)
            elif transfers_used_last_gw == 1:
                # Used exactly 1 transfer (the free one), get 1 new
                return 1
            else:
                # Used more than 1 transfer (took hits), still get 1 new
                return 1
                
        except Exception as e:
            logger.warning(f"Error calculating available transfers: {e}")
            return 1  # Default fallback
    
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
        """Get the current gameweek number"""
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
