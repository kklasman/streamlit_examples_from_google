import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os
import datetime
import numpy as np

st.set_page_config(page_title="Rider Timeline Tracker", layout="wide")
st.title("🚴 Rider Progress Timeline & Map Animation")

# --- DATABASE PERSISTENCE LAYER ---
# In production, use Supabase/Neon PostgreSQL.
# For local development, we maintain a session state ledger that tracks every historical sync event.
if "historical_ledger_db" not in st.session_state:
    st.session_state.historical_ledger_db = pd.DataFrame([
        # Baseline data from early 2025
        {"user_id": "rider_01", "geo_key": "MA_MIDDLESEX_BOSTON", "miles_added": 12.5, "sync_date": "2025-01-15"},
        {"user_id": "rider_01", "geo_key": "MA_MIDDLESEX_CAMBRIDGE", "miles_added": 8.2, "sync_date": "2025-02-10"},
        {"user_id": "rider_01", "geo_key": "MA_MIDDLESEX_BOSTON", "miles_added": 15.0, "sync_date": "2025-03-22"},
        {"user_id": "rider_01", "geo_key": "MA_SUFFOLK_CHELSEA", "miles_added": 5.4, "sync_date": "2025-04-05"},
    ])

if "db_update_tick" not in st.session_state:
    st.session_state.db_update_tick = 0


# --- 1. DYNAMIC API CALL ROUTER ---
def fetch_county_town_data_from_source(user_id, state, county):
    """Simulates hitting the third-party URL passing specific parameters.
    Example: requests.get(f"https://source.com{user_id}&state={state}&county={county}")
    """
    state_up = state.upper()
    county_up = county.upper()

    # Simulating the returned data payload for every town inside that county
    return [
        {"geo_key": f"{state_up}_{county_up}_BOSTON", "current_total": 45.5},
        {"geo_key": f"{state_up}_{county_up}_CAMBRIDGE", "current_total": 25.0},
        {"geo_key": f"{state_up}_{county_up}_SOMERVILLE", "current_total": 14.2}
    ]


def sync_impacted_regions(user_id, target_regions):
    """Loops through required unique calls, detects changes, and logs them with today's date."""
    ledger = st.session_state.historical_ledger_db
    today_str = datetime.date.today().isoformat()

    for region in target_regions:
        state, county = region["state"], region["county"]
        # Execute the separate URL request for this specific county
        api_response = fetch_county_town_data_from_source(user_id, state, county)

        for town_data in api_response:
            geo_key = town_data["geo_key"]

            # Find the sum of miles we already have logged in our database for this town
            existing_miles = ledger[(ledger['user_id'] == user_id) & (ledger['geo_key'] == geo_key)][
                'miles_added'].sum()

            # Calculate the delta (new miles ridden since last sync)
            new_miles_delta = town_data["current_total"] - existing_miles

            if new_miles_delta > 0.01:
                # Log only the new miles as a distinct historical event
                new_event = {
                    "user_id": user_id,
                    "geo_key": geo_key,
                    "miles_added": new_miles_delta,
                    "sync_date": today_str
                }
                ledger = pd.concat([ledger, pd.DataFrame([new_event])], ignore_index=True)

    st.session_state.historical_ledger_db = ledger
    st.session_state.db_update_tick += 1


# --- 2. SIDEBAR SYNC UI PANEL ---
st.sidebar.header("🔄 Sync On-Demand")
current_user = "rider_01"

# In production, you would parse the list of counties out of the user's notification email automatically
st.sidebar.caption("Identify regions to update:")
sync_state = st.sidebar.text_input("State Code:", value="MA")
sync_county = st.sidebar.text_input("County Name:", value="Middlesex")

if st.sidebar.button("📥 Pull New County Metrics"):
    regions_to_call = [{"state": sync_state, "county": sync_county}]
    sync_impacted_regions(current_user, regions_to_call)
    st.sidebar.success("Successfully synchronized and calculated mile differences!")

# --- 3. TIMELINE & HISTORICAL CONTROLS ---
st.header("🕒 Historical Playback Panel")

ledger_df = st.session_state.historical_ledger_db
ledger_df['sync_date'] = pd.to_datetime(ledger_df['sync_date'])

# Generate list of available months for historical tracking
# months_available = ledger_df['sync_date'].dt.to_period('M').unique().sort_values()
months_available = ledger_df['sync_date'].dt.to_period('M').unique()
month_labels = [str(m) for m in months_available]

# Interactive Slider for Selecting Point-In-Time History
selected_month_str = st.select_slider(
    "Slide to view map at a specific point in time:",
    options=month_labels,
    value=month_labels[-1]
)

# --- 4. DATA ACCUMULATION PIPELINE ---
# Filter ledger up to the selected historical month cutoff
cutoff_date = pd.Period(selected_month_str, freq='M').to_timestamp(how='end')
filtered_ledger = ledger_df[(ledger_df['user_id'] == current_user) & (ledger_df['sync_date'] <= cutoff_date)]

# Accumulate the totals up to that specific date
historical_totals = filtered_ledger.groupby('geo_key')['miles_added'].sum().reset_index()


# --- 5. RENDER INTERACTIVE PLOTLY MAP ---
# Load optimized geography configurations
@st.cache_data
def get_mock_geojson():
    # Placeholder layout to ensure plot stability
    return {"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": "MA_MIDDLESEX_BOSTON", "geometry": {"type": "Polygon", "coordinates": [
            [[-71.1, 42.3], [-71.0, 42.3], [-71.0, 42.4], [-71.1, 42.4], [-71.1, 42.3]]]}},
        {"type": "Feature", "id": "MA_MIDDLESEX_CAMBRIDGE", "geometry": {"type": "Polygon", "coordinates": [
            [[-71.15, 42.35], [-71.1, 42.35], [-71.1, 42.42], [-71.15, 42.42], [-71.15, 42.35]]]}},
        {"type": "Feature", "id": "MA_SUFFOLK_CHELSEA", "geometry": {"type": "Polygon", "coordinates": [
            [[-71.05, 42.38], [-71.0, 42.38], [-71.0, 42.43], [-71.05, 42.43], [-71.05, 42.38]]]}},
        {"type": "Feature", "id": "MA_MIDDLESEX_SOMERVILLE", "geometry": {"type": "Polygon", "coordinates": [
            [[-71.26, 42.07], [-71.23, 42.07],[-71.23, 42.04], [-71.27, 42.04],[-71.26, 42.07]]]}}
    ]}


fig = go.Figure()
fig.add_trace(go.Choroplethmap(
    geojson=get_mock_geojson(),
    locations=historical_totals["geo_key"],
    z=historical_totals["miles_added"],
    colorscale="Viridis",
    zmin=0, zmax=50,  # Keep color scale fixed during history changes so colors match values accurately
    marker_opacity=0.6,
    name="Miles Covered"
))

zoom = 8
fig.update_layout(
    map=dict(style="carto-positron", center=dict(lat=42.36, lon=-71.06), zoom=zoom),
    margin=dict(l=0, r=0, t=0, b=0)
)

st.plotly_chart(fig, width='stretch')

# Historical Summary Tables
st.subheader("📜 Sync History Log Ledger")
st.dataframe(ledger_df.sort_values(by="sync_date", ascending=False), width='stretch')

# # Convert a list of all affected locations into unique pairs before looping
# impacted_counties = list({(r['state'], r['county']) for r in raw_notification_list})
