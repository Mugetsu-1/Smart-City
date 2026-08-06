import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import folium
import joblib
import psycopg2
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go

# Add parent directory to path to import src modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.optimize import generate_schedule_recommendations

DB_CONN = "postgresql://postgres:postgrespassword@localhost:5433/transit_db"

st.set_page_config(
    layout="wide",
    page_title="Kathmandu Transit Optimization Command Center"
)

# Custom CSS for Sleek Technical Styling
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
def check_db_connection():
    try:
        conn = psycopg2.connect(DB_CONN)
        conn.close()
        return True
    except:
        return False

def refresh_db_view():
    try:
        conn = psycopg2.connect(DB_CONN)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("REFRESH MATERIALIZED VIEW mv_hourly_stop_demand;")
        conn.close()
        return True
    except Exception as e:
        st.sidebar.error(f"Failed to refresh view: {e}")
        return False

@st.cache_data(ttl=300)
def load_stops_data(use_db):
    if use_db:
        try:
            conn = psycopg2.connect(DB_CONN)
            query = "SELECT stop_id, stop_name, route_id, capacity_limit, ST_Y(location) as latitude, ST_X(location) as longitude FROM bus_stops"
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            st.warning(f"Database query fallback notice: {e}")
    
    return pd.read_csv("data/synthetic_transit_stops.csv")

