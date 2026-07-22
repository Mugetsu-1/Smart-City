import os
import streamlit as st
import pandas as pd
import numpy as np
import folium
import joblib
import psycopg2
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go

# Append parent dir to path so we can import src modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.optimize import generate_schedule_recommendations

DB_CONN = "postgresql://postgres:postgrespassword@localhost:5432/transit_db"

st.set_page_config(
    layout="wide",
    page_title="Smart Transit Command Center",
    page_icon="🚌"
)

# Custom CSS for Premium Design
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Outfit', sans-serif;
        }
        
        .main-header {
            font-size: 2.8rem;
            font-weight: 800;
            background: linear-gradient(90deg, #FF4B4B 0%, #FF8F00 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.2rem;
        }
        
        .sub-header {
            font-size: 1.2rem;
            color: #6C757D;
            margin-bottom: 2rem;
        }
        
        .metric-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 1.5rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
            backdrop-filter: blur(8px);
        }
        
        .status-connected {
            color: #2ECC71;
            font-weight: bold;
        }
        
        .status-fallback {
            color: #F1C40F;
            font-weight: bold;
        }
    </style>
""", unsafe_allowed_html=True)

# ----------------- Database and Loading helpers -----------------
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
            query = "SELECT stop_id, stop_name, route_id, ST_Y(location) as latitude, ST_X(location) as longitude FROM bus_stops"
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            st.warning(f"Error loading stops from DB: {e}. Falling back to CSV.")
    
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
                    hc.precipitation_mm,
                    hc.temperature_c AS temp_c
                FROM mv_hourly_stop_demand mv
                LEFT JOIN hourly_context hc ON mv.demand_hour = hc.context_timestamp
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['is_weekend'] = (df['timestamp'].dt.dayofweek >= 5).astype(int)
            return df
        except Exception as e:
            st.warning(f"Error loading demand from DB: {e}. Falling back to CSV.")
            
    return pd.read_csv("data/synthetic_transit_demand.csv", parse_dates=['timestamp'])

# ----------------- UI -----------------

st.markdown("<div class='main-header'>🚌 Smart City Transit Optimization & Dispatch System</div>", unsafe_allowed_html=True)
st.markdown("<div class='sub-header'>Real-time passenger demand forecasting, spatial hotspot clustering, and automated schedule adjustments.</div>", unsafe_allowed_html=True)

# Connection Status
is_connected = check_db_connection()

# Sidebar Control Panel
st.sidebar.header("Control Panel")

if is_connected:
    st.sidebar.markdown("Database Status: <span class='status-connected'>● Connected to PostgreSQL</span>", unsafe_allowed_html=True)
    if st.sidebar.button("Refresh Materialized View"):
        if refresh_db_view():
            st.sidebar.success("Materialized view refreshed!")
            st.cache_data.clear()
else:
    st.sidebar.markdown("Database Status: <span class='status-fallback'>● Falling back to CSVs</span>", unsafe_allowed_html=True)

# Select Corridor and Forecast Slider
selected_route = st.sidebar.selectbox("Select Route Corridor", ["All Routes", "ROUTE_1", "ROUTE_2", "ROUTE_3"])
time_window = st.sidebar.slider("Forecast Hour Ahead", 1, 24, 1)

# Load stops and demand
stops_df = load_stops_data(is_connected)
demand_df = load_demand_data(is_connected)

# Model Prediction & Data Prep
model_loaded = False
model_path = "models/xgboost_transit_model.joblib"
feature_cols_path = "models/feature_cols.joblib"

if os.path.exists(model_path) and os.path.exists(feature_cols_path):
    try:
        model = joblib.load(model_path)
        feature_cols = joblib.load(feature_cols_path)
        model_loaded = True
    except Exception as e:
        st.sidebar.warning(f"Could not load model: {e}")

# Get the latest timestamp in the dataset
latest_timestamp = demand_df['timestamp'].max()

# Construct predicted data
if model_loaded:
    # Use actual XGBoost model predictions
    # To predict 'time_window' hours ahead:
    # We look at the latest records for each stop, and construct features for the target time.
    # Since lag features are based on previous hours, let's extract them from the dataset.
    target_time = latest_timestamp + pd.Timedelta(hours=time_window)
    
    # We construct features for the target time for each stop
    stops_features = []
    
    # Pre-process the full dataset to compute lags and rolling averages
    # We need a temporary df to compute features
    df_temp = demand_df.sort_values(['stop_id', 'timestamp']).copy()
    df_temp['hour'] = df_temp['timestamp'].dt.hour
    df_temp['dayofweek'] = df_temp['timestamp'].dt.dayofweek
    df_temp['month'] = df_temp['timestamp'].dt.month
    df_temp['is_peak'] = df_temp['hour'].isin([7, 8, 9, 17, 18, 19]).astype(int)
    
    # Lag Features per Stop
    df_temp['demand_lag_1h'] = df_temp.groupby('stop_id')['demand'].shift(1)
    df_temp['demand_lag_24h'] = df_temp.groupby('stop_id')['demand'].shift(24)
    df_temp['demand_lag_168h'] = df_temp.groupby('stop_id')['demand'].shift(168)
    
    # Rolling Averages
    df_temp['rolling_3h_mean'] = df_temp.groupby('stop_id')['demand_lag_1h'].transform(lambda x: x.rolling(3).mean())
    df_temp['rolling_24h_mean'] = df_temp.groupby('stop_id')['demand_lag_1h'].transform(lambda x: x.rolling(24).mean())
    
    # Find the features of the last hour for each stop and shift them to construct target features
    # Since we are predicting 'time_window' ahead:
    # For time_window=1, demand_lag_1h will be the actual demand at latest_timestamp
    # For simplicity, we grab the latest computed features and feed them to the model, adjusting the time components
    latest_features_df = df_temp[df_temp['timestamp'] == latest_timestamp].copy()
    
    if len(latest_features_df) > 0:
        latest_features_df['timestamp'] = target_time
        latest_features_df['hour'] = target_time.hour
        latest_features_df['dayofweek'] = target_time.dayofweek
        latest_features_df['month'] = target_time.month
        latest_features_df['is_peak'] = latest_features_df['hour'].isin([7, 8, 9, 17, 18, 19]).astype(int)
        latest_features_df['is_weekend'] = int(target_time.dayofweek >= 5)
        
        # Predict using model
        X_latest = latest_features_df[feature_cols]
        preds = model.predict(X_latest)
        latest_features_df['predicted_demand'] = np.clip(preds, 0, None)
        latest_data = latest_features_df[['stop_id', 'predicted_demand', 'demand']].copy()
    else:
        model_loaded = False
        
if not model_loaded:
    # Fallback to mock prediction as described in the PDF
    latest_data = demand_df[demand_df['timestamp'] == latest_timestamp].copy()
    # Mock prediction sample
    np.random.seed(42 + time_window) # Unique seed per hour window
    latest_data['predicted_demand'] = latest_data['demand'] * np.random.uniform(0.9, 1.1, size=len(latest_data))
    latest_data = latest_data[['stop_id', 'predicted_demand', 'demand']].copy()

# Generate schedule recommendations and hotspots
df_rec, df_hotspots = generate_schedule_recommendations(stops_df, latest_data)

# Filter by selected Route Corridor
if selected_route != "All Routes":
    df_rec = df_rec[df_rec['route_id'] == selected_route]
    if len(df_hotspots) > 0:
        df_hotspots = df_hotspots[df_hotspots['route_id'] == selected_route]

# ----------------- Metrics Section -----------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    total_demand = int(df_rec['predicted_demand'].sum())
    st.metric("Total System Demand", f"{total_demand:,} passengers")

with col2:
    avg_occupancy = int(df_rec['occupancy_ratio'].mean() * 100)
    st.metric("Average Bus Occupancy", f"{avg_occupancy}%")

with col3:
    critical_hotspots = len(df_rec[df_rec['alert_level'] == 'RED'])
    st.metric("Critical Hotspots (Red)", f"{critical_hotspots}")

with col4:
    underutilized = len(df_rec[df_rec['alert_level'] == 'GREEN'])
    st.metric("Underutilized Stops", f"{underutilized}")

st.write("---")

# ----------------- Visualizations: Map and Table -----------------
col_left, col_right = st.columns([7, 5])

with col_left:
    st.subheader("📍 Live Congestion & Route Heatmap")
    
    if len(df_rec) > 0:
        # Centering map around selected corridor's stops
        map_lat = df_rec['latitude'].mean()
        map_lon = df_rec['longitude'].mean()
        
        m = folium.Map(location=[map_lat, map_lon], zoom_start=12, tiles="cartodbpositron")
        
        # Color mapper
        color_map = {
            'RED': '#E74C3C',
            'AMBER': '#E67E22',
            'GREEN': '#3498DB',
            'NORMAL': '#2ECC71'
        }
        
        for idx, row in df_rec.iterrows():
            color = color_map.get(row['alert_level'], '#95A5A6')
            
            # Larger radius for higher occupancy ratio
            radius = 8 + (row['occupancy_ratio'] * 5)
            
            # Prepare pop-up content
            popup_html = f"""
                <div style="font-family: 'Outfit', sans-serif; font-size: 13px;">
                    <strong>{row['stop_name']}</strong><br/>
                    Route: {row['route_id']}<br/>
                    Predicted Demand: {row['predicted_demand']}<br/>
                    Occupancy Ratio: {row['occupancy_ratio']:.2f}<br/>
                    <b>Status: {row['alert_level']}</b>
                </div>
            """
            
            # Highlight hotspots with an extra pulsing effect (using double circles)
            if row['alert_level'] in ['RED', 'AMBER']:
                folium.CircleMarker(
                    location=[row['latitude'], row['longitude']],
                    radius=radius + 4,
                    color=color,
                    fill=False,
                    opacity=0.3,
                    weight=3
                ).add_to(m)
                
            folium.CircleMarker(
                location=[row['latitude'], row['longitude']],
                radius=radius,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.8,
                popup=folium.Popup(popup_html, max_width=250)
            ).add_to(m)
            
        # Draw clusters if any
        if len(df_hotspots) > 0 and 'hotspot_cluster' in df_hotspots.columns:
            # Group stops by cluster and draw a shaded polygon or markers connecting them
            for cluster_id in df_hotspots['hotspot_cluster'].dropna().unique():
                cluster_stops = df_hotspots[df_hotspots['hotspot_cluster'] == cluster_id]
                if len(cluster_stops) >= 2:
                    coords = cluster_stops[['latitude', 'longitude']].values.tolist()
                    # Draw a PolyLine connecting the hotspot stops in the cluster
                    folium.PolyLine(
                        coords,
                        color='#8E44AD',
                        weight=3,
                        opacity=0.6,
                        tooltip=f"Hotspot Cluster {int(cluster_id) + 1}"
                    ).add_to(m)
        
        st_folium(m, width=700, height=500, key="transit_map")
    else:
        st.info("No stops match the corridor filter.")

with col_right:
    st.subheader("⚡ Automated Dynamic Dispatch Recommendations")
    
    if len(df_rec) > 0:
        # Select columns to display
        display_df = df_rec[['stop_id', 'stop_name', 'predicted_demand', 'occupancy_ratio', 'action_recommended', 'alert_level']]
        display_df = display_df.sort_values(by='occupancy_ratio', ascending=False)
        
        # Color coding rows using Streamlit's dataframe formatting
        def color_alert(val):
            if val == 'RED':
                return 'background-color: rgba(231, 76, 60, 0.2); color: #E74C3C; font-weight: bold;'
            elif val == 'AMBER':
                return 'background-color: rgba(230, 126, 34, 0.2); color: #E67E22;'
            elif val == 'GREEN':
                return 'background-color: rgba(52, 152, 219, 0.2); color: #3498DB;'
            else:
                return 'color: #2ECC71;'
                
        st.dataframe(
            display_df.style.applymap(color_alert, subset=['alert_level']),
            use_container_width=True,
            height=500
        )
    else:
        st.info("No recommendations generated.")

st.write("---")

# ----------------- Historical Trend & Forecast Chart -----------------
st.subheader("📈 Demand Over Time & Prediction Analysis")

# Get aggregated demand for the route corridor
route_demand = demand_df.copy()
if selected_route != "All Routes":
    # Get stop_ids for selected route
    selected_stops = stops_df[stops_df['route_id'] == selected_route]['stop_id'].tolist()
    route_demand = route_demand[route_demand['stop_id'].isin(selected_stops)]

# Group by timestamp to show overall corridor demand over time
time_demand = route_demand.groupby('timestamp')['demand'].sum().reset_index()

# Plot last 7 days of data for cleaner visualization
last_seven_days = time_demand.tail(24 * 7)

fig = go.Figure()

# Add Historical Line
fig.add_trace(go.Scatter(
    x=last_seven_days['timestamp'], 
    y=last_seven_days['demand'],
    mode='lines',
    name='Historical Demand',
    line=dict(color='#3498DB', width=2)
))

# Add Prediction Point
if len(df_rec) > 0:
    pred_time = latest_timestamp + pd.Timedelta(hours=time_window)
    fig.add_trace(go.Scatter(
        x=[pred_time],
        y=[total_demand],
        mode='markers+text',
        name='Future Forecast',
        text=[f"Forecast: {total_demand}"],
        textposition="top center",
        marker=dict(color='#FF4B4B', size=12, symbol='star')
    ))

fig.update_layout(
    title=f"Passenger Demand Trend (Corridor: {selected_route})",
    xaxis_title="Time",
    yaxis_title="Total Passengers / Hour",
    template="plotly_dark",
    margin=dict(l=40, r=40, t=40, b=40),
    height=400
)

st.plotly_chart(fig, use_container_width=True)
