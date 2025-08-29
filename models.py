"""
Data models for the FPL Assistant application
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from datetime import datetime
from enum import Enum

class ChipType(Enum):
    WILDCARD = "wildcard"
    FREE_HIT = "freehit"
    BENCH_BOOST = "bboost"
    TRIPLE_CAPTAIN = "3xc"

class Position(Enum):
    GOALKEEPER = "GKP"
    DEFENDER = "DEF"
    MIDFIELDER = "MID"
    FORWARD = "FWD"

@dataclass
class Player:
    """Represents a Fantasy Premier League player"""
    id: int
    web_name: str
    full_name: str
    team_id: int
    team_name: str
    position: Position
    price: float
    total_points: int
    form: float
    points_per_game: float
    minutes: int
    goals_scored: int
    assists: int
    clean_sheets: int
    goals_conceded: int
    own_goals: int
    penalties_saved: int
    penalties_missed: int
    yellow_cards: int
    red_cards: int
    saves: int
    bonus: int
    bps: int  # Bonus points system
    influence: float
    creativity: float
    threat: float
    ict_index: float
    starts: int
    expected_goals: float
    expected_assists: float
    expected_goal_involvements: float
    expected_goals_conceded: float
    
    # Calculated fields
    value_per_point: float = field(init=False)
    form_rating: str = field(init=False)
    
    def __post_init__(self):
        self.value_per_point = self.price / max(self.total_points, 1)
        
        if self.form >= 6.0:
            self.form_rating = "Excellent"
        elif self.form >= 4.5:
            self.form_rating = "Good"
        elif self.form >= 3.0:
            self.form_rating = "Average"
        elif self.form >= 1.5:
            self.form_rating = "Poor"
        else:
            self.form_rating = "Very Poor"

@dataclass
class Team:
    """Represents an FPL team"""
    id: int
    name: str
    short_name: str
    strength: int
    strength_overall_home: int
    strength_overall_away: int
    strength_attack_home: int
    strength_attack_away: int
    strength_defence_home: int
    strength_defence_away: int
    pulse_id: int

@dataclass
class Fixture:
    """Represents a fixture"""
    id: int
    gameweek: int
    team_h: int
    team_a: int
    team_h_name: str
    team_a_name: str
    team_h_difficulty: int
    team_a_difficulty: int
    kickoff_time: datetime
    finished: bool
    started: bool
    team_h_score: Optional[int] = None
    team_a_score: Optional[int] = None

@dataclass
class PlayerGameweekStats:
    """Player performance in a specific gameweek"""
    player_id: int
    gameweek: int
    minutes: int
    goals_scored: int
    assists: int
    clean_sheets: int
    goals_conceded: int
    own_goals: int
    penalties_saved: int
    penalties_missed: int
    yellow_cards: int
    red_cards: int
    saves: int
    bonus: int
    bps: int
    influence: float
    creativity: float
    threat: float
    ict_index: float
    total_points: int
    was_home: bool
    opponent_team: int
    difficulty: int

@dataclass
class ChipStrategy:
    """Represents a planned chip usage strategy"""
    chip_type: ChipType
    planned_gameweek: int
    priority: int  # 1 = highest priority
    reason: str
    locked: bool = False  # If True, this chip timing is confirmed
    
@dataclass
class UserStrategy:
    """User's overall FPL strategy"""
    manager_id: int
    team_name: str
    current_team_value: float
    free_transfers: int
    bank: float
    total_points: int
    overall_rank: int
    league_rank: int
    
    # Chip strategy
    chips_remaining: List[ChipType]
    planned_chips: List[ChipStrategy]
    
    # Transfer strategy
    transfer_targets: List[int] = field(default_factory=list)  # Player IDs
    transfer_budget: float = 0.0
    priority_positions: List[Position] = field(default_factory=list)
    
    # Season targets
    target_overall_rank: Optional[int] = None
    target_league_rank: int = 1

@dataclass
class TransferRecommendation:
    """A recommended transfer"""
    player_out_id: int
    player_in_id: int
    player_out_name: str
    player_in_name: str
    cost_change: float  # Positive means more expensive
    points_potential: float  # Expected additional points over next 6 GWs
    confidence: float  # 0-1 confidence score
    reason: str
    priority: int  # 1 = highest priority
    
@dataclass
class WeeklyRecommendation:
    """Complete weekly recommendation package"""
    gameweek: int
    deadline: datetime
    
    # Transfer recommendations
    recommended_transfers: List[TransferRecommendation]
    free_transfers_available: int
    suggested_hits: int  # Number of point hits to take
    
    # Team selection
    recommended_captain: int  # Player ID
    recommended_vice_captain: int  # Player ID
    recommended_lineup: List[int]  # 11 Player IDs in order
    recommended_bench: List[int]  # 4 Player IDs in order
    
    # Chip recommendation
    recommended_chip: Optional[ChipType] = None
    chip_reasoning: str = ""
    
    # Overall strategy
    strategy_notes: str = ""
    risk_level: str = "Medium"  # Low, Medium, High
    expected_points: float = 0.0
    confidence: float = 0.0

@dataclass
class LeagueCompetitor:
    """Information about a mini-league competitor"""
    manager_id: int
    team_name: str
    player_name: str
    total_points: int
    rank: int
    last_gw_points: int
    team_value: float
    
    # Analysis
    points_gap: int = 0  # Gap to user's team
    recent_form: float = 0.0  # Average points last 3 GWs
    threat_level: str = "Low"  # Low, Medium, High
    
@dataclass
class MiniLeagueAnalysis:
    """Analysis of the user's mini-league"""
    league_id: int
    league_name: str
    user_rank: int
    total_teams: int
    
    competitors: List[LeagueCompetitor]
    
    # Strategic insights
    points_to_leader: int = 0
    points_to_next_rank: int = 0
    average_team_value: float = 0.0
    user_vs_average_value: float = 0.0
    
    # Recommendations
    key_differentials: List[int] = field(default_factory=list)  # Player IDs
    popular_picks: List[int] = field(default_factory=list)  # Player IDs
    strategic_advice: str = ""