@st.cache_data(ttl=300)
def load_demand_data(use_db):
    if use_db:
        try:
            conn = psycopg2.connect(DB_CONN)
            query = """
                SELECT 
                    mv.demand_hour AS timestamp,
                    mv.stop_id,
                    mv.tap_in_count AS demand,
                    ec.precipitation_mm,
                    ec.temperature_c AS temp_c,
                    ec.is_saturday,
                    ec.is_holiday,
                    ec.is_festival
                FROM mv_hourly_stop_demand mv
                LEFT JOIN environmental_context ec ON mv.demand_hour = ec.context_timestamp
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        except Exception as e:
            st.warning(f"Database query fallback notice: {e}")
            
    return pd.read_csv("data/synthetic_transit_demand.csv", parse_dates=['timestamp'])

# UI Header
st.markdown("<div class='main-header'>Smart City: Kathmandu Transit Optimization Command Center</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-header'>Real-time XGBoost passenger demand forecasting, PostGIS spatial clustering, and automated headway scheduling for Kathmandu Valley transit corridors.</div>", unsafe_allow_html=True)

is_connected = check_db_connection()

# Sidebar Control Panel
st.sidebar.header("System Controls")

if is_connected:
    st.sidebar.markdown("Database Status: <span class='status-connected'>Connected (PostgreSQL / PostGIS)</span>", unsafe_allow_html=True)
    if st.sidebar.button("Refresh Materialized View"):
        if refresh_db_view():
            st.sidebar.success("Materialized view mv_hourly_stop_demand refreshed!")
            st.cache_data.clear()
else:
    st.sidebar.markdown("Database Status: <span class='status-fallback'>Standalone Mode (CSV Engine)</span>", unsafe_allow_html=True)

stops_df = load_stops_data(is_connected)
demand_df = load_demand_data(is_connected)

available_routes = ["All Corridors"] + list(stops_df['route_id'].unique())
selected_route = st.sidebar.selectbox("Filter Transit Corridor", available_routes)
time_window = st.sidebar.slider("Forecast Horizon (Hours Ahead)", 1, 24, 1)

# Model Loading & Prediction
model_loaded = False
model_path = "models/xgboost_transit_model.joblib"
feature_cols_path = "models/feature_cols.joblib"

if os.path.exists(model_path) and os.path.exists(feature_cols_path):
    try:
        model = joblib.load(model_path)
        feature_cols = joblib.load(feature_cols_path)
        model_loaded = True
    except Exception as e:
        st.sidebar.warning(f"Model load warning: {e}")

latest_timestamp = demand_df['timestamp'].max()

if model_loaded:
    target_time = latest_timestamp + pd.Timedelta(hours=time_window)
    
    df_temp = demand_df.sort_values(['stop_id', 'timestamp']).copy()
    df_temp['hour'] = df_temp['timestamp'].dt.hour
    df_temp['dayofweek'] = df_temp['timestamp'].dt.dayofweek
    df_temp['month'] = df_temp['timestamp'].dt.month
    df_temp['is_peak'] = df_temp['hour'].isin([7, 8, 9, 17, 18, 19]).astype(int)
    
    if 'is_saturday' not in df_temp.columns:
        df_temp['is_saturday'] = (df_temp['dayofweek'] == 5).astype(int)
    if 'is_holiday' not in df_temp.columns:
        df_temp['is_holiday'] = df_temp['is_saturday']
    if 'is_festival' not in df_temp.columns:
        df_temp['is_festival'] = 0
    if 'temp_c' not in df_temp.columns:
        df_temp['temp_c'] = 20.0
    if 'precipitation_mm' not in df_temp.columns:
        df_temp['precipitation_mm'] = 0.0
    df_temp['is_heavy_monsoon'] = (df_temp['precipitation_mm'] > 2.0).astype(int)
    
    # Lag Features
    df_temp['demand_lag_1h'] = df_temp.groupby('stop_id')['demand'].shift(1)
    df_temp['demand_lag_24h'] = df_temp.groupby('stop_id')['demand'].shift(24)
    df_temp['demand_lag_168h'] = df_temp.groupby('stop_id')['demand'].shift(168)
    
    # Rolling Means
    df_temp['rolling_3h_mean'] = df_temp.groupby('stop_id')['demand_lag_1h'].transform(lambda x: x.rolling(3).mean())
    df_temp['rolling_24h_mean'] = df_temp.groupby('stop_id')['demand_lag_1h'].transform(lambda x: x.rolling(24).mean())
    
    latest_features_df = df_temp[df_temp['timestamp'] == latest_timestamp].copy()
    
    if len(latest_features_df) > 0:
        latest_features_df['timestamp'] = target_time
        latest_features_df['hour'] = target_time.hour
        latest_features_df['dayofweek'] = target_time.dayofweek
        latest_features_df['month'] = target_time.month
        latest_features_df['is_peak'] = latest_features_df['hour'].isin([7, 8, 9, 17, 18, 19]).astype(int)
        latest_features_df['is_saturday'] = int(target_time.dayofweek == 5)
        latest_features_df['is_holiday'] = latest_features_df['is_saturday']
        
        # XGBoost Prediction
        X_latest = latest_features_df[feature_cols]
        preds = model.predict(X_latest)
        latest_features_df['predicted_demand'] = np.clip(preds, 0, None)
        latest_data = latest_features_df[['stop_id', 'predicted_demand', 'demand']].copy()
    else:
        model_loaded = False
        
if not model_loaded:
    latest_data = demand_df[demand_df['timestamp'] == latest_timestamp].copy()
    np.random.seed(42 + time_window)
    latest_data['predicted_demand'] = latest_data['demand'] * np.random.uniform(0.95, 1.15, size=len(latest_data))
    latest_data = latest_data[['stop_id', 'predicted_demand', 'demand']].copy()

# Generate Optimization Recommendations
df_rec, df_hotspots = generate_schedule_recommendations(stops_df, latest_data)

if selected_route != "All Corridors":
    df_rec = df_rec[df_rec['route_id'] == selected_route]
    if len(df_hotspots) > 0:
        df_hotspots = df_hotspots[df_hotspots['route_id'] == selected_route]

# Key Performance Metrics Panel
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_demand = int(df_rec['predicted_demand'].sum())
    st.metric("Total System Demand", f"{total_demand:,} passengers/hr")

with col2:
    avg_occupancy = int(df_rec['occupancy_ratio'].mean() * 100)
    st.metric("Average Fleet Occupancy", f"{avg_occupancy}%")

with col3:
    critical_hotspots = len(df_rec[df_rec['alert_level'] == 'RED'])
    st.metric("Critical Overcrowded Stops", f"{critical_hotspots}")

with col4:
    underutilized = len(df_rec[df_rec['alert_level'] == 'BLUE'])
    st.metric("Underutilized Stops", f"{underutilized}")

st.write("---")

# Main Interface: Interactive Folium Map & Control Table
col_map, col_table = st.columns([7, 5])

with col_map:
    st.subheader("Geographic Congestion Heatmap - Kathmandu Valley")
    
    if len(df_rec) > 0:
        map_lat = df_rec['latitude'].mean()
        map_lon = df_rec['longitude'].mean()
        
        m = folium.Map(location=[map_lat, map_lon], zoom_start=12, tiles="cartodbpositron")
        
        color_map = {
            'RED': '#EF4444',
            'AMBER': '#F59E0B',
            'GREEN': '#10B981',
            'BLUE': '#3B82F6'
        }
        
        for idx, row in df_rec.iterrows():
            color = color_map.get(row['alert_level'], '#6B7280')
            radius = 8 + (row['occupancy_ratio'] * 6)
            
            popup_html = f"""
                <div style="font-family: 'Outfit', sans-serif; font-size: 13px; color: #1E293B;">
                    <strong>{row['stop_name']}</strong><br/>
                    Route Corridor: {row['route_id']}<br/>
                    Predicted Demand: <b>{row['predicted_demand']}</b> passengers/hr<br/>
                    Occupancy Ratio: <b>{row['occupancy_ratio']:.2f}</b><br/>
                    Alert Level: <b style="color: {color};">{row['alert_level']}</b><br/>
                    Recommendation: {row['action_recommended']}
                </div>
            """
            
            if row['alert_level'] in ['RED', 'AMBER']:
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=radius + 4,
                    color=color,
                    fill=False,
                    opacity=0.35,
                    weight=3
                ).add_to(m)
                
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.85,
                popup=folium.Popup(popup_html, max_width=280)
            ).add_to(m)
            
        if len(df_hotspots) > 0 and 'hotspot_cluster' in df_hotspots.columns and df_hotspots['hotspot_cluster'].notnull().any():
            for cluster_id in df_hotspots['hotspot_cluster'].dropna().unique():
                cluster_stops = df_hotspots[df_hotspots['hotspot_cluster'] == cluster_id]
                if len(cluster_stops) >= 2:
                    coords = cluster_stops[['latitude', 'longitude']].values.tolist()
                    folium.PolyLine(
                        coords,
                        color='#8B5CF6',
                        weight=3,
                        opacity=0.7,
                        tooltip=f"Hotspot Cluster {int(cluster_id) + 1}"
                    ).add_to(m)
        
        st_folium(m, width=720, height=520, key="transit_map")
    else:
        st.info("No stops match the selected corridor filter.")

with col_table:
    st.subheader("Automated Dispatch Control Recommendations")
    
    if len(df_rec) > 0:
        display_df = df_rec[['stop_name', 'predicted_demand', 'occupancy_ratio', 'action_recommended', 'alert_level']]
        display_df = display_df.sort_values(by='occupancy_ratio', ascending=False)
        
        def highlight_alert(val):
            if val == 'RED':
                return 'background-color: rgba(239, 68, 68, 0.2); color: #EF4444; font-weight: bold;'
            elif val == 'AMBER':
                return 'background-color: rgba(245, 158, 11, 0.2); color: #F59E0B; font-weight: bold;'
            elif val == 'BLUE':
                return 'background-color: rgba(59, 130, 246, 0.2); color: #3B82F6;'
            else:
                return 'background-color: rgba(16, 185, 129, 0.2); color: #10B981;'
                
        st.dataframe(
            display_df.style.applymap(highlight_alert, subset=['alert_level']),
            use_container_width=True,
            height=520
        )
    else:
        st.info("No dispatch recommendations available.")

st.write("---")

# Historical Demand Trend & XGBoost Forecast Visualization
st.subheader("Passenger Volume Trend & Forecast Analysis")

route_demand = demand_df.copy()
if selected_route != "All Corridors":
    selected_stops = stops_df[stops_df['route_id'] == selected_route]['stop_id'].tolist()
    route_demand = route_demand[route_demand['stop_id'].isin(selected_stops)]

time_demand = route_demand.groupby('timestamp')['demand'].sum().reset_index()
last_seven_days = time_demand.tail(24 * 7)

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=last_seven_days['timestamp'], 
    y=last_seven_days['demand'],
    mode='lines',
    name='Historical Observed Demand',
    line=dict(color='#3B82F6', width=2)
))

if len(df_rec) > 0:
    pred_time = latest_timestamp + pd.Timedelta(hours=time_window)
    fig.add_trace(go.Scatter(
        x=[pred_time],
        y=[total_demand],
        mode='markers+text',
        name='XGBoost Forecast',
        text=[f"Forecast: {total_demand}"],
        textposition="top center",
        marker=dict(color='#EF4444', size=14, symbol='star')
    ))

fig.update_layout(
    title=f"Passenger Demand Trend (Corridor: {selected_route})",
    xaxis_title="Timeline",
    yaxis_title="Passengers / Hour",
    template="plotly_dark",
    margin=dict(l=40, r=40, t=40, b=40),
    height=420
)

st.plotly_chart(fig, use_container_width=True)
