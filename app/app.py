import os
import sys

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.optimize import generate_schedule_recommendations
from src.data_feeds import (
    load_transit_stops,
    load_demand_feed,
    CACHE_MAX_AGE_HOURS,
)

AUTO_REFRESH_MS = 60000
KTM_TZ = "Asia/Katmandu"

st.set_page_config(
    layout="wide",
    page_title="Kathmandu Transit Optimization Command Center",
)

st.html(
    f"""
    <script>
      setTimeout(function() {{
        window.location.reload();
      }}, {AUTO_REFRESH_MS});
    </script>
    """
)

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Outfit', sans-serif;
        }

        .main-header {
            font-size: 2.6rem;
            font-weight: 800;
            background: linear-gradient(90deg, #00C9FF 0%, #92FE9D 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.2rem;
        }

        .sub-header {
            font-size: 1.1rem;
            color: #94A3B8;
            margin-bottom: 1.8rem;
        }

        .metric-container {
            background: rgba(30, 41, 59, 0.7);
            border-radius: 10px;
            padding: 1.2rem;
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .status-connected {
            color: #10B981;
            font-weight: 600;
        }

        .status-fallback {
            color: #F59E0B;
            font-weight: 600;
        }
    </style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_stops_data():
    return load_transit_stops()


@st.cache_data(ttl=60)
def load_demand_data():
    return load_demand_feed()


def refresh_dor_feed():
    try:
        load_demand_feed(force_refresh=True)
        load_transit_stops(force_refresh=True)
        return True
    except Exception as exc:
        st.sidebar.error(f"DOR refresh failed: {exc}")
        return False


# UI Header
st.markdown(
    "<div class='main-header'>Smart City: Kathmandu Transit Optimization Command Center</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='sub-header'>Real Department of Roads (DOR) traffic counts "
    "for Kathmandu Valley corridors, spatial congestion clustering, and "
    "automated headway dispatch recommendations.</div>",
    unsafe_allow_html=True,
)

# Sidebar Control Panel
st.sidebar.header("System Controls")

st.sidebar.markdown(
    "Data Source: <span class='status-connected'>DOR SSRN Traffic Portal (real)</span>",
    unsafe_allow_html=True,
)
st.sidebar.markdown(
    f"Snapshot refresh window: every {CACHE_MAX_AGE_HOURS} hours "
    f"(dashboard auto-refresh: {AUTO_REFRESH_MS // 1000}s)",
    unsafe_allow_html=True,
)

if st.sidebar.button("Refresh Data from DOR Portal Now"):
    if refresh_dor_feed():
        st.cache_data.clear()
        st.sidebar.success("DOR data refreshed from the official portal!")
    else:
        st.sidebar.warning("Refresh failed - showing last cached real snapshot.")

if st.sidebar.button("Clear Data Cache"):
    st.cache_data.clear()
    st.sidebar.success("Cache cleared.")

stops_df = load_stops_data()
demand_df = load_demand_data()

if len(stops_df) == 0 or len(demand_df) == 0:
    st.error(
        "No real traffic data could be loaded from the Department of Roads portal. "
        "Run `.venv\\Scripts\\python.exe src/generate_data.py` once to fetch the "
        "real Kathmandu traffic snapshot, then relaunch this dashboard."
    )
    st.stop()

available_routes = ["All Corridors"] + list(stops_df["route_id"].unique())
selected_route = st.sidebar.selectbox("Filter Transit Corridor", available_routes)

# Operational snapshot: the most recently published count per station.
latest_data = demand_df.sort_values("timestamp").groupby("stop_id", as_index=False).tail(1)
if len(latest_data) == 0:
    latest_data = demand_df.copy()
latest_data["predicted_demand"] = pd.to_numeric(latest_data["demand"], errors="coerce").fillna(0)
latest_data = latest_data[["stop_id", "predicted_demand", "demand"]].copy()

latest_year = demand_df["traffic_year"].max()

# Generate Optimization Recommendations
df_rec, df_hotspots = generate_schedule_recommendations(stops_df, latest_data)

if selected_route != "All Corridors":
    df_rec = df_rec[df_rec["route_id"] == selected_route]
    if len(df_hotspots) > 0:
        df_hotspots = df_hotspots[df_hotspots["route_id"] == selected_route]

# Key Performance Metrics Panel
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_demand = int(df_rec["predicted_demand"].fillna(0).sum()) if len(df_rec) > 0 else 0
    st.metric("Total System Demand", f"{total_demand:,} pcu/hr")

with col2:
    occupancy_series = pd.to_numeric(df_rec["occupancy_ratio"], errors="coerce") if len(df_rec) > 0 else pd.Series(dtype=float)
    if len(occupancy_series) > 0 and occupancy_series.notna().any():
        avg_occupancy = int(occupancy_series.fillna(0).mean() * 100)
    else:
        avg_occupancy = 0
    st.metric("Average Junction Pressure", f"{avg_occupancy}%")

with col3:
    critical_hotspots = len(df_rec[df_rec["alert_level"] == "RED"]) if len(df_rec) > 0 else 0
    st.metric("Critical Overcrowded Stops", f"{critical_hotspots}")

with col4:
    underutilized = len(df_rec[df_rec["alert_level"] == "BLUE"]) if len(df_rec) > 0 else 0
    st.metric("Underutilized Stops", f"{underutilized}")

st.write("---")

st.subheader("Live Operational Snapshot")
live_cols = st.columns(2)
demand_source = (
    demand_df["data_source"].iloc[0]
    if len(demand_df) > 0 and "data_source" in demand_df.columns
    else "unknown"
)
with live_cols[0]:
    st.markdown("**Current Kathmandu Time**  \n" + pd.Timestamp.now(tz=KTM_TZ).strftime("%Y-%m-%d %H:%M"))
with live_cols[1]:
    st.markdown(
        f"**Real Demand Feed**  \n{demand_source}  \n"
        f"Latest published count year: {latest_year}"
    )

st.subheader("Corridor Dispatch Priorities")
if len(df_rec) > 0 and {"corridor_action", "corridor_peak_occupancy", "corridor_recommended_buses"}.issubset(df_rec.columns):
    corridor_view = (
        df_rec[["route_id", "corridor_predicted_demand", "corridor_avg_occupancy",
                "corridor_peak_occupancy", "corridor_recommended_buses",
                "corridor_headway_change_min", "corridor_action"]]
        .drop_duplicates(subset=["route_id"])
        .sort_values(by="corridor_peak_occupancy", ascending=False)
    )
    if selected_route != "All Corridors":
        corridor_view = corridor_view[corridor_view["route_id"] == selected_route]
    st.dataframe(corridor_view, width='stretch', height=220)
else:
    st.info("No corridor-level dispatch summary available.")

# Main Interface: Interactive Folium Map and Dispatch Control Table
col_map, col_table = st.columns([7, 5])

with col_map:
    st.subheader("Geographic Congestion Heatmap - Kathmandu Valley")

    if len(df_rec) > 0:
        map_lat = df_rec["latitude"].mean()
        map_lon = df_rec["longitude"].mean()

        m = folium.Map(location=[map_lat, map_lon], zoom_start=12, tiles="cartodbpositron")

        color_map = {
            "RED":   "#EF4444",
            "AMBER": "#F59E0B",
            "GREEN": "#10B981",
            "BLUE":  "#3B82F6",
        }

        for _, row in df_rec.iterrows():
            color = color_map.get(row["alert_level"], "#6B7280")
            occupancy_ratio = float(row["occupancy_ratio"]) if pd.notna(row["occupancy_ratio"]) else 0.0
            radius = 8 + (occupancy_ratio * 6)

            popup_html = f"""
                <div style="font-family: 'Outfit', sans-serif; font-size: 13px; color: #1E293B;">
                    <strong>{row['stop_name']}</strong><br/>
                    Route Corridor: {row['route_id']}<br/>
                    Observed Demand: <b>{row['predicted_demand']}</b> pcu/hr<br/>
                    Pressure Ratio: <b>{occupancy_ratio:.2f}</b><br/>
                    Alert Level: <b style="color: {color};">{row['alert_level']}</b><br/>
                    Recommendation: {row['action_recommended']}
                </div>
            """

            if row["alert_level"] in ["RED", "AMBER"]:
                folium.CircleMarker(
                    location=[row["latitude"], row["longitude"]],
                    radius=radius + 4,
                    color=color,
                    fill=False,
                    opacity=0.35,
                    weight=3,
                ).add_to(m)

            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.85,
                popup=folium.Popup(popup_html, max_width=280),
            ).add_to(m)

        if (
            len(df_hotspots) > 0
            and "hotspot_cluster" in df_hotspots.columns
            and df_hotspots["hotspot_cluster"].notnull().any()
        ):
            for cluster_id in df_hotspots["hotspot_cluster"].dropna().unique():
                cluster_stops = df_hotspots[df_hotspots["hotspot_cluster"] == cluster_id]
                if len(cluster_stops) >= 2:
                    coords = cluster_stops[["latitude", "longitude"]].values.tolist()
                    folium.PolyLine(
                        coords,
                        color="#8B5CF6",
                        weight=3,
                        opacity=0.7,
                        tooltip=f"Hotspot Cluster {int(cluster_id) + 1}",
                    ).add_to(m)

        st_folium(m, width=720, height=520, key="transit_map")
    else:
        st.info("No stops match the selected corridor filter.")

with col_table:
    st.subheader("Automated Dispatch Control Recommendations")

    if len(df_rec) > 0:
        display_df = df_rec[
            ["stop_name", "predicted_demand", "occupancy_ratio", "action_recommended", "alert_level"]
        ].sort_values(by="occupancy_ratio", ascending=False)

        def highlight_alert(val):
            if val == "RED":
                return "background-color: rgba(239, 68, 68, 0.2); color: #EF4444; font-weight: bold;"
            elif val == "AMBER":
                return "background-color: rgba(245, 158, 11, 0.2); color: #F59E0B; font-weight: bold;"
            elif val == "BLUE":
                return "background-color: rgba(59, 130, 246, 0.2); color: #3B82F6;"
            else:
                return "background-color: rgba(16, 185, 129, 0.2); color: #10B981;"

        st.dataframe(
            display_df.style.map(highlight_alert, subset=["alert_level"]),
            width='stretch',
            height=520,
        )
    else:
        st.info("No dispatch recommendations available.")

st.write("---")

# Real multi-year traffic history (DOR published counts per station)
st.subheader("Traffic History by Station (DOR Portal, Real Counts)")

route_demand = demand_df.copy()
if selected_route != "All Corridors":
    selected_stops = stops_df[stops_df["route_id"] == selected_route]["stop_id"].tolist()
    route_demand = route_demand[route_demand["stop_id"].isin(selected_stops)]

station_years = (
    route_demand.groupby(["stop_name", "timestamp"], as_index=False)["traffic_aadt_pcu"]
    .sum()
    .sort_values("timestamp")
)

fig = go.Figure()
for stop_name, series in station_years.groupby("stop_name"):
    fig.add_trace(go.Scatter(
        x=series["timestamp"],
        y=series["traffic_aadt_pcu"],
        mode="lines+markers",
        name=stop_name,
        line=dict(width=2),
    ))

fig.update_layout(
    title=f"Published Annual Average Daily Traffic (PCU) per Station - Corridor: {selected_route}",
    xaxis_title="Count Year",
    yaxis_title="AADT (PCU / day)",
    template="plotly_dark",
    margin=dict(l=40, r=40, t=60, b=40),
    height=480,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)

st.plotly_chart(fig, width='stretch')

st.caption(
    f"Data: Department of Roads (DOR) - Strategic Road Network (SSRN) public traffic "
    f"count portal, all published years (2011/12 .. {latest_year}). Real Annual Average "
    "Daily Traffic (AADT) in PCUs per official Kathmandu Valley count station. "
    "No synthetic data is used anywhere in this system."
)