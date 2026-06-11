# from ..my_decorators import my_timeit
from functools import wraps
import json
import logging
import os
import plotly.graph_objects as go
import streamlit as st
from streamlit import session_state as ss
import time


def timeit(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        logging.info(f'{func.__name__} took {total_time:.4f} seconds')
        return result
    return timeit_wrapper

def get_browse_wandrer_data_root_folder():
    return r'C:\Users\kk4si\PycharmProjects\osmb_and_wandrer'


# @timeit
@st.cache_data
def get_browse_wandrer_data_boundaries_folder():
    logging.info('Getting boundaries folder...')
    root_folder = get_browse_wandrer_data_root_folder()
    boundaries_folder_path = os.path.join(root_folder, 'Lib', 'data', 'boundaries')
    return boundaries_folder_path


@timeit
@st.cache_data(ttl=300, max_entries=10, show_spinner="Adding town trace...")
def add_town_trace(fig, combined_features):
    logging.info('Running add_town_trace...')
    geojson = {"type": "FeatureCollection", "features": combined_features}
    fig.add_trace(go.Choroplethmap(
        geojson=geojson,
        locations=combined_locations,
        featureidkey='properties.long_name',
        # locations=parks_merged_df['long_name'],
        z=combined_z,
        colorscale="Viridis",
        marker_opacity=0.6,
        name="Town Boundaries"
    ))

    return fig

def add_empty_town_trace(fig):
    # geojson = {"type": "FeatureCollection", "features": []}
    fig.add_trace(go.Choroplethmap(
        geojson={"type": "FeatureCollection", "features": []},
        locations=[], z=[],
        name="Town Boundaries (Toggled Off)",
        visible="legendonly"
    ))

    return fig


# 2. Memory-Pinned Caching Function (Crucial for Streamlit Cloud)
# max_entries prevents memory accumulation; it discards oldest entries if RAM gets tight.
@timeit
@st.cache_data(ttl=300, max_entries=10, show_spinner="Parsing state shapes from disk...")
def load_state_geojson(state_code: str):
    """Loads a single state file and caches it globally in memory across all users."""
    logging.info(f'Running load_state_geojson for {state_code} from disk...')
    fq_boundaries_folder = get_browse_wandrer_data_boundaries_folder()
    row_filename = f"{state_code.replace(' ','-')}_locations.geojson"
    fq_filename = os.path.join(fq_boundaries_folder, row_filename)
    file_path = fq_filename.replace(' ','-')

    if not os.path.exists(file_path):
        logging.info(f'File path not found: {file_path}')
        return None

    with open(file_path, "r") as f:
        data = json.load(f)

    # Extract structural components efficiently
    features = data.get("features", [])
    # locations = [f["id"] for f in features]
    locations = [f["properties"]["long_name"] for f in features]
    # Generate mock metric for demo; map this to your actual dataframe data
    metrics = [len(loc) * 12 for loc in locations]

    logging.info(f'Loaded {len(features)} features for {state_code}')

    return {"features": features, "locations": locations, "z": metrics}

@timeit
@st.cache_data(ttl=300, max_entries=10, show_spinner="Showing figure...")
def show_chart(fig):
    logging.info('Running show_chart...')
    st.plotly_chart(fig, width='stretch', height=750)


## main logic

logging.basicConfig(level=logging.INFO)

# 1. Page Configuration
st.set_page_config(page_title="Regional Town Mapper", layout="wide")
st.title("🗺️ US Town-Level Explorer")

st.write(f'cwd = {os.getcwd()}')
fq_boundaries_folder = get_browse_wandrer_data_boundaries_folder()
st.write(f'{fq_boundaries_folder=}')

# 3. Sidebar Inputs (Acting as our Dynamic Selector)
# available_states = {"Massachusetts": "MA", "Rhode Island": "RI", "Connecticut": "CT", "New York": "NY"}
available_states = {"MA": "Massachusetts", "RI": "Rhode Island", "CT": "Connecticut", "NH": "New Hampshire"}
# selected_names = st.sidebar.multiselect("Select States to Load:", list(available_states.keys()), default=["MA"])
if 'selected_state' not in st.session_state:
    ss.selected_state = ['MA']
# selected_names = st.sidebar.multiselect("Select States to Load:", list(available_states.keys()), key='selected_state', default=ss.selected_state)
selected_names = st.sidebar.multiselect("Select States to Load:", list(available_states.keys()), key='selected_state')

# Initialize toggles to keep things snappy
load_heavy_towns = st.sidebar.toggle("Render Heavy Town Boundaries", value=False)

# 4. Process and Merge Selected States in Memory
combined_features = []
combined_locations = []
combined_z = []

if load_heavy_towns and selected_names:
    for name in selected_names:
        state_code = available_states[name]
        state_data = load_state_geojson(state_code)
        if state_data:
            # print(f'Loaded {len(state_data["features"])} features for {state_code}')
            combined_features.extend(state_data["features"])
            combined_locations.extend(state_data["locations"])
            combined_z.extend(state_data["z"])

# 5. Construct the Plotly Map Figure
fig = go.Figure()

# Trace 0: Light Overview Layer (Always Visible)
fig.add_trace(go.Scattermap(
    lat=[42.3601], lon=[-71.0589],
    mode='markers',
    marker=dict(size=10, color='royalblue'),
    name="Regional Reference Centers"
))

# Trace 1: The Lazy Region Layer
if load_heavy_towns and combined_features:
    # If toggled ON, stream the dynamically stitched geojson directly
    fig = add_town_trace(fig, combined_features)
else:
    # Keep it clean and completely empty on initial load
    fig = add_empty_town_trace(fig)

# Standardize map interface configurations
fig.update_layout(
    map=dict(style="carto-positron", center=dict(lat=42.0, lon=-71.5), zoom=6),
    margin=dict(l=1, r=10, t=30, b=1),
    showlegend=True
)


# 6. Render the Map Window
# st.plotly_chart(fig, use_container_width=True, height=750)
show_chart(fig)
logging.info('')

# Optional Status Monitor to ensure Streamlit remains healthy
st.caption(f"Currently monitoring {len(combined_locations):,} town polygons in real-time.")
