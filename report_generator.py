"""
FPL Team Analysis Report Generator
Creates comprehensive PDF reports with team analysis and recommendations
"""

from fpdf import FPDF
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import io
import base64
import re

logger = logging.getLogger(__name__)

def remove_emojis(text: str) -> str:
    """Remove emoji characters and special symbols from text for PDF compatibility"""
    # Remove emoji characters and special symbols
    emoji_pattern = re.compile("["
                              u"\U0001F600-\U0001F64F"  # emoticons
                              u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                              u"\U0001F680-\U0001F6FF"  # transport & map symbols
                              u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                              u"\U00002702-\U000027B0"
                              u"\U000024C2-\U0001F251"
                              u"\u2190-\u21FF"          # arrows
                              u"\u2600-\u26FF"          # miscellaneous symbols
                              u"\u2700-\u27BF"          # dingbats
                              "]+", flags=re.UNICODE)
    
    # Also replace common problematic characters manually
    text = text.replace('→', ' -> ')
    text = text.replace('←', ' <- ')
    text = text.replace('↑', ' ^ ')
    text = text.replace('↓', ' v ')
    text = text.replace('•', '* ')
    text = text.replace('…', '...')
    
    return emoji_pattern.sub('', text).strip()

class SafePDF(FPDF):
    """FPDF wrapper that automatically removes emojis from text"""
    
    def cell(self, w, h, txt='', border=0, ln=0, align='', fill=False, link=''):
        safe_txt = remove_emojis(str(txt))
        return super().cell(w, h, safe_txt, border, ln, align, fill, link)
    
    def multi_cell(self, w, h, txt, border=0, align='J', fill=False, split_only=False):
        safe_txt = remove_emojis(str(txt))
        # If text is short, use cell instead to avoid spacing issues
        if len(safe_txt) < 80:
            if align == 'L':
                return self.cell(w, h, safe_txt, border, 1, 'L', fill)
            else:
                return self.cell(w, h, safe_txt, border, 1, align, fill)
        return super().multi_cell(w, h, safe_txt, border, align, fill, split_only)

