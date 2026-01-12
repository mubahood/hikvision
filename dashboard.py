"""
Hikvision Bridge Dashboard
Professional monitoring and control interface with URL-based routing
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import subprocess
import json
import time
from pathlib import Path

# Must be first Streamlit command
st.set_page_config(
    page_title="Hikvision Access Control",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23A22431'><path d='M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z'/></svg>",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - Light theme, compact spacing, no rounded corners
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    /* Base light theme - force all text dark */
    .stApp {
        background-color: #FFFFFF;
        color: #111827 !important;
    }
    
    /* Global text color override */
    .stApp * {
        color: #374151;
    }
    
    :root {
        --primary: #A22431;
        --text-dark: #111827;
        --text-medium: #374151;
        --text-light: #6B7280;
        --border: #E5E7EB;
        --bg-light: #F9FAFB;
    }
    
    /* Remove all dark headers */
    header[data-testid="stHeader"] {
        background-color: #FFFFFF !important;
        border-bottom: 1px solid #E5E7EB;
    }
    
    .stApp > header {
        background-color: transparent !important;
    }
    
    /* Force labels to be visible */
    label, .stTextInput label, .stSelectbox label, .stDateInput label, .stNumberInput label {
        color: #374151 !important;
        font-weight: 500 !important;
    }
    /* Main content - proper spacing */
    .block-container {
        padding: 1rem 1rem 1rem 1rem !important;
        max-width: 100% !important;
    }
    
    /* Sidebar - clean light design */
    [data-testid="stSidebar"] {
        background-color: #FAFAFA;
        border-right: 1px solid #E5E7EB;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background-color: #FAFAFA;
        padding-top: 0.5rem;
    }
    
    /* Sidebar brand */
    .sidebar-brand {
        color: #A22431;
        font-size: 1rem;
        font-weight: 700;
        padding: 0.5rem 0.75rem;
        margin: 0;
        border-bottom: 1px solid #E5E7EB;
    }
    
    /* Navigation links */
    .nav-link {
        display: block;
        padding: 0.5rem 0.75rem;
        color: #374151;
        text-decoration: none;
        font-size: 0.8125rem;
        font-weight: 500;
        border-left: 2px solid transparent;
        transition: all 0.1s;
    }
    
    .nav-link:hover {
        background-color: #F3F4F6;
        color: #A22431;
    }
    
    .nav-link.active {
        background-color: #FEF2F2;
        color: #A22431;
        border-left-color: #A22431;
        font-weight: 600;
    }
    
    /* Sidebar radio navigation - clean single-level styling */
    [data-testid="stSidebar"] .stRadio > label {
        display: none !important;
    }
    
    [data-testid="stSidebar"] .stRadio > div {
        gap: 0 !important;
        background: transparent !important;
        width: 100% !important;
    }
    
    [data-testid="stSidebar"] .stRadio > div > div {
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Style only the label container, not children */
    [data-testid="stSidebar"] .stRadio label {
        background-color: transparent !important;
        border-left: 3px solid transparent !important;
        padding: 0.4rem 0.75rem !important;
        margin: 0 !important;
        border-radius: 0 !important;
        cursor: pointer;
        display: block !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    
    /* Text inside labels - no extra styling */
    [data-testid="stSidebar"] .stRadio label span,
    [data-testid="stSidebar"] .stRadio label p,
    [data-testid="stSidebar"] .stRadio label div {
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
        font-size: 0.8125rem !important;
        font-weight: 500 !important;
        color: #374151 !important;
        line-height: 1.3 !important;
    }
    
    /* Hover state - only on label */
    [data-testid="stSidebar"] .stRadio label:hover {
        background-color: #F3F4F6 !important;
        border-left-color: #E5E7EB !important;
    }
    
    [data-testid="stSidebar"] .stRadio label:hover span,
    [data-testid="stSidebar"] .stRadio label:hover p {
        color: #A22431 !important;
    }
    
    /* Selected state - only on label */
    [data-testid="stSidebar"] .stRadio label[data-checked="true"],
    [data-testid="stSidebar"] .stRadio label:has(input:checked) {
        background-color: #FEF2F2 !important;
        border-left-color: #A22431 !important;
    }
    
    [data-testid="stSidebar"] .stRadio label[data-checked="true"] span,
    [data-testid="stSidebar"] .stRadio label[data-checked="true"] p,
    [data-testid="stSidebar"] .stRadio label:has(input:checked) span,
    [data-testid="stSidebar"] .stRadio label:has(input:checked) p {
        color: #A22431 !important;
        font-weight: 600 !important;
    }
    
    /* Hide radio inputs */
    [data-testid="stSidebar"] input[type="radio"],
    [data-testid="stSidebar"] .stRadio div[role="radio"] {
        display: none !important;
    }
    
    /* Hide the "Navigation" label text */
    [data-testid="stSidebar"] .stRadio > div:first-child {
        display: none !important;
    }
    
    /* Force all sidebar text to be dark */
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] div {
        color: #374151 !important;
    }
    
    [data-testid="stSidebar"] .stRadio label p {
        color: inherit !important;
        margin: 0 !important;
    }
    
    /* Headers - compact */
    h1 {
        color: #111827 !important;
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        margin: 0 0 0.75rem 0 !important;
        padding: 0 !important;
    }
    
    h2, .stSubheader {
        color: #374151 !important;
        font-size: 0.9375rem !important;
        font-weight: 600 !important;
        margin: 0.75rem 0 0.5rem 0 !important;
    }
    
    h3 {
        color: #4B5563 !important;
        font-size: 0.875rem !important;
        font-weight: 600 !important;
        margin: 0.5rem 0 0.25rem 0 !important;
    }
    
    /* Metrics - compact */
    [data-testid="stMetric"] {
        background-color: #FAFAFA;
        border: 1px solid #E5E7EB;
        border-radius: 0 !important;
        padding: 0.5rem !important;
    }
    
    [data-testid="stMetricValue"] {
        color: #A22431 !important;
        font-size: 1.25rem !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: #6B7280 !important;
        font-size: 0.75rem !important;
        font-weight: 500 !important;
    }
    
    /* Buttons - no rounded corners, white text */
    .stButton > button {
        background-color: #A22431 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 0.375rem 0.75rem !important;
        font-size: 0.8125rem !important;
        font-weight: 500 !important;
        min-height: auto !important;
    }
    
    .stButton > button p,
    .stButton > button span,
    .stButton > button div {
        color: #FFFFFF !important;
    }
    
    .stButton > button:hover {
        background-color: #8B1D28 !important;
    }
    
    .stButton > button:hover p,
    .stButton > button:hover span,
    .stButton > button:hover div {
        color: #FFFFFF !important;
    }
    
    .stButton > button:disabled {
        background-color: #E5E7EB !important;
        color: #6B7280 !important;
    }
    
    .stButton > button:disabled p,
    .stButton > button:disabled span,
    .stButton > button:disabled div {
        color: #6B7280 !important;
    }
    
    /* Small icon buttons */
    .stButton > button:has(> div:only-child) {
        padding: 0.25rem 0.5rem !important;
        min-width: 32px !important;
    }
    
    /* Download button compact */
    .stDownloadButton > button {
        background-color: #374151 !important;
        border-radius: 0 !important;
        padding: 0.25rem 0.5rem !important;
        min-height: auto !important;
        font-size: 0.75rem !important;
    }
    
    .stDownloadButton > button:hover {
        background-color: #1F2937 !important;
    }
    
    /* Form inputs - light, no rounded corners */
    input, select, textarea,
    [data-baseweb="input"] input,
    [data-baseweb="select"] > div,
    [data-baseweb="base-input"] {
        background-color: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 0 !important;
        color: #111827 !important;
        font-size: 0.8125rem !important;
    }
    
    input:focus, select:focus, textarea:focus,
    [data-baseweb="input"]:focus-within,
    [data-baseweb="base-input"]:focus-within {
        border-color: #A22431 !important;
        box-shadow: none !important;
        outline: none !important;
    }
    
    /* Selectbox */
    [data-baseweb="select"] > div {
        border-radius: 0 !important;
        min-height: 2rem !important;
    }
    
    /* Tables - no rounded corners, compact */
    [data-testid="stDataFrame"] {
        border: 1px solid #E5E7EB !important;
        border-radius: 0 !important;
    }
    
    [data-testid="stDataFrame"] thead th {
        background-color: #F9FAFB !important;
        color: #374151 !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        padding: 0.375rem 0.5rem !important;
        border-bottom: 1px solid #E5E7EB !important;
    }
    
    [data-testid="stDataFrame"] tbody td {
        font-size: 0.75rem !important;
        padding: 0.25rem 0.5rem !important;
        color: #111827 !important;
        border-bottom: 1px solid #F3F4F6 !important;
    }
    
    [data-testid="stDataFrame"] tbody tr:hover {
        background-color: #F9FAFB !important;
    }
    
    /* Expander - compact, light background */
    .streamlit-expanderHeader {
        background-color: #F9FAFB !important;
        border: 1px solid #E5E7EB !important;
        border-radius: 0 !important;
        padding: 0.375rem 0.75rem !important;
        font-size: 0.8125rem !important;
        font-weight: 600 !important;
        color: #374151 !important;
    }
    
    .streamlit-expanderHeader p,
    .streamlit-expanderHeader span,
    .streamlit-expanderHeader svg {
        color: #374151 !important;
        fill: #374151 !important;
    }
    
    .streamlit-expanderContent {
        padding: 0.5rem 0 !important;
        border: none !important;
    }
    
    details[open] .streamlit-expanderHeader {
        border-radius: 0 !important;
    }
    
    /* Alerts - no rounded corners, compact */
    .stAlert, [data-baseweb="notification"] {
        border-radius: 0 !important;
        padding: 0.375rem 0.75rem !important;
        font-size: 0.8125rem !important;
    }
    
    .stAlert p, [data-baseweb="notification"] p {
        font-size: 0.8125rem !important;
    }
    
    /* Info box */
    div[data-testid="stAlert"] {
        background-color: #EFF6FF !important;
        border: 1px solid #BFDBFE !important;
        border-radius: 0 !important;
    }
    
    div[data-testid="stAlert"] p {
        color: #1E40AF !important;
    }
    
    /* Text area - no rounded corners */
    .stTextArea textarea {
        border-radius: 0 !important;
        font-size: 0.75rem !important;
        font-family: 'Monaco', 'Menlo', monospace !important;
    }
    
    /* Number input */
    [data-testid="stNumberInput"] input {
        border-radius: 0 !important;
    }
    
    [data-testid="stNumberInput"] button {
        border-radius: 0 !important;
        background-color: #F9FAFB !important;
        border: 1px solid #D1D5DB !important;
    }
    
    /* Date input */
    [data-testid="stDateInput"] > div > div {
        border-radius: 0 !important;
    }
    
    /* Slider */
    .stSlider > div > div {
        background-color: #E5E7EB !important;
    }
    
    .stSlider > div > div > div {
        background-color: #A22431 !important;
    }
    
    /* Dividers - tighter */
    hr {
        margin: 0.5rem 0 !important;
        border-color: #E5E7EB !important;
    }
    
    /* Remove extra element spacing */
    .element-container {
        margin-bottom: 0.25rem !important;
    }
    
    /* Columns - tighter */
    [data-testid="column"] {
        padding: 0 0.25rem !important;
    }
    
    [data-testid="column"]:first-child {
        padding-left: 0 !important;
    }
    
    [data-testid="column"]:last-child {
        padding-right: 0 !important;
    }
    
    /* Forms - compact */
    .stForm {
        border: 1px solid #E5E7EB !important;
        border-radius: 0 !important;
        padding: 0.75rem !important;
        background-color: #FAFAFA !important;
    }
    
    /* Checkbox */
    .stCheckbox label {
        font-size: 0.8125rem !important;
    }
    
    /* Hide branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Sidebar footer */
    [data-testid="stSidebar"] hr {
        margin: 0.5rem 0 !important;
    }
    
    [data-testid="stSidebar"] p {
        font-size: 0.6875rem !important;
        color: #9CA3AF !important;
        padding: 0 0.75rem !important;
    }
    
    /* Plotly charts - remove extra padding */
    .js-plotly-plot {
        margin: 0 !important;
    }
    
    /* JSON display */
    .stJson {
        border-radius: 0 !important;
    }
    
    /* Spinner */
    .stSpinner > div {
        border-color: #A22431 !important;
    }
    
    /* Tab styling if used */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0 !important;
        border-bottom: 1px solid #E5E7EB !important;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 0 !important;
        padding: 0.375rem 0.75rem !important;
        font-size: 0.8125rem !important;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #FEF2F2 !important;
        border-bottom: 2px solid #A22431 !important;
    }
    
    /* Dialog/Modal styling */
    [data-testid="stModal"] > div {
        background-color: #FFFFFF !important;
        border-radius: 0 !important;
        border: 1px solid #E5E7EB !important;
    }
    
    [data-testid="stModal"] h1 {
        font-size: 1rem !important;
        color: #A22431 !important;
    }
    
    /* Compact selectbox */
    .stSelectbox > div > div {
        min-height: 32px !important;
    }
    
    /* Event details modal */
    .event-detail-label {
        font-size: 0.7rem;
        color: #6B7280;
        margin-bottom: 2px;
    }
    .event-detail-value {
        font-size: 0.8rem;
        color: #111827;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

# Import controllers (MVC architecture)
from controllers.event_controller import EventController
from controllers.config_controller import ConfigController
from controllers.bridge_controller import BridgeController
from controllers.device_controller import DeviceController
from controllers.upload_sync_controller import UploadSyncController

# Initialize controllers (cached for performance)
@st.cache_resource
def init_controllers():
    return {
        'event': EventController(),
        'config': ConfigController(),
        'bridge': BridgeController()
    }

controllers = init_controllers()
event_ctrl = controllers['event']
config_ctrl = controllers['config']
bridge_ctrl = controllers['bridge']

# Device controller - fresh instance each time for accurate connection status
def get_device_ctrl():
    return DeviceController()

def get_upload_sync_ctrl():
    return UploadSyncController()

device_ctrl = get_device_ctrl()
upload_sync_ctrl = get_upload_sync_ctrl()

# URL-based routing
PAGES = {
    "overview": "Overview",
    "events": "Events", 
    "statistics": "Statistics",
    "bridge": "Bridge Control",
    "device_sync": "Device Sync",
    "upload_sync": "Upload Sync",
    "logs": "Logs",
    "controls": "Settings",
    "configuration": "Configuration"
}

# Get current page from URL query params
query_params = st.query_params
current_page = query_params.get("page", "overview")

# Validate page
if current_page not in PAGES:
    current_page = "overview"

# Sidebar
st.sidebar.markdown('<p class="sidebar-brand">HIKVISION</p>', unsafe_allow_html=True)

# Navigation with URL routing
selected_page = st.sidebar.radio(
    "Navigation",
    options=list(PAGES.keys()),
    format_func=lambda x: PAGES[x],
    index=list(PAGES.keys()).index(current_page),
    key="nav",
    label_visibility="collapsed"
)

# Update URL when selection changes
if selected_page != current_page:
    st.query_params["page"] = selected_page
    st.rerun()

# Sidebar footer
st.sidebar.markdown("---")
st.sidebar.markdown("v1.0 | Access Control")

# ============================================
# PAGE: OVERVIEW
# ============================================
if current_page == "overview":
    # Compact CSS for this page
    st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
    .overview-header { display:flex; align-items:center; justify-content:space-between; padding:6px 12px; background:#F9FAFB; border:1px solid #E5E7EB; margin-bottom:8px; }
    .stat-row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
    .stat-box { background:#fff; border:1px solid #E5E7EB; padding:4px 12px; min-width:70px; text-align:center; }
    .stat-box.highlight { border-left:3px solid #A22431; }
    .stat-val { font-size:14px; font-weight:600; color:#111827; }
    .stat-val.primary { color:#A22431; }
    .stat-val.success { color:#10B981; }
    .stat-val.warning { color:#F59E0B; }
    .stat-val.danger { color:#DC2626; }
    .stat-lbl { font-size:8px; color:#6B7280; text-transform:uppercase; }
    .section-title { font-size:12px; font-weight:600; color:#374151; margin:12px 0 6px 0; display:flex; align-items:center; gap:6px; }
    .event-row { display:flex; justify-content:space-between; align-items:center; padding:6px 10px; background:#FAFAFA; margin:2px 0; font-size:10px; border-left:2px solid #E5E7EB; }
    .event-row:hover { background:#F3F4F6; border-left-color:#A22431; }
    .chart-card { background:#fff; border:1px solid #E5E7EB; padding:12px; }
    .quick-action { background:#fff; border:1px solid #E5E7EB; padding:8px 12px; display:flex; align-items:center; gap:8px; cursor:pointer; transition:all 0.15s; }
    .quick-action:hover { border-color:#A22431; background:#FEF2F2; }
    .quick-action i { color:#A22431; font-size:14px; }
    .quick-action span { font-size:11px; color:#374151; font-weight:500; }
    </style>
    """, unsafe_allow_html=True)
    
    today_stats = event_ctrl.get_today_stats()
    sync_stats = event_ctrl.get_sync_stats()
    bridge_status = bridge_ctrl.get_status()
    is_running = bridge_status.get("running", False)
    
    # === HEADER: System Status + Key Stats ===
    bridge_badge = '<span style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:8px;font-size:9px;font-weight:600;background:#DCFCE7;color:#166534;"><i class="fa-solid fa-circle" style="font-size:5px;"></i> BRIDGE RUNNING</span>' if is_running else '<span style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:8px;font-size:9px;font-weight:600;background:#FEE2E2;color:#991B1B;"><i class="fa-solid fa-circle" style="font-size:5px;"></i> BRIDGE STOPPED</span>'
    
    last_event_text = "-"
    if today_stats.get('last_event'):
        time_diff = datetime.now() - today_stats['last_event']
        minutes_ago = time_diff.seconds // 60
        last_event_text = f"{minutes_ago}m ago" if minutes_ago > 0 else "Just now"
    
    header_html = f"""
    <div class="overview-header">
        <div style="display:flex;align-items:center;gap:16px;">
            {bridge_badge}
            <div class="stat-row">
                <div class="stat-box highlight"><div class="stat-val primary">{today_stats.get('total_events', 0)}</div><div class="stat-lbl">Today</div></div>
                <div class="stat-box"><div class="stat-val">{today_stats.get('unique_users', 0)}</div><div class="stat-lbl">Users</div></div>
                <div class="stat-box"><div class="stat-val">{today_stats.get('doors_accessed', 0)}</div><div class="stat-lbl">Doors</div></div>
                <div class="stat-box"><div class="stat-val">{last_event_text}</div><div class="stat-lbl">Last Event</div></div>
            </div>
        </div>
        <div class="stat-row">
            <div class="stat-box"><div class="stat-val success">{sync_stats.get('synced', 0)}</div><div class="stat-lbl">Synced</div></div>
            <div class="stat-box"><div class="stat-val warning">{sync_stats.get('pending', 0)}</div><div class="stat-lbl">Pending</div></div>
            <div class="stat-box"><div class="stat-val danger">{sync_stats.get('failed', 0)}</div><div class="stat-lbl">Failed</div></div>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # === MAIN CONTENT: Two columns ===
    left, right = st.columns([1.5, 1])
    
    # --- LEFT: Recent Events + Chart ---
    with left:
        st.markdown('<p class="section-title"><i class="fa-solid fa-clock-rotate-left" style="color:#A22431;"></i> Recent Events</p>', unsafe_allow_html=True)
        
        recent_events = event_ctrl.get_events_as_dicts(limit=8)
        
        if recent_events:
            event_box = st.container(height=180)
            with event_box:
                for evt in recent_events:
                    occur = evt.get('occur_time', '-')
                    if hasattr(occur, 'strftime'):
                        occur = occur.strftime('%H:%M:%S')
                    name = evt.get('name', '-')[:20] if evt.get('name') else '-'
                    emp = evt.get('employee_no', '-')
                    door = evt.get('door_no', '-')
                    sync = evt.get('sync_status', 'pending')
                    sync_icon = '<i class="fa-solid fa-check" style="color:#10B981;font-size:8px;"></i>' if sync == 'synced' else '<i class="fa-solid fa-clock" style="color:#F59E0B;font-size:8px;"></i>'
                    st.markdown(f"""
                    <div class="event-row">
                        <span style="color:#6B7280;">{occur}</span>
                        <span style="font-weight:500;">{name}</span>
                        <span>#{emp}</span>
                        <span>Door {door}</span>
                        {sync_icon}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="padding:20px;text-align:center;color:#6B7280;font-size:11px;">No events recorded yet</div>', unsafe_allow_html=True)
        
        # Events Chart (24h)
        st.markdown('<p class="section-title"><i class="fa-solid fa-chart-line" style="color:#A22431;"></i> Activity (24h)</p>', unsafe_allow_html=True)
        
        hourly = event_ctrl.get_hourly_stats(days=1)
        if hourly:
            df_hourly = pd.DataFrame(hourly)
            fig = px.area(df_hourly, x='event_hour', y='event_count')
            fig.update_traces(line_color='#A22431', fillcolor='rgba(162, 36, 49, 0.1)')
            fig.update_layout(
                plot_bgcolor='white', paper_bgcolor='white',
                font=dict(size=9, color="#6B7280"),
                margin=dict(l=0, r=0, t=5, b=0),
                showlegend=False,
                xaxis=dict(title="", showgrid=False, tickfont=dict(size=8)),
                yaxis=dict(title="", showgrid=True, gridcolor='#F3F4F6', tickfont=dict(size=8)),
                height=140
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.markdown('<div style="padding:20px;text-align:center;color:#6B7280;font-size:11px;">No activity data</div>', unsafe_allow_html=True)
    
    # --- RIGHT: Quick Actions + Top Users ---
    with right:
        st.markdown('<p class="section-title"><i class="fa-solid fa-bolt" style="color:#A22431;"></i> Quick Actions</p>', unsafe_allow_html=True)
        
        qa1, qa2 = st.columns(2)
        with qa1:
            if st.button("Start Bridge" if not is_running else "Stop Bridge", use_container_width=True, key="qa_bridge"):
                if is_running:
                    bridge_ctrl.stop()
                else:
                    bridge_ctrl.start()
                st.rerun()
        with qa2:
            if st.button("Sync Device", use_container_width=True, key="qa_sync"):
                st.query_params["page"] = "device_sync"
                st.rerun()
        
        qa3, qa4 = st.columns(2)
        with qa3:
            if st.button("Upload Events", use_container_width=True, key="qa_upload"):
                st.query_params["page"] = "upload_sync"
                st.rerun()
        with qa4:
            if st.button("View Logs", use_container_width=True, key="qa_logs"):
                st.query_params["page"] = "logs"
                st.rerun()
        
        # Top Users
        st.markdown('<p class="section-title"><i class="fa-solid fa-users" style="color:#A22431;"></i> Top Users (30d)</p>', unsafe_allow_html=True)
        
        top_users = event_ctrl.get_top_users(limit=5)
        if top_users:
            user_box = st.container(height=160)
            with user_box:
                for i, user in enumerate(top_users):
                    name = user.get('name', '-')[:18] if user.get('name') else '-'
                    count = user.get('access_count', 0)
                    bar_width = min(count / max(u.get('access_count', 1) for u in top_users) * 100, 100)
                    st.markdown(f"""
                    <div style="margin:4px 0;">
                        <div style="display:flex;justify-content:space-between;font-size:10px;margin-bottom:2px;">
                            <span style="color:#374151;font-weight:500;">{name}</span>
                            <span style="color:#6B7280;">{count}</span>
                        </div>
                        <div style="background:#F3F4F6;height:4px;width:100%;">
                            <div style="background:#A22431;height:4px;width:{bar_width}%;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown('<div style="padding:20px;text-align:center;color:#6B7280;font-size:11px;">No user data</div>', unsafe_allow_html=True)
        
        # System Health
        st.markdown('<p class="section-title"><i class="fa-solid fa-heart-pulse" style="color:#A22431;"></i> System Health</p>', unsafe_allow_html=True)
        
        health_items = [
            ("Bridge", "Running" if is_running else "Stopped", is_running),
            ("Device", "Connected" if device_ctrl.get_device_status().get('connected') else "Offline", device_ctrl.get_device_status().get('connected')),
            ("Webhook", "Configured" if upload_sync_ctrl.get_webhook_config()['configured'] else "Not Set", upload_sync_ctrl.get_webhook_config()['configured']),
        ]
        
        for label, value, is_ok in health_items:
            icon = '<i class="fa-solid fa-circle-check" style="color:#10B981;font-size:10px;"></i>' if is_ok else '<i class="fa-solid fa-circle-xmark" style="color:#DC2626;font-size:10px;"></i>'
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid #F3F4F6;font-size:10px;">
                <span style="color:#6B7280;">{label}</span>
                <span style="display:flex;align-items:center;gap:4px;">{icon} <span style="color:{'#10B981' if is_ok else '#DC2626'};font-weight:500;">{value}</span></span>
            </div>
            """, unsafe_allow_html=True)

# ============================================
# PAGE: EVENTS
# ============================================
elif current_page == "events":
    # Initialize session state
    if 'show_filters' not in st.session_state:
        st.session_state.show_filters = False
    if 'view_event_id' not in st.session_state:
        st.session_state.view_event_id = None
    
    # Compact CSS for this page
    st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
    .events-header { display:flex; align-items:center; justify-content:space-between; padding:6px 12px; background:#F9FAFB; border:1px solid #E5E7EB; margin-bottom:8px; }
    .stat-row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
    .stat-box { background:#fff; border:1px solid #E5E7EB; padding:3px 10px; min-width:50px; text-align:center; }
    .stat-val { font-size:12px; font-weight:600; color:#111827; }
    .stat-val.primary { color:#A22431; }
    .stat-lbl { font-size:8px; color:#6B7280; text-transform:uppercase; }
    .section-title { font-size:12px; font-weight:600; color:#374151; margin:8px 0 6px 0; display:flex; align-items:center; gap:6px; }
    .filter-row { background:#FAFAFA; border:1px solid #E5E7EB; padding:8px 12px; margin-bottom:8px; }
    .event-detail { background:#fff; border:1px solid #E5E7EB; padding:12px; margin:8px 0; }
    .detail-grid { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
    .detail-section { background:#FAFAFA; padding:8px; }
    .detail-title { font-size:10px; font-weight:600; color:#6B7280; margin-bottom:6px; text-transform:uppercase; }
    .detail-row { display:flex; justify-content:space-between; padding:2px 0; font-size:10px; border-bottom:1px solid #F3F4F6; }
    .detail-label { color:#6B7280; }
    .detail-value { color:#111827; font-weight:500; font-family:monospace; }
    .sync-badge { display:inline-flex; align-items:center; gap:3px; padding:1px 6px; border-radius:8px; font-size:8px; font-weight:600; }
    .sync-ok { background:#DCFCE7; color:#166534; }
    .sync-pending { background:#FEF3C7; color:#92400E; }
    .sync-fail { background:#FEE2E2; color:#991B1B; }
    </style>
    """, unsafe_allow_html=True)
    
    # Default filter values
    date_start = datetime.now().date() - timedelta(days=7)
    date_end = datetime.now().date()
    event_type = "All"
    limit = 100
    
    # Get total counts for header
    total_count_all = event_ctrl.get_event_count()
    today_count = event_ctrl.get_today_stats().get('total_events', 0)
    sync_stats = event_ctrl.get_sync_stats()
    
    # === HEADER: Stats ===
    header_html = f"""
    <div class="events-header">
        <div class="stat-row">
            <div class="stat-box"><div class="stat-val primary">{total_count_all:,}</div><div class="stat-lbl">Total</div></div>
            <div class="stat-box"><div class="stat-val">{today_count}</div><div class="stat-lbl">Today</div></div>
            <div class="stat-box"><div class="stat-val" style="color:#10B981;">{sync_stats.get('synced', 0):,}</div><div class="stat-lbl">Synced</div></div>
            <div class="stat-box"><div class="stat-val" style="color:#F59E0B;">{sync_stats.get('pending', 0):,}</div><div class="stat-lbl">Pending</div></div>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # === CONTROLS ROW ===
    c1, c2, c3, c4, c5, c6 = st.columns([1.5, 1.5, 1, 1, 0.8, 0.8])
    
    with c1:
        date_start = st.date_input("From", value=date_start, label_visibility="collapsed", key="ev_date_start")
    with c2:
        date_end = st.date_input("To", value=date_end, label_visibility="collapsed", key="ev_date_end")
    with c3:
        event_type = st.selectbox("Type", ["All", "AccessControllerEvent"], label_visibility="collapsed", key="ev_type")
    with c4:
        limit = st.selectbox("", [50, 100, 200, 500], index=1, format_func=lambda x: f"{x} rows", label_visibility="collapsed", key="ev_limit")
    with c5:
        if st.button("Refresh", use_container_width=True, key="ev_refresh"):
            st.rerun()
    with c6:
        # Export button placeholder
        export_clicked = st.button("Export", use_container_width=True, key="ev_export")
    
    # Query data
    start_date = datetime.combine(date_start, datetime.min.time())
    end_date = datetime.combine(date_end, datetime.max.time())
    events = event_ctrl.get_events_as_dicts(limit=limit, start_date=start_date, end_date=end_date, event_type=event_type)
    total_count = event_ctrl.get_event_count(start_date=start_date, end_date=end_date, event_type=event_type)
    
    # Export handler
    if export_clicked and events:
        df_export = pd.DataFrame(events)
        csv = df_export.to_csv(index=False)
        st.download_button("Download CSV", csv, f"events_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", key="download_csv")
    
    # Status line
    st.caption(f"Showing {len(events)} of {total_count:,} events")
    
    # Events display
    if events:
        df = pd.DataFrame(events)
        
        # Prepare display dataframe
        display_cols = ['id', 'occur_time', 'name', 'employee_no', 'door_no', 'verify_mode', 'sync_status']
        display_cols = [c for c in display_cols if c in df.columns]
        display_df = df[display_cols].copy()
        
        # Format sync status with icons for display
        if 'sync_status' in display_df.columns:
            display_df['sync_status'] = display_df['sync_status'].apply(
                lambda x: '✓' if x == 'synced' else '○' if x == 'pending' else '✗'
            )
        
        # Rename for cleaner headers
        col_names = {'id': 'ID', 'occur_time': 'Time', 'name': 'Name', 'employee_no': 'Employee', 'door_no': 'Door', 'verify_mode': 'Mode', 'sync_status': 'Sync'}
        display_df.rename(columns=col_names, inplace=True)
        
        # Show table
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=300,
            column_config={
                "ID": st.column_config.NumberColumn(width="small"),
                "Time": st.column_config.TextColumn(width="medium"),
                "Name": st.column_config.TextColumn(width="medium"),
                "Employee": st.column_config.TextColumn(width="small"),
                "Door": st.column_config.NumberColumn(width="small"),
                "Mode": st.column_config.TextColumn(width="small"),
                "Sync": st.column_config.TextColumn(width="small"),
            }
        )
        
        # Event detail viewer
        st.markdown('<p class="section-title"><i class="fa-solid fa-magnifying-glass" style="color:#A22431;"></i> Event Details</p>', unsafe_allow_html=True)
        
        v1, v2 = st.columns([3, 1])
        with v1:
            event_ids = list(df['id'])
            selected_id = st.selectbox(
                "Select event",
                options=event_ids,
                format_func=lambda x: f"Event #{x}",
                label_visibility="collapsed",
                key="event_selector"
            )
        with v2:
            view_clicked = st.button("View Details", use_container_width=True, key="btn_view_detail")
        
        if view_clicked:
            st.session_state.view_event_id = selected_id
        
        # Show event details
        if st.session_state.view_event_id:
            event_row = df[df['id'] == st.session_state.view_event_id]
            if not event_row.empty:
                event_data = event_row.iloc[0].to_dict()
                
                sync_status = event_data.get('sync_status', 'pending')
                if sync_status == 'synced':
                    sync_badge = '<span class="sync-badge sync-ok"><i class="fa-solid fa-check"></i> Synced</span>'
                elif sync_status == 'pending':
                    sync_badge = '<span class="sync-badge sync-pending"><i class="fa-solid fa-clock"></i> Pending</span>'
                else:
                    sync_badge = '<span class="sync-badge sync-fail"><i class="fa-solid fa-xmark"></i> Failed</span>'
                
                st.markdown(f"""
                <div class="event-detail">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                        <span style="font-size:12px;font-weight:600;color:#374151;">Event #{event_data.get('id', '-')}</span>
                        {sync_badge}
                    </div>
                    <div class="detail-grid">
                        <div class="detail-section">
                            <div class="detail-title"><i class="fa-solid fa-user" style="margin-right:4px;"></i> User Info</div>
                            <div class="detail-row"><span class="detail-label">Name</span><span class="detail-value">{event_data.get('name', '-')}</span></div>
                            <div class="detail-row"><span class="detail-label">Employee No</span><span class="detail-value">{event_data.get('employee_no', '-')}</span></div>
                            <div class="detail-row"><span class="detail-label">Card No</span><span class="detail-value">{event_data.get('card_no', '-')}</span></div>
                        </div>
                        <div class="detail-section">
                            <div class="detail-title"><i class="fa-solid fa-door-open" style="margin-right:4px;"></i> Access Info</div>
                            <div class="detail-row"><span class="detail-label">Time</span><span class="detail-value">{event_data.get('occur_time', '-')}</span></div>
                            <div class="detail-row"><span class="detail-label">Door</span><span class="detail-value">{event_data.get('door_no', '-')}</span></div>
                            <div class="detail-row"><span class="detail-label">Verify Mode</span><span class="detail-value">{event_data.get('verify_mode', '-')}</span></div>
                        </div>
                        <div class="detail-section">
                            <div class="detail-title"><i class="fa-solid fa-server" style="margin-right:4px;"></i> Device Info</div>
                            <div class="detail-row"><span class="detail-label">IP</span><span class="detail-value">{event_data.get('device_ip', '-')}</span></div>
                            <div class="detail-row"><span class="detail-label">Device ID</span><span class="detail-value">{event_data.get('device_id', '-')}</span></div>
                            <div class="detail-row"><span class="detail-label">Serial No</span><span class="detail-value">{event_data.get('serial_no', '-')}</span></div>
                        </div>
                        <div class="detail-section">
                            <div class="detail-title"><i class="fa-solid fa-cloud-arrow-up" style="margin-right:4px;"></i> Sync Info</div>
                            <div class="detail-row"><span class="detail-label">Status</span><span class="detail-value">{sync_status}</span></div>
                            <div class="detail-row"><span class="detail-label">Attempts</span><span class="detail-value">{event_data.get('sync_attempts', 0)}</span></div>
                            <div class="detail-row"><span class="detail-label">Synced At</span><span class="detail-value">{event_data.get('synced_at', '-')}</span></div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Show error if failed
                if event_data.get('sync_error'):
                    st.markdown(f"""
                    <div style="background:#FEF2F2;border-left:3px solid #EF4444;padding:8px 12px;margin:8px 0;font-size:10px;color:#991B1B;">
                        <strong>Sync Error:</strong> {event_data.get('sync_error')}
                    </div>
                    """, unsafe_allow_html=True)
                
                # Raw JSON expander
                with st.expander("Raw JSON Data"):
                    st.json(event_data)
                
                if st.button("Close", key="close_details"):
                    st.session_state.view_event_id = None
                    st.rerun()
    else:
        st.markdown('<div style="padding:40px;text-align:center;color:#6B7280;font-size:12px;background:#FAFAFA;border:1px solid #E5E7EB;">No events found for the selected filters</div>', unsafe_allow_html=True)

# ============================================
# PAGE: STATISTICS
# ============================================
elif current_page == "statistics":
    # Compact CSS for this page
    st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
    .stats-header { display:flex; align-items:center; justify-content:space-between; padding:6px 12px; background:#F9FAFB; border:1px solid #E5E7EB; margin-bottom:8px; }
    .stat-row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
    .stat-box { background:#fff; border:1px solid #E5E7EB; padding:4px 12px; min-width:70px; text-align:center; }
    .stat-box.highlight { border-left:3px solid #A22431; }
    .stat-val { font-size:14px; font-weight:600; color:#111827; }
    .stat-val.primary { color:#A22431; }
    .stat-lbl { font-size:8px; color:#6B7280; text-transform:uppercase; }
    .section-title { font-size:12px; font-weight:600; color:#374151; margin:12px 0 6px 0; display:flex; align-items:center; gap:6px; }
    .chart-card { background:#fff; border:1px solid #E5E7EB; padding:12px; margin-bottom:12px; }
    .user-row { display:flex; justify-content:space-between; align-items:center; padding:4px 8px; margin:2px 0; font-size:10px; background:#FAFAFA; }
    .user-bar { height:4px; background:#F3F4F6; margin-top:2px; }
    .user-bar-fill { height:4px; background:#A22431; }
    </style>
    """, unsafe_allow_html=True)
    
    # Period selector in header
    c1, c2, c3 = st.columns([2, 1, 1])
    with c2:
        period = st.selectbox("", ["Last 24 Hours", "Last 7 Days", "Last 30 Days", "All Time"], index=1, label_visibility="collapsed", key="stats_period")
    with c3:
        if st.button("Refresh", use_container_width=True, key="stats_refresh"):
            st.rerun()
    
    days_map = {"Last 24 Hours": 1, "Last 7 Days": 7, "Last 30 Days": 30, "All Time": 365}
    days = days_map[period]
    
    # Calculate stats for period
    start_date = datetime.now() - timedelta(days=days)
    events = event_ctrl.get_events_as_dicts(limit=10000, start_date=start_date)
    total_events = len(events)
    
    # Calculate unique users and doors
    unique_users = len(set(e.get('employee_no') for e in events if e.get('employee_no')))
    unique_doors = len(set(e.get('door_no') for e in events if e.get('door_no')))
    
    # Daily average
    daily_avg = total_events / max(days, 1)
    
    # === HEADER: Period Stats ===
    header_html = f"""
    <div class="stats-header">
        <div class="stat-row">
            <div class="stat-box highlight"><div class="stat-val primary">{total_events:,}</div><div class="stat-lbl">Total Events</div></div>
            <div class="stat-box"><div class="stat-val">{unique_users}</div><div class="stat-lbl">Users</div></div>
            <div class="stat-box"><div class="stat-val">{unique_doors}</div><div class="stat-lbl">Doors</div></div>
            <div class="stat-box"><div class="stat-val">{daily_avg:.1f}</div><div class="stat-lbl">Daily Avg</div></div>
        </div>
        <div style="font-size:10px;color:#6B7280;"><i class="fa-solid fa-calendar" style="margin-right:4px;"></i>{period}</div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # === MAIN CONTENT ===
    
    # Activity Over Time Chart
    st.markdown('<p class="section-title"><i class="fa-solid fa-chart-area" style="color:#A22431;"></i> Activity Over Time</p>', unsafe_allow_html=True)
    
    hourly_stats = event_ctrl.get_hourly_stats(days=days)
    if hourly_stats:
        df_hourly = pd.DataFrame(hourly_stats)
        df_hourly['datetime'] = pd.to_datetime(df_hourly['event_date'].astype(str) + ' ' + df_hourly['event_hour'].astype(str) + ':00:00')
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_hourly['datetime'], y=df_hourly['event_count'],
            mode='lines', line=dict(color='#A22431', width=2),
            fill='tozeroy', fillcolor='rgba(162, 36, 49, 0.1)'
        ))
        fig.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            font=dict(size=9, color="#6B7280"),
            margin=dict(l=0, r=0, t=5, b=0),
            height=160,
            xaxis=dict(title="", showgrid=False, tickfont=dict(size=8)),
            yaxis=dict(title="", showgrid=True, gridcolor='#F3F4F6', tickfont=dict(size=8))
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.markdown('<div style="padding:20px;text-align:center;color:#6B7280;font-size:11px;">No activity data for this period</div>', unsafe_allow_html=True)
    
    # Two columns: Top Users and Door Activity
    left, right = st.columns(2)
    
    with left:
        st.markdown('<p class="section-title"><i class="fa-solid fa-ranking-star" style="color:#A22431;"></i> Top Users</p>', unsafe_allow_html=True)
        
        top_users = event_ctrl.get_top_users(limit=10)
        if top_users:
            # Horizontal bar chart
            df_users = pd.DataFrame(top_users)
            fig = px.bar(df_users.head(8), x='access_count', y='name', orientation='h')
            fig.update_traces(marker_color='#A22431')
            fig.update_layout(
                plot_bgcolor='white', paper_bgcolor='white',
                font=dict(size=9, color="#6B7280"),
                margin=dict(l=0, r=0, t=5, b=0),
                height=200,
                xaxis=dict(title="", showgrid=True, gridcolor='#F3F4F6', tickfont=dict(size=8)),
                yaxis=dict(title="", tickfont=dict(size=8), autorange="reversed")
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.markdown('<div style="padding:20px;text-align:center;color:#6B7280;font-size:11px;">No user data</div>', unsafe_allow_html=True)
    
    with right:
        st.markdown('<p class="section-title"><i class="fa-solid fa-door-open" style="color:#A22431;"></i> Door Activity</p>', unsafe_allow_html=True)
        
        if events:
            df = pd.DataFrame(events)
            if 'door_no' in df.columns:
                door_counts = df.groupby('door_no').size().reset_index(name='count')
                door_counts = door_counts.sort_values('count', ascending=False)
                
                fig = px.pie(door_counts, values='count', names='door_no', hole=0.4)
                fig.update_traces(
                    marker=dict(colors=['#A22431', '#C92A38', '#E63946', '#F25C66', '#F8969F']),
                    textinfo='percent+label',
                    textfont_size=9
                )
                fig.update_layout(
                    plot_bgcolor='white', paper_bgcolor='white',
                    font=dict(size=9, color="#6B7280"),
                    margin=dict(l=0, r=0, t=5, b=0),
                    height=200,
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            else:
                st.markdown('<div style="padding:20px;text-align:center;color:#6B7280;font-size:11px;">No door data</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="padding:20px;text-align:center;color:#6B7280;font-size:11px;">No data</div>', unsafe_allow_html=True)
    
    # Hourly Distribution
    st.markdown('<p class="section-title"><i class="fa-solid fa-clock" style="color:#A22431;"></i> Hourly Distribution</p>', unsafe_allow_html=True)
    
    if events:
        df = pd.DataFrame(events)
        if 'occur_time' in df.columns:
            df['hour'] = pd.to_datetime(df['occur_time']).dt.hour
            hourly_dist = df.groupby('hour').size().reset_index(name='count')
            
            # Ensure all hours are present
            all_hours = pd.DataFrame({'hour': range(24)})
            hourly_dist = all_hours.merge(hourly_dist, on='hour', how='left').fillna(0)
            
            fig = px.bar(hourly_dist, x='hour', y='count')
            fig.update_traces(marker_color='#A22431')
            fig.update_layout(
                plot_bgcolor='white', paper_bgcolor='white',
                font=dict(size=9, color="#6B7280"),
                margin=dict(l=0, r=0, t=5, b=0),
                height=120,
                xaxis=dict(title="", tickmode='linear', dtick=2, tickfont=dict(size=8)),
                yaxis=dict(title="", showgrid=True, gridcolor='#F3F4F6', tickfont=dict(size=8)),
                bargap=0.1
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.markdown('<div style="padding:20px;text-align:center;color:#6B7280;font-size:11px;">No data</div>', unsafe_allow_html=True)

# ============================================
# PAGE: BRIDGE CONTROL
# ============================================
elif current_page == "bridge":
    # Initialize states
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = False
    if 'log_filter' not in st.session_state:
        st.session_state.log_filter = ""
    
    # Get current status
    status = bridge_ctrl.get_status()
    is_running = status.get("running", False)
    today_stats = event_ctrl.get_today_stats()
    sync_stats = event_ctrl.get_sync_stats()
    
    # Compact CSS - override Streamlit defaults
    st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
    /* Reduce Streamlit's default gaps on bridge page */
    [data-testid="stVerticalBlock"] > div:has(.bridge-header) { gap: 0.3rem !important; }
    [data-testid="stHorizontalBlock"] { gap: 0.5rem !important; }
    .stButton > button { padding: 0.25rem 0.5rem !important; font-size: 12px !important; min-height: 32px !important; color: #FFFFFF !important; }
    .stButton > button p, .stButton > button span, .stButton > button div { color: #FFFFFF !important; }
    .bridge-header { display:flex; align-items:center; justify-content:space-between; padding:3px 8px; background:#F9FAFB; border:1px solid #E5E7EB; margin:0; }
    .status-badge { display:inline-flex; align-items:center; gap:3px; padding:1px 6px; border-radius:8px; font-size:9px; font-weight:600; }
    .status-on { background:#DCFCE7; color:#166534; }
    .status-off { background:#FEE2E2; color:#991B1B; }
    .metric-row { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
    .metric-box { background:#fff; border:1px solid #E5E7EB; padding:1px 6px; min-width:40px; text-align:center; line-height:1.2; }
    .metric-val { font-size:11px; font-weight:600; color:#111827; }
    .metric-lbl { font-size:7px; color:#6B7280; text-transform:uppercase; }
    .event-item { font-size:10px; padding:4px 8px; margin:2px 0; border-left:3px solid; background:#FAFAFA; display:flex; align-items:center; gap:6px; }
    .event-new { border-color:#10B981; background:#F0FDF4; }
    .event-sync { border-color:#3B82F6; background:#EFF6FF; }
    .event-db { border-color:#8B5CF6; background:#F5F3FF; }
    .log-entry { font-family:'Monaco','Menlo',monospace; font-size:9px; padding:2px 4px; margin:1px 0; line-height:1.4; }
    .log-err { color:#DC2626; background:#FEF2F2; }
    .log-ok { color:#059669; }
    .log-warn { color:#D97706; }
    .section-head { font-size:12px; font-weight:600; color:#374151; margin:0 0 6px 0; display:flex; align-items:center; gap:6px; }
    </style>
    """, unsafe_allow_html=True)
    
    # === HEADER ROW: Status + Controls + Metrics ===
    if is_running:
        header_html = f"""
        <div class="bridge-header">
            <div style="display:flex;align-items:center;gap:16px;">
                <span class="status-badge status-on"><i class="fa-solid fa-circle" style="font-size:6px;"></i> RUNNING</span>
                <div class="metric-row">
                    <div class="metric-box"><div class="metric-val">{status.get('pid','-')}</div><div class="metric-lbl">PID</div></div>
                    <div class="metric-box"><div class="metric-val">{status.get('cpu_percent',0)}%</div><div class="metric-lbl">CPU</div></div>
                    <div class="metric-box"><div class="metric-val">{status.get('memory_mb',0)}</div><div class="metric-lbl">MB</div></div>
                    <div class="metric-box"><div class="metric-val">{status.get('uptime_formatted','-')}</div><div class="metric-lbl">Uptime</div></div>
                </div>
            </div>
            <div class="metric-row">
                <div class="metric-box"><div class="metric-val">{today_stats.get('total_events',0)}</div><div class="metric-lbl">Today</div></div>
                <div class="metric-box"><div class="metric-val">{sync_stats.get('synced',0)}</div><div class="metric-lbl">Synced</div></div>
                <div class="metric-box"><div class="metric-val" style="color:#DC2626;">{sync_stats.get('failed',0)}</div><div class="metric-lbl">Failed</div></div>
            </div>
        </div>
        """
    else:
        header_html = f"""
        <div class="bridge-header">
            <span class="status-badge status-off"><i class="fa-solid fa-circle" style="font-size:6px;"></i> STOPPED</span>
            <div class="metric-row">
                <div class="metric-box"><div class="metric-val">{today_stats.get('total_events',0)}</div><div class="metric-lbl">Today</div></div>
                <div class="metric-box"><div class="metric-val">{sync_stats.get('synced',0)}</div><div class="metric-lbl">Synced</div></div>
            </div>
        </div>
        """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # === CONTROLS ROW ===
    c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1.5])
    with c1:
        if st.button("Start", disabled=is_running, use_container_width=True, key="btn_start"):
            result = bridge_ctrl.start()
            st.toast(f"{'Success' if result['success'] else 'Error'}: {result['message']}")
            time.sleep(0.5)
            st.rerun()
    with c2:
        if st.button("Stop", disabled=not is_running, use_container_width=True, key="btn_stop"):
            result = bridge_ctrl.stop()
            st.toast(f"{'Success' if result['success'] else 'Error'}: {result['message']}")
            time.sleep(0.5)
            st.rerun()
    with c3:
        if st.button("Restart", disabled=not is_running, use_container_width=True, key="btn_restart"):
            result = bridge_ctrl.restart()
            st.toast(f"{'Success' if result['success'] else 'Error'}: {result['message']}")
            time.sleep(0.5)
            st.rerun()
    with c4:
        if st.button("Refresh", use_container_width=True, key="btn_refresh"):
            st.rerun()
    with c5:
        auto = st.checkbox("Auto-refresh (3s)", value=st.session_state.auto_refresh, key="auto_chk")
        if auto != st.session_state.auto_refresh:
            st.session_state.auto_refresh = auto
    
    # === MAIN CONTENT: Two columns ===
    left, right = st.columns([1, 1.2])
    
    # --- LEFT: Live Events ---
    with left:
        st.markdown('<p class="section-head"><i class="fa-solid fa-tower-broadcast" style="color:#A22431;"></i> Live Events</p>', unsafe_allow_html=True)
        
        recent_events = bridge_ctrl.get_recent_events_from_log(lines=20)
        event_box = st.container(height=320)
        
        with event_box:
            if recent_events:
                for evt in reversed(recent_events):
                    text = evt["text"]
                    if "New event:" in text:
                        parts = text.split("New event:")
                        if len(parts) > 1:
                            info = parts[1].strip()
                            # Parse info to show key details
                            st.markdown(f'<div class="event-item event-new"><i class="fa-solid fa-arrow-down" style="color:#10B981;"></i> {info[:80]}</div>', unsafe_allow_html=True)
                    elif "synced successfully" in text:
                        # Extract event ID
                        if "Event #" in text:
                            eid = text.split("Event #")[1].split()[0]
                            st.markdown(f'<div class="event-item event-sync"><i class="fa-solid fa-check" style="color:#3B82F6;"></i> Event #{eid} synced</div>', unsafe_allow_html=True)
                    elif "saved to database" in text:
                        if "ID" in text:
                            eid = text.split("ID")[-1].strip().split()[0]
                            st.markdown(f'<div class="event-item event-db"><i class="fa-solid fa-database" style="color:#8B5CF6;"></i> Saved ID {eid}</div>', unsafe_allow_html=True)
            else:
                st.caption("No recent events. Scan a face to see activity.")
    
    # --- RIGHT: Logs ---
    with right:
        # Log header with controls
        lh1, lh2, lh3 = st.columns([2.5, 1, 0.8])
        with lh1:
            st.markdown('<p class="section-head"><i class="fa-solid fa-file-lines" style="color:#A22431;"></i> Logs</p>', unsafe_allow_html=True)
        with lh2:
            log_lines = st.selectbox("", [30, 50, 100, 200], index=1, label_visibility="collapsed", key="log_lines_sel")
        with lh3:
            if st.button("Clear", use_container_width=True, key="btn_clear"):
                bridge_ctrl.clear_logs()
                st.rerun()
        
        # Filter
        log_filter = st.text_input("", placeholder="Filter logs...", label_visibility="collapsed", key="log_filter")
        
        # Log content
        log_entries = bridge_ctrl.get_log_lines(lines=log_lines, filter_text=log_filter if log_filter else None)
        log_box = st.container(height=260)
        
        with log_box:
            if log_entries:
                for entry in reversed(log_entries[-log_lines:]):
                    text = entry["text"]
                    lt = entry["type"]
                    css = "log-err" if lt == "error" else "log-ok" if lt == "success" else "log-warn" if lt == "warning" else ""
                    st.markdown(f'<div class="log-entry {css}">{text}</div>', unsafe_allow_html=True)
            else:
                st.caption("No logs")
        
        # Footer
        st.caption(f"Log size: {bridge_ctrl.get_log_file_size()}")
    
    # Auto-refresh
    if st.session_state.auto_refresh and is_running:
        time.sleep(3)
        st.rerun()
    
    # Auto-refresh
    if st.session_state.auto_refresh and is_running:
        time.sleep(3)
        st.rerun()

# ============================================
# PAGE: LOGS
# ============================================
elif current_page == "logs":
    # Compact CSS for this page
    st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
    .logs-header { display:flex; align-items:center; justify-content:space-between; padding:6px 12px; background:#F9FAFB; border:1px solid #E5E7EB; margin-bottom:8px; }
    .stat-row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
    .stat-box { background:#fff; border:1px solid #E5E7EB; padding:3px 10px; min-width:50px; text-align:center; }
    .stat-val { font-size:11px; font-weight:600; color:#111827; }
    .stat-lbl { font-size:8px; color:#6B7280; text-transform:uppercase; }
    .log-container { background:#1F2937; border:1px solid #374151; padding:8px; font-family:'Monaco','Menlo',monospace; font-size:10px; line-height:1.5; overflow-x:auto; }
    .log-line { padding:1px 0; }
    .log-error { color:#F87171; }
    .log-warning { color:#FBBF24; }
    .log-success { color:#34D399; }
    .log-info { color:#9CA3AF; }
    .section-title { font-size:12px; font-weight:600; color:#374151; margin:8px 0 6px 0; display:flex; align-items:center; gap:6px; }
    </style>
    """, unsafe_allow_html=True)
    
    # Get log info
    log_size = bridge_ctrl.get_log_file_size()
    bridge_status = bridge_ctrl.get_status()
    is_running = bridge_status.get("running", False)
    
    # === HEADER: Log Info ===
    status_badge = '<span style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:8px;font-size:9px;font-weight:600;background:#DCFCE7;color:#166534;"><i class="fa-solid fa-circle" style="font-size:5px;"></i> BRIDGE RUNNING</span>' if is_running else '<span style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:8px;font-size:9px;font-weight:600;background:#FEE2E2;color:#991B1B;"><i class="fa-solid fa-circle" style="font-size:5px;"></i> BRIDGE STOPPED</span>'
    
    header_html = f"""
    <div class="logs-header">
        <div class="stat-row">
            {status_badge}
            <div class="stat-box"><div class="stat-val">{log_size}</div><div class="stat-lbl">File Size</div></div>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # === CONTROLS ROW ===
    c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1, 1])
    
    with c1:
        log_filter = st.text_input("", placeholder="Filter logs...", label_visibility="collapsed", key="logs_filter")
    with c2:
        lines = st.selectbox("", [50, 100, 200, 500, 1000], index=2, format_func=lambda x: f"{x} lines", label_visibility="collapsed", key="logs_lines")
    with c3:
        if st.button("Refresh", use_container_width=True, key="logs_refresh"):
            st.rerun()
    with c4:
        if st.button("Clear Logs", use_container_width=True, key="logs_clear"):
            bridge_ctrl.clear_logs()
            st.toast("Logs cleared")
            st.rerun()
    with c5:
        logs_raw = bridge_ctrl.get_logs(lines=lines)
        if logs_raw:
            st.download_button(
                "Download",
                logs_raw,
                file_name=f"bridge_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
                mime="text/plain",
                use_container_width=True,
                key="logs_download"
            )
    
    # === LOG CONTENT ===
    st.markdown('<p class="section-title"><i class="fa-solid fa-file-lines" style="color:#A22431;"></i> Bridge Logs</p>', unsafe_allow_html=True)
    
    log_entries = bridge_ctrl.get_log_lines(lines=lines, filter_text=log_filter if log_filter else None)
    
    if log_entries:
        log_box = st.container(height=450)
        with log_box:
            # Build log HTML
            log_html = '<div class="log-container">'
            for entry in log_entries:
                text = entry["text"]
                lt = entry["type"]
                
                # Apply filter if set
                if log_filter and log_filter.lower() not in text.lower():
                    continue
                
                css_class = "log-error" if lt == "error" else "log-success" if lt == "success" else "log-warning" if lt == "warning" else "log-info"
                # Escape HTML and preserve formatting
                import html
                text_escaped = html.escape(text)
                log_html += f'<div class="log-line {css_class}">{text_escaped}</div>'
            log_html += '</div>'
            
            st.markdown(log_html, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="padding:40px;text-align:center;color:#6B7280;font-size:12px;background:#FAFAFA;border:1px solid #E5E7EB;">
            <i class="fa-solid fa-file-circle-xmark" style="font-size:24px;color:#D1D5DB;margin-bottom:8px;display:block;"></i>
            No logs available
        </div>
        """, unsafe_allow_html=True)
    
    # === LOG LEGEND ===
    st.markdown("""
    <div style="display:flex;gap:16px;margin-top:8px;font-size:9px;">
        <span><span style="color:#34D399;">●</span> Success</span>
        <span><span style="color:#FBBF24;">●</span> Warning</span>
        <span><span style="color:#F87171;">●</span> Error</span>
        <span><span style="color:#9CA3AF;">●</span> Info</span>
    </div>
    """, unsafe_allow_html=True)

# ============================================
# PAGE: CONTROLS (now Settings)
# ============================================
elif current_page == "controls":
    # Compact CSS for this page
    st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
    .settings-header { display:flex; align-items:center; justify-content:space-between; padding:6px 12px; background:#F9FAFB; border:1px solid #E5E7EB; margin-bottom:8px; }
    .stat-row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; }
    .stat-box { background:#fff; border:1px solid #E5E7EB; padding:4px 12px; min-width:60px; text-align:center; }
    .stat-val { font-size:12px; font-weight:600; color:#111827; }
    .stat-val.success { color:#10B981; }
    .stat-val.warning { color:#F59E0B; }
    .stat-val.danger { color:#DC2626; }
    .stat-lbl { font-size:8px; color:#6B7280; text-transform:uppercase; }
    .section-title { font-size:12px; font-weight:600; color:#374151; margin:12px 0 8px 0; display:flex; align-items:center; gap:6px; }
    .settings-card { background:#fff; border:1px solid #E5E7EB; padding:16px; margin-bottom:12px; }
    .input-label { font-size:10px; font-weight:500; color:#6B7280; margin-bottom:4px; text-transform:uppercase; }
    .result-box { padding:8px 12px; margin:8px 0; font-size:11px; }
    .result-success { background:#F0FDF4; border-left:3px solid #10B981; color:#166534; }
    .result-error { background:#FEF2F2; border-left:3px solid #EF4444; color:#991B1B; }
    .result-info { background:#EFF6FF; border-left:3px solid #3B82F6; color:#1E40AF; }
    </style>
    """, unsafe_allow_html=True)
    
    # Get current status
    status = bridge_ctrl.get_status()
    is_running = status.get("running", False)
    sync_stats = event_ctrl.get_sync_stats()
    config = config_ctrl.get_all_config()
    
    # === HEADER: Webhook Status ===
    webhook_url = config.get('webhook_url', '')
    webhook_configured = bool(webhook_url.strip())
    
    if webhook_configured:
        webhook_badge = '<span style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:8px;font-size:9px;font-weight:600;background:#DCFCE7;color:#166534;"><i class="fa-solid fa-link" style="font-size:8px;"></i> CONFIGURED</span>'
    else:
        webhook_badge = '<span style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:8px;font-size:9px;font-weight:600;background:#FEE2E2;color:#991B1B;"><i class="fa-solid fa-link-slash" style="font-size:8px;"></i> NOT SET</span>'
    
    header_html = f"""
    <div class="settings-header">
        <div class="stat-row">
            {webhook_badge}
            <div class="stat-box"><div class="stat-val">{event_ctrl.get_event_count():,}</div><div class="stat-lbl">Total</div></div>
            <div class="stat-box"><div class="stat-val success">{sync_stats.get('synced', 0):,}</div><div class="stat-lbl">Synced</div></div>
            <div class="stat-box"><div class="stat-val warning">{sync_stats.get('pending', 0):,}</div><div class="stat-lbl">Pending</div></div>
            <div class="stat-box"><div class="stat-val danger">{sync_stats.get('failed', 0):,}</div><div class="stat-lbl">Failed</div></div>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # Auto-sync notice
    st.markdown("""
    <div class="result-box result-info">
        <i class="fa-solid fa-info-circle" style="margin-right:6px;"></i>
        <strong>Auto-Sync:</strong> Events are automatically synced to your webhook when captured by the bridge.
    </div>
    """, unsafe_allow_html=True)
    
    # === MAIN CONTENT: Two columns ===
    left, right = st.columns([1.5, 1])
    
    # --- LEFT: Webhook Configuration ---
    with left:
        st.markdown('<p class="section-title"><i class="fa-solid fa-link" style="color:#A22431;"></i> Webhook Configuration</p>', unsafe_allow_html=True)
        
        st.markdown('<div class="input-label">Webhook URL</div>', unsafe_allow_html=True)
        webhook_url_input = st.text_input(
            "Webhook URL",
            value=config.get('webhook_url', ''),
            placeholder="https://your-backend.com/api/webhook",
            label_visibility="collapsed",
            key="webhook_url_input"
        )
        
        st.markdown('<div class="input-label">API Key (Optional)</div>', unsafe_allow_html=True)
        api_key_input = st.text_input(
            "API Key",
            value=config.get('webhook_api_key', ''),
            type="password",
            placeholder="Your API key for authentication",
            label_visibility="collapsed",
            key="api_key_input"
        )
        
        # Action buttons
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("Save Settings", use_container_width=True, key="btn_save_webhook"):
                config_ctrl.set_config('webhook_url', webhook_url_input)
                config_ctrl.set_config('webhook_api_key', api_key_input)
                st.toast("Settings saved! Restart bridge to apply.")
                st.rerun()
        
        with b2:
            if st.button("Test Webhook", use_container_width=True, disabled=not webhook_url_input, key="btn_test_webhook"):
                try:
                    import requests
                    test_payload = {
                        "event_id": 0,
                        "event_type": "test",
                        "message": "Test event from Hikvision Bridge",
                        "timestamp": datetime.now().isoformat()
                    }
                    headers = {"Content-Type": "application/json"}
                    if api_key_input:
                        headers["X-API-Key"] = api_key_input
                    
                    response = requests.post(webhook_url_input, json=test_payload, headers=headers, timeout=10)
                    if response.status_code == 200:
                        st.toast(f"Test successful! Response: {response.text[:50]}")
                    else:
                        st.toast(f"HTTP {response.status_code}: {response.text[:100]}")
                except Exception as e:
                    st.toast(f"Error: {str(e)}")
        
        with b3:
            pending = sync_stats.get('pending', 0) or 0
            failed = sync_stats.get('failed', 0) or 0
            total_retry = pending + failed
            if st.button(f"Retry ({total_retry})", use_container_width=True, disabled=total_retry == 0 or not webhook_url_input, key="btn_retry"):
                with st.spinner("Syncing..."):
                    result = event_ctrl.sync_pending_events(
                        webhook_url=webhook_url_input,
                        api_key=api_key_input if api_key_input else None,
                        limit=100
                    )
                
                if result['synced'] > 0:
                    st.toast(f"Synced {result['synced']} events")
                if result['failed'] > 0:
                    st.toast(f"Failed: {result['failed']} events")
                if result['synced'] == 0 and result['failed'] == 0:
                    st.toast("No events to sync")
                st.rerun()
    
    # --- RIGHT: Quick Status ---
    with right:
        st.markdown('<p class="section-title"><i class="fa-solid fa-circle-info" style="color:#A22431;"></i> Status</p>', unsafe_allow_html=True)
        
        # Bridge status
        if is_running:
            st.markdown(f"""
            <div class="result-box result-success">
                <i class="fa-solid fa-play" style="margin-right:6px;"></i>
                Bridge is running (PID: {status.get('pid', '-')})
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="result-box result-error">
                <i class="fa-solid fa-stop" style="margin-right:6px;"></i>
                Bridge is stopped. Start it from Bridge Control.
            </div>
            """, unsafe_allow_html=True)
        
        # Webhook status
        if webhook_configured:
            # Show truncated URL
            display_url = webhook_url[:40] + "..." if len(webhook_url) > 40 else webhook_url
            st.markdown(f"""
            <div style="background:#FAFAFA;border:1px solid #E5E7EB;padding:12px;margin:8px 0;">
                <div style="font-size:9px;color:#6B7280;text-transform:uppercase;margin-bottom:6px;">Endpoint</div>
                <div style="font-size:11px;color:#111827;font-family:monospace;word-break:break-all;">{display_url}</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Sync summary
        st.markdown('<p class="section-title" style="margin-top:16px;"><i class="fa-solid fa-chart-pie" style="color:#A22431;"></i> Sync Summary</p>', unsafe_allow_html=True)
        
        total = event_ctrl.get_event_count()
        synced = sync_stats.get('synced', 0) or 0
        pending = sync_stats.get('pending', 0) or 0
        failed = sync_stats.get('failed', 0) or 0
        
        if total > 0:
            sync_rate = (synced / total) * 100
        else:
            sync_rate = 0
        
        summary_items = [
            ("Sync Rate", f"{sync_rate:.1f}%", "#A22431"),
            ("Synced", f"{synced:,}", "#10B981"),
            ("Pending", f"{pending:,}", "#F59E0B"),
            ("Failed", f"{failed:,}", "#DC2626"),
        ]
        
        for label, value, color in summary_items:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #F3F4F6;font-size:11px;">
                <span style="color:#6B7280;">{label}</span>
                <span style="color:{color};font-weight:600;">{value}</span>
            </div>
            """, unsafe_allow_html=True)

# ============================================
# PAGE: CONFIGURATION
# ============================================
elif current_page == "configuration":
    # Compact CSS for this page
    st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
    .config-header { display:flex; align-items:center; justify-content:space-between; padding:6px 12px; background:#F9FAFB; border:1px solid #E5E7EB; margin-bottom:8px; }
    .section-title { font-size:12px; font-weight:600; color:#374151; margin:12px 0 8px 0; display:flex; align-items:center; gap:6px; }
    .config-card { background:#fff; border:1px solid #E5E7EB; padding:16px; margin-bottom:12px; }
    .input-label { font-size:10px; font-weight:500; color:#6B7280; margin-bottom:4px; text-transform:uppercase; }
    .result-box { padding:8px 12px; margin:8px 0; font-size:11px; }
    .result-success { background:#F0FDF4; border-left:3px solid #10B981; color:#166534; }
    .result-error { background:#FEF2F2; border-left:3px solid #EF4444; color:#991B1B; }
    .result-info { background:#EFF6FF; border-left:3px solid #3B82F6; color:#1E40AF; }
    .config-row { display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid #F3F4F6; font-size:11px; }
    .config-label { color:#6B7280; }
    .config-value { color:#111827; font-weight:500; font-family:monospace; }
    </style>
    """, unsafe_allow_html=True)
    
    config = config_ctrl.get_all_config()
    device_status = device_ctrl.get_device_status()
    is_connected = device_status.get('connected', False)
    
    # === HEADER ===
    conn_badge = '<span style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:8px;font-size:9px;font-weight:600;background:#DCFCE7;color:#166534;"><i class="fa-solid fa-plug" style="font-size:8px;"></i> DEVICE CONNECTED</span>' if is_connected else '<span style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:8px;font-size:9px;font-weight:600;background:#FEE2E2;color:#991B1B;"><i class="fa-solid fa-plug-circle-xmark" style="font-size:8px;"></i> DEVICE OFFLINE</span>'
    
    header_html = f"""
    <div class="config-header">
        {conn_badge}
        <span style="font-size:10px;color:#6B7280;"><i class="fa-solid fa-server" style="margin-right:4px;"></i>{config.get('device_ip', '192.168.1.128')}</span>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # === MAIN CONTENT: Two columns ===
    left, right = st.columns(2)
    
    # --- LEFT: Device Settings ---
    with left:
        st.markdown('<p class="section-title"><i class="fa-solid fa-camera" style="color:#A22431;"></i> Device Settings</p>', unsafe_allow_html=True)
        
        st.markdown('<div class="input-label">Device IP Address</div>', unsafe_allow_html=True)
        device_ip = st.text_input(
            "Device IP",
            value=config.get('device_ip', '192.168.1.128'),
            label_visibility="collapsed",
            key="config_device_ip"
        )
        
        st.markdown('<div class="input-label">Username</div>', unsafe_allow_html=True)
        device_user = st.text_input(
            "Username",
            value=config.get('device_user', 'admin'),
            label_visibility="collapsed",
            key="config_device_user"
        )
        
        st.markdown('<div class="input-label">Device ID</div>', unsafe_allow_html=True)
        device_id = st.text_input(
            "Device ID",
            value=config.get('device_id', 'door1'),
            label_visibility="collapsed",
            key="config_device_id"
        )
        
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Save Device", use_container_width=True, key="btn_save_device"):
                config_ctrl.set_config('device_ip', device_ip)
                config_ctrl.set_config('device_user', device_user)
                config_ctrl.set_config('device_id', device_id)
                st.toast("Device settings saved! Restart bridge to apply.")
                st.rerun()
        
        with b2:
            if st.button("Test Device", use_container_width=True, key="btn_test_device"):
                with st.spinner("Testing..."):
                    result = device_ctrl.test_connection()
                    if result['success']:
                        st.toast("Device connection OK!")
                    else:
                        st.toast(f"Failed: {result['message']}")
    
    # --- RIGHT: System Settings ---
    with right:
        st.markdown('<p class="section-title"><i class="fa-solid fa-gear" style="color:#A22431;"></i> System Settings</p>', unsafe_allow_html=True)
        
        st.markdown('<div class="input-label">Log Level</div>', unsafe_allow_html=True)
        log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        current_level = config.get('log_level', 'INFO')
        log_level = st.selectbox(
            "Log Level",
            options=log_levels,
            index=log_levels.index(current_level) if current_level in log_levels else 1,
            label_visibility="collapsed",
            key="config_log_level"
        )
        
        st.markdown('<div class="input-label">Data Retention (Days)</div>', unsafe_allow_html=True)
        retention = st.number_input(
            "Retention",
            value=int(config.get('data_retention_days', 90)),
            min_value=1,
            max_value=365,
            label_visibility="collapsed",
            key="config_retention"
        )
        
        st.markdown('<div class="input-label">Options</div>', unsafe_allow_html=True)
        backup = st.checkbox(
            "Enable Auto Backup",
            value=config.get('auto_backup_enabled', 'true') == 'true',
            key="config_backup"
        )
        
        if st.button("Save System", use_container_width=True, key="btn_save_system"):
            config_ctrl.set_config('log_level', log_level)
            config_ctrl.set_config('data_retention_days', str(retention))
            config_ctrl.set_config('auto_backup_enabled', 'true' if backup else 'false')
            st.toast("System settings saved!")
            st.rerun()
    
    # === DEVICE INFO (if connected) ===
    if is_connected:
        st.markdown('<p class="section-title"><i class="fa-solid fa-circle-info" style="color:#A22431;"></i> Device Information</p>', unsafe_allow_html=True)
        
        info_items = [
            ("Device Name", device_status.get('device_name', '-')),
            ("Model", device_status.get('model', '-')),
            ("Serial Number", device_status.get('serial_number', '-')),
            ("Firmware", device_status.get('firmware_version', '-')),
            ("IP Address", device_status.get('ip_address', '-')),
        ]
        
        c1, c2 = st.columns(2)
        with c1:
            for label, value in info_items[:3]:
                st.markdown(f"""
                <div class="config-row">
                    <span class="config-label">{label}</span>
                    <span class="config-value">{value}</span>
                </div>
                """, unsafe_allow_html=True)
        with c2:
            for label, value in info_items[3:]:
                st.markdown(f"""
                <div class="config-row">
                    <span class="config-label">{label}</span>
                    <span class="config-value">{value}</span>
                </div>
                """, unsafe_allow_html=True)
    
    # === CURRENT CONFIGURATION ===
    st.markdown('<p class="section-title"><i class="fa-solid fa-list" style="color:#A22431;"></i> Current Configuration</p>', unsafe_allow_html=True)
    
    with st.expander("View All Settings"):
        config_display = {k: v for k, v in config.items() if not any(x in k.lower() for x in ['password', 'secret', 'key'])}
        st.json(config_display)

# ============================================
# PAGE: DEVICE SYNC
# ============================================
elif current_page == "device_sync":
    # Initialize session states
    if 'sync_running' not in st.session_state:
        st.session_state.sync_running = False
    if 'sync_result' not in st.session_state:
        st.session_state.sync_result = None
    
    # Compact CSS for this page
    st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
    .device-header { display:flex; align-items:center; justify-content:space-between; padding:6px 12px; background:#F9FAFB; border:1px solid #E5E7EB; margin-bottom:8px; }
    .conn-badge { display:inline-flex; align-items:center; gap:4px; padding:2px 8px; border-radius:8px; font-size:10px; font-weight:600; }
    .conn-ok { background:#DCFCE7; color:#166534; }
    .conn-fail { background:#FEE2E2; color:#991B1B; }
    .device-info { display:flex; gap:12px; flex-wrap:wrap; align-items:center; }
    .info-box { background:#fff; border:1px solid #E5E7EB; padding:3px 10px; min-width:60px; text-align:center; }
    .info-val { font-size:11px; font-weight:600; color:#111827; }
    .info-lbl { font-size:8px; color:#6B7280; text-transform:uppercase; }
    .sync-card { background:#fff; border:1px solid #E5E7EB; padding:12px; margin:8px 0; }
    .sync-title { font-size:12px; font-weight:600; color:#374151; margin-bottom:8px; display:flex; align-items:center; gap:6px; }
    .result-box { padding:8px 12px; margin:6px 0; font-size:11px; }
    .result-success { background:#F0FDF4; border-left:3px solid #10B981; color:#166534; }
    .result-error { background:#FEF2F2; border-left:3px solid #EF4444; color:#991B1B; }
    .result-info { background:#EFF6FF; border-left:3px solid #3B82F6; color:#1E40AF; }
    .history-row { display:flex; justify-content:space-between; padding:4px 8px; background:#FAFAFA; margin:2px 0; font-size:10px; border-left:2px solid #E5E7EB; }
    </style>
    """, unsafe_allow_html=True)
    
    # Get device status
    device_status = device_ctrl.get_device_status()
    is_connected = device_status.get('connected', False)
    
    # Get database stats
    db_event_count = event_ctrl.get_event_count()
    sync_stats = event_ctrl.get_sync_stats()
    
    # === HEADER: Device Status ===
    if is_connected:
        header_html = f"""
        <div class="device-header">
            <div style="display:flex;align-items:center;gap:12px;">
                <span class="conn-badge conn-ok"><i class="fa-solid fa-circle" style="font-size:6px;"></i> CONNECTED</span>
                <div class="device-info">
                    <div class="info-box"><div class="info-val">{device_status.get('device_name', '-')}</div><div class="info-lbl">Device</div></div>
                    <div class="info-box"><div class="info-val">{device_status.get('model', '-')}</div><div class="info-lbl">Model</div></div>
                    <div class="info-box"><div class="info-val">{device_status.get('ip_address', '-')}</div><div class="info-lbl">IP</div></div>
                </div>
            </div>
            <div class="device-info">
                <div class="info-box"><div class="info-val">{db_event_count}</div><div class="info-lbl">In DB</div></div>
                <div class="info-box"><div class="info-val">{sync_stats.get('synced', 0)}</div><div class="info-lbl">Synced</div></div>
            </div>
        </div>
        """
    else:
        header_html = f"""
        <div class="device-header">
            <span class="conn-badge conn-fail"><i class="fa-solid fa-circle" style="font-size:6px;"></i> DISCONNECTED</span>
            <div class="device-info">
                <div class="info-box"><div class="info-val">{device_status.get('ip_address', '-')}</div><div class="info-lbl">IP</div></div>
                <div class="info-box"><div class="info-val">{db_event_count}</div><div class="info-lbl">In DB</div></div>
            </div>
        </div>
        """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # === CONTROLS ROW ===
    c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1.5])
    
    with c1:
        if st.button("Sync 1000 Events", disabled=st.session_state.sync_running or not is_connected, use_container_width=True, key="btn_sync_1000"):
            st.session_state.sync_running = True
            st.session_state.sync_result = None
            st.rerun()
    
    with c2:
        if st.button("Test Connection", use_container_width=True, key="btn_test"):
            with st.spinner("Testing..."):
                result = device_ctrl.test_connection()
                if result['success']:
                    st.toast("Connection OK!")
                else:
                    st.toast(f"Failed: {result['message']}")
            st.rerun()
    
    with c3:
        if st.button("Refresh", use_container_width=True, key="btn_refresh_device"):
            st.rerun()
    
    with c4:
        days_back = st.selectbox("", [7, 14, 30, 60, 90], index=2, format_func=lambda x: f"Last {x} days", label_visibility="collapsed", key="days_back")
    
    # === RUN SYNC IF REQUESTED ===
    if st.session_state.sync_running:
        st.markdown('<div class="sync-card">', unsafe_allow_html=True)
        st.markdown('<p class="sync-title"><i class="fa-solid fa-rotate fa-spin" style="color:#A22431;"></i> Syncing Events from Device...</p>', unsafe_allow_html=True)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(pct, msg):
            progress_bar.progress(int(pct) / 100)
            status_text.caption(msg)
        
        # Run the sync
        result = device_ctrl.sync_events_from_device(
            max_events=1000,
            days_back=days_back,
            progress_callback=update_progress
        )
        
        st.session_state.sync_result = result
        st.session_state.sync_running = False
        st.markdown('</div>', unsafe_allow_html=True)
        st.rerun()
    
    # === DISPLAY SYNC RESULT ===
    if st.session_state.sync_result:
        result = st.session_state.sync_result
        
        if result['success']:
            st.markdown(f"""
            <div class="result-box result-success">
                <strong>Sync Complete</strong><br>
                Fetched: {result['total_fetched']} | New: {result['new_events']} | Duplicates: {result['duplicates']} | Errors: {result['errors']}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="result-box result-error">
                <strong>Sync Failed</strong><br>
                {result['message']}
            </div>
            """, unsafe_allow_html=True)
        
        # Clear result button
        if st.button("Clear Result", key="clear_result"):
            st.session_state.sync_result = None
            st.rerun()
    
    # === MAIN CONTENT: Two columns ===
    left, right = st.columns([1, 1])
    
    # --- LEFT: Device Info & Quick Actions ---
    with left:
        st.markdown('<p class="sync-title"><i class="fa-solid fa-microchip" style="color:#A22431;"></i> Device Information</p>', unsafe_allow_html=True)
        
        if is_connected:
            info_data = {
                "Device Name": device_status.get('device_name', '-'),
                "Model": device_status.get('model', '-'),
                "Serial Number": device_status.get('serial_number', '-'),
                "Firmware": device_status.get('firmware', '-'),
                "IP Address": device_status.get('ip_address', '-'),
                "Last Check": device_status.get('last_check', '-')
            }
            
            for label, value in info_data.items():
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #F3F4F6;font-size:11px;">
                    <span style="color:#6B7280;">{label}</span>
                    <span style="color:#111827;font-weight:500;">{value}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="result-box result-error">
                Cannot connect to device. Check IP and credentials in Configuration.
            </div>
            """, unsafe_allow_html=True)
        
        # Count on device
        st.markdown("---")
        st.markdown('<p class="sync-title"><i class="fa-solid fa-calculator" style="color:#A22431;"></i> Events on Device</p>', unsafe_allow_html=True)
        
        if is_connected:
            count_result = device_ctrl.get_event_count_on_device(days_back=days_back)
            if count_result['success']:
                st.markdown(f"""
                <div class="result-box result-info">
                    <strong>{count_result['count']:,}</strong> events found in last {days_back} days
                </div>
                """, unsafe_allow_html=True)
            else:
                st.caption(f"Could not count: {count_result.get('error', 'Unknown error')}")
        else:
            st.caption("Connect to device to see event count")
    
    # --- RIGHT: Sync History ---
    with right:
        st.markdown('<p class="sync-title"><i class="fa-solid fa-clock-rotate-left" style="color:#A22431;"></i> Recent Imports</p>', unsafe_allow_html=True)
        
        history = device_ctrl.get_sync_history(limit=10)
        
        if history:
            for entry in history:
                sync_date = entry.get('sync_date', '-')
                if hasattr(sync_date, 'strftime'):
                    sync_date = sync_date.strftime('%Y-%m-%d')
                
                st.markdown(f"""
                <div class="history-row">
                    <span>{sync_date}</span>
                    <span><strong>{entry.get('event_count', 0)}</strong> events</span>
                    <span style="color:#10B981;">{entry.get('synced_count', 0)} synced</span>
                    <span style="color:#F59E0B;">{entry.get('pending_count', 0)} pending</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No import history yet")
        
        st.markdown("---")
        
        # Database stats
        st.markdown('<p class="sync-title"><i class="fa-solid fa-database" style="color:#A22431;"></i> Database Stats</p>', unsafe_allow_html=True)
        
        stats_data = {
            "Total Events": f"{db_event_count:,}",
            "Synced to Webhook": f"{sync_stats.get('synced', 0):,}",
            "Pending Sync": f"{sync_stats.get('pending', 0):,}",
            "Failed": f"{sync_stats.get('failed', 0):,}"
        }
        
        for label, value in stats_data.items():
            color = "#DC2626" if "Failed" in label and int(value.replace(',', '')) > 0 else "#111827"
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #F3F4F6;font-size:11px;">
                <span style="color:#6B7280;">{label}</span>
                <span style="color:{color};font-weight:500;">{value}</span>
            </div>
            """, unsafe_allow_html=True)

# ============================================
# PAGE: UPLOAD SYNC
# ============================================
elif current_page == "upload_sync":
    # Initialize session states
    if 'upload_sync_running' not in st.session_state:
        st.session_state.upload_sync_running = False
    if 'upload_sync_result' not in st.session_state:
        st.session_state.upload_sync_result = None
    
    # Compact CSS for this page
    st.markdown("""
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
    .upload-header { display:flex; align-items:center; justify-content:space-between; padding:6px 12px; background:#F9FAFB; border:1px solid #E5E7EB; margin-bottom:8px; }
    .webhook-badge { display:inline-flex; align-items:center; gap:4px; padding:2px 8px; border-radius:8px; font-size:10px; font-weight:600; }
    .webhook-ok { background:#DCFCE7; color:#166534; }
    .webhook-fail { background:#FEE2E2; color:#991B1B; }
    .webhook-warn { background:#FEF3C7; color:#92400E; }
    .stat-row { display:flex; gap:12px; flex-wrap:wrap; align-items:center; }
    .stat-box { background:#fff; border:1px solid #E5E7EB; padding:3px 10px; min-width:60px; text-align:center; }
    .stat-val { font-size:12px; font-weight:600; color:#111827; }
    .stat-lbl { font-size:8px; color:#6B7280; text-transform:uppercase; }
    .stat-val.pending { color:#F59E0B; }
    .stat-val.failed { color:#DC2626; }
    .stat-val.synced { color:#10B981; }
    .sync-card { background:#fff; border:1px solid #E5E7EB; padding:12px; margin:8px 0; }
    .sync-title { font-size:12px; font-weight:600; color:#374151; margin-bottom:8px; display:flex; align-items:center; gap:6px; }
    .result-box { padding:8px 12px; margin:6px 0; font-size:11px; }
    .result-success { background:#F0FDF4; border-left:3px solid #10B981; color:#166534; }
    .result-error { background:#FEF2F2; border-left:3px solid #EF4444; color:#991B1B; }
    .result-info { background:#EFF6FF; border-left:3px solid #3B82F6; color:#1E40AF; }
    .result-warn { background:#FFFBEB; border-left:3px solid #F59E0B; color:#92400E; }
    .pending-row { display:flex; justify-content:space-between; align-items:center; padding:6px 8px; background:#FAFAFA; margin:2px 0; font-size:10px; border-left:2px solid #F59E0B; }
    .failed-row { display:flex; justify-content:space-between; align-items:center; padding:6px 8px; background:#FEF2F2; margin:2px 0; font-size:10px; border-left:2px solid #EF4444; }
    .history-item { display:flex; justify-content:space-between; padding:4px 8px; background:#F0FDF4; margin:2px 0; font-size:10px; border-left:2px solid #10B981; }
    </style>
    """, unsafe_allow_html=True)
    
    # Get sync stats and webhook config
    sync_stats = upload_sync_ctrl.get_sync_stats()
    webhook_config = upload_sync_ctrl.get_webhook_config()
    overall = sync_stats.get('overall', {})
    today = sync_stats.get('today', {})
    
    # === HEADER: Webhook Status + Stats ===
    if webhook_config['configured']:
        # Quick test webhook in background
        webhook_status = upload_sync_ctrl.test_webhook()
        if webhook_status['success']:
            badge_class = "webhook-ok"
            badge_text = "WEBHOOK OK"
        else:
            badge_class = "webhook-fail"
            badge_text = "WEBHOOK ERROR"
    else:
        badge_class = "webhook-warn"
        badge_text = "NOT CONFIGURED"
        webhook_status = {'success': False}
    
    header_html = f"""
    <div class="upload-header">
        <div style="display:flex;align-items:center;gap:12px;">
            <span class="webhook-badge {badge_class}"><i class="fa-solid fa-circle" style="font-size:6px;"></i> {badge_text}</span>
            <div class="stat-row">
                <div class="stat-box"><div class="stat-val">{overall.get('total', 0):,}</div><div class="stat-lbl">Total</div></div>
                <div class="stat-box"><div class="stat-val synced">{overall.get('synced', 0):,}</div><div class="stat-lbl">Synced</div></div>
                <div class="stat-box"><div class="stat-val pending">{overall.get('pending', 0):,}</div><div class="stat-lbl">Pending</div></div>
                <div class="stat-box"><div class="stat-val failed">{overall.get('failed', 0):,}</div><div class="stat-lbl">Failed</div></div>
            </div>
        </div>
        <div class="stat-row">
            <div class="stat-box"><div class="stat-val">{sync_stats.get('sync_rate_24h', 0)}%</div><div class="stat-lbl">24h Rate</div></div>
            <div class="stat-box"><div class="stat-val">{today.get('synced', 0)}</div><div class="stat-lbl">Today</div></div>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)
    
    # === CONTROLS ROW ===
    pending_count = overall.get('pending', 0) or 0
    failed_count = overall.get('failed', 0) or 0
    total_to_sync = pending_count + failed_count
    
    c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1, 1, 1])
    
    with c1:
        sync_disabled = st.session_state.upload_sync_running or total_to_sync == 0 or not webhook_config['configured']
        if st.button(f"Sync All ({total_to_sync})", disabled=sync_disabled, use_container_width=True, key="btn_sync_all"):
            st.session_state.upload_sync_running = True
            st.session_state.upload_sync_result = None
            st.rerun()
    
    with c2:
        if st.button("Test Webhook", disabled=not webhook_config['configured'], use_container_width=True, key="btn_test_webhook"):
            with st.spinner("Testing..."):
                result = upload_sync_ctrl.test_webhook()
                if result['success']:
                    st.toast(f"Webhook OK! ({result.get('response_time', 0):.2f}s)")
                else:
                    st.toast(f"Failed: {result['message']}")
            st.rerun()
    
    with c3:
        if st.button("Reset Failed", disabled=failed_count == 0, use_container_width=True, key="btn_reset_failed"):
            result = upload_sync_ctrl.reset_failed_events()
            st.toast(result['message'])
            st.rerun()
    
    with c4:
        if st.button("Refresh", use_container_width=True, key="btn_refresh_upload"):
            st.rerun()
    
    with c5:
        sync_limit = st.selectbox("", [50, 100, 200, 500, 1000], index=1, format_func=lambda x: f"Limit: {x}", label_visibility="collapsed", key="sync_limit")
    
    # === RUN SYNC IF REQUESTED ===
    if st.session_state.upload_sync_running:
        st.markdown('<div class="sync-card">', unsafe_allow_html=True)
        st.markdown('<p class="sync-title"><i class="fa-solid fa-cloud-arrow-up fa-beat" style="color:#A22431;"></i> Uploading Events to Webhook...</p>', unsafe_allow_html=True)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(pct, msg):
            progress_bar.progress(int(pct) / 100)
            status_text.caption(msg)
        
        result = upload_sync_ctrl.sync_batch(
            limit=sync_limit,
            sync_failed=True,
            progress_callback=update_progress
        )
        
        st.session_state.upload_sync_result = result
        st.session_state.upload_sync_running = False
        st.markdown('</div>', unsafe_allow_html=True)
        st.rerun()
    
    # === DISPLAY SYNC RESULT ===
    if st.session_state.upload_sync_result:
        result = st.session_state.upload_sync_result
        
        if result['success']:
            if result['synced'] > 0:
                st.markdown(f"""
                <div class="result-box result-success">
                    <strong>Upload Complete</strong><br>
                    Total: {result['total']} | Synced: {result['synced']} | Failed: {result['failed']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="result-box result-info">
                    <strong>{result['message']}</strong>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="result-box result-error">
                <strong>Upload Failed</strong><br>
                {result['message']}
            </div>
            """, unsafe_allow_html=True)
        
        if st.button("Clear Result", key="clear_upload_result"):
            st.session_state.upload_sync_result = None
            st.rerun()
    
    # === MAIN CONTENT: Two columns ===
    left, right = st.columns([1, 1])
    
    # --- LEFT: Pending & Failed Events ---
    with left:
        st.markdown('<p class="sync-title"><i class="fa-solid fa-clock" style="color:#F59E0B;"></i> Pending Events</p>', unsafe_allow_html=True)
        
        pending_events = upload_sync_ctrl.get_pending_events(limit=20)
        pending_only = [e for e in pending_events if e.get('sync_status') == 'pending']
        
        if pending_only:
            event_box = st.container(height=150)
            with event_box:
                for evt in pending_only[:10]:
                    occur = evt.get('occur_time', '-')
                    if hasattr(occur, 'strftime'):
                        occur = occur.strftime('%H:%M:%S')
                    st.markdown(f"""
                    <div class="pending-row">
                        <span>#{evt.get('id', '-')}</span>
                        <span>{evt.get('employee_no', '-')}</span>
                        <span>{evt.get('name', '-')[:15] if evt.get('name') else '-'}</span>
                        <span>{occur}</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown('<div class="result-box result-success">No pending events</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown('<p class="sync-title"><i class="fa-solid fa-triangle-exclamation" style="color:#DC2626;"></i> Failed Events</p>', unsafe_allow_html=True)
        
        recent_failed = sync_stats.get('recent_failed', [])
        
        if recent_failed:
            failed_box = st.container(height=150)
            with failed_box:
                for evt in recent_failed[:10]:
                    occur = evt.get('occur_time', '-')
                    if hasattr(occur, 'strftime'):
                        occur = occur.strftime('%H:%M:%S')
                    error = evt.get('sync_error', '-')[:30] if evt.get('sync_error') else '-'
                    st.markdown(f"""
                    <div class="failed-row">
                        <span>#{evt.get('id', '-')}</span>
                        <span>{evt.get('employee_no', '-')}</span>
                        <span style="color:#DC2626;" title="{evt.get('sync_error', '')}">{error}</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown('<div class="result-box result-success">No failed events</div>', unsafe_allow_html=True)
    
    # --- RIGHT: Webhook Config & History ---
    with right:
        st.markdown('<p class="sync-title"><i class="fa-solid fa-link" style="color:#A22431;"></i> Webhook Configuration</p>', unsafe_allow_html=True)
        
        if webhook_config['configured']:
            webhook_url = webhook_config['webhook_url']
            # Mask URL for display
            if len(webhook_url) > 40:
                display_url = webhook_url[:35] + "..."
            else:
                display_url = webhook_url
            
            has_key = "Yes" if webhook_config['api_key'] else "No"
            
            config_data = {
                "URL": display_url,
                "API Key": has_key,
                "Status": "Connected" if webhook_status.get('success') else "Error"
            }
            
            for label, value in config_data.items():
                color = "#10B981" if value == "Connected" else "#DC2626" if value == "Error" else "#111827"
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #F3F4F6;font-size:11px;">
                    <span style="color:#6B7280;">{label}</span>
                    <span style="color:{color};font-weight:500;">{value}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="result-box result-warn">
                Webhook not configured. Go to Settings to add your webhook URL.
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown('<p class="sync-title"><i class="fa-solid fa-clock-rotate-left" style="color:#A22431;"></i> Recent Uploads</p>', unsafe_allow_html=True)
        
        history = upload_sync_ctrl.get_sync_history(limit=10)
        
        if history:
            history_box = st.container(height=150)
            with history_box:
                for entry in history:
                    sync_hour = entry.get('sync_hour', '-')
                    count = entry.get('count', 0)
                    st.markdown(f"""
                    <div class="history-item">
                        <span>{sync_hour}</span>
                        <span><strong>{count}</strong> synced</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.caption("No upload history yet")
        
        st.markdown("---")
        
        # Today's summary
        st.markdown('<p class="sync-title"><i class="fa-solid fa-calendar-day" style="color:#A22431;"></i> Today\'s Summary</p>', unsafe_allow_html=True)
        
        today_data = {
            "Total Events": today.get('total', 0),
            "Synced": today.get('synced', 0),
            "Pending": today.get('pending', 0),
            "Failed": today.get('failed', 0)
        }
        
        for label, value in today_data.items():
            color = "#10B981" if "Synced" in label else "#F59E0B" if "Pending" in label else "#DC2626" if "Failed" in label else "#111827"
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #F3F4F6;font-size:11px;">
                <span style="color:#6B7280;">{label}</span>
                <span style="color:{color};font-weight:500;">{value}</span>
            </div>
            """, unsafe_allow_html=True)
