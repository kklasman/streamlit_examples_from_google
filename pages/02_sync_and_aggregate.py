import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os

st.set_page_config(page_title="Rider Milestone Tracker", layout="wide")
st.title("🚴 Personal Biking Aggregation Explorer")

# --- SIMULATED DATABASE LAYER (Swap out for Supabase/Neon pg in production) ---
# In production, connect via: engine = create_engine("postgresql://user:pass@host/db")
# For development, we manage a session-state dataframe to mock cloud persistence.
if "production_db_mock" not in st.session_state:
    st.session_state.production_db_mock = pd.DataFrame([
        {"user_id": "rider_01", "geo_key": "MA_MIDDLESEX_BOSTON", "town_miles": 45.2, "county": "MIDDLESEX",
         "state": "MA"},
        {"user_id": "rider_01", "geo_key": "MA_MIDDLESEX_CAMBRIDGE", "town_miles": 12.8, "county": "MIDDLESEX",
         "state": "MA"},
        {"user_id": "rider_01", "geo_key": "MA_SUFFOLK_CHELSEA", "town_miles": 5.0, "county": "SUFFOLK", "state": "MA"}
    ])

if "db_update_tick" not in st.session_state:
    st.session_state.db_update_tick = 0


# --- 1. DYNAMIC API SYNC PIPELINE ---
def query_source_system_api(user_id):
    """Simulates querying the 3rd-party source system for the newly ridden miles.
    In production, you would run a requests.get() against their endpoint.
    """
    # Mocking the payload received after the user gets their email notification
    return [
        {"geo_key": "MA_MIDDLESEX_BOSTON", "new_miles": 15.5, "county": "MIDDLESEX", "state": "MA"},
        {"geo_key": "MA_NORFOLK_QUINCY", "new_miles": 22.1, "county": "NORFOLK", "state": "MA"}
    ]


def execute_on_demand_sync(user_id):
    """Fetches new targeted data, updates persistent storage, and bumps the UI state."""
    new_data = query_source_system_api(user_id)
    db = st.session_state.production_db_mock

    for record in new_data:
        # Match using your unified compound string key
        match_idx = db[(db['user_id'] == user_id) & (db['geo_key'] == record['geo_key'])].index

        if not match_idx.empty:
            # Add new miles to existing town record
            db.loc[match_idx, 'town_miles'] += record['new_miles']
        else:
            # Create a brand new town entry
            new_row = {
                "user_id": user_id,
                "geo_key": record['geo_key'],
                "town_miles": record['new_miles'],
                "county": record['county'],
                "state": record['state']
            }
            db = pd.concat([db, pd.DataFrame([new_row])], ignore_index=True)

    st.session_state.production_db_mock = db
    # Incrementing the tick invalidates user-bound caches instantly
    st.session_state.db_update_tick += 1


# --- 2. USER STATE BOUND CACHE ---
@st.cache_data(ttl=600)
def fetch_and_aggregate_user_data(user_id, update_tick):
    """Pulls current entries from storage and builds multi-level aggregations."""
    all_data = st.session_state.production_db_mock
    user_rows = all_data[all_data['user_id'] == user_id]

    if user_rows.empty:
        return None, None, None

    # Build on-the-fly higher level rollups using pandas
    county_rollup = user_rows.groupby(['state', 'county'])['town_miles'].sum().reset_index()
    state_rollup = user_rows.groupby(['state'])['town_miles'].sum().reset_index()

    return user_rows, county_rollup, state_rollup


# --- 3. UI SIDEBAR & INTERFACE TRIGGERS ---
st.sidebar.header("🔄 Source Synchronizer")
current_user = "rider_01"

if st.sidebar.button("📥 Sync New Miles From Source System"):
    with st.spinner("Reaching out to source platform..."):
        execute_on_demand_sync(current_user)
    st.sidebar.success("Sync Complete! Maps recalculated.")

# Select View Level for Plotly
view_level = st.radio("Select Map Target Aggregation Level:", ["Town Level", "County Level", "State Level"],
                      horizontal=True)

# Fetch current structured arrays tied to our invalidation tick
town_df, county_df, state_df = fetch_and_aggregate_user_data(current_user, st.session_state.db_update_tick)

# --- 4. MAP VIEW ROUTER ---
fig = go.Figure()

if town_df is not None and not town_df.empty:
    if view_level == "Town Level":
        # Load your pre-normalized state town files...
        fig.add_trace(go.Choroplethmap(
            geojson={"type": "FeatureCollection", "features": []},  # Inject town geojson here
            locations=town_df["geo_key"],
            z=town_df["town_miles"],
            colorscale="Plasma", name="Town Progress"
        ))
    elif view_level == "County Level":
        # Build county mapping keys (e.g. MA_MIDDLESEX) to pass to a county GeoJSON
        county_df['county_key'] = county_df['state'] + "_" + county_df['county']
        fig.add_trace(go.Choroplethmap(
            geojson={"type": "FeatureCollection", "features": []},  # Inject county geojson here
            locations=county_df["county_key"],
            z=county_df["town_miles"],
            colorscale="Cividis", name="County Progress"
        ))
    elif view_level == "State Level":
        fig.add_trace(go.Choroplethmap(
            geojson={"type": "FeatureCollection", "features": []},  # Inject state geojson here
            locations=state_df["state"],
            z=state_df["town_miles"],
            colorscale="Viridis", name="State Progress"
        ))

fig.update_layout(map=dict(style="carto-positron", center=dict(lat=42.2, lon=-71.5), zoom=7),
                  margin=dict(l=0, r=0, t=0, b=0))
st.plotly_chart(fig, width='stretch')

# Metrics Display Row
if town_df is not None:
    col1, col2 = st.columns(2)
    col1.metric("Total Unique Miles Tracked", f"{town_df['town_miles'].sum():,.1f} mi")
    col2.metric("Unique Towns Explored", len(town_df))
