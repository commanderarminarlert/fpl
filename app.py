"""
FPL Assistant - Main Streamlit Application
Professional Fantasy Premier League analysis and recommendation system
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our custom modules
from fpl_api import FPLApiClient
from analysis_engine import AnalysisEngine
from transfer_optimizer import TransferOptimizer, ChipPlanner
from models import UserStrategy, ChipType, Position, ChipStrategy

# Page configuration
st.set_page_config(
    page_title="FPL Assistant Pro",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# PERFECT MODERN UI - All light backgrounds, all dark text, no visual bugs
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* UNIVERSAL RESET */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        box-sizing: border-box !important;
    }
    
    /* MAIN APPLICATION */
    .stApp {
        background: #ffffff !important;
        color: #1a202c !important;
        line-height: 1.6 !important;
    }
    
    .main > div {
        padding: 2rem 1rem !important;
        background: #ffffff !important;
        color: #1a202c !important;
        max-width: 100% !important;
        margin: 0 !important;
    }
    
    /* SIDEBAR */
    .css-1d391kg, .css-1aumxhk, .stSidebar {
        background: #f8fafc !important;
        border-right: 1px solid #e2e8f0 !important;
        color: #1a202c !important;
        padding: 1.5rem 1rem !important;
    }
    
    /* TYPOGRAPHY */
    h1, h2, h3, h4, h5, h6 {
        color: #1a202c !important;
        font-weight: 600 !important;
        margin-bottom: 1rem !important;
    }
    
    h1 {
        font-size: 2.25rem !important;
        color: #111827 !important;
        margin-bottom: 1.5rem !important;
        border-bottom: 2px solid #3b82f6 !important;
        padding-bottom: 0.75rem !important;
    }
    
    h2 {
        font-size: 1.75rem !important;
        color: #374151 !important;
        margin-bottom: 1rem !important;
        border-left: 3px solid #3b82f6 !important;
        padding-left: 0.75rem !important;
    }
    
    h3 {
        font-size: 1.25rem !important;
        color: #374151 !important;
        margin-bottom: 0.75rem !important;
    }
    
    .stMarkdown, .stText, p, span, div, label {
        color: #374151 !important;
        font-size: 0.875rem !important;
        line-height: 1.5 !important;
    }
    
    /* METRICS */
    .stMetric {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        padding: 1.5rem !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1) !important;
        color: #1a202c !important;
        margin-bottom: 1rem !important;
        width: 100% !important;
    }
    
    .stMetric * {
        color: #1a202c !important;
    }
    
    /* INPUT FIELDS */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #ffffff !important;
        color: #374151 !important;
        border: 1px solid #d1d5db !important;
        border-radius: 6px !important;
        padding: 0.5rem 0.75rem !important;
        font-size: 0.875rem !important;
        width: 100% !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #3b82f6 !important;
        outline: none !important;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1) !important;
    }
    
    /* SIDEBAR INPUTS - NON-DROPDOWN ONLY */
    .stSidebar .stTextInput > div > div > input,
    .stSidebar .stNumberInput > div > div > input,
    .stSidebar .stTextArea > div > div > textarea {
        background: #ffffff !important;
        color: #374151 !important;
        border: 1px solid #d1d5db !important;
        border-radius: 6px !important;
        width: 100% !important;
    }
    
    /* DROPDOWN STYLING - WHITE BACKGROUNDS WITH DARK TEXT */
    .stSelectbox > div > div {
        background-color: #ffffff !important;
    }
    
    .stSelectbox [data-baseweb="select"] {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    .stSelectbox [data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    .stSelectbox [data-baseweb="select"] span {
        color: #000000 !important;
    }
    
    .stSelectbox [data-baseweb="select"] input {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    /* AGGRESSIVE DROPDOWN MENU STYLING - FORCE WHITE BACKGROUND */
    
    /* All possible dropdown menu containers */
    .stSelectbox [data-baseweb="menu"],
    .stSelectbox [data-baseweb="popover"],
    .stSelectbox [role="listbox"],
    .stSelectbox ul,
    .stSelectbox div[role="listbox"],
    .stSelectbox [data-baseweb="menu-list"],
    .stSelectbox [data-testid="stSelectbox"] [data-baseweb],
    div[data-baseweb="menu"],
    div[data-baseweb="popover"],
    div[role="listbox"] {
        background-color: #ffffff !important;
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
    }
    
    /* All possible dropdown option elements */
    .stSelectbox [data-baseweb="menu"] li,
    .stSelectbox [data-baseweb="menu"] div,
    .stSelectbox [role="option"],
    .stSelectbox li,
    div[data-baseweb="menu"] li,
    div[data-baseweb="menu"] div,
    div[role="option"],
    [role="listbox"] li,
    [role="listbox"] div {
        background-color: #ffffff !important;
        background: #ffffff !important;
        color: #000000 !important;
        padding: 0.5rem 0.75rem !important;
    }
    
    /* Hover states */
    .stSelectbox [data-baseweb="menu"] li:hover,
    .stSelectbox [data-baseweb="menu"] div:hover,
    .stSelectbox [role="option"]:hover,
    .stSelectbox li:hover,
    div[data-baseweb="menu"] li:hover,
    div[data-baseweb="menu"] div:hover,
    div[role="option"]:hover,
    [role="listbox"] li:hover,
    [role="listbox"] div:hover {
        background-color: #ffffff !important;
        background: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Focus states */
    .stSelectbox [data-baseweb="menu"] li:focus,
    .stSelectbox [data-baseweb="menu"] div:focus,
    .stSelectbox [role="option"]:focus,
    .stSelectbox li:focus,
    div[data-baseweb="menu"] li:focus,
    div[data-baseweb="menu"] div:focus,
    div[role="option"]:focus,
    [role="listbox"] li:focus,
    [role="listbox"] div:focus {
        background-color: #ffffff !important;
        background: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Selected states */
    .stSelectbox [data-baseweb="menu"] li[aria-selected="true"],
    .stSelectbox [data-baseweb="menu"] div[aria-selected="true"],
    .stSelectbox [role="option"][aria-selected="true"],
    .stSelectbox li[aria-selected="true"],
    div[data-baseweb="menu"] li[aria-selected="true"],
    div[data-baseweb="menu"] div[aria-selected="true"],
    div[role="option"][aria-selected="true"],
    [role="listbox"] li[aria-selected="true"],
    [role="listbox"] div[aria-selected="true"] {
        background-color: #ffffff !important;
        background: #ffffff !important;
        color: #000000 !important;
        font-weight: 600 !important;
    }
    
    /* Catch-all for any dropdown-related elements */
    .stSelectbox * {
        background-color: inherit !important;
    }
    
    .stSelectbox [data-baseweb] {
        background-color: #ffffff !important;
    }
    
    /* NUCLEAR OPTION - FORCE ALL POSSIBLE DROPDOWN BACKGROUNDS WHITE */
    [data-baseweb*="menu"] {
        background-color: #ffffff !important;
        background: #ffffff !important;
    }
    
    [data-baseweb*="popover"] {
        background-color: #ffffff !important;
        background: #ffffff !important;
    }
    
    [data-baseweb*="select"] [role] {
        background-color: #ffffff !important;
        background: #ffffff !important;
        color: #000000 !important;
    }
    
    /* Target any div that might be a dropdown menu */
    div[style*="position: absolute"],
    div[style*="position: fixed"] {
        background-color: #ffffff !important;
    }
    
    /* ULTRA AGGRESSIVE DROPDOWN STYLING - TARGETING EVERY POSSIBLE ELEMENT */
    
    /* Base Web Menu Components */
    [data-baseweb="menu"],
    [data-baseweb="menu"] *,
    [data-baseweb="popover"],
    [data-baseweb="popover"] *,
    [data-baseweb="menu-list"],
    [data-baseweb="menu-list"] * {
        background: white !important;
        background-color: white !important;
        color: black !important;
    }
    
    /* Role-based selectors */
    [role="listbox"],
    [role="listbox"] *,
    [role="option"],
    [role="option"] * {
        background: white !important;
        background-color: white !important;
        color: black !important;
    }
    
    /* Streamlit selectbox everything */
    .stSelectbox *,
    .stSelectbox [data-baseweb],
    .stSelectbox [data-baseweb] *,
    .stSelectbox div,
    .stSelectbox ul,
    .stSelectbox li {
        background: white !important;
        background-color: white !important;
        color: black !important;
    }
    
    /* Nuclear option - target all possible dropdown containers */
    div[data-baseweb*="menu"] *,
    div[data-baseweb*="popover"] *,
    div[data-baseweb*="select"] *,
    ul[data-baseweb*="menu"] *,
    ul[data-baseweb*="popover"] * {
        background: white !important;
        background-color: white !important;
        color: black !important;
    }
    
    /* NUMBER INPUT / COUNTER STYLING - WHITE BACKGROUND WITH BLACK TEXT */
    .stNumberInput > div > div {
        background-color: #ffffff !important;
    }
    
    .stNumberInput input {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 6px !important;
    }
    
    .stNumberInput button {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #e2e8f0 !important;
    }
    
    .stNumberInput button:hover {
        background-color: #f8fafc !important;
        color: #000000 !important;
    }
    

    
    /* TABLES - FORCE LIGHT BACKGROUNDS */
    .dataframe, .stDataFrame, table {
        background: #ffffff !important;
        color: #374151 !important;
        border-radius: 8px !important;
        overflow: hidden !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1) !important;
        border: 1px solid #e2e8f0 !important;
        width: 100% !important;
        margin: 1rem 0 !important;
    }
    
    .dataframe th, .stDataFrame th, th {
        background: #f8fafc !important;
        color: #1a202c !important;
        font-weight: 600 !important;
        padding: 0.75rem !important;
        text-align: left !important;
        border-bottom: 1px solid #e2e8f0 !important;
        border-right: none !important;
        border-left: none !important;
        border-top: none !important;
    }
    
    .dataframe td, .stDataFrame td, td {
        background: #ffffff !important;
        color: #374151 !important;
        padding: 0.75rem !important;
        border-bottom: 1px solid #f3f4f6 !important;
        border-right: none !important;
        border-left: none !important;
        border-top: none !important;
    }
    
    .dataframe tr:hover td, .stDataFrame tr:hover td {
        background: #f9fafb !important;
        color: #374151 !important;
    }
    
    .dataframe tr:last-child td, .stDataFrame tr:last-child td {
        border-bottom: none !important;
    }
    
    /* FORCE OVERRIDE ALL TABLE STYLES */
    [data-testid="stDataFrame"] {
        background: #ffffff !important;
    }
    
    [data-testid="stDataFrame"] > div {
        background: #ffffff !important;
    }
    
    [data-testid="stDataFrame"] table {
        background: #ffffff !important;
        color: #374151 !important;
    }
    
    [data-testid="stDataFrame"] th {
        background: #f8fafc !important;
        color: #1a202c !important;
    }
    
    [data-testid="stDataFrame"] td {
        background: #ffffff !important;
        color: #374151 !important;
    }
    
    /* TABS */
    .stTabs [data-baseweb="tab-list"] {
        border-bottom: 2px solid #e2e8f0 !important;
        background: #ffffff !important;
        padding: 0 !important;
        gap: 0 !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: #ffffff !important;
        color: #6b7280 !important;
        border: none !important;
        border-bottom: 3px solid transparent !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        transition: all 0.2s ease !important;
        border-radius: 0 !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: #ffffff !important;
        color: #3b82f6 !important;
        border-bottom: 3px solid #3b82f6 !important;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: #f9fafb !important;
        color: #3b82f6 !important;
    }
    
    /* BUTTONS */
    .stButton > button {
        background: #3b82f6 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 6px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button:hover {
        background: #2563eb !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* SPECIAL BUTTONS */
    .stDownloadButton > button {
        background: #10b981 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 6px !important;
    }
    
    .stDownloadButton > button:hover {
        background: #059669 !important;
    }
    
    .stLinkButton > button {
        background: #8b5cf6 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 6px !important;
    }
    
    .stLinkButton > button:hover {
        background: #7c3aed !important;
    }
    
    /* REMOVED ALL EXPANDER CSS - USING CUSTOM HTML EXPANDERS NOW */
    
    /* ALERTS */
    .stAlert, .stSuccess, .stInfo, .stWarning, .stError {
        background: #ffffff !important;
        color: #374151 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 6px !important;
        border-left: 4px solid #3b82f6 !important;
        padding: 1rem !important;
    }
    
    /* CUSTOM CLASSES */
    .transfer-rec {
        background: #f0fdf4 !important;
        color: #166534 !important;
        border: 1px solid #bbf7d0 !important;
        border-left: 4px solid #10b981 !important;
        border-radius: 6px !important;
        padding: 1rem !important;
        margin: 1rem 0 !important;
    }
    
    .chip-strategy {
        background: #fffbeb !important;
        color: #92400e !important;
        border: 1px solid #fef3c7 !important;
        border-left: 4px solid #f59e0b !important;
        border-radius: 6px !important;
        padding: 1rem !important;
        margin: 1rem 0 !important;
    }
    
    .league-position {
        background: #eff6ff !important;
        color: #1e40af !important;
        border: 1px solid #dbeafe !important;
        border-left: 4px solid #3b82f6 !important;
        border-radius: 6px !important;
        padding: 1rem !important;
        margin: 1rem 0 !important;
    }
    
    /* CHARTS */
    .stPlotlyChart {
        background: #ffffff !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1) !important;
        padding: 1rem !important;
        border: 1px solid #e2e8f0 !important;
        margin: 1rem 0 !important;
        width: 100% !important;
    }
    
    /* WIDGETS */
    .stCheckbox, .stRadio {
        color: #374151 !important;
        font-size: 0.875rem !important;
    }
    
    .stSlider {
        color: #374151 !important;
    }
    
    /* CONTAINERS AND LAYOUT */
    .stContainer {
        padding: 0 !important;
        max-width: 100% !important;
    }
    
    .stColumn {
        padding: 0 0.5rem !important;
    }
    
    [data-testid="column"] {
        padding: 0 0.5rem !important;
    }
    
    /* UNIVERSAL TEXT OVERRIDE */
    .main *, .stSidebar *, .stApp * {
        color: #374151 !important;
    }
    
    /* HEADER OVERRIDES */
    .main h1, .main h2, .main h3,
    .stSidebar h1, .stSidebar h2, .stSidebar h3 {
        color: #1a202c !important;
    }
    
    /* ENSURE ALL ELEMENTS ARE READABLE */
    button, input, select, textarea, label, span, div, p {
        color: #374151 !important;
    }
    
    /* SIDEBAR SPECIFIC */
    .stSidebar h1, .stSidebar h2, .stSidebar h3 {
        color: #1a202c !important;
        font-size: 1rem !important;
        border-left: 3px solid #3b82f6 !important;
        padding-left: 0.5rem !important;
        margin-bottom: 0.75rem !important;
    }
    
    /* SCROLLBARS */
    ::-webkit-scrollbar {
        width: 6px !important;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f5f9 !important;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #ffffff !important;
        border-radius: 3px !important;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #ffffff !important;
    }
    
    /* RESPONSIVE LAYOUT */
    @media (max-width: 768px) {
        .main > div {
            padding: 1rem 0.5rem !important;
        }
        
        .stColumn {
            padding: 0 0.25rem !important;
        }
        
        h1 {
            font-size: 1.75rem !important;
        }
        
        h2 {
            font-size: 1.5rem !important;
        }
    }
    
    /* FORCE LIGHT BACKGROUNDS ON ALL STREAMLIT ELEMENTS */
    [class*="stDataFrame"], [class*="dataframe"], [class*="table"] {
        background: #ffffff !important;
        color: #374151 !important;
    }
    
    [class*="stDataFrame"] * {
        background: #ffffff !important;
        color: #374151 !important;
    }
    
    /* ADDITIONAL TABLE OVERRIDES */
    .stDataFrame > div > div > div > div {
        background: #ffffff !important;
    }
    
    .stDataFrame table tbody tr {
        background: #ffffff !important;
    }
    
    .stDataFrame table tbody tr:hover {
        background: #f9fafb !important;
    }
    
    .stDataFrame table thead tr {
        background: #f8fafc !important;
    }
    
    /* FORCE CLEAN EXPANDERS - OVERRIDE ANY INTERFERENCE */
    .stExpander {
        position: relative !important;
        z-index: 1 !important;
        clear: both !important;
    }
    
    .stExpander summary {
        position: relative !important;
        z-index: 2 !important;
        display: block !important;
        clear: both !important;
    }
    
    .stExpander button {
        position: relative !important;
        z-index: 3 !important;
        display: block !important;
        clear: both !important;
        width: 100% !important;
        text-align: left !important;
    }
    
    .stExpander button * {
        position: relative !important;
        z-index: 4 !important;
    }
    
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)  # Cache for 10 minutes
def load_fpl_data():
    """Load and cache FPL data"""
    try:
        api = FPLApiClient()
        analysis = AnalysisEngine(api)
        optimizer = TransferOptimizer(api, analysis)
        planner = ChipPlanner(api, analysis)
        
        # Update data
        analysis.update_data()
        
        return api, analysis, optimizer, planner
    except Exception as e:
        st.error(f"Error loading FPL data: {e}")
        return None, None, None, None

def extract_manager_id_from_url(team_url: str) -> Optional[int]:
    """Extract manager ID from FPL team URL"""
    try:
        # Expected format: https://fantasy.premierleague.com/entry/123456/
        if 'entry/' in team_url:
            parts = team_url.split('entry/')
            if len(parts) > 1:
                manager_id = parts[1].split('/')[0]
                return int(manager_id)
    except:
        pass
    return None

def extract_league_id_from_url(league_url: str) -> Optional[int]:
    """Extract league ID from FPL league URL"""
    try:
        # Expected format: https://fantasy.premierleague.com/leagues/37044/standings/c
        if 'leagues/' in league_url:
            parts = league_url.split('leagues/')
            if len(parts) > 1:
                league_id = parts[1].split('/')[0]
                return int(league_id)
    except:
        pass
    return None

def create_html_table(df: pd.DataFrame) -> str:
    """Create a properly styled HTML table with guaranteed dark text on light background"""
    html_table = '<div style="background: #ffffff; padding: 1rem; border-radius: 8px; border: 1px solid #e2e8f0; margin: 1rem 0;">'
    html_table += '<table style="width: 100%; border-collapse: collapse; background: #ffffff; color: #374151; font-family: Inter, sans-serif;">'
    
    # Table header
    html_table += '<thead><tr style="background: #f8fafc; color: #1a202c; font-weight: 600;">'
    for col in df.columns:
        html_table += f'<th style="padding: 0.75rem; text-align: left; border-bottom: 1px solid #e2e8f0; color: #1a202c; font-weight: 600; font-size: 0.875rem;">{col}</th>'
    html_table += '</tr></thead>'
    
    # Table body
    html_table += '<tbody>'
    for i, row in df.iterrows():
        row_style = 'background: #f9fafb;' if i % 2 == 1 else 'background: #ffffff;'
        html_table += f'<tr style="{row_style} border-bottom: 1px solid #f3f4f6;">'
        for col in df.columns:
            cell_value = str(row[col]) if pd.notna(row[col]) else ''
            html_table += f'<td style="padding: 0.75rem; color: #374151; font-size: 0.875rem;">{cell_value}</td>'
        html_table += '</tr>'
    html_table += '</tbody></table></div>'
    
    return html_table



def main():
    """Main application"""
    
    # Header
    st.title("⚽ FPL Assistant Pro")
    st.markdown("**Your Professional Fantasy Premier League Analysis & Strategy Tool**")
    
    # Load data
    with st.spinner("Loading FPL data..."):
        api, analysis, optimizer, planner = load_fpl_data()
    
    if not api:
        st.error("Failed to load FPL data. Please check your internet connection and try again.")
        return
    
    # Sidebar for user inputs
    st.sidebar.header("🔧 Configuration")
    
    # User team setup
    st.sidebar.subheader("Your Team Details")
    
    team_url = st.sidebar.text_input(
        "FPL Team URL",
        value="",
        help="Enter your FPL team URL (e.g., https://fantasy.premierleague.com/entry/123456/)"
    )
    
    league_url = st.sidebar.text_input(
        "Mini League URL",
        value="https://fantasy.premierleague.com/leagues/37044/standings/c",
        help="Enter your mini league URL"
    )
    
    # Extract IDs
    manager_id = None
    league_id = None
    
    if team_url:
        manager_id = extract_manager_id_from_url(team_url)
        if not manager_id:
            st.sidebar.error("Invalid team URL format")
    
    if league_url:
        league_id = extract_league_id_from_url(league_url)
        if not league_id:
            st.sidebar.error("Invalid league URL format")
    
    # Manual ID inputs as fallback
    if not manager_id:
        manager_id = st.sidebar.number_input(
            "Manager ID (Manual)",
            value=0,
            help="Enter your FPL manager ID manually if URL doesn't work"
        )
    
    if not league_id:
        league_id = st.sidebar.number_input(
            "League ID (Manual)",
            value=37044,
            help="Enter your mini league ID manually if URL doesn't work"
        )
    
    # Strategy preferences
    st.sidebar.subheader("Strategy Preferences")
    
    risk_appetite = st.sidebar.selectbox(
        "Risk Appetite",
        ["Conservative", "Balanced", "Aggressive"],
        index=1
    )
    
    enable_hits = st.sidebar.checkbox(
        "Allow Point Hits",
        value=True,
        help="Allow taking point hits for transfers"
    )
    
    max_transfers = st.sidebar.slider(
        "Max Transfers per Week",
        min_value=1,
        max_value=4,
        value=2
    )
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard", 
        "🔄 Transfer Analysis", 
        "🎯 Chip Strategy", 
        "🏆 League Analysis",
        "📈 Player Analytics"
    ])
    
    with tab1:
        dashboard_tab(api, analysis, manager_id, league_id)
    
    with tab2:
        transfer_tab(api, analysis, optimizer, manager_id, enable_hits, max_transfers)
    
    with tab3:
        chip_strategy_tab(api, planner, manager_id)
    
    with tab4:
        league_analysis_tab(api, analysis, manager_id, league_id)
    
    with tab5:
        player_analytics_tab(api, analysis)

def dashboard_tab(api: FPLApiClient, analysis: AnalysisEngine, manager_id: int, league_id: int):
    """Main dashboard tab"""
    
    st.header("📊 Team Dashboard")
    
    if not manager_id:
        st.warning("Please enter your team URL or Manager ID in the sidebar to see your dashboard.")
        return
    
    try:
        # Get current gameweek info
        current_gw = api.get_current_gameweek()
        gw_info = api.get_gameweek_info(current_gw)
        
        # Get manager data
        manager_data = api.get_manager_data(manager_id)
        
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Overall Rank",
                f"#{manager_data.get('summary_overall_rank', 'N/A'):,}",
                delta=f"{manager_data.get('summary_overall_points', 0)} pts"
            )
        
        with col2:
            st.metric(
                "Total Points",
                manager_data.get('summary_overall_points', 0),
                delta=f"GW{current_gw}: {manager_data.get('summary_event_points', 0)}"
            )
        
        with col3:
            # Calculate current team value from actual picks
            team_data_for_value = api.get_manager_team(manager_id, current_gw)
            current_team_value = 100.0  # Default fallback
            
            if team_data_for_value and 'picks' in team_data_for_value:
                players_df_for_value = api.get_players_data()
                total_value = sum(
                    players_df_for_value[players_df_for_value['id'] == pick['element']].iloc[0]['value']
                    for pick in team_data_for_value['picks']
                    if not players_df_for_value[players_df_for_value['id'] == pick['element']].empty
                )
                current_team_value = total_value
            
            st.metric(
                "Team Value",
                f"£{current_team_value:.1f}m",
                delta=f"Bank: £{manager_data.get('last_deadline_bank', 0)/10:.1f}m"
            )
        
        with col4:
            # Calculate correct available transfers
            available_transfers = api.calculate_available_transfers(manager_id)
            st.metric(
                "Free Transfers",
                available_transfers,
                delta="Available"
            )
        
        # Current team
        try:
            team_data = api.get_manager_team(manager_id, current_gw)
            if team_data and 'picks' in team_data:
                
                st.subheader("Current Team")
                
                # Get player details - ensure data is loaded
                if analysis.players_df is None:
                    analysis.update_data()
                players_df = analysis.players_df
                team_picks = team_data['picks']
                
                team_players = []
                for pick in team_picks:
                    player_info = players_df[players_df['id'] == pick['element']]
                    if not player_info.empty:
                        player = player_info.iloc[0]
                        team_players.append({
                            'Name': player['web_name'],
                            'Team': player['team_name'],
                            'Position': player['position_name'],
                            'Price': f"£{player['value']:.1f}m",
                            'Points': player['total_points'],
                            'Form': f"{player['form_float']:.1f}",
                            'Captain': '(C)' if pick['is_captain'] else '(VC)' if pick['is_vice_captain'] else '',
                            'Starting': '✓' if pick['position'] <= 11 else 'Bench'
                        })
                
                if team_players:
                    team_df = pd.DataFrame(team_players)
                    st.markdown(create_html_table(team_df), unsafe_allow_html=True)
                else:
                    st.warning(f"No team players found. Picks loaded: {len(team_picks)}, Players DF size: {len(players_df) if players_df is not None else 'None'}")
                
        except Exception as e:
            st.warning(f"Could not load current team data: {e}")
        
        # Recent form chart
        try:
            history_data = api.get_manager_history(manager_id)
            if history_data and 'current' in history_data:
                
                st.subheader("Season Performance")
                
                gw_history = pd.DataFrame(history_data['current'])
                if not gw_history.empty:
                    
                    fig = make_subplots(
                        rows=2, cols=1,
                        subplot_titles=('Gameweek Points', 'Overall Rank'),
                        vertical_spacing=0.15
                    )
                    
                    # Points per gameweek
                    fig.add_trace(
                        go.Scatter(
                            x=gw_history['event'],
                            y=gw_history['points'],
                            mode='lines+markers',
                            name='GW Points',
                            line=dict(color='#4CAF50', width=3)
                        ),
                        row=1, col=1
                    )
                    
                    # Overall rank (inverted so lower rank = higher on chart)
                    fig.add_trace(
                        go.Scatter(
                            x=gw_history['event'],
                            y=gw_history['overall_rank'],
                            mode='lines+markers',
                            name='Overall Rank',
                            line=dict(color='#FF9800', width=3)
                        ),
                        row=2, col=1
                    )
                    
                    fig.update_layout(
                        height=600,
                        showlegend=True,
                        title=dict(
                            text="Performance Trends",
                            font=dict(color='#1a202c', size=16),
                            x=0.5,
                            xanchor='center'
                        ),
                        plot_bgcolor='#ffffff',
                        paper_bgcolor='#ffffff',
                        font=dict(color='#374151', size=12),
                        margin=dict(t=80, b=60, l=60, r=60),
                        legend=dict(
                            bgcolor='#ffffff',
                            bordercolor='#e2e8f0',
                            borderwidth=1,
                            font=dict(color='#374151'),
                            orientation="h",
                            xanchor="center",
                            x=0.5,
                            y=-0.15
                        )
                    )
                    
                    fig.update_xaxes(
                        title_text="Gameweek", 
                        gridcolor='#f3f4f6',
                        zerolinecolor='#e5e7eb',
                        title_font=dict(color='#374151', size=12)
                    )
                    fig.update_yaxes(
                        title_text="Points", 
                        row=1, col=1,
                        gridcolor='#f3f4f6',
                        zerolinecolor='#e5e7eb',
                        title_font=dict(color='#374151', size=12)
                    )
                    fig.update_yaxes(
                        title_text="Rank", 
                        autorange="reversed", 
                        row=2, col=1,
                        gridcolor='#f3f4f6',
                        zerolinecolor='#e5e7eb',
                        title_font=dict(color='#374151', size=12)
                    )
                    
                    st.plotly_chart(fig, width='stretch')
        
        except Exception as e:
            st.warning(f"Could not load performance history: {e}")
        
    except Exception as e:
        st.error(f"Error loading dashboard: {e}")

def transfer_tab(api: FPLApiClient, analysis: AnalysisEngine, optimizer: TransferOptimizer, 
                manager_id: int, enable_hits: bool, max_transfers: int):
    """Transfer analysis tab"""
    
    st.header("🔄 Transfer Analysis")
    
    if not manager_id:
        st.warning("Please enter your Manager ID to get transfer recommendations.")
        return
    
    try:
        # Get current team
        current_gw = api.get_current_gameweek()
        team_data = api.get_manager_team(manager_id, current_gw)
        manager_data = api.get_manager_data(manager_id)
        
        if not team_data or 'picks' not in team_data:
            st.error("Could not load current team data.")
            return
        
        # Create user strategy
        user_strategy = UserStrategy(
            manager_id=manager_id,
            team_name=manager_data.get('name', 'Unknown'),
            current_team_value=manager_data.get('last_deadline_value', 1000) / 10,
            free_transfers=api.calculate_available_transfers(manager_id),
            bank=manager_data.get('last_deadline_bank', 0) / 10,
            total_points=manager_data.get('summary_overall_points', 0),
            overall_rank=manager_data.get('summary_overall_rank', 0),
            league_rank=1,
            chips_remaining=[ChipType.WILDCARD, ChipType.BENCH_BOOST, ChipType.TRIPLE_CAPTAIN, ChipType.FREE_HIT],
            planned_chips=[]
        )
        
        current_team = [pick['element'] for pick in team_data['picks']]
        
        # Get transfer recommendations
        with st.spinner("Analyzing optimal transfers..."):
            transfers = optimizer.optimize_transfers(
                user_strategy, current_team, max_transfers=max_transfers, allow_hits=enable_hits
            )
        
        if transfers:
            st.subheader("🎯 Recommended Transfers")
            
            for i, transfer in enumerate(transfers, 1):
                with st.container():
                    st.markdown(f"""
                    <div class="transfer-rec">
                        <strong>Transfer {i}</strong><br>
                        <strong>OUT:</strong> {transfer.player_out_name} → <strong>IN:</strong> {transfer.player_in_name}<br>
                        <strong>Cost:</strong> £{transfer.cost_change:+.1f}m | 
                        <strong>Expected Points:</strong> +{transfer.points_potential:.1f} | 
                        <strong>Confidence:</strong> {transfer.confidence:.0%}<br>
                        <em>{transfer.reason}</em>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Transfer summary
            total_cost = sum(t.cost_change for t in transfers)
            total_points = sum(t.points_potential for t in transfers)
            hits_required = max(0, len(transfers) - user_strategy.free_transfers)
            net_points = total_points - (hits_required * 4)
            
            st.subheader("Transfer Summary")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Cost", f"£{total_cost:+.1f}m")
            with col2:
                st.metric("Expected Points", f"+{total_points:.1f}")
            with col3:
                st.metric("Point Hits", hits_required)
            with col4:
                st.metric("Net Benefit", f"{net_points:+.1f} pts", 
                         delta="Recommended" if net_points > 0 else "Not Recommended")
        
        else:
            st.info("No beneficial transfers found at this time. Your team looks well optimized!")
        
        # Alternative players by position
        st.subheader("🔍 Alternative Players by Position")
        
        players_df = analysis.calculate_player_scores()
        
        for position in ['Goalkeeper', 'Defender', 'Midfielder', 'Forward']:
            position_id = {'Goalkeeper': 1, 'Defender': 2, 'Midfielder': 3, 'Forward': 4}[position]
            
            pos_players = players_df[
                (players_df['element_type'] == position_id) &
                (~players_df['id'].isin(current_team))
            ].nlargest(10, 'total_score')
            
            if not pos_players.empty:
                display_df = pos_players[[
                    'web_name', 'team_name', 'value', 'total_points', 
                    'form_float', 'selected_by_percent', 'total_score'
                ]].copy()
                
                display_df.columns = [
                    'Player', 'Team', 'Price (£m)', 'Points', 
                    'Form', 'Ownership (%)', 'Analysis Score'
                ]
                
                # Create custom expandable section with HTML table content
                table_html = create_html_table(display_df)
                
                # Use simple header instead of expander to avoid text overlap
                st.markdown(f"### {position} Options")
                with st.container():
                    st.markdown(table_html, unsafe_allow_html=True)
                st.markdown("---")  # Add separator
        
    except Exception as e:
        st.error(f"Error in transfer analysis: {e}")

