import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json
import datetime
import numpy as np

st.set_page_config(page_title="State Explorer Milestone Tracker", layout="wide")
st.title("🚴 State Completion Challenge: Explore Every Town")

# --- FIXED STATE TARGET DENOMINATORS ---
# In production, pull these totals dynamically by running a COUNT(DISTINCT town)
# against a master geography lookup table in your cloud database.
STATE_TOWN_COUNTS = {
    "MA": 10,  # Massachusetts has exactly 351 cities/towns
    "RI": 39,  # Rhode Island has 39 municipalities
    "CT": 169  # Connecticut has 169 towns
}

# --- SAMPLE HISTORICAL DATA STORAGE ---
if "historical_ledger_db" not in st.session_state:
    st.session_state.historical_ledger_db = pd.DataFrame([
        {"user_id": "rider_01", "geo_key": "MA_MIDDLESEX_BOSTON", "miles_added": 12.5, "sync_date": "2025-03-15",
         "state_code": "MA"},
        {"user_id": "rider_01", "geo_key": "MA_MIDDLESEX_CAMBRIDGE", "miles_added": 8.2, "sync_date": "2025-04-10",
         "state_code": "MA"},
        {"user_id": "rider_01", "geo_key": "MA_SUFFOLK_CHELSEA", "miles_added": 5.4, "sync_date": "2025-05-22",
         "state_code": "MA"},
        {"user_id": "rider_01", "geo_key": "MA_NORFOLK_QUINCY", "miles_added": 14.1, "sync_date": "2025-06-05",
         "state_code": "MA"},
    ])

current_user = "rider_01"
ledger_df = st.session_state.historical_ledger_db.copy()
ledger_df['sync_date'] = pd.to_datetime(ledger_df['sync_date'])

# --- 1. USER VIEW SELECTION PANEL ---
selected_state = st.sidebar.selectbox("Target Challenge State:", list(STATE_TOWN_COUNTS.keys()))
total_towns_in_state = STATE_TOWN_COUNTS[selected_state]

# --- 2. THE HISTORICAL ACCUMULATION ENGINE ---
# Extract all historical sync marks to populate our playback bar
months_available = ledger_df[ledger_df['state_code'] == selected_state]['sync_date'].dt.to_period('M').unique()
month_labels = [str(m) for m in months_available]

if month_labels:
    selected_month_str = st.select_slider(
        "⏳ Adjust Timeline to View Historical Progress:",
        options=month_labels,
        value=month_labels[-1]
    )
    cutoff_date = pd.Period(selected_month_str, freq='M').to_timestamp(how='end')
else:
    st.warning("No riding records logged yet for this state.")
    st.stop()

# Filter data up to the slider's point-in-time cutoff
historical_snapshot = ledger_df[
    (ledger_df['user_id'] == current_user) &
    (ledger_df['state_code'] == selected_state) &
    (ledger_df['sync_date'] <= cutoff_date)
    ]

# Calculate accumulated totals up to this specific point in history
town_totals = historical_snapshot.groupby('geo_key')['miles_added'].sum().reset_index()
towns_explored_so_far = len(town_totals[town_totals['miles_added'] > 0])
completion_percentage = (towns_explored_so_far / total_towns_in_state) * 100

# --- 3. GOAL TRACKING DASHBOARD METRICS ---
col1, col2, col3 = st.columns([1, 1, 2])
col1.metric("Towns Explored", f"{towns_explored_so_far} / {total_towns_in_state}")
col2.metric("Total State Distance", f"{town_totals['miles_added'].sum():,.1f} mi")

# Progress bar toward the completion goal
with col3:
    st.markdown(f"**Challenge Completion Progress: {completion_percentage:.1f}%**")
    st.progress(completion_percentage / 100.0)

# --- 4. MAP INTERFACE LAYOUT ---
# (Inject your optimized go.Choroplethmap here using town_totals)
# Set zmin=0 and fixed zmax values to keep visual shading steady during updates
st.caption(f"🗺️ Map representation reflecting your total coverage up to: **{selected_month_str}**")

# --- 5. THE TRAJECTORY GROWTH CHART ---
st.subheader("📈 Your Challenge Trajectory Over Time")


def build_progress_timeline(df, state_code, total_towns):
    """Calculates cumulative unique town counts over a historical timeline."""
    state_df = df[df['state_code'] == state_code].sort_values('sync_date')

    if state_df.empty:
        return pd.DataFrame()

    # Drop duplicate entries for the same town so we only count the FIRST time a town was visited
    first_visits = state_df.drop_duplicates(subset=['geo_key'], keep='first').copy()

    # Generate a running count of unique towns discovered over time
    first_visits['unique_towns_cumulative'] = range(1, len(first_visits) + 1)
    first_visits['percent_complete'] = (first_visits['unique_towns_cumulative'] / total_towns) * 100

    return first_visits


timeline_data = build_progress_timeline(ledger_df, selected_state, total_towns_in_state)

if not timeline_data.empty:
    # Generate a stepped line chart to display achievement updates clearly
    fig_line = px.line(
        timeline_data,
        x='sync_date',
        y='percent_complete',
        title="Percent of State Explored Over Time",
        labels={'sync_date': 'Date Registered', 'percent_complete': '% State Explored'},
        markers=True,
        line_shape='hv'  # 'hv' creates step-lines which are ideal for milestone goals
    )

    # Lock the chart's max boundary at 100% to represent the finish line
    fig_line.update_layout(yaxis=dict(range=[0, 105]), template="plotly_white")

    # Draw a horizontal target indicator line marking the 100% completion goal
    fig_line.add_hline(y=100, line_dash="dash", line_color="green", annotation_text="State Master Milestone (100%)")

    st.plotly_chart(fig_line, width='stretch')
