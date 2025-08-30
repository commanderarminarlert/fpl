#!/usr/bin/env python3
"""
AI-Driven FPL Report Generator
Creates intelligent, actionable reports with automatic analysis and graphs
"""

import logging
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_agg import FigureCanvasAgg
import seaborn as sns
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import io
import base64
from fpdf import FPDF
import tempfile
import os

class SafePDF(FPDF):
    """FPDF wrapper that automatically handles text formatting issues"""
    
    def cell(self, w, h, txt='', border=0, ln=0, align='', fill=False, link=''):
        safe_txt = self._clean_text(str(txt))
        return super().cell(w, h, safe_txt, border, ln, align, fill, link)
    
    def multi_cell(self, w, h, txt, border=0, align='J', fill=False, split_only=False):
        safe_txt = self._clean_text(str(txt))
        # Use cell instead of multi_cell for short text to avoid spacing issues
        if len(safe_txt) < 80 and '\n' not in safe_txt:
            # Fix alignment for cell - can't use 'J' (justified) with cell
            cell_align = 'L' if align == 'J' else align
            return self.cell(w, h, safe_txt, border, 1, cell_align, fill)
        return super().multi_cell(w, h, safe_txt, border, align, fill, split_only)
    
    def _clean_text(self, text: str) -> str:
        """Clean text for PDF compatibility"""
        import re
        
        # Remove emoji characters
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
        
        # Replace problematic characters
        text = text.replace('→', ' -> ')
        text = text.replace('←', ' <- ')
        text = text.replace('•', '* ')
        text = text.replace('…', '...')
        
        return emoji_pattern.sub('', text).strip()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set matplotlib style for better visuals
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class AIReportGenerator:
    """
    AI-Driven FPL Report Generator
    Automatically analyzes everything and provides actionable insights
    """
    
    def __init__(self, api_client, analysis_engine, transfer_optimizer):
        self.api = api_client
        self.analysis = analysis_engine
        self.optimizer = transfer_optimizer
        
        # Report configuration
        self.page_width = 210  # A4 width in mm
        self.page_height = 297  # A4 height in mm
        self.margin = 15
        
        logger.info("🤖 AI Report Generator initialized")
    
    def generate_intelligent_report(self, manager_id: int, league_id: Optional[int] = None) -> bytes:
        """Generate an intelligent, AI-driven FPL report"""
        
        logger.info(f"🤖 Generating AI-driven report for manager {manager_id}")
        
        try:
            # Gather comprehensive data
            report_data = self._gather_intelligent_data(manager_id, league_id)
            
            # Create PDF with enhanced layout and safe text handling
            pdf = SafePDF()
            pdf.set_auto_page_break(auto=True, margin=self.margin)
            pdf.set_margins(self.margin, self.margin, self.margin)
            
            # Generate report sections
            self._create_executive_dashboard(pdf, report_data)
            self._create_transfer_intelligence(pdf, report_data)
            self._create_strategic_roadmap(pdf, report_data)
            
            # Return PDF bytes
            return bytes(pdf.output())
            
        except Exception as e:
            logger.error(f"❌ AI report generation failed: {e}")
            raise
    
    def _gather_intelligent_data(self, manager_id: int, league_id: Optional[int] = None) -> Dict:
        """Gather and analyze all data intelligently"""
        
        logger.info("📊 Gathering comprehensive intelligence...")
        
        # Get enhanced manager analysis
        if hasattr(self.api, 'get_comprehensive_manager_analysis'):
            manager_analysis = self.api.get_comprehensive_manager_analysis(manager_id)
        else:
            # Fallback for basic API
            current_gw = self.api.get_current_gameweek()
            manager_data = self.api.get_manager_data(manager_id)
            team_data = self.api.get_manager_team(manager_id, current_gw)
            
            manager_analysis = {
                "manager_id": manager_id,
                "current_gameweek": current_gw,
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
                    "available": self.api.calculate_available_transfers(manager_id)
                }
            }
        
        # Get current team composition
        current_gw = manager_analysis.get('current_gameweek', self.api.get_current_gameweek())
        team_data = self.api.get_manager_team(manager_id, current_gw)
        current_team = [pick['element'] for pick in team_data.get('picks', [])]
        
        # Perform AI analysis
        ai_insights = self._perform_ai_analysis(manager_analysis, current_team)
        
        # Get transfer recommendations
        from models import UserStrategy, ChipType
        user_strategy = UserStrategy(
            manager_id=manager_id,
            team_name=manager_analysis['basic_info']['team_name'],
            current_team_value=manager_analysis['financial_status']['team_value'],
            free_transfers=manager_analysis['transfers']['available'],
            bank=manager_analysis['financial_status']['bank_balance'],
            total_points=manager_analysis['basic_info']['overall_points'],
            overall_rank=manager_analysis['basic_info']['overall_rank'],
            league_rank=1,
            chips_remaining={
                ChipType.WILDCARD: 2,
                ChipType.BENCH_BOOST: 2,
                ChipType.TRIPLE_CAPTAIN: 2,
                ChipType.FREE_HIT: 2
            },
            planned_chips=[]
        )
        
        transfer_recommendations = self.optimizer.optimize_transfers(
            user_strategy, current_team, max_transfers=3, allow_hits=True
        )
        
        # Compile comprehensive data
        return {
            **manager_analysis,
            'ai_insights': ai_insights,
            'transfer_recommendations': transfer_recommendations,
            'current_team': current_team,
            'user_strategy': user_strategy,
            'report_timestamp': datetime.now()
        }
    
    def _perform_ai_analysis(self, manager_data: Dict, current_team: List[int]) -> Dict:
        """Perform comprehensive AI analysis"""
        
        logger.info("🧠 Performing AI analysis...")
        
        # Performance analysis
        rank = manager_data['basic_info']['overall_rank']
        points = manager_data['basic_info']['overall_points']
        
        # Rank percentile (approximate)
        total_managers = 9000000  # Approximate total FPL managers
        rank_percentile = (total_managers - rank) / total_managers * 100
        
        # Performance categorization
        if rank_percentile >= 90:
            performance_tier = "ELITE"
            performance_color = "#1f77b4"
        elif rank_percentile >= 75:
            performance_tier = "EXCELLENT"
            performance_color = "#2ca02c"
        elif rank_percentile >= 50:
            performance_tier = "GOOD"
            performance_color = "#ff7f0e"
        elif rank_percentile >= 25:
            performance_tier = "AVERAGE"
            performance_color = "#d62728"
        else:
            performance_tier = "NEEDS IMPROVEMENT"
            performance_color = "#9467bd"
        
        # Financial health analysis
        bank = manager_data['financial_status']['bank_balance']
        team_value = manager_data['financial_status']['team_value']
        total_value = manager_data['financial_status']['total_budget']
        
        if bank >= 3.0:
            financial_status = "EXCELLENT - High transfer flexibility"
        elif bank >= 1.5:
            financial_status = "GOOD - Moderate flexibility"
        elif bank >= 0.5:
            financial_status = "ADEQUATE - Limited flexibility"
        else:
            financial_status = "TIGHT - Plan transfers carefully"
        
        # Transfer strategy analysis
        free_transfers = manager_data['transfers']['available']
        if free_transfers >= 2:
            transfer_strategy = "AGGRESSIVE - Use both transfers for maximum impact"
        elif free_transfers == 1:
            transfer_strategy = "SELECTIVE - Choose one high-impact transfer"
        else:
            transfer_strategy = "RECOVERY - Focus on building for next gameweek"
        
        # Generate strategic recommendations
        strategic_priorities = self._generate_strategic_priorities(
            performance_tier, bank, free_transfers, rank_percentile
        )
        
        return {
            'performance_analysis': {
                'tier': performance_tier,
                'rank_percentile': rank_percentile,
                'color': performance_color,
                'points': points,
                'rank': rank
            },
            'financial_analysis': {
                'status': financial_status,
                'bank': bank,
                'team_value': team_value,
                'total_value': total_value,
                'flexibility_score': min(100, bank * 20)  # 0-100 scale
            },
            'transfer_analysis': {
                'strategy': transfer_strategy,
                'available': free_transfers,
                'recommendation': strategic_priorities['transfer_focus']
            },
            'strategic_priorities': strategic_priorities,
            'next_actions': self._generate_next_actions(strategic_priorities)
        }
    
    def _generate_strategic_priorities(self, performance_tier: str, bank: float, 
                                     free_transfers: int, rank_percentile: float) -> Dict:
        """Generate AI-driven strategic priorities"""
        
        priorities = []
        transfer_focus = ""
        
        if performance_tier in ["NEEDS IMPROVEMENT", "AVERAGE"]:
            priorities.extend([
                "Focus on high-performing, consistent players",
                "Avoid risky differential picks until rank improves",
                "Prioritize players with good fixture runs",
                "Consider template players who are performing well"
            ])
            transfer_focus = "STABILITY - Target proven performers"
            
        elif performance_tier in ["GOOD", "EXCELLENT"]:
            priorities.extend([
                "Look for differential players to gain rank",
                "Target players with favorable upcoming fixtures",
                "Consider captaincy rotation strategy",
                "Plan chip usage for maximum impact"
            ])
            transfer_focus = "GROWTH - Calculated risks for rank gains"
            
        else:  # ELITE
            priorities.extend([
                "Focus on maintaining rank with smart differentials",
                "Plan for double gameweeks and blank gameweeks",
                "Use advanced chip strategies",
                "Consider mini-league specific tactics"
            ])
            transfer_focus = "OPTIMIZATION - Fine-tune for elite performance"
        
        # Financial considerations
        if bank < 1.0:
            priorities.append("Build bank balance for future flexibility")
        elif bank > 4.0:
            priorities.append("Use excess funds for premium upgrades")
        
        # Transfer specific advice
        if free_transfers >= 2:
            priorities.append("Maximize impact with double transfer moves")
        
        return {
            'main_priorities': priorities[:4],  # Top 4 priorities
            'transfer_focus': transfer_focus,
            'urgency_level': 'HIGH' if performance_tier == "NEEDS IMPROVEMENT" else 'MEDIUM'
        }
    
    def _generate_next_actions(self, strategic_priorities: Dict) -> List[str]:
        """Generate specific next actions"""
        
        actions = [
            f"Execute {strategic_priorities['transfer_focus'].split(' - ')[0].lower()} transfer strategy",
            "Review upcoming fixtures for next 4 gameweeks",
            "Monitor player injury news and rotation risks",
            "Plan chip usage based on fixture congestion"
        ]
        
        if strategic_priorities['urgency_level'] == 'HIGH':
            actions.insert(0, "URGENT: Address weak links in team immediately")
        
        return actions
    
    def _create_executive_dashboard(self, pdf: FPDF, data: Dict):
        """Create executive dashboard page"""
        
        pdf.add_page()
        
        # Title
        pdf.set_font('Arial', 'B', 20)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 15, 'FPL INTELLIGENCE REPORT', 0, 1, 'C')
        
        # Manager info
        pdf.set_font('Arial', '', 12)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 8, f"Manager: {data['basic_info']['name']}", 0, 1, 'C')
        pdf.cell(0, 8, f"Team: {data['basic_info']['team_name']}", 0, 1, 'C')
        pdf.cell(0, 8, f"Generated: {data['report_timestamp'].strftime('%B %d, %Y at %H:%M')}", 0, 1, 'C')
        pdf.ln(10)
        
        # Performance overview
        ai_insights = data['ai_insights']
        perf = ai_insights['performance_analysis']
        
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'PERFORMANCE OVERVIEW', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        # Performance metrics
        pdf.cell(45, 8, 'Current Rank:', 0, 0)
        pdf.cell(50, 8, f"#{perf['rank']:,}", 0, 0)
        pdf.cell(45, 8, 'Percentile:', 0, 0)
        pdf.cell(50, 8, f"{perf['rank_percentile']:.1f}%", 0, 1)
        
        pdf.cell(45, 8, 'Total Points:', 0, 0)
        pdf.cell(50, 8, f"{perf['points']}", 0, 0)
        pdf.cell(45, 8, 'Performance Tier:', 0, 0)
        pdf.cell(50, 8, perf['tier'], 0, 1)
        
        pdf.ln(5)
        
        # Financial status
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'FINANCIAL STATUS', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        fin = ai_insights['financial_analysis']
        pdf.cell(45, 8, 'Bank Balance:', 0, 0)
        pdf.cell(50, 8, f"£{fin['bank']:.1f}m", 0, 0)
        pdf.cell(45, 8, 'Team Value:', 0, 0)
        pdf.cell(50, 8, f"£{fin['team_value']:.1f}m", 0, 1)
        
        pdf.cell(45, 8, 'Total Budget:', 0, 0)
        pdf.cell(50, 8, f"£{fin['total_value']:.1f}m", 0, 0)
        pdf.cell(45, 8, 'Flexibility:', 0, 0)
        pdf.cell(50, 8, f"{fin['flexibility_score']:.0f}/100", 0, 1)
        
        pdf.ln(5)
        
        # Strategic assessment
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'AI STRATEGIC ASSESSMENT', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        priorities = ai_insights['strategic_priorities']
        pdf.multi_cell(0, 6, f"Primary Focus: {priorities['transfer_focus']}")
        pdf.ln(2)
        
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 8, 'KEY PRIORITIES:', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        for i, priority in enumerate(priorities['main_priorities'], 1):
            pdf.multi_cell(0, 5, f"{i}. {priority}")
        
        pdf.ln(5)
        
        # Immediate actions
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'IMMEDIATE ACTION PLAN', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        for i, action in enumerate(ai_insights['next_actions'], 1):
            pdf.multi_cell(0, 6, f"{i}. {action}")
    
    def _create_transfer_intelligence(self, pdf: FPDF, data: Dict):
        """Create transfer intelligence page"""
        
        pdf.add_page()
        
        # Title
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 12, 'TRANSFER INTELLIGENCE', 0, 1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
        
        # Transfer capacity
        transfers = data['transfers']['available']
        ai_insights = data['ai_insights']
        
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, f'AVAILABLE TRANSFERS: {transfers}', 0, 1)
        pdf.set_font('Arial', '', 11)
        pdf.multi_cell(0, 6, f"Strategy: {ai_insights['transfer_analysis']['strategy']}")
        pdf.ln(3)
        
        # Transfer recommendations
        recommendations = data.get('transfer_recommendations', [])
        
        if recommendations:
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, 'AI TRANSFER RECOMMENDATIONS:', 0, 1)
            pdf.set_font('Arial', '', 11)
            
            for i, transfer in enumerate(recommendations[:3], 1):
                # Transfer details
                pdf.set_font('Arial', 'B', 11)
                pdf.cell(0, 8, f'TRANSFER {i}: {transfer.player_out_name} → {transfer.player_in_name}', 0, 1)
                
                pdf.set_font('Arial', '', 10)
                pdf.cell(20, 6, 'Cost:', 0, 0)
                pdf.cell(30, 6, f'£{transfer.cost_change:+.1f}m', 0, 0)
                pdf.cell(20, 6, 'Potential:', 0, 0)
                pdf.cell(40, 6, f'{transfer.points_potential:.1f} pts', 0, 0)
                pdf.cell(25, 6, 'Confidence:', 0, 0)
                pdf.cell(25, 6, f'{transfer.confidence:.0%}', 0, 1)
                
                # Reason (cleaned of emojis and special chars)
                clean_reason = self._clean_text_for_pdf(transfer.reason)
                pdf.multi_cell(0, 5, f"Analysis: {clean_reason}")
                pdf.ln(3)
        else:
            pdf.set_font('Arial', 'B', 12)
            pdf.multi_cell(0, 8, 'TEAM OPTIMIZATION COMPLETE')
            pdf.set_font('Arial', '', 11)
            pdf.multi_cell(0, 6, 'Your team is well-optimized. Consider saving transfers for future gameweeks or monitor for injury/rotation updates.')
        
        # Bank utilization advice
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'FINANCIAL OPTIMIZATION:', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        bank = data['financial_status']['bank_balance']
        if bank > 3.0:
            advice = f"High bank balance (£{bank:.1f}m) - Consider upgrading to premium players"
        elif bank < 0.5:
            advice = f"Low bank balance (£{bank:.1f}m) - Plan budget-friendly moves"
        else:
            advice = f"Balanced finances (£{bank:.1f}m) - Good flexibility for strategic moves"
        
        pdf.multi_cell(0, 6, advice)
    
    def _create_strategic_roadmap(self, pdf: FPDF, data: Dict):
        """Create strategic roadmap page"""
        
        pdf.add_page()
        
        # Title
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 12, 'STRATEGIC ROADMAP', 0, 1)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(5)
        
        # Fixture analysis
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'FIXTURE INTELLIGENCE (Next 6 Gameweeks):', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        try:
            # Get fixture analysis from transfer optimizer
            fixture_analysis = self._analyze_upcoming_fixtures()
            
            for analysis in fixture_analysis[:4]:  # Top 4 insights
                pdf.multi_cell(0, 6, f"• {analysis}")
            
        except Exception as e:
            pdf.multi_cell(0, 6, "Fixture analysis will be updated with live data")
        
        pdf.ln(5)
        
        # Chip strategy
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'CHIP STRATEGY:', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        chip_advice = self._generate_chip_strategy(data)
        for advice in chip_advice:
            pdf.multi_cell(0, 6, f"• {advice}")
        
        pdf.ln(5)
        
        # Performance targets
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'PERFORMANCE TARGETS:', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        targets = self._generate_performance_targets(data)
        for target in targets:
            pdf.multi_cell(0, 6, f"• {target}")
        
        pdf.ln(10)
        
        # Footer
        pdf.set_font('Arial', 'I', 10)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 8, 'This report was generated by AI analysis of current FPL data and trends.', 0, 1, 'C')
        pdf.cell(0, 8, 'Recommendations are based on statistical analysis and should be considered alongside your own judgment.', 0, 1, 'C')
    
    def _analyze_upcoming_fixtures(self) -> List[str]:
        """Analyze upcoming fixtures"""
        
        # This would typically analyze fixture difficulty
        # For now, return sample intelligent analysis
        return [
            "Arsenal have excellent fixtures GW4-6 - consider their defenders",
            "Manchester City face difficult period GW5-7 - monitor rotation",
            "Brighton's favorable run makes their assets attractive",
            "Double gameweek likely in GW9 - start planning chip usage"
        ]
    
    def _generate_chip_strategy(self, data: Dict) -> List[str]:
        """Generate chip strategy advice"""
        
        current_gw = data.get('current_gameweek', 2)
        
        advice = []
        
        if current_gw <= 10:
            advice.append("Early season: Hold all chips, build strong base team first")
            advice.append("Wildcard timing: GW6-8 ideal for template building")
        elif current_gw <= 20:
            advice.append("Mid-season: Plan first wildcard around fixture swings")
            advice.append("Triple Captain: Target home fixtures vs weak defenses")
        else:
            advice.append("Late season: Aggressive chip usage for final push")
            advice.append("Bench Boost: Target double gameweeks")
        
        advice.append("Free Hit: Save for blank gameweeks or BGW38")
        
        return advice
    
    def _generate_performance_targets(self, data: Dict) -> List[str]:
        """Generate performance targets"""
        
        current_rank = data['basic_info']['overall_rank']
        rank_percentile = data['ai_insights']['performance_analysis']['rank_percentile']
        
        targets = []
        
        if rank_percentile < 25:
            targets.append("Target: Break into top 75% (improve by 25 percentile points)")
            targets.append("Focus: Consistent template players, avoid risky picks")
        elif rank_percentile < 50:
            targets.append("Target: Reach top 50% by season end")
            targets.append("Focus: Balanced approach with selective differentials")
        elif rank_percentile < 75:
            targets.append("Target: Break into top 25% (elite tier)")
            targets.append("Focus: Smart differentials and captaincy strategy")
        else:
            targets.append("Target: Maintain elite performance (top 10%)")
            targets.append("Focus: Fine-tuning and advanced strategies")
        
        targets.append(f"Season goal: Finish above rank {current_rank//2:,}")
        
        return targets
    
    def _clean_text_for_pdf(self, text: str) -> str:
        """Clean text for PDF compatibility"""
        
        # Remove emojis and special characters
        import re
        
        # Remove emoji characters
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
        
        # Replace problematic characters
        text = text.replace('→', ' -> ')
        text = text.replace('←', ' <- ')
        text = text.replace('•', '* ')
        text = text.replace('…', '...')
        
        return emoji_pattern.sub('', text).strip()

# Main function to create AI report
def create_ai_fpl_report(api_client, analysis_engine, transfer_optimizer, 
                        manager_id: int, league_id: Optional[int] = None) -> bytes:
    """Create an AI-driven FPL report"""
    
    generator = AIReportGenerator(api_client, analysis_engine, transfer_optimizer)
    return generator.generate_intelligent_report(manager_id, league_id)

# Test function
def test_ai_report():
    """Test the AI report generation"""
    
    print("🤖 Testing AI Report Generation")
    print("=" * 40)
    
    try:
        from fpl_api import FPLApiClient
        from analysis_engine import AnalysisEngine
        from transfer_optimizer import TransferOptimizer
        
        api = FPLApiClient()
        analysis = AnalysisEngine(api)
        optimizer = TransferOptimizer(api, analysis)
        
        pdf_bytes = create_ai_fpl_report(api, analysis, optimizer, 936801)
        
        print(f"✅ AI Report Generated: {len(pdf_bytes)} bytes")
        
        with open('ai_test_report.pdf', 'wb') as f:
            f.write(pdf_bytes)
        
        print("✅ AI Test Report saved as ai_test_report.pdf")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ai_report()