def chip_strategy_tab(api: FPLApiClient, planner: ChipPlanner, manager_id: int):
    """Chip strategy planning tab"""
    
    st.header("🎯 Chip Strategy Planner")
    
    # Get current gameweek and remaining chips info
    current_gw = api.get_current_gameweek()
    
    # User input for remaining chips
    st.subheader("Current Chip Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Select your remaining chips:**")
        wildcard_remaining = st.checkbox("Wildcard", value=True)
        free_hit_remaining = st.checkbox("Free Hit", value=True)
    
    with col2:
        st.write("")  # Spacing
        bench_boost_remaining = st.checkbox("Bench Boost", value=True)
        triple_captain_remaining = st.checkbox("Triple Captain", value=True)
    
    # Create chips list
    remaining_chips = []
    if wildcard_remaining:
        remaining_chips.append(ChipType.WILDCARD)
    if free_hit_remaining:
        remaining_chips.append(ChipType.FREE_HIT)
    if bench_boost_remaining:
        remaining_chips.append(ChipType.BENCH_BOOST)
    if triple_captain_remaining:
        remaining_chips.append(ChipType.TRIPLE_CAPTAIN)
    
    if remaining_chips:
        # Create mock user strategy for chip planning
        user_strategy = UserStrategy(
            manager_id=manager_id or 123456,
            team_name="Your Team",
            current_team_value=100.0,
            free_transfers=1,
            bank=1.0,
            total_points=1000,
            overall_rank=100000,
            league_rank=5,
            chips_remaining=remaining_chips,
            planned_chips=[]
        )
        
        # Generate chip strategy
        with st.spinner("Analyzing optimal chip timing..."):
            chip_strategies = planner.create_chip_strategy(user_strategy)
        
        if chip_strategies:
            st.subheader("📅 Recommended Chip Schedule")
            
            for strategy in chip_strategies:
                chip_name = strategy.chip_type.value.upper().replace('_', ' ')
                
                st.markdown(f"""
                <div class="chip-strategy">
                    <strong>{chip_name}</strong> - Gameweek {strategy.planned_gameweek}<br>
                    <strong>Priority:</strong> {strategy.priority} | 
                    <strong>Reasoning:</strong> {strategy.reason}
                </div>
                """, unsafe_allow_html=True)
        
        # Interactive chip planner
        st.subheader("🎯 Chip Bookmarking")
        st.markdown("Bookmark specific gameweeks for chip usage:")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            selected_chip = st.selectbox(
                "Select Chip",
                options=[chip.value for chip in remaining_chips],
                format_func=lambda x: x.upper().replace('_', ' ')
            )
        
        with col2:
            target_gameweek = st.number_input(
                "Target Gameweek",
                min_value=current_gw,
                max_value=38,
                value=current_gw + 5
            )
        
        with col3:
            st.write("")  # Spacing
            if st.button("📌 Bookmark Chip"):
                st.success(f"Bookmarked {selected_chip.upper()} for GW{target_gameweek}")
        
        # Fixture analysis for upcoming weeks
        st.subheader("📊 Upcoming Fixture Analysis")
        
        try:
            fixtures_df = api.get_fixtures()
            upcoming_fixtures = fixtures_df[
                (fixtures_df['event'] >= current_gw) & 
                (fixtures_df['event'] <= current_gw + 10)
            ]
            
            if not upcoming_fixtures.empty:
                # Group fixtures by gameweek
                gw_analysis = []
                for gw in range(current_gw, current_gw + 11):
                    gw_fixtures = upcoming_fixtures[upcoming_fixtures['event'] == gw]
                    
                    if not gw_fixtures.empty:
                        total_fixtures = len(gw_fixtures)
                        avg_difficulty = (gw_fixtures['team_h_difficulty'].mean() + 
                                        gw_fixtures['team_a_difficulty'].mean()) / 2
                        
                        # Determine gameweek type
                        if total_fixtures > 10:
                            gw_type = "Double GW 🔥"
                        elif total_fixtures < 5:
                            gw_type = "Blank GW ❄️"
                        else:
                            gw_type = "Normal"
                        
                        gw_analysis.append({
                            'Gameweek': gw,
                            'Fixtures': total_fixtures,
                            'Avg Difficulty': f"{avg_difficulty:.1f}",
                            'Type': gw_type,
                            'Chip Recommendation': get_chip_recommendation(gw_type, avg_difficulty)
                        })
                
                if gw_analysis:
                    analysis_df = pd.DataFrame(gw_analysis)
                    
                    st.markdown(create_html_table(analysis_df), unsafe_allow_html=True)
        
        except Exception as e:
            st.warning(f"Could not load fixture analysis: {e}")
    
    else:
        st.info("Select your remaining chips above to see strategic recommendations.")