class FPLReportGenerator:
    """Generate comprehensive FPL analysis reports"""
    
    def __init__(self, api_client, analysis_engine, transfer_optimizer):
        self.api = api_client
        self.analysis = analysis_engine
        self.optimizer = transfer_optimizer
        
    def generate_comprehensive_report(self, manager_id: int, league_id: Optional[int] = None) -> bytes:
        """Generate a complete FPL analysis report"""
        
        try:
            # Gather all data
            report_data = self._gather_report_data(manager_id, league_id)
            
            # Create PDF with safe emoji handling
            pdf = SafePDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_margins(10, 10, 10)  # Smaller margins for more space
            
            # Generate report sections
            self._add_title_page(pdf, report_data)
            self._add_executive_summary(pdf, report_data)
            self._add_current_team_analysis(pdf, report_data)
            self._add_transfer_recommendations(pdf, report_data)
            self._add_chip_strategy(pdf, report_data)
            self._add_fixture_analysis(pdf, report_data)
            self._add_league_position_analysis(pdf, report_data)
            self._add_action_plan(pdf, report_data)
            
            # Return PDF as bytes
            # Return PDF bytes (fpdf2 returns bytearray directly)
            return bytes(pdf.output())
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            raise
    
    def _gather_report_data(self, manager_id: int, league_id: Optional[int] = None) -> Dict:
        """Gather all necessary data for the report"""
        
        current_gw = self.api.get_current_gameweek()
        
        # Get manager and team data
        manager_data = self.api.get_manager_data(manager_id)
        team_data = self.api.get_manager_team(manager_id, current_gw)
        
        # Get current team player IDs
        current_team = [pick['element'] for pick in team_data['picks']] if team_data else []
        
        # Calculate real-time team value and bank balance
        real_team_value = 100.0
        real_bank_balance = manager_data.get('last_deadline_bank', 0) / 10
        
        if team_data and 'picks' in team_data:
            try:
                players_df = self.api.get_players_data()
                total_value = 0
                
                for pick in team_data['picks']:
                    player_data = players_df[players_df['id'] == pick['element']]
                    if not player_data.empty:
                        total_value += player_data.iloc[0]['value']
                
                real_team_value = total_value
                
                # Get actual bank from current gameweek data if available
                if 'entry_history' in team_data:
                    real_bank_balance = team_data['entry_history'].get('bank', real_bank_balance)
                    
            except Exception as e:
                logger.warning(f"Error calculating real-time team value: {e}")
                real_team_value = manager_data.get('last_deadline_value', 1000) / 10
        
        # Create user strategy with real-time data
        from models import UserStrategy, ChipType
        user_strategy = UserStrategy(
            manager_id=manager_id,
            team_name=manager_data.get('player_first_name', '') + ' ' + manager_data.get('player_last_name', ''),
            current_team_value=real_team_value,
            free_transfers=self.api.calculate_available_transfers(manager_id),
            bank=real_bank_balance,
            total_points=manager_data.get('summary_overall_points', 0),
            overall_rank=manager_data.get('summary_overall_rank', 0),
            league_rank=1,
            chips_remaining={
                ChipType.WILDCARD: 2,
                ChipType.BENCH_BOOST: 2,
                ChipType.TRIPLE_CAPTAIN: 2,
                ChipType.FREE_HIT: 2
            },
            planned_chips=[]
        )
        
        # Get transfer recommendations
        transfers = self.optimizer.optimize_transfers(
            user_strategy, current_team, max_transfers=2, allow_hits=True
        )
        
        # Get player scores and analysis
        players_df = self.analysis.calculate_player_scores()
        
        # Get team difficulty analysis
        team_difficulty = self.api.get_team_difficulty()
        
        # Get league data if available
        league_data = None
        if league_id:
            try:
                league_data = self.api.get_league_standings(league_id)
            except:
                league_data = None
        
        # Calculate team stats
        team_stats = self._calculate_team_stats(current_team, players_df)
        
        # Get fixture analysis
        fixture_analysis = self._get_fixture_insights(team_difficulty)
        
        return {
            'manager_data': manager_data,
            'team_data': team_data,
            'current_team': current_team,
            'user_strategy': user_strategy,
            'transfers': transfers,
            'players_df': players_df,
            'team_difficulty': team_difficulty,
            'league_data': league_data,
            'team_stats': team_stats,
            'fixture_analysis': fixture_analysis,
            'current_gw': current_gw,
            'report_date': datetime.now().strftime("%d %B %Y")
        }
    
    def _calculate_team_stats(self, current_team: List[int], players_df: pd.DataFrame) -> Dict:
        """Calculate comprehensive team statistics"""
        
        if players_df.empty or not current_team:
            return {}
        
        team_players = players_df[players_df['id'].isin(current_team)]
        
        stats = {
            'total_value': team_players['value'].sum(),
            'total_points': team_players['total_points'].sum(),
            'avg_form': team_players['form_float'].mean(),
            'avg_points_per_game': team_players['points_per_game'].mean(),
            'total_minutes': team_players['minutes'].sum(),
            'injury_risks': len(team_players[team_players['minutes'] < 500]),
            'top_performers': team_players.nlargest(3, 'total_points')[['web_name', 'total_points']].to_dict('records'),
            'weakest_links': team_players.nsmallest(3, 'total_score')[['web_name', 'total_score']].to_dict('records')
        }
        
        return stats
    
    def _get_fixture_insights(self, team_difficulty: Dict) -> Dict:
        """Get fixture insights for next few gameweeks"""
        
        good_fixtures = []
        bad_fixtures = []
        
        for team_id, data in team_difficulty.items():
            avg_diff = data.get('avg_difficulty', 3)
            team_name = data.get('team_name', 'Unknown')
            
            if avg_diff <= 2.5:
                good_fixtures.append(f"{team_name} ({avg_diff:.1f})")
            elif avg_diff >= 3.5:
                bad_fixtures.append(f"{team_name} ({avg_diff:.1f})")
        
        return {
            'good_fixtures': good_fixtures[:5],
            'bad_fixtures': bad_fixtures[:5]
        }
    
    def _add_title_page(self, pdf: FPDF, data: Dict):
        """Add title page to the report"""
        pdf.add_page()
        
        # Header
        pdf.set_font('Arial', 'B', 24)
        pdf.set_text_color(0, 100, 200)
        pdf.cell(0, 20, 'FPL TEAM ANALYSIS REPORT', 0, 1, 'C')
        
        pdf.set_font('Arial', '', 16)
        pdf.set_text_color(0, 0, 0)
        manager_name = f"Manager: {data['manager_data'].get('player_first_name', '')} {data['manager_data'].get('player_last_name', '')}"
        pdf.cell(0, 10, remove_emojis(manager_name), 0, 1, 'C')
        team_text = f"Team: {data['user_strategy'].team_name}"
        pdf.cell(0, 10, remove_emojis(team_text), 0, 1, 'C')
        pdf.cell(0, 10, f"Report Date: {data['report_date']}", 0, 1, 'C')
        pdf.cell(0, 10, f"Gameweek {data['current_gw']}", 0, 1, 'C')
        
        # Logo/Branding space
        pdf.ln(20)
        pdf.set_font('Arial', 'I', 12)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 10, 'Generated by FPL Assistant Pro', 0, 1, 'C')
        pdf.cell(0, 10, 'Advanced AI-Powered Fantasy Premier League Analysis', 0, 1, 'C')
        
        # Current stats overview
        pdf.ln(30)
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, 'QUICK STATS OVERVIEW', 0, 1, 'C')
        
        pdf.set_font('Arial', '', 12)
        stats = [
            f"Total Points: {data['manager_data'].get('summary_overall_points', 0):,}",
            f"Overall Rank: {data['manager_data'].get('summary_overall_rank', 0):,}",
            f"Team Value: £{data['team_stats'].get('total_value', 0):.1f}m",
            f"Bank: £{data['user_strategy'].bank:.1f}m",
            f"Free Transfers: {data['user_strategy'].free_transfers}"
        ]
        
        for stat in stats:
            pdf.cell(0, 8, stat, 0, 1, 'C')
    
    def _add_executive_summary(self, pdf: FPDF, data: Dict):
        """Add executive summary section"""
        pdf.add_page()
        
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(0, 100, 200)
        pdf.cell(0, 10, 'EXECUTIVE SUMMARY', 0, 1)
        
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(0, 0, 0)
        
        # Key insights
        current_rank = data['manager_data'].get('summary_overall_rank', 0)
        total_points = data['manager_data'].get('summary_overall_points', 0)
        
        # Generate insights based on data
        insights = []
        
        if current_rank > 1000000:
            insights.append("PRIORITY: Your rank needs immediate attention. Focus on proven performers and avoid risky picks.")
        elif current_rank > 500000:
            insights.append("IMPROVEMENT NEEDED: You're in the bottom half. Time for strategic changes.")
        else:
            insights.append("✅ SOLID POSITION: You're performing well. Focus on maintaining momentum.")
        
        if data['user_strategy'].free_transfers > 1:
            insights.append(f"💰 OPPORTUNITY: You have {data['user_strategy'].free_transfers} free transfers - perfect timing for upgrades.")
        
        if data['team_stats'].get('avg_form', 0) < 4:
            insights.append("FORM CONCERN: Your team's average form is low. Consider targeting in-form players.")
        
        if len(data['transfers']) > 0:
            insights.append(f"TRANSFER TARGETS: {len(data['transfers'])} high-value transfers identified.")
        
        # Write insights
        for insight in insights:
            clean_insight = remove_emojis(insight)
            pdf.multi_cell(0, 7, clean_insight, 0, 'L')
            pdf.ln(2)
        
        # Key recommendations preview
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'TOP 3 IMMEDIATE ACTIONS:', 0, 1)
        
        pdf.set_font('Arial', '', 11)
        actions = self._generate_top_actions(data)
        for i, action in enumerate(actions[:3], 1):
            clean_action = remove_emojis(f"{i}. {action}")
            pdf.multi_cell(0, 6, clean_action, 0, 'L')
            pdf.ln(1)
    
    def _generate_top_actions(self, data: Dict) -> List[str]:
        """Generate top recommended actions"""
        actions = []
        
        if data['transfers']:
            top_transfer = data['transfers'][0]
            transfer_text = f"Make transfer: {top_transfer.player_out_name} -> {top_transfer.player_in_name} ({top_transfer.reason})"
            actions.append(remove_emojis(transfer_text))
        
        good_fixtures = data['fixture_analysis']['good_fixtures']
        if good_fixtures:
            actions.append(f"Target players from teams with good fixtures: {', '.join(good_fixtures[:2])}")
        
        if data['team_stats'].get('injury_risks', 0) > 2:
            actions.append("Address rotation risks - several players have low minutes played")
        
        if data['user_strategy'].bank > 2:
            actions.append(f"Utilize your £{data['user_strategy'].bank:.1f}m bank to upgrade key positions")
        
        actions.append("Review chip strategy timing for upcoming double gameweeks")
        
        return actions
    
    def _add_current_team_analysis(self, pdf: FPDF, data: Dict):
        """Add current team analysis section"""
        pdf.add_page()
        
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(0, 100, 200)
        pdf.cell(0, 10, 'CURRENT TEAM ANALYSIS', 0, 1)
        
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(0, 0, 0)
        
        # Team value and financial status
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'FINANCIAL OVERVIEW', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        financial_items = [
            f"Team Value: £{data['team_stats'].get('total_value', 0):.1f}m",
            f"Bank Balance: £{data['user_strategy'].bank:.1f}m",
            f"Total Budget: £{data['team_stats'].get('total_value', 0) + data['user_strategy'].bank:.1f}m",
            f"Free Transfers Available: {data['user_strategy'].free_transfers}"
        ]
        
        for item in financial_items:
            item_text = f"* {item}"
            pdf.cell(0, 6, remove_emojis(item_text), 0, 1)
        
        pdf.ln(5)
        
        # Team performance metrics
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'PERFORMANCE METRICS', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        performance_items = [
            f"Total Points: {data['team_stats'].get('total_points', 0)}",
            f"Average Form: {data['team_stats'].get('avg_form', 0):.1f}/10",
            f"Points per Game: {data['team_stats'].get('avg_points_per_game', 0):.1f}",
            f"Players at Risk (low minutes): {data['team_stats'].get('injury_risks', 0)}"
        ]
        
        for item in performance_items:
            item_text = f"* {item}"
            pdf.cell(0, 6, remove_emojis(item_text), 0, 1)
        
        pdf.ln(5)
        
        # Top performers
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'YOUR STAR PLAYERS', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        top_performers = data['team_stats'].get('top_performers', [])
        for player in top_performers:
            star_text = f"STAR: {player['web_name']}: {player['total_points']} points"
            pdf.cell(0, 6, remove_emojis(star_text), 0, 1)
        
        pdf.ln(5)
        
        # Weak links
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'AREAS FOR IMPROVEMENT', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        weak_links = data['team_stats'].get('weakest_links', [])
        for player in weak_links:
            warning_text = f"WARNING: {player['web_name']}: Low analysis score ({player['total_score']:.1f})"
            pdf.cell(0, 6, remove_emojis(warning_text), 0, 1)
    
    def _add_transfer_recommendations(self, pdf: FPDF, data: Dict):
        """Add transfer recommendations section"""
        pdf.add_page()
        
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(0, 100, 200)
        pdf.cell(0, 10, 'SMART TRANSFER RECOMMENDATIONS', 0, 1)
        
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(0, 0, 0)
        
        transfers = data['transfers']
        
        if not transfers:
            good_news_text = "GREAT NEWS: Your team is well optimized. No immediate transfers needed."
            pdf.multi_cell(0, 8, remove_emojis(good_news_text), 0, 'L')
            return
        
        pdf.multi_cell(0, 8, f"Based on fixture analysis and AI predictions, here are {len(transfers)} recommended transfers:", 0, 'L')
        pdf.ln(5)
        
        for i, transfer in enumerate(transfers, 1):
            pdf.set_font('Arial', 'B', 12)
            transfer_title = f"TRANSFER {i}: {transfer.player_out_name} -> {transfer.player_in_name}"
            pdf.cell(0, 8, remove_emojis(transfer_title), 0, 1)
            
            pdf.set_font('Arial', '', 11)
            pdf.cell(0, 6, f"Cost Change: £{transfer.cost_change:+.1f}m", 0, 1)
            pdf.cell(0, 6, f"Expected Points Gain: +{transfer.points_potential:.1f} points", 0, 1)
            pdf.cell(0, 6, f"Confidence: {transfer.confidence:.0%}", 0, 1)
            
            pdf.multi_cell(0, 6, f"Reason: {transfer.reason}", 0, 'L')
            pdf.ln(3)
        
        # Transfer timing advice
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'TIMING ADVICE:', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        if data['user_strategy'].free_transfers >= len(transfers):
            perfect_timing_text = "PERFECT TIMING: You can make all recommended transfers without point hits."
            pdf.multi_cell(0, 6, remove_emojis(perfect_timing_text), 0, 'L')
        else:
            hits_needed = len(transfers) - data['user_strategy'].free_transfers
            warning_text = f"WARNING: You'll need {hits_needed} point hit(s) for all transfers. Consider prioritizing the top recommendations."
            pdf.multi_cell(0, 6, remove_emojis(warning_text), 0, 'L')
    
    def _add_chip_strategy(self, pdf: FPDF, data: Dict):
        """Add chip strategy section"""
        pdf.add_page()
        
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(0, 100, 200)
        pdf.cell(0, 10, 'CHIP STRATEGY MASTER PLAN', 0, 1)
        
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(0, 0, 0)
        
        pdf.multi_cell(0, 8, "Strategic chip usage can make or break your season. Here's your optimized plan:", 0, 'L')
        pdf.ln(5)
        
        # Chip recommendations
        chip_strategies = [
            ("WILDCARD", "Gameweek 8-15", "Use early for team restructuring before good fixture runs"),
            ("BENCH BOOST", "Double Gameweeks", "Target weeks when your bench players also have fixtures"),
            ("TRIPLE CAPTAIN", "Double Gameweeks", "Save for premium players in easy double gameweeks"),
            ("FREE HIT", "Blank Gameweeks", "Navigate weeks with few fixtures or exploit fixture swings")
        ]
        
        for chip, timing, strategy in chip_strategies:
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 7, f"{chip}:", 0, 1)
            pdf.set_font('Arial', '', 10)
            pdf.cell(10, 6, "", 0, 0)  # Indent
            pdf.multi_cell(170, 5, f"Timing: {timing} | Strategy: {strategy}", 0, 'L')
            pdf.ln(2)
        
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'UPCOMING OPPORTUNITIES:', 0, 1)
        pdf.set_font('Arial', '', 11)
        # Use simple cell instead of multi_cell to avoid spacing issues
        opportunities = [
            "* Monitor double gameweek announcements",
            "* Plan wildcard timing around breaks", 
            "* Keep free hit for blank gameweeks"
        ]
        
        for opp in opportunities:
            pdf.cell(0, 6, opp, 0, 1, 'L')
            pdf.ln(2)
    
    def _add_fixture_analysis(self, pdf: FPDF, data: Dict):
        """Add fixture analysis section"""
        pdf.add_page()
        
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(0, 100, 200)
        pdf.cell(0, 10, 'FIXTURE ANALYSIS & OPPORTUNITIES', 0, 1)
        
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(0, 0, 0)
        
        # Good fixtures
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(0, 150, 0)
        pdf.cell(0, 8, '✅ TEAMS WITH GREAT FIXTURES (Target for transfers):', 0, 1)
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(0, 0, 0)
        
        good_fixtures = data['fixture_analysis']['good_fixtures']
        if good_fixtures:
            for team in good_fixtures:
                team_text = f"* {team}"
                pdf.cell(0, 6, remove_emojis(team_text), 0, 1)
        else:
            pdf.cell(0, 6, "No standout easy fixtures identified", 0, 1)
        
        pdf.ln(5)
        
        # Bad fixtures
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(200, 0, 0)
        pdf.cell(0, 8, '❌ TEAMS WITH DIFFICULT FIXTURES (Avoid transfers):', 0, 1)
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(0, 0, 0)
        
        bad_fixtures = data['fixture_analysis']['bad_fixtures']
        if bad_fixtures:
            for team in bad_fixtures:
                team_text = f"* {team}"
                pdf.cell(0, 6, remove_emojis(team_text), 0, 1)
        else:
            pdf.cell(0, 6, "No particularly difficult fixtures identified", 0, 1)
        
        pdf.ln(10)
        
        # Fixture strategy tips
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, 'FIXTURE STRATEGY TIPS:', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        tips = [
            "Always check next gameweek fixtures before making transfers",
            "Avoid bringing in players before tough fixtures (like Arsenal vs Liverpool)",
            "Target players from teams with 2-3 easy fixtures in a row",
            "Consider fixture difficulty more than form for short-term picks",
            "Plan 3-4 gameweeks ahead for optimal transfer timing"
        ]
        
        for tip in tips:
            tip_text = f"TIP: {tip}"
            pdf.multi_cell(0, 6, remove_emojis(tip_text), 0, 'L')
            pdf.ln(1)
    
    def _add_league_position_analysis(self, pdf: FPDF, data: Dict):
        """Add league position analysis"""
        pdf.add_page()
        
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(0, 100, 200)
        pdf.cell(0, 10, 'MINI LEAGUE WINNING STRATEGY', 0, 1)
        
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(0, 0, 0)
        
        current_rank = data['manager_data'].get('summary_overall_rank', 0)
        
        # Overall ranking analysis
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, f"CURRENT OVERALL RANK: {current_rank:,}", 0, 1)
        pdf.set_font('Arial', '', 11)
        
        if current_rank <= 100000:
            strategy = "MAINTAIN LEAD: You're in elite territory. Focus on safe, consistent picks and avoid risky differentials."
        elif current_rank <= 500000:
            strategy = "CLIMB STEADILY: You're doing well. Balance proven performers with selective differentials."
        elif current_rank <= 1000000:
            strategy = "PUSH FOR TOP HALF: Time for calculated risks. Target form players and favorable fixtures."
        else:
            strategy = "MAJOR OVERHAUL NEEDED: Consider wildcarding for complete team refresh. Take bigger risks on differentials."
        
        pdf.multi_cell(0, 8, strategy, 0, 'L')
        pdf.ln(5)
        
        # Mini league strategy
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'MINI LEAGUE TACTICS:', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        tactics = [
            "Monitor rivals' teams weekly to identify their key players",
            "Consider differential picks if you're behind (low ownership gems)",
            "Play safe with proven captains if you're leading",
            "Time your chips differently from rivals for maximum advantage",
            "Track rivals' chip usage to plan your own timing"
        ]
        
        for tactic in tactics:
            tactic_text = f"STRATEGY: {tactic}"
            pdf.multi_cell(0, 6, remove_emojis(tactic_text), 0, 'L')
            pdf.ln(1)
        
        pdf.ln(5)
        
        # League data analysis if available
        if data['league_data']:
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, 'LEAGUE INSIGHTS:', 0, 1)
            pdf.set_font('Arial', '', 11)
            pdf.multi_cell(0, 6, "League analysis reveals key opportunities to gain on your rivals.", 0, 'L')
        else:
            pdf.set_font('Arial', 'I', 10)
            pdf.multi_cell(0, 6, "Add your Mini League URL in the app for detailed head-to-head analysis.", 0, 'L')
    
    def _add_action_plan(self, pdf: FPDF, data: Dict):
        """Add action plan section"""
        pdf.add_page()
        
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(0, 100, 200)
        pdf.cell(0, 10, 'YOUR WEEKLY ACTION PLAN', 0, 1)
        
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(0, 0, 0)
        
        # This week's actions
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(200, 0, 0)
        pdf.cell(0, 10, f'THIS WEEK (Gameweek {data["current_gw"]}):', 0, 1)
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(0, 0, 0)
        
        this_week_actions = self._generate_top_actions(data)
        for i, action in enumerate(this_week_actions[:3], 1):
            action_text = f"DONE: {action}"
            pdf.multi_cell(0, 6, remove_emojis(action_text), 0, 'L')
            pdf.ln(2)
        
        pdf.ln(5)
        
        # Next 2-3 gameweeks
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(255, 140, 0)
        pdf.cell(0, 10, 'NEXT 2-3 GAMEWEEKS:', 0, 1)
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(0, 0, 0)
        
        medium_term_actions = [
            "Monitor injury news and rotation risks for your players",
            "Track form changes and fixture swings for potential targets",
            "Plan chip usage timing based on upcoming fixture announcements",
            "Consider banking transfers if no urgent changes needed",
            "Research differential options if you need to make up ground"
        ]
        
        for action in medium_term_actions:
            pdf.multi_cell(0, 6, f"📅 {action}", 0, 'L')
            pdf.ln(2)
        
        pdf.ln(5)
        
        # Long-term planning
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(0, 100, 0)
        pdf.cell(0, 10, 'LONG-TERM PLANNING (Next 6+ Gameweeks):', 0, 1)
        pdf.set_font('Arial', '', 11)
        pdf.set_text_color(0, 0, 0)
        
        long_term_actions = [
            "Plan wildcard timing around breaks",
            "Identify teams with good fixtures",
            "Monitor double gameweek announcements",
            "Track mini league rivals strategies",
            "Build team structure for strong season finish"
        ]
        
        for action in long_term_actions:
            action_text = f"ACTION: {action}"
            pdf.multi_cell(0, 6, remove_emojis(action_text), 0, 'L')
            pdf.ln(2)
        
        # Footer
        pdf.ln(10)
        pdf.set_font('Arial', 'I', 10)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 6, "This report was generated by FPL Assistant Pro using advanced AI analysis of your team, fixtures, and performance data. Update your analysis weekly for optimal results.", 0, 'C')

def create_pdf_report(api_client, analysis_engine, transfer_optimizer, manager_id: int, league_id: Optional[int] = None) -> bytes:
    """Create and return PDF report as bytes"""
    generator = FPLReportGenerator(api_client, analysis_engine, transfer_optimizer)
    return generator.generate_comprehensive_report(manager_id, league_id)
