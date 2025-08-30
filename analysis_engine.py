"""
Analysis Engine for FPL Assistant
Provides advanced analytics, predictions, and recommendations
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

from models import (
    Player, Team, Fixture, PlayerGameweekStats, TransferRecommendation,
    WeeklyRecommendation, ChipType, Position, UserStrategy, LeagueCompetitor,
    MiniLeagueAnalysis, ChipStrategy
)
from fpl_api import FPLApiClient
try:
    from learning_engine import (
        LearningEngine, PredictionRecord, create_prediction_id, 
        extract_prediction_factors
    )
    LEARNING_AVAILABLE = True
except ImportError:
    LEARNING_AVAILABLE = False
    logger.warning("Learning engine not available - running in basic mode")

logger = logging.getLogger(__name__)

class AnalysisEngine:
    """Advanced analysis engine for FPL recommendations"""
    
    def __init__(self, api_client: FPLApiClient):
        self.api = api_client
        self.players_df = None
        self.fixtures_df = None
        # Initialize learning system if available
        if LEARNING_AVAILABLE:
            try:
                self.learning_engine = LearningEngine()
            except Exception as e:
                logger.warning(f"Could not initialize learning engine: {e}")
                self.learning_engine = None
        else:
            self.learning_engine = None
        self.teams_df = None
        self._prediction_models = {}
        self._last_model_update = None
        
    def update_data(self, force_refresh: bool = False):
        """Update all data from the API"""
        logger.info("Updating analysis data...")
        
        try:
            self.players_df = self.api.get_players_data()
            self.fixtures_df = self.api.get_fixtures()
            
            # Create teams dataframe
            bootstrap = self.api.get_bootstrap_data(force_refresh)
            self.teams_df = pd.DataFrame(bootstrap['teams'])
            
            logger.info(f"Updated data: {len(self.players_df)} players, {len(self.fixtures_df)} fixtures")
            
        except Exception as e:
            logger.error(f"Error updating data: {e}")
            raise
    
    def calculate_player_scores(self) -> pd.DataFrame:
        """Calculate comprehensive player scores for recommendations using learning-enhanced weights"""
        if self.players_df is None:
            self.update_data()
        
        df = self.players_df.copy()
        
        # Get updated weights from learning engine (if available)
        if self.learning_engine:
            weights = self.learning_engine.factor_weights
        else:
            # Default weights if learning engine not available
            weights = {
                'form_weight': 0.30,
                'value_weight': 0.25,
                'minutes_weight': 0.20,
                'recent_weight': 0.15,
                'bonus_weight': 0.10
            }
        
        # Calculate scores using learned weights (convert to percentages)
        form_weight = weights.get('form_weight', 0.30) * 100
        value_weight = weights.get('value_weight', 0.25) * 100
        minutes_weight = weights.get('minutes_weight', 0.20) * 100
        recent_weight = weights.get('recent_weight', 0.15) * 100
        bonus_weight = weights.get('bonus_weight', 0.10) * 100
        
        # Form score (adaptive weight)
        df['form_score'] = (df['form_float'] / df['form_float'].max()) * form_weight
        
        # Value score (adaptive weight) - higher score for better value
        df['value_score'] = (1 / df['value_per_point']) / (1 / df['value_per_point']).max() * value_weight
        
        # Minutes played score (adaptive weight)
        df['minutes_score'] = (df['minutes'] / df['minutes'].max()) * minutes_weight
        
        # Recent performance (adaptive weight)
        df['recent_score'] = (df['points_per_game'] / df['points_per_game'].max()) * recent_weight
        
        # Bonus potential (adaptive weight)
        df['bonus_score'] = (df['bonus'] / df['bonus'].max()) * bonus_weight
        
        # Combine all scores
        df['total_score'] = (
            df['form_score'].fillna(0) +
            df['value_score'].fillna(0) +
            df['minutes_score'].fillna(0) +
            df['recent_score'].fillna(0) +
            df['bonus_score'].fillna(0)
        )
        
        return df
    
    def predict_player_points(self, player_id: int, gameweeks: int = 6, record_prediction: bool = True) -> float:
        """Predict points for a player over the next N gameweeks with learning integration"""
        if self.players_df is None:
            self.update_data()
        
        player = self.players_df[self.players_df['id'] == player_id].iloc[0]
        
        # Get upcoming fixtures difficulty
        team_difficulty = self.api.get_team_difficulty()
        team_id = player['team']
        
        if team_id in team_difficulty:
            avg_difficulty = team_difficulty[team_id]['avg_difficulty']
            num_fixtures = min(team_difficulty[team_id]['num_fixtures'], gameweeks)
        else:
            avg_difficulty = 3.0  # Default
            num_fixtures = gameweeks
        
        # Base prediction on recent form and adjust for difficulty
        base_points = player['points_per_game'] * num_fixtures
        
        # Use learning-enhanced weights for multipliers (if available)
        if self.learning_engine:
            weights = self.learning_engine.factor_weights
        else:
            weights = {'fixture_difficulty_weight': 0.15, 'form_weight': 0.30}
        
        difficulty_impact = weights.get('fixture_difficulty_weight', 0.15) * 2  # Scale up for multiplier
        form_impact = weights.get('form_weight', 0.30) * 0.2  # Scale for multiplier
        
        # Adjust for fixture difficulty (easier fixtures = more points)
        difficulty_multiplier = 1.0 + (3.0 - avg_difficulty) * difficulty_impact
        
        # Adjust for form
        form_multiplier = 1.0 + (player['form_float'] - 3.0) * form_impact
        
        predicted_points = base_points * difficulty_multiplier * form_multiplier
        predicted_points = max(0, predicted_points)
        
        # Record prediction for learning (if enabled and available)
        if record_prediction and self.learning_engine and LEARNING_AVAILABLE:
            try:
                current_gw = self.api.get_current_gameweek()
                prediction_id = create_prediction_id(player_id, current_gw, 'points')
                factors = extract_prediction_factors(player, avg_difficulty)
                confidence = self.learning_engine.get_prediction_confidence(player_id, 'points')
                
                prediction_record = PredictionRecord(
                    prediction_id=prediction_id,
                    player_id=player_id,
                    gameweek=current_gw,
                    prediction_type='points',
                    predicted_value=predicted_points,
                    confidence=confidence,
                    factors_used=factors
                )
                
                self.learning_engine.record_prediction(prediction_record)
            except Exception as e:
                logger.warning(f"Could not record prediction: {e}")
        
        return predicted_points
    
    def _analyze_transfer_fixtures(self, player_out_id: int, player_in_id: int, 
                                 player_out_name: str, player_in_name: str) -> Dict:
        """Comprehensive fixture analysis for transfer recommendations"""
        
        if self.players_df is None:
            self.update_data()
        
        current_gw = self.api.get_current_gameweek()
        
        # Get player data
        player_out = self.players_df[self.players_df['id'] == player_out_id].iloc[0]
        player_in = self.players_df[self.players_df['id'] == player_in_id].iloc[0]
        
        # Get team fixture difficulties for next 7 gameweeks (immediate + 6 ahead)
        team_difficulty = self.api.get_team_difficulty()
        
        player_out_team = player_out['team']
        player_in_team = player_in['team']
        
        # Get difficulties
        out_difficulties = team_difficulty.get(player_out_team, {}).get('difficulties', [3] * 7)[:7]
        in_difficulties = team_difficulty.get(player_in_team, {}).get('difficulties', [3] * 7)[:7]
        
        # Ensure we have 7 weeks of data
        while len(out_difficulties) < 7:
            out_difficulties.append(3)
        while len(in_difficulties) < 7:
            in_difficulties.append(3)
        
        # Immediate fixture analysis (next gameweek)
        immediate_out_diff = out_difficulties[0]
        immediate_in_diff = in_difficulties[0]
        immediate_advantage = immediate_out_diff - immediate_in_diff
        
        # Short-term analysis (next 3 gameweeks)
        short_term_out = sum(out_difficulties[:3]) / 3
        short_term_in = sum(in_difficulties[:3]) / 3
        short_term_advantage = short_term_out - short_term_in
        
        # Medium-term analysis (next 6 gameweeks)
        medium_term_out = sum(out_difficulties[1:7]) / 6  # Exclude immediate
        medium_term_in = sum(in_difficulties[1:7]) / 6
        medium_term_advantage = medium_term_out - medium_term_in
        
        # Overall advantage (weighted)
        overall_advantage = (
            immediate_advantage * 0.4 +  # 40% weight on immediate
            short_term_advantage * 0.4 + # 40% weight on next 3 GWs
            medium_term_advantage * 0.2  # 20% weight on GW 4-7
        )
        
        # Base points prediction
        points_out = self.predict_player_points(player_out_id, gameweeks=6, record_prediction=False)
        points_in = self.predict_player_points(player_in_id, gameweeks=6, record_prediction=False)
        points_potential = points_in - points_out
        
        # Fixture adjustment to points potential
        fixture_multiplier = 1.0 + (overall_advantage * 0.15)  # Each difficulty point difference = 15% impact
        adjusted_points_potential = points_potential * fixture_multiplier
        
        # Decision logic
        should_recommend = True
        warning_flags = []
        
        # Red flags that should prevent recommendation
        if immediate_in_diff >= 4 and immediate_advantage <= -1:
            should_recommend = False
            warning_flags.append("Very difficult immediate fixture")
        
        if immediate_in_diff >= 4 and short_term_in >= 3.5:
            should_recommend = False
            warning_flags.append("Difficult run of fixtures ahead")
        
        if adjusted_points_potential <= 0.5:
            should_recommend = False
            warning_flags.append("Minimal point improvement expected")
        
        # Generate detailed reasoning
        if should_recommend:
            fixture_assessment = self._get_fixture_assessment(in_difficulties[:6])
            timing_advice = self._get_timing_advice(immediate_advantage, short_term_advantage)
            
            detailed_reason = f"Upgrade: {player_in_name} has {fixture_assessment} ({timing_advice})"
            
            # Add specific fixture warnings if needed
            if immediate_in_diff >= 4:
                detailed_reason += f" ⚠️ Tough immediate fixture (difficulty {immediate_in_diff})"
            elif immediate_in_diff <= 2:
                detailed_reason += f" ✨ Great immediate fixture (difficulty {immediate_in_diff})"
            
        else:
            detailed_reason = f"⚠️ AVOID: {player_in_name} - {', '.join(warning_flags)}"
        
        # Confidence calculation
        confidence = min(abs(adjusted_points_potential) / 15.0, 1.0)
        if immediate_in_diff >= 4:
            confidence *= 0.7  # Reduce confidence for difficult immediate fixtures
        
        return {
            'should_recommend': should_recommend,
            'points_potential': max(adjusted_points_potential, 0) if should_recommend else 0,
            'confidence': confidence,
            'detailed_reason': detailed_reason,
            'immediate_advantage': immediate_advantage,
            'fixture_analysis': {
                'immediate_difficulty': immediate_in_diff,
                'short_term_avg': round(short_term_in, 1),
                'medium_term_avg': round(medium_term_in, 1),
                'overall_advantage': round(overall_advantage, 2)
            }
        }
    
    def _get_fixture_assessment(self, difficulties: List[int]) -> str:
        """Get human-readable fixture assessment"""
        avg_diff = sum(difficulties) / len(difficulties)
        
        if avg_diff <= 2.0:
            return "excellent fixtures ahead"
        elif avg_diff <= 2.5:
            return "good fixture run"
        elif avg_diff <= 3.0:
            return "decent fixtures"
        elif avg_diff <= 3.5:
            return "mixed fixtures"
        else:
            return "challenging fixtures"
    
    def _get_timing_advice(self, immediate_adv: float, short_term_adv: float) -> str:
        """Get timing advice for the transfer"""
        if immediate_adv >= 1.0:
            return "excellent timing"
        elif immediate_adv >= 0.5:
            return "good timing"
        elif immediate_adv >= 0:
            return "reasonable timing"
        elif immediate_adv >= -0.5:
            return "consider waiting"
        else:
            return "poor timing - wait if possible"
    
    def get_learning_insights(self) -> Dict:
        """Get learning insights and system performance"""
        if self.learning_engine:
            return self.learning_engine.generate_learning_report()
        else:
            return {
                'summary': {
                    'total_predictions_made': 0,
                    'completed_predictions': 0,
                    'overall_accuracy': 0,
                    'learning_confidence': 0
                },
                'top_insights': [],
                'current_weights': {
                    'form_weight': 0.30,
                    'value_weight': 0.25,
                    'minutes_weight': 0.20,
                    'recent_weight': 0.15,
                    'bonus_weight': 0.10
                },
                'recommendations': ["Learning system not available - using default weights"]
            }
    
    def update_learning_weights(self):
        """Manually trigger weight updates based on learning"""
        if self.learning_engine:
            self.learning_engine.update_factor_weights()
            logger.info("Updated analysis weights based on learning insights")
        else:
            logger.warning("Learning engine not available - cannot update weights")
    
    def get_transfer_recommendations(self, user_strategy: UserStrategy, 
                                   current_team: List[int], 
                                   num_recommendations: int = 5) -> List[TransferRecommendation]:
        """Generate transfer recommendations based on current team and strategy"""
        
        if self.players_df is None:
            self.update_data()
        
        recommendations = []
        scored_players = self.calculate_player_scores()
        
        # Get current team players
        current_players = scored_players[scored_players['id'].isin(current_team)]
        available_players = scored_players[~scored_players['id'].isin(current_team)]
        
        # For each position, find potential upgrades
        for position in ['Goalkeeper', 'Defender', 'Midfielder', 'Forward']:
            current_pos_players = current_players[current_players['position_name'] == position]
            available_pos_players = available_players[available_players['position_name'] == position]
            
            if len(current_pos_players) == 0 or len(available_pos_players) == 0:
                continue
            
            # Find worst performing player in position to potentially transfer out
            worst_current = current_pos_players.nsmallest(1, 'total_score')
            if len(worst_current) == 0:
                continue
                
            worst_player = worst_current.iloc[0]
            
            # Find best available players in this position within budget
            budget = user_strategy.bank + worst_player['value']
            affordable_players = available_pos_players[available_pos_players['value'] <= budget]
            
            if len(affordable_players) == 0:
                continue
            
            # Get top candidates
            top_candidates = affordable_players.nlargest(3, 'total_score')
            
            for _, candidate in top_candidates.iterrows():
                if candidate['total_score'] > worst_player['total_score']:
                    
                    # Enhanced fixture-aware scoring
                    transfer_analysis = self._analyze_transfer_fixtures(
                        worst_player['id'], candidate['id'], 
                        worst_player['web_name'], candidate['web_name']
                    )
                    
                    # Only recommend if transfer makes sense for both immediate and medium-term
                    if transfer_analysis['should_recommend']:
                        recommendation = TransferRecommendation(
                            player_out_id=int(worst_player['id']),
                            player_in_id=int(candidate['id']),
                            player_out_name=worst_player['web_name'],
                            player_in_name=candidate['web_name'],
                            cost_change=candidate['value'] - worst_player['value'],
                            points_potential=transfer_analysis['points_potential'],
                            confidence=transfer_analysis['confidence'],
                            reason=transfer_analysis['detailed_reason'],
                            priority=len(recommendations) + 1
                        )
                        recommendations.append(recommendation)
        
        # Sort by points potential and return top recommendations
        recommendations.sort(key=lambda x: x.points_potential, reverse=True)
        return recommendations[:num_recommendations]
    
    def recommend_chip_usage(self, user_strategy: UserStrategy, 
                           current_gameweek: int) -> Optional[ChipType]:
        """Recommend optimal chip usage for current gameweek"""
        
        # Get fixture difficulty for upcoming weeks
        team_difficulty = self.api.get_team_difficulty()
        
        # Check if any good double gameweeks coming up
        fixtures_df = self.fixtures_df[self.fixtures_df['event'] >= current_gameweek]
        gameweek_fixtures = fixtures_df.groupby('event').size()
        
        # Look for double gameweeks (more than 10 fixtures)
        potential_dgws = gameweek_fixtures[gameweek_fixtures > 10]
        
        for chip in user_strategy.chips_remaining:
            # Check if this chip is already planned for this gameweek
            planned_this_gw = any(
                cs.planned_gameweek == current_gameweek and cs.chip_type == chip 
                for cs in user_strategy.planned_chips
            )
            
            if planned_this_gw:
                return chip
        
        # Basic chip recommendation logic
        if ChipType.BENCH_BOOST in user_strategy.chips_remaining:
            # Recommend bench boost during double gameweeks
            if current_gameweek in potential_dgws.index:
                return ChipType.BENCH_BOOST
        
        if ChipType.TRIPLE_CAPTAIN in user_strategy.chips_remaining:
            # Recommend triple captain for easy fixtures with top players
            if current_gameweek in potential_dgws.index:
                return ChipType.TRIPLE_CAPTAIN
        
        return None
    
    def generate_weekly_recommendation(self, user_strategy: UserStrategy,
                                     current_team: List[int]) -> WeeklyRecommendation:
        """Generate comprehensive weekly recommendation"""
        
        current_gw = self.api.get_current_gameweek()
        gw_info = self.api.get_gameweek_info(current_gw)
        
        # Get transfer recommendations
        transfer_recs = self.get_transfer_recommendations(user_strategy, current_team)
        
        # Recommend chip usage
        chip_rec = self.recommend_chip_usage(user_strategy, current_gw)
        
        # Get captain recommendations
        captain_recs = self.get_captain_recommendations(current_team)
        
        # Build weekly recommendation
        weekly_rec = WeeklyRecommendation(
            gameweek=current_gw,
            deadline=datetime.fromisoformat(gw_info.get('deadline_time', '').replace('Z', '+00:00')) if gw_info.get('deadline_time') else datetime.now(),
            recommended_transfers=transfer_recs[:2],  # Max 2 transfers normally
            free_transfers_available=user_strategy.free_transfers,
            suggested_hits=max(0, len(transfer_recs[:2]) - user_strategy.free_transfers),
            recommended_captain=captain_recs[0] if captain_recs else current_team[0],
            recommended_vice_captain=captain_recs[1] if len(captain_recs) > 1 else current_team[1],
            recommended_lineup=current_team[:11],  # TODO: Optimize lineup
            recommended_bench=current_team[11:15],  # TODO: Optimize bench
            recommended_chip=chip_rec,
            chip_reasoning="Good fixtures and team setup" if chip_rec else "Hold for better opportunity",
            strategy_notes=f"Focus on form players with good fixtures. Current team value: £{user_strategy.current_team_value:.1f}m",
            risk_level="Medium",
            expected_points=sum(self.predict_player_points(pid, 1) for pid in current_team[:11]),
            confidence=0.8
        )
        
        return weekly_rec
    
    def get_captain_recommendations(self, current_team: List[int]) -> List[int]:
        """Get captain recommendations from current team"""
        if self.players_df is None:
            self.update_data()
        
        team_players = self.players_df[self.players_df['id'].isin(current_team)]
        
        # Score players for captaincy based on form, fixtures, and role
        team_players = team_players.copy()
        team_players['captain_score'] = (
            team_players['form_float'] * 0.4 +
            team_players['points_per_game'] * 0.3 +
            team_players['total_points'] / 100 * 0.3
        )
        
        # Prefer attacking players
        attacking_positions = [3, 4]  # MID, FWD
        team_players.loc[team_players['element_type'].isin(attacking_positions), 'captain_score'] *= 1.2
        
        # Sort by captain score
        captains = team_players.nlargest(5, 'captain_score')['id'].tolist()
        
        return captains
    
    def analyze_mini_league(self, league_id: int, user_id: int) -> MiniLeagueAnalysis:
        """Analyze mini league and provide strategic insights"""
        
        # Get league standings
        standings = self.api.get_league_standings(league_id)
        
        league_name = standings['league']['name']
        results = standings['standings']['results']
        
        competitors = []
        user_rank = 0
        user_points = 0
        
        for i, entry in enumerate(results):
            if entry['entry'] == user_id:
                user_rank = entry['rank']
                user_points = entry['total']
            
            competitor = LeagueCompetitor(
                manager_id=entry['entry'],
                team_name=entry['entry_name'],
                player_name=entry['player_name'],
                total_points=entry['total'],
                rank=entry['rank'],
                last_gw_points=entry['event_total'],
                team_value=0.0,  # Would need additional API call
                points_gap=entry['total'] - user_points if entry['entry'] != user_id else 0
            )
            competitors.append(competitor)
        
        # Calculate strategic insights
        points_to_leader = max(0, max(c.total_points for c in competitors) - user_points)
        
        # Find next rank
        points_to_next = 0
        if user_rank > 1:
            better_competitors = [c for c in competitors if c.rank < user_rank]
            if better_competitors:
                closest_better = min(better_competitors, key=lambda x: x.total_points)
                points_to_next = closest_better.total_points - user_points
        
        analysis = MiniLeagueAnalysis(
            league_id=league_id,
            league_name=league_name,
            user_rank=user_rank,
            total_teams=len(results),
            competitors=competitors,
            points_to_leader=points_to_leader,
            points_to_next_rank=points_to_next,
            strategic_advice=f"You are rank {user_rank} of {len(results)}. "
                           f"Need {points_to_leader} points to lead, {points_to_next} for next rank."
        )
        
        return analysis
    
    def _get_position_id(self, position_name: str) -> int:
        """Convert position name to ID"""
        position_map = {'GKP': 1, 'DEF': 2, 'MID': 3, 'FWD': 4}
        return position_map.get(position_name, 1)
    
    def get_differential_picks(self, ownership_threshold: float = 10.0) -> List[int]:
        """Find good differential picks (low ownership, high potential)"""
        if self.players_df is None:
            self.update_data()
        
        # Filter players with low ownership but good stats
        # Convert ownership to numeric to handle string values
        players_numeric = self.players_df.copy()
        players_numeric['selected_by_percent_num'] = pd.to_numeric(
            players_numeric['selected_by_percent'], errors='coerce'
        ).fillna(0)
        
        # Adjust criteria based on current gameweek (early season = lower thresholds)
        current_gw = self.api.get_current_gameweek()
        points_threshold = max(10, min(50, current_gw * 8))  # Scale with gameweek progress
        form_threshold = max(1.0, min(3.0, current_gw * 0.5))  # Scale form threshold
        
        differentials = players_numeric[
            (players_numeric['selected_by_percent_num'] < ownership_threshold) &
            (players_numeric['total_points'] > points_threshold) &
            (players_numeric['form_float'] > form_threshold)
        ]
        
        scored_differentials = self.calculate_player_scores()
        differential_scores = scored_differentials[
            scored_differentials['id'].isin(differentials['id'])
        ]
        
        return differential_scores.nlargest(10, 'total_score')['id'].tolist()

# Test the analysis engine
if __name__ == "__main__":
    from fpl_api import FPLApiClient
    
    api = FPLApiClient()
    engine = AnalysisEngine(api)
    
    try:
        print("Testing Analysis Engine...")
        
        # Update data
        engine.update_data()
        print(f"Loaded {len(engine.players_df)} players for analysis")
        
        # Test player scoring
        scored_players = engine.calculate_player_scores()
        top_players = scored_players.nlargest(5, 'total_score')[
            ['web_name', 'team_name', 'position_name', 'total_score', 'form_float']
        ]
        print("\nTop 5 players by analysis score:")
        print(top_players.to_string(index=False))
        
        # Test predictions
        top_player_id = scored_players.iloc[0]['id']
        predicted_points = engine.predict_player_points(top_player_id, 6)
        print(f"\nPredicted points for {scored_players.iloc[0]['web_name']} (next 6 GWs): {predicted_points:.1f}")
        
        print("\nAnalysis engine test completed successfully!")
        
    except Exception as e:
        print(f"Error testing analysis engine: {e}")
        import traceback
        traceback.print_exc()