def get_chip_recommendation(gw_type: str, avg_difficulty: float) -> str:
    """Get chip recommendation based on gameweek type and difficulty"""
    if "Double" in gw_type:
        if avg_difficulty < 3.0:
            return "Triple Captain / Bench Boost"
        else:
            return "Bench Boost"
    elif "Blank" in gw_type:
        return "Free Hit"
    elif avg_difficulty < 2.5:
        return "Consider Triple Captain"
    else:
        return "Hold chips"

def league_analysis_tab(api: FPLApiClient, analysis: AnalysisEngine, manager_id: int, league_id: int):
    """League analysis tab"""
    
    st.header("🏆 Mini League Analysis")
    
    if not league_id:
        st.warning("Please enter your League ID to see league analysis.")
        return
    
    try:
        # Get league standings
        with st.spinner("Loading league data..."):
            league_analysis_data = analysis.analyze_mini_league(league_id, manager_id or 0)
        
        # League overview
        st.subheader(f"📊 {league_analysis_data.league_name}")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Your Rank", f"{league_analysis_data.user_rank}/{league_analysis_data.total_teams}")
        
        with col2:
            st.metric("Points to Leader", league_analysis_data.points_to_leader)
        
        with col3:
            st.metric("Points to Next Rank", league_analysis_data.points_to_next_rank)
        
        with col4:
            st.metric("Teams in League", league_analysis_data.total_teams)
        
        # League table
        st.subheader("📋 Current Standings")
        
        standings_data = []
        # Find the leader's points (first competitor has the highest points)
        leader_points = league_analysis_data.competitors[0].total_points if league_analysis_data.competitors else 0
        
        for competitor in league_analysis_data.competitors[:10]:  # Top 10
            # Calculate gap from leader
            points_gap = leader_points - competitor.total_points
            
            standings_data.append({
                'Rank': competitor.rank,
                'Team Name': competitor.team_name,
                'Manager': competitor.player_name,
                'Total Points': competitor.total_points,
                'Last GW': competitor.last_gw_points,
                'Points Gap': points_gap,
                'manager_id': competitor.manager_id  # For user identification
            })
        
        if standings_data:
            standings_df = pd.DataFrame(standings_data)
            
            # Hide manager_id column from display
            display_columns = [col for col in standings_df.columns if col != 'manager_id']
            
            # Create HTML table with user highlighting
            html_table = '<div style="background: #ffffff; padding: 1rem; border-radius: 8px; border: 1px solid #e2e8f0; margin: 1rem 0;">'
            html_table += '<table style="width: 100%; border-collapse: collapse; background: #ffffff; color: #374151; font-family: Inter, sans-serif;">'
            
            # Table header
            html_table += '<thead><tr style="background: #f8fafc; color: #1a202c; font-weight: 600;">'
            for col in display_columns:
                html_table += f'<th style="padding: 0.75rem; text-align: left; border-bottom: 1px solid #e2e8f0; color: #1a202c; font-weight: 600; font-size: 0.875rem;">{col}</th>'
            html_table += '</tr></thead>'
            
            # Table body with user highlighting
            html_table += '<tbody>'
            for i, row in standings_df.iterrows():
                # Highlight user's row (based on manager_id)
                is_user_row = manager_id and row['manager_id'] == manager_id
                if is_user_row:
                    row_style = 'background: #e8f5e8; border-left: 4px solid #10b981;'
                else:
                    row_style = 'background: #f9fafb;' if i % 2 == 1 else 'background: #ffffff;'
                
                html_table += f'<tr style="{row_style} border-bottom: 1px solid #f3f4f6;">'
                for col in display_columns:
                    cell_value = str(row[col]) if pd.notna(row[col]) else ''
                    font_weight = 'font-weight: 600;' if is_user_row else ''
                    html_table += f'<td style="padding: 0.75rem; color: #374151; font-size: 0.875rem; {font_weight}">{cell_value}</td>'
                html_table += '</tr>'
            html_table += '</tbody></table></div>'
            
            st.markdown(html_table, unsafe_allow_html=True)
        
        # Strategic advice
        st.subheader("💡 Strategic Insights")
        
        st.markdown(f"""
        <div class="league-position">
            <strong>Position Analysis:</strong><br>
            {league_analysis_data.strategic_advice}
        </div>
        """, unsafe_allow_html=True)
        
        # Points progression chart
        if len(league_analysis_data.competitors) > 1:
            st.subheader("📈 League Competition")
            
            # Create a simple points comparison chart
            top_5 = league_analysis_data.competitors[:5]
            
            fig = go.Figure()
            
            for i, competitor in enumerate(top_5):
                color = '#4CAF50' if competitor.manager_id == manager_id else f'rgba(100, 100, 100, {1-i*0.1})'
                
                fig.add_trace(go.Bar(
                    name=competitor.team_name[:15] + "..." if len(competitor.team_name) > 15 else competitor.team_name,
                    x=[competitor.rank],
                    y=[competitor.total_points],
                    marker_color=color,
                    text=f"{competitor.total_points} pts",
                    textposition='auto'
                ))
            
            fig.update_layout(
                title=dict(
                    text="Top 5 Teams - Total Points",
                    font=dict(color='#1a202c', size=16)
                ),
                xaxis_title="League Rank",
                yaxis_title="Total Points",
                showlegend=True,
                height=400,
                plot_bgcolor='#ffffff',
                paper_bgcolor='#ffffff',
                font=dict(color='#374151', size=12),
                xaxis=dict(
                    gridcolor='#f3f4f6',
                    zerolinecolor='#e5e7eb',
                    color='#374151'
                ),
                yaxis=dict(
                    gridcolor='#f3f4f6',
                    zerolinecolor='#e5e7eb',
                    color='#374151'
                ),
                legend=dict(
                    bgcolor='#ffffff',
                    bordercolor='#e2e8f0',
                    borderwidth=1,
                    font=dict(color='#374151')
                )
            )
            
            st.plotly_chart(fig, width='stretch')
        
    except Exception as e:
        st.error(f"Error loading league analysis: {e}")

