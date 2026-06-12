import plotly.graph_objects as go
import pandas as pd

# 1. Create Mock Time-Series Data
# data = {
#     'Year': [2021, 2021, 2021, 2022, 2022, 2022, 2023, 2023, 2023,2024, 2024, 2024, 2025, 2025, 2025, 2026, 2026, 2026],
#     'State': ['NY', 'CA', 'TX', 'NY', 'CA', 'TX', 'NY', 'CA', 'TX','NY', 'CA', 'TX', 'NY', 'CA', 'TX', 'NY', 'CA', 'TX'],
#     'Value': [2,4,6,4,6,8,6,8,10,10, 15, 12, 14, 18, 11, 22, 25, 19]
# }

data = {
    'Year': [2021, 2022, 2022, 2023, 2023, 2023,2024, 2024, 2024, 2025, 2025, 2025, 2026, 2026, 2026, 2026],
    'State': ['NY', 'NY', 'CA', 'NY', 'CA', 'TX','NY', 'CA', 'TX', 'NY', 'CA', 'TX', 'NY', 'CA', 'TX', 'NH'],
    'Value': [2,     4,    6,    6,8,10,10, 15, 12, 14, 18, 11, 22, 25, 19,30]
}
df = pd.DataFrame(data)
years = sorted(df['Year'].unique())

# 2. Define Global Color Limits (Crucial for consistent animation framing)
min_val = df['Value'].min()
max_val = df['Value'].max()

# 3. Define the Initial Base Trace (Frame 0)
df_start = df[df['Year'] == years[0]]
initial_trace = go.Choropleth(
    locations=df_start['State'],
    z=df_start['Value'],
    locationmode='USA-states',
    colorscale='Viridis',
    zmin=min_val,
    zmax=max_val,
    colorbar=dict(title="Value Scale")
)

# 4. Build Individual Frames for Each Year
frames = []
for yr in years:
    df_frame = df[df['Year'] == yr]
    frames.append(
        go.Frame(
            data=[
                go.Choropleth(
                    locations=df_frame['State'],
                    z=df_frame['Value'],
                    locationmode='USA-states'
                )
            ],
            name=str(yr) # Used to tie the frame to the time slider steps
        )
    )

# 5. Configure Interactive Play/Pause Buttons
updatemenus = [
    {
        "type": "buttons",
        "buttons": [
            {
                "label": "Play",
                "method": "animate",
                "args": [None, {"frame": {"duration": 2000, "redraw": True}, "fromcurrent": True}]
            },
            {
                "label": "Pause",
                "method": "animate",
                "args": [[None], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate"}]
            }
        ],
        "direction": "left",
        "pad": {"r": 10, "t": 87},
        "showactive": False,
        "x": 0.1,
        "y": 0
    }
]

# 6. Build the Interactive Slider Component
sliders = [
    {
        "active": 0,
        "yanchor": "top",
        "xanchor": "left",
        "currentvalue": {
            "font": {"size": 20},
            "prefix": "Year: ",
            "visible": True
            # "placement": "top"
        },
        "transition": {"duration": 300, "easing": "cubic-in-out"},
        "pad": {"b": 10, "t": 50},
        "len": 0.9,
        "x": 0.1,
        "y": 0,
        "steps": [
            {
                "args": [
                    [str(yr)], # Matches frame name
                    {"frame": {"duration": 300, "redraw": True}, "mode": "immediate"}
                ],
                "label": str(yr),
                "method": "animate"
            } for yr in years
        ]
    }
]

# 7. Finalize Map Layout Assembly
layout = go.Layout(
    title=dict(text="Time-Series State Analysis via go.Choropleth", x=0.5),
    geo=dict(scope="usa", projection=dict(type="albers usa")),
    updatemenus=updatemenus,
    sliders=sliders
)

# Assemble Figure
fig = go.Figure(data=[initial_trace], layout=layout, frames=frames)
fig.show()
