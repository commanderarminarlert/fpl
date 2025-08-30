"""
Transfer Optimizer for FPL Assistant
Advanced transfer planning and optimization system
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime, timedelta
import logging
from itertools import combinations
import pulp

from models import (
    Player, TransferRecommendation, UserStrategy, ChipType, Position,
    ChipStrategy, WeeklyRecommendation
)
from fpl_api import FPLApiClient
from analysis_engine import AnalysisEngine

logger = logging.getLogger(__name__)

class TransferOptimizer:
    """Advanced transfer optimization system"""
    
    def __init__(self, api_client: FPLApiClient, analysis_engine: AnalysisEngine):
        self.api = api_client
        self.analysis = analysis_engine
        self.players_df = None
        self.fixtures_df = None
        
    def update_data(self):
        """Update data for optimization"""
        self.analysis.update_data()
        self.players_df = self.analysis.players_df
        self.fixtures_df = self.analysis.fixtures_df
    
    def optimize_transfers(self, user_strategy: UserStrategy, 
                          current_team: List[int], 
                          weeks_ahead: int = 6,
                          max_transfers: int = 2,
                          allow_hits: bool = True) -> List[TransferRecommendation]:
        """
        Optimize transfers using advanced algorithms considering:
        - Future fixtures
        - Player form and value
        - Team structure
        - Chip strategy
        """
        
        if self.players_df is None:
            self.update_data()
        
        logger.info(f"Optimizing transfers for {weeks_ahead} weeks ahead, max {max_transfers} transfers")
        
        # Get current team structure
        current_team_df = self.players_df[self.players_df['id'].isin(current_team)]
        available_players = self.players_df[~self.players_df['id'].isin(current_team)]
        
        # Calculate expected points for all players over the period
        player_projections = self._calculate_player_projections(weeks_ahead)
        
        # Find optimal transfers using mathematical optimization
        optimal_transfers = self._solve_transfer_optimization(
            current_team, player_projections, user_strategy, max_transfers, allow_hits
        )
        
        return optimal_transfers
    
    def _calculate_player_projections(self, weeks_ahead: int) -> Dict[int, float]:
        """Calculate expected points for all players over specified weeks"""
        projections = {}
        
        # Get fixture difficulty for upcoming weeks
        team_difficulty = self.api.get_team_difficulty()
        current_gw = self.api.get_current_gameweek()
        
        for _, player in self.players_df.iterrows():
            player_id = int(player['id'])
            team_id = player['team']
            
            # Base projection from recent form and stats
            base_points = self._calculate_base_projection(player, weeks_ahead)
            
            # Adjust for fixtures
            fixture_adjustment = self._calculate_fixture_adjustment(
                team_id, team_difficulty, weeks_ahead
            )
            
            # Adjust for position and role
            position_adjustment = self._calculate_position_adjustment(player)
            
            # Injury/rotation risk
            availability_adjustment = self._calculate_availability_adjustment(player)
            
            final_projection = (base_points * fixture_adjustment * 
                              position_adjustment * availability_adjustment)
            
            projections[player_id] = max(0, final_projection)
        
        return projections
    
    def _calculate_base_projection(self, player: pd.Series, weeks: int) -> float:
        """Calculate base points projection from player stats"""
        # Weight recent form more heavily
        form_weight = 0.6
        season_weight = 0.4
        
        # Form-based projection
        form_projection = player['form_float'] * weeks * form_weight
        
        # Season average projection
        season_projection = player['points_per_game'] * weeks * season_weight
        
        # Minutes adjustment (players who play more get higher projections)
        minutes_factor = min(player['minutes'] / (self.api.get_current_gameweek() * 90), 1.0)
        
        base_projection = (form_projection + season_projection) * minutes_factor
        
        # Bonus potential (some players get bonuses more consistently)
        bonus_factor = 1.0 + (player['bonus'] / max(player['total_points'], 1)) * 0.1
        
        return base_projection * bonus_factor
    
    def _calculate_fixture_adjustment(self, team_id: int, team_difficulty: Dict, 
                                    weeks: int) -> float:
        """Calculate fixture difficulty adjustment"""
        if team_id not in team_difficulty:
            return 1.0
        
        difficulties = team_difficulty[team_id]['difficulties'][:weeks]
        if not difficulties:
            return 1.0
        
        avg_difficulty = sum(difficulties) / len(difficulties)
        
        # Easier fixtures (lower difficulty) = higher multiplier
        # Difficulty scale: 1 (easiest) to 5 (hardest)
        # Multiplier range: 0.8 to 1.2
        multiplier = 1.0 + (3.0 - avg_difficulty) * 0.1
        
        return max(0.8, min(1.2, multiplier))
    
    def _calculate_position_adjustment(self, player: pd.Series) -> float:
        """Position-specific adjustments"""
        position = player['element_type']
        
        # Goalkeepers: more predictable, slight bonus for good teams
        if position == 1:
            # Bonus for teams with good defensive records
            cs_rate = player['clean_sheets'] / max(player['starts'], 1)
            return 1.0 + cs_rate * 0.1
        
        # Defenders: bonus for attacking defenders
        elif position == 2:
            # Bonus for goals/assists
            attacking_bonus = (player['goals_scored'] + player['assists']) / 10
            return 1.0 + attacking_bonus * 0.1
        
        # Midfielders: balanced, bonus for high ICT
        elif position == 3:
            ict_index = pd.to_numeric(player['ict_index'], errors='coerce')
            ict_bonus = ict_index / 100 if pd.notna(ict_index) else 0
            return 1.0 + ict_bonus * 0.05
        
        # Forwards: bonus for shots and goal threat
        else:
            goal_bonus = player['goals_scored'] / 10
            return 1.0 + goal_bonus * 0.1
    
    def _calculate_availability_adjustment(self, player: pd.Series) -> float:
        """Calculate injury/rotation risk adjustment"""
        # Players with more consistent minutes get bonus
        games_started = max(player['starts'], 1)
        minutes_per_game = player['minutes'] / games_started
        
        # Full game = 90 minutes
        availability_factor = min(minutes_per_game / 90, 1.0)
        
        # Penalty for recent injuries (if minutes have dropped)
        if player['minutes'] < games_started * 45:  # Less than half game average
            availability_factor *= 0.9
        
        return max(0.7, availability_factor)
    
    def _solve_transfer_optimization(self, current_team: List[int], 
                                   projections: Dict[int, float],
                                   user_strategy: UserStrategy,
                                   max_transfers: int,
                                   allow_hits: bool) -> List[TransferRecommendation]:
        """Solve transfer optimization using linear programming"""
        
        recommendations = []
        
        # Simple greedy approach for now (can be enhanced with LP solver)
        current_team_df = self.players_df[self.players_df['id'].isin(current_team)]
        available_players = self.players_df[~self.players_df['id'].isin(current_team)]
        
        # Calculate value improvements for potential transfers
        transfer_candidates = []
        
        for _, current_player in current_team_df.iterrows():
            current_id = int(current_player['id'])
            current_projection = projections.get(current_id, 0)
            current_value = current_player['value']
            position = current_player['element_type']
            
            # Find better players in same position
            position_players = available_players[
                available_players['element_type'] == position
            ]
            
            for _, candidate in position_players.iterrows():
                candidate_id = int(candidate['id'])
                candidate_projection = projections.get(candidate_id, 0)
                candidate_value = candidate['value']
                
                # Check if affordable
                cost_diff = candidate_value - current_value
                if cost_diff <= user_strategy.bank:
                    
                    points_improvement = candidate_projection - current_projection
                    
                    if points_improvement > 0:
                        transfer_candidates.append({
                            'out_id': current_id,
                            'in_id': candidate_id,
                            'out_name': current_player['web_name'],
                            'in_name': candidate['web_name'],
                            'cost_change': cost_diff,
                            'points_improvement': points_improvement,
                            'value_ratio': points_improvement / max(abs(cost_diff), 0.1)
                        })
        
        # Sort by value ratio (points per cost)
        transfer_candidates.sort(key=lambda x: x['value_ratio'], reverse=True)
        
        # Select best transfers within constraints
        selected_transfers = []
        used_players_out = set()
        used_players_in = set()
        remaining_budget = user_strategy.bank
        
        for candidate in transfer_candidates:
            if len(selected_transfers) >= max_transfers:
                break
            
            # Check constraints
            if (candidate['out_id'] in used_players_out or 
                candidate['in_id'] in used_players_in or
                candidate['cost_change'] > remaining_budget):
                continue
            
            # Check if hit is worth it
            if len(selected_transfers) >= user_strategy.free_transfers:
                if not allow_hits or candidate['points_improvement'] < 4:
                    continue
            
            selected_transfers.append(candidate)
            used_players_out.add(candidate['out_id'])
            used_players_in.add(candidate['in_id'])
            remaining_budget -= candidate['cost_change']
        
        # Convert to TransferRecommendation objects
        for i, transfer in enumerate(selected_transfers):
            rec = TransferRecommendation(
                player_out_id=transfer['out_id'],
                player_in_id=transfer['in_id'],
                player_out_name=transfer['out_name'],
                player_in_name=transfer['in_name'],
                cost_change=transfer['cost_change'],
                points_potential=transfer['points_improvement'],
                confidence=min(transfer['points_improvement'] / 10, 1.0),
                reason=f"Expected {transfer['points_improvement']:.1f} additional points over next 6 GWs",
                priority=i + 1
            )
            recommendations.append(rec)
        
        return recommendations
    
    def plan_season_transfers(self, user_strategy: UserStrategy,
                            current_team: List[int],
                            target_gameweeks: List[int]) -> Dict[int, List[TransferRecommendation]]:
        """Plan transfers for specific target gameweeks (e.g., before chip usage)"""
        
        transfer_plan = {}
        current_gw = self.api.get_current_gameweek()
        
        for target_gw in target_gameweeks:
            if target_gw <= current_gw:
                continue
            
            # Calculate optimal team for that gameweek
            weeks_ahead = target_gw - current_gw
            
            # Get transfers needed to optimize for that period
            transfers = self.optimize_transfers(
                user_strategy, current_team, weeks_ahead, max_transfers=8, allow_hits=True
            )
            
            transfer_plan[target_gw] = transfers
        
        return transfer_plan
    
    def evaluate_transfer_timing(self, transfer: TransferRecommendation,
                               user_strategy: UserStrategy) -> Dict[str, any]:
        """Evaluate optimal timing for a specific transfer"""
        
        current_gw = self.api.get_current_gameweek()
        
        # Get fixture difficulty for both players over next few weeks
        player_out_fixtures = self._get_player_fixture_difficulty(
            transfer.player_out_id, weeks=4
        )
        player_in_fixtures = self._get_player_fixture_difficulty(
            transfer.player_in_id, weeks=4
        )
        
        # Calculate optimal timing
        best_gw = current_gw
        max_advantage = 0
        
        for gw in range(current_gw, current_gw + 4):
            gw_index = gw - current_gw
            if gw_index < len(player_in_fixtures) and gw_index < len(player_out_fixtures):
                
                # Advantage = easier fixture for new player - old player's fixture
                advantage = (player_out_fixtures[gw_index] - player_in_fixtures[gw_index])
                
                if advantage > max_advantage:
                    max_advantage = advantage
                    best_gw = gw
        
        return {
            'recommended_gameweek': best_gw,
            'advantage_score': max_advantage,
            'immediate': best_gw == current_gw,
            'reasoning': f"Optimal fixtures in GW{best_gw}" if best_gw != current_gw else "Make transfer now"
        }
    
    def _get_player_fixture_difficulty(self, player_id: int, weeks: int = 4) -> List[int]:
        """Get fixture difficulty for a player over specified weeks"""
        if self.players_df is None:
            self.update_data()
        
        player = self.players_df[self.players_df['id'] == player_id].iloc[0]
        team_id = player['team']
        
        team_difficulty = self.api.get_team_difficulty()
        
        if team_id in team_difficulty:
            difficulties = team_difficulty[team_id]['difficulties'][:weeks]
            return difficulties
        
        return [3] * weeks  # Default medium difficulty

class ChipPlanner:
    """Strategic chip planning system"""
    
    def __init__(self, api_client: FPLApiClient, analysis_engine: AnalysisEngine):
        self.api = api_client
        self.analysis = analysis_engine
    
    def create_chip_strategy(self, user_strategy: UserStrategy) -> List[ChipStrategy]:
        """Create optimal chip usage strategy for the season"""
        
        current_gw = self.api.get_current_gameweek()
        remaining_gws = 38 - current_gw + 1
        
        strategies = []
        
        # Analyze upcoming fixtures and double gameweeks
        fixture_analysis = self._analyze_upcoming_fixtures(remaining_gws)
        double_gameweeks = self._identify_double_gameweeks(fixture_analysis, current_gw)
        blank_gameweeks = self._identify_blank_gameweeks(fixture_analysis, current_gw)
        
        # Plan Wildcard usage (2 available)
        try:
            wildcards_remaining = user_strategy.chips_remaining.get(ChipType.WILDCARD, 0)
        except AttributeError:
            # Fallback for old-style chips_remaining list
            wildcards_remaining = 2 if ChipType.WILDCARD in getattr(user_strategy, 'chips_remaining', []) else 0
        
        if wildcards_remaining > 0:
            wc_plans = self._plan_multiple_wildcards(fixture_analysis, current_gw, wildcards_remaining)
            for i, wc_gw in enumerate(wc_plans):
                priority = 1 if i == 0 else 5  # First wildcard high priority, second lower
                reason = "Optimal team restructuring before good fixture run" if i == 0 else "Late season squad overhaul"
                strategies.append(ChipStrategy(
                    chip_type=ChipType.WILDCARD,
                    planned_gameweek=wc_gw,
                    priority=priority,
                    reason=reason
                ))
        
        # Plan Bench Boost usage (2 available)
        try:
            bb_remaining = user_strategy.chips_remaining.get(ChipType.BENCH_BOOST, 0)
        except AttributeError:
            bb_remaining = 2 if ChipType.BENCH_BOOST in getattr(user_strategy, 'chips_remaining', []) else 0
        
        if bb_remaining > 0:
            bb_plans = self._plan_multiple_bench_boosts(double_gameweeks, fixture_analysis, current_gw, bb_remaining)
            for i, bb_gw in enumerate(bb_plans):
                priority = 2 if i == 0 else 6
                reason = "Prime double gameweek with full bench participation" if i == 0 else "Secondary double gameweek opportunity"
                strategies.append(ChipStrategy(
                    chip_type=ChipType.BENCH_BOOST,
                    planned_gameweek=bb_gw,
                    priority=priority,
                    reason=reason
                ))
        
        # Plan Triple Captain usage (2 available)
        try:
            tc_remaining = user_strategy.chips_remaining.get(ChipType.TRIPLE_CAPTAIN, 0)
        except AttributeError:
            tc_remaining = 2 if ChipType.TRIPLE_CAPTAIN in getattr(user_strategy, 'chips_remaining', []) else 0
        
        if tc_remaining > 0:
            tc_plans = self._plan_multiple_triple_captains(double_gameweeks, fixture_analysis, current_gw, tc_remaining)
            for i, tc_gw in enumerate(tc_plans):
                priority = 3 if i == 0 else 7
                reason = "Premium captain pick in ideal double gameweek" if i == 0 else "Secondary captain opportunity"
                strategies.append(ChipStrategy(
                    chip_type=ChipType.TRIPLE_CAPTAIN,
                    planned_gameweek=tc_gw,
                    priority=priority,
                    reason=reason
                ))
        
        # Plan Free Hit usage (2 available)
        try:
            fh_remaining = user_strategy.chips_remaining.get(ChipType.FREE_HIT, 0)
        except AttributeError:
            fh_remaining = 2 if ChipType.FREE_HIT in getattr(user_strategy, 'chips_remaining', []) else 0
        
        if fh_remaining > 0:
            fh_plans = self._plan_multiple_free_hits(blank_gameweeks, fixture_analysis, current_gw, fh_remaining)
            for i, fh_gw in enumerate(fh_plans):
                priority = 4 if i == 0 else 8
                reason = "Critical blank gameweek navigation" if i == 0 else "Secondary blank gameweek or fixture exploit"
                strategies.append(ChipStrategy(
                    chip_type=ChipType.FREE_HIT,
                    planned_gameweek=fh_gw,
                    priority=priority,
                    reason=reason
                ))
        
        # Sort by priority
        strategies.sort(key=lambda x: x.priority)
        
        return strategies
    
    def _analyze_upcoming_fixtures(self, weeks: int) -> Dict[int, Dict]:
        """Analyze upcoming fixtures for chip planning"""
        
        current_gw = self.api.get_current_gameweek()
        fixtures_df = self.api.get_fixtures()
        
        analysis = {}
        
        for gw in range(current_gw, current_gw + weeks):
            gw_fixtures = fixtures_df[fixtures_df['event'] == gw]
            
            # Count fixtures per team
            team_fixtures = {}
            total_fixtures = len(gw_fixtures)
            
            for _, fixture in gw_fixtures.iterrows():
                team_h = fixture['team_h']
                team_a = fixture['team_a']
                
                team_fixtures[team_h] = team_fixtures.get(team_h, 0) + 1
                team_fixtures[team_a] = team_fixtures.get(team_a, 0) + 1
            
            # Calculate average difficulty
            difficulties = []
            if len(gw_fixtures) > 0:
                difficulties = list(gw_fixtures['team_h_difficulty']) + list(gw_fixtures['team_a_difficulty'])
            
            avg_difficulty = sum(difficulties) / len(difficulties) if difficulties else 3.0
            
            # Identify double gameweeks and blank gameweeks
            is_double_gw = total_fixtures > 10
            is_blank_gw = total_fixtures < 5
            
            analysis[gw] = {
                'total_fixtures': total_fixtures,
                'avg_difficulty': avg_difficulty,
                'is_double_gw': is_double_gw,
                'is_blank_gw': is_blank_gw,
                'team_fixtures': team_fixtures
            }
        
        return analysis
    
    def _identify_double_gameweeks(self, fixture_analysis: Dict, current_gw: int) -> List[int]:
        """Identify confirmed and likely double gameweeks"""
        double_gws = []
        
        for gw, data in fixture_analysis.items():
            # More accurate double gameweek detection
            if data['total_fixtures'] > 10 or (data['total_fixtures'] > 8 and gw > 25):
                double_gws.append(gw)
        
        # Typical double gameweek periods (historical pattern)
        # Double gameweeks usually occur in GW25-29 and GW36-37
        likely_periods = [range(25, 30), range(36, 38)]
        
        for period in likely_periods:
            for gw in period:
                if gw >= current_gw and gw not in double_gws and gw in fixture_analysis:
                    # Check if this gameweek has fewer fixtures than normal (indicating postponements)
                    if fixture_analysis[gw]['total_fixtures'] < 8:
                        # Look for makeup gameweeks nearby
                        for makeup_gw in range(gw + 1, min(gw + 5, 39)):
                            if makeup_gw in fixture_analysis and makeup_gw not in double_gws:
                                double_gws.append(makeup_gw)
                                break
        
        return sorted(double_gws)
    
    def _identify_blank_gameweeks(self, fixture_analysis: Dict, current_gw: int) -> List[int]:
        """Identify confirmed and likely blank gameweeks"""
        blank_gws = []
        
        for gw, data in fixture_analysis.items():
            # Blank gameweek detection
            if data['total_fixtures'] < 5:
                blank_gws.append(gw)
        
        # Check for FA Cup/European fixture clashes (typically GW18, GW28-29)
        typical_blank_periods = [18, 28, 29]
        for gw in typical_blank_periods:
            if gw >= current_gw and gw not in blank_gws and gw in fixture_analysis:
                if fixture_analysis[gw]['total_fixtures'] < 8:
                    blank_gws.append(gw)
        
        return sorted(blank_gws)
    
    def _plan_multiple_wildcards(self, fixture_analysis: Dict, current_gw: int, count: int) -> List[int]:
        """Plan multiple wildcard usage throughout the season"""
        wildcards = []
        
        if count >= 1:
            # First wildcard: Early-mid season for team structure (GW8-15)
            wc1 = self._find_optimal_wildcard_timing(fixture_analysis, current_gw, max(current_gw + 1, 8), 15)
            wildcards.append(wc1)
        
        if count >= 2:
            # Second wildcard: Later in season for final push (GW25-35)
            wc2 = self._find_optimal_wildcard_timing(fixture_analysis, max(wildcards[0] + 8, 25), 25, 35)
            wildcards.append(wc2)
        
        return wildcards
    
    def _plan_multiple_bench_boosts(self, double_gws: List[int], fixture_analysis: Dict, current_gw: int, count: int) -> List[int]:
        """Plan multiple bench boost usage"""
        bench_boosts = []
        
        # Sort double gameweeks by attractiveness (difficulty + timing)
        scored_dgws = []
        for gw in double_gws:
            if gw >= current_gw + 1:
                score = (5 - fixture_analysis[gw]['avg_difficulty']) * 2
                # Prefer later double gameweeks (more planning time)
                if gw > current_gw + 3:
                    score += 1
                scored_dgws.append((gw, score))
        
        scored_dgws.sort(key=lambda x: x[1], reverse=True)
        
        for i in range(min(count, len(scored_dgws))):
            bench_boosts.append(scored_dgws[i][0])
        
        # If no double gameweeks available, pick best regular gameweeks
        while len(bench_boosts) < count:
            best_gw = self._find_best_regular_gameweek(fixture_analysis, current_gw, bench_boosts)
            if best_gw:
                bench_boosts.append(best_gw)
            else:
                break
        
        return sorted(bench_boosts)
    
    def _plan_multiple_triple_captains(self, double_gws: List[int], fixture_analysis: Dict, current_gw: int, count: int) -> List[int]:
        """Plan multiple triple captain usage"""
        triple_captains = []
        
        # Prefer the best double gameweeks
        scored_dgws = []
        for gw in double_gws:
            if gw >= current_gw + 1:
                score = (5 - fixture_analysis[gw]['avg_difficulty']) * 3
                # Heavily favor earlier opportunities (captain form is unpredictable)
                if gw <= current_gw + 10:
                    score += 2
                scored_dgws.append((gw, score))
        
        scored_dgws.sort(key=lambda x: x[1], reverse=True)
        
        for i in range(min(count, len(scored_dgws))):
            triple_captains.append(scored_dgws[i][0])
        
        # If insufficient double gameweeks, find best single gameweeks
        while len(triple_captains) < count:
            best_gw = self._find_best_captain_gameweek(fixture_analysis, current_gw, triple_captains)
            if best_gw:
                triple_captains.append(best_gw)
            else:
                break
        
        return sorted(triple_captains)
    
    def _plan_multiple_free_hits(self, blank_gws: List[int], fixture_analysis: Dict, current_gw: int, count: int) -> List[int]:
        """Plan multiple free hit usage"""
        free_hits = []
        
        # First priority: blank gameweeks
        for gw in blank_gws:
            if gw >= current_gw + 1 and len(free_hits) < count:
                free_hits.append(gw)
        
        # Second priority: unique fixture opportunities (teams playing twice when others don't)
        if len(free_hits) < count:
            for gw in range(current_gw + 1, 39):
                if gw not in free_hits and gw in fixture_analysis:
                    # Look for gameweeks where specific teams have great fixtures
                    team_fixtures = fixture_analysis[gw]['team_fixtures']
                    
                    # Find teams with multiple fixtures and good difficulty
                    good_opportunities = 0
                    for team, fixture_count in team_fixtures.items():
                        if fixture_count > 1:  # Team plays more than once
                            good_opportunities += 1
                    
                    # If many teams have good opportunities, consider for free hit
                    if good_opportunities >= 6 and fixture_analysis[gw]['avg_difficulty'] < 3.0:
                        free_hits.append(gw)
                        if len(free_hits) >= count:
                            break
        
        return sorted(free_hits)
    
    def _find_optimal_wildcard_timing(self, fixture_analysis: Dict, current_gw: int, min_gw: int, max_gw: int) -> int:
        """Find optimal wildcard timing within a range"""
        best_gw = min_gw
        best_score = 0
        
        for gw in range(max(current_gw + 1, min_gw), min(max_gw + 1, 39)):
            if gw not in fixture_analysis:
                continue
            
            # Score based on upcoming fixtures after this gameweek
            score = 0
            for future_gw in range(gw + 1, min(gw + 6, 39)):  # Next 5 weeks
                if future_gw in fixture_analysis:
                    # Prefer easier fixtures and more fixtures
                    difficulty_score = (5 - fixture_analysis[future_gw]['avg_difficulty']) * 2
                    fixture_bonus = 2 if fixture_analysis[future_gw]['is_double_gw'] else 0
                    score += difficulty_score + fixture_bonus
            
            if score > best_score:
                best_score = score
                best_gw = gw
        
        return best_gw
    
    def _find_best_regular_gameweek(self, fixture_analysis: Dict, current_gw: int, exclude: List[int]) -> Optional[int]:
        """Find best regular gameweek for chip usage"""
        best_gw = None
        best_score = 0
        
        for gw in range(current_gw + 1, 39):
            if gw not in exclude and gw in fixture_analysis:
                # Score based on difficulty and fixture count
                score = (5 - fixture_analysis[gw]['avg_difficulty']) * 2
                score += fixture_analysis[gw]['total_fixtures'] / 10  # Slight bonus for more fixtures
                
                if score > best_score:
                    best_score = score
                    best_gw = gw
        
        return best_gw
    
    def _find_best_captain_gameweek(self, fixture_analysis: Dict, current_gw: int, exclude: List[int]) -> Optional[int]:
        """Find best gameweek for captain chip"""
        best_gw = None
        best_score = 0
        
        for gw in range(current_gw + 1, 39):
            if gw not in exclude and gw in fixture_analysis:
                # Heavily weight difficulty for captain picks
                score = (5 - fixture_analysis[gw]['avg_difficulty']) * 4
                
                if score > best_score:
                    best_score = score
                    best_gw = gw
        
        return best_gw
    
    def _plan_wildcard(self, fixture_analysis: Dict, current_gw: int) -> int:
        """Plan optimal wildcard timing"""
        
        # Look for a good fixture run 2-3 weeks ahead
        best_gw = current_gw + 2
        best_score = 0
        
        for gw in range(current_gw + 1, current_gw + 15):
            if gw not in fixture_analysis:
                continue
            
            # Score based on upcoming fixtures after this gameweek
            score = 0
            for future_gw in range(gw + 1, min(gw + 7, 39)):  # Next 6 weeks
                if future_gw in fixture_analysis:
                    # Prefer easier fixtures and more fixtures
                    difficulty_score = (5 - fixture_analysis[future_gw]['avg_difficulty']) * 2
                    fixture_bonus = 1 if fixture_analysis[future_gw]['is_double_gw'] else 0
                    score += difficulty_score + fixture_bonus
            
            if score > best_score:
                best_score = score
                best_gw = gw
        
        return best_gw
    
    def _plan_bench_boost(self, fixture_analysis: Dict, current_gw: int) -> int:
        """Plan optimal bench boost timing"""
        
        # Look for double gameweeks
        for gw in range(current_gw + 1, current_gw + 20):
            if gw in fixture_analysis and fixture_analysis[gw]['is_double_gw']:
                return gw
        
        # If no double gameweeks found, use in a good fixture week
        best_gw = current_gw + 10
        best_difficulty = 5
        
        for gw in range(current_gw + 5, current_gw + 25):
            if gw in fixture_analysis:
                if fixture_analysis[gw]['avg_difficulty'] < best_difficulty:
                    best_difficulty = fixture_analysis[gw]['avg_difficulty']
                    best_gw = gw
        
        return best_gw
    
    def _plan_triple_captain(self, fixture_analysis: Dict, current_gw: int) -> int:
        """Plan optimal triple captain timing"""
        
        # Look for double gameweeks first
        for gw in range(current_gw + 1, current_gw + 20):
            if gw in fixture_analysis and fixture_analysis[gw]['is_double_gw']:
                return gw
        
        # Otherwise, find easiest fixture week
        best_gw = current_gw + 5
        best_difficulty = 5
        
        for gw in range(current_gw + 1, current_gw + 15):
            if gw in fixture_analysis:
                if fixture_analysis[gw]['avg_difficulty'] < best_difficulty:
                    best_difficulty = fixture_analysis[gw]['avg_difficulty']
                    best_gw = gw
        
        return best_gw
    
    def _plan_free_hit(self, fixture_analysis: Dict, current_gw: int) -> int:
        """Plan optimal free hit timing"""
        
        # Look for blank gameweeks first
        for gw in range(current_gw + 1, 39):
            if gw in fixture_analysis and fixture_analysis[gw]['is_blank_gw']:
                return gw
        
        # Otherwise, save for late in season for unique opportunities
        return min(35, current_gw + 20)
    
    def update_chip_bookmarks(self, user_strategy: UserStrategy, 
                            chip_type: ChipType, gameweek: int, 
                            locked: bool = False) -> UserStrategy:
        """Update or add chip bookmark"""
        
        # Remove existing plan for this chip type
        user_strategy.planned_chips = [
            cs for cs in user_strategy.planned_chips 
            if cs.chip_type != chip_type
        ]
        
        # Add new plan
        new_strategy = ChipStrategy(
            chip_type=chip_type,
            planned_gameweek=gameweek,
            priority=len(user_strategy.planned_chips) + 1,
            reason="User bookmarked",
            locked=locked
        )
        
        user_strategy.planned_chips.append(new_strategy)
        
        return user_strategy

# Test the optimizer
if __name__ == "__main__":
    from fpl_api import FPLApiClient
    from analysis_engine import AnalysisEngine
    
    api = FPLApiClient()
    analysis = AnalysisEngine(api)
    optimizer = TransferOptimizer(api, analysis)
    
    try:
        print("Testing Transfer Optimizer...")
        
        # Create mock user strategy
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
        
        # Mock current team (top 15 players for testing)
        optimizer.update_data()
        top_players = optimizer.players_df.nlargest(15, 'total_points')
        current_team = top_players['id'].tolist()
        
        # Test transfer optimization
        transfers = optimizer.optimize_transfers(user_strategy, current_team, max_transfers=2)
        
        print(f"Generated {len(transfers)} transfer recommendations:")
        for i, transfer in enumerate(transfers, 1):
            print(f"{i}. {transfer.player_out_name} → {transfer.player_in_name}")
            print(f"   Cost: £{transfer.cost_change:.1f}m, Points: +{transfer.points_potential:.1f}")
            print(f"   {transfer.reason}")
        
        print("\nTransfer optimizer test completed successfully!")
        
    except Exception as e:
        print(f"Error testing transfer optimizer: {e}")
        import traceback
        traceback.print_exc()