def player_analytics_tab(api: FPLApiClient, analysis: AnalysisEngine):
    """Player analytics tab"""
    
    st.header("📈 Player Analytics")
    
    # Player search and analysis
    players_df = analysis.calculate_player_scores()
    
    if players_df is None or players_df.empty:
        st.error("No player data available.")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        position_filter = st.selectbox(
            "Position Filter",
            options=['All'] + sorted(list(players_df['position_name'].unique()))
        )
    
    with col2:
        team_filter = st.selectbox(
            "Team Filter",
            options=['All'] + sorted(list(players_df['team_name'].unique()))
        )
    
    with col3:
        price_filter = st.slider(
            "Max Price (£m)",
            min_value=0.0,
            max_value=15.0,
            value=15.0,
            step=0.5
        )
    
    # Apply filters
    filtered_df = players_df.copy()
    
    if position_filter != 'All':
        filtered_df = filtered_df[filtered_df['position_name'] == position_filter]
    
    if team_filter != 'All':
        filtered_df = filtered_df[filtered_df['team_name'] == team_filter]
    
    filtered_df = filtered_df[filtered_df['value'] <= price_filter]
    
    # Top players analysis
    st.subheader("🌟 Top Players by Analysis Score")
    
    top_players = filtered_df.nlargest(20, 'total_score')
    
    if not top_players.empty:
        display_cols = [
            'web_name', 'team_name', 'position_name', 'value', 'total_points',
            'form_float', 'points_per_game', 'selected_by_percent', 'total_score'
        ]
        
        display_df = top_players[display_cols].copy()
        display_df.columns = [
            'Player', 'Team', 'Position', 'Price (£m)', 'Total Points',
            'Form', 'PPG', 'Ownership (%)', 'Score'
        ]
        
        # Round numerical columns safely
        numerical_cols = ['Price (£m)', 'Form', 'PPG', 'Ownership (%)', 'Score']
        for col in numerical_cols:
            if col in display_df.columns:
                # Only round if the column is numeric
                if pd.api.types.is_numeric_dtype(display_df[col]):
                    display_df[col] = display_df[col].round(1)
        
        st.markdown(create_html_table(display_df), unsafe_allow_html=True)
        
        # Scatter plot analysis
        st.subheader("📊 Player Value Analysis")
        
        fig = px.scatter(
            top_players,
            x='value',
            y='total_points',
            color='position_name',
            size='form_float',
            hover_name='web_name',
            hover_data=['team_name', 'points_per_game'],
            title="Player Value vs Total Points (Size = Form)",
            labels={
                'value': 'Price (£m)',
                'total_points': 'Total Points',
                'position_name': 'Position'
            }
        )
        
        fig.update_layout(
            height=500,
            plot_bgcolor='#ffffff',
            paper_bgcolor='#ffffff',
            font=dict(color='#374151', size=12),
            title=dict(font=dict(color='#1a202c', size=16)),
            legend=dict(
                bgcolor='#ffffff',
                bordercolor='#e2e8f0',
                borderwidth=1,
                font=dict(color='#374151')
            ),
            xaxis=dict(
                gridcolor='#f3f4f6',
                zerolinecolor='#e5e7eb',
                color='#374151'
            ),
            yaxis=dict(
                gridcolor='#f3f4f6',
                zerolinecolor='#e5e7eb',
                color='#374151'
            )
        )
        st.plotly_chart(fig, width='stretch')
    
    # Differential picks
    st.subheader("💎 Differential Picks")
    st.markdown("Low ownership players with high potential:")
    
    # Convert columns to numeric for filtering
    filtered_df_numeric = filtered_df.copy()
    filtered_df_numeric['ownership_num'] = pd.to_numeric(filtered_df_numeric['selected_by_percent'], errors='coerce').fillna(0)
    filtered_df_numeric['points_num'] = pd.to_numeric(filtered_df_numeric['total_points'], errors='coerce').fillna(0)
    filtered_df_numeric['form_num'] = pd.to_numeric(filtered_df_numeric['form_float'], errors='coerce').fillna(0)
    
    # Adjust criteria based on current gameweek (early season = lower thresholds)
    current_gw = api.get_current_gameweek()
    points_threshold = max(10, min(50, current_gw * 8))  # Scale with gameweek progress
    form_threshold = max(1.0, min(3.0, current_gw * 0.5))  # Scale form threshold
    
    differentials = filtered_df_numeric[
        (filtered_df_numeric['ownership_num'] < 10) &
        (filtered_df_numeric['points_num'] > points_threshold) &
        (filtered_df_numeric['form_num'] > form_threshold)
    ].nlargest(10, 'total_score')
    
    if not differentials.empty:
        diff_display = differentials[[
            'web_name', 'team_name', 'position_name', 'value', 
            'total_points', 'form_float', 'selected_by_percent'
        ]].copy()
        
        diff_display.columns = [
            'Player', 'Team', 'Position', 'Price (£m)', 
            'Points', 'Form', 'Ownership (%)'
        ]
        
        st.markdown(create_html_table(diff_display), unsafe_allow_html=True)
    else:
        st.info("No suitable differential picks found with current filters.")

if __name__ == "__main__":
    main()
