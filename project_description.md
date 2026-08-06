# Project Description: Smart City - Dynamic Transit Scheduling and Route Optimization in Nepal

## 1. The Fundamental Urban Problem
Public transit networks in rapidly growing urban centers like the Kathmandu Valley face a critical operational dilemma: buses are dangerously overcrowded during morning and evening peak commute hours, yet run completely empty during off-peak windows, incurring massive fuel waste and driver burnout. 

Traditional public transit systems rely on rigid, fixed bus timetables published months in advance that cannot adapt to real-time fluctuations, extreme weather events like monsoon rains, or sudden demand spikes during festival seasons (such as Dashain and Tihar).

## 2. The Core Objective
This project builds an enterprise-grade, data-driven dynamic dispatch system titled **"Smart City: Dynamic Transit Scheduling and Route Optimization in Nepal"**. The system replaces static timetables with an adaptive intelligent network that forecasts passenger demand 1 to 24 hours in advance and automatically recommends real-time fleet adjustments.

## 3. How the System Solves the Problem

1. **Ingest Telemetry (Data Engineering)**:
   Collects live and historical data—including passenger tap card swipes, bus GPS coordinates, vehicle occupancy, and weather metrics—and structures it using PostgreSQL and PostGIS with GIST spatial indexing and materialized view aggregations (`mv_hourly_stop_demand`).

2. **Forecast Demand (Machine Learning)**:
   Employs an XGBoost regression model trained on temporal encodings, Nepal calendar features (Saturday weekend structure, Dashain/Tihar festival surges), monsoon precipitation indicators (>2.0 mm/hr), and multi-horizon time-series lags (1h, 24h, 168h, rolling means) to forecast hourly passenger volume per stop.

3. **Identify Bottlenecks (Spatial Optimization)**:
   Applies spatial clustering (K-Means / DBSCAN) on stop spatial coordinates weighted by predicted demand to group localized overcrowding hotspots along major Nepal transit corridors.

4. **Automate Fleet Dispatch (Decision Layer)**:
   Calculates vehicle occupancy ratios against Nepal transit vehicle bounds (15-20 microbus vs 40-60 Sajha Yatayat bus) and outputs automated dispatch instructions (e.g., "Critical Overcrowding at Kalanki: Inject 2 short-turn express buses toward Ratna Park and reduce headway by 5 minutes").

5. **Visualize Operations (Dashboard)**:
   Provides a real-time Streamlit Command Center displaying system health metrics, color-coded Folium spatial heatmaps, sortable dispatch recommendation tables, and Plotly demand trend charts.

## 4. Who Benefits and Why It Matters

- **For Commuters**: Shorter wait times at bus stops, safer passenger density, and reliable, predictable travel times across major corridors (Ring Road, Ratna Park - Lagankhel, Arniko Highway, Tribhuvan Rajpath).
- **For Transit Operations**: Reduced fuel consumption, minimized driver burnout, and optimal fleet utilization without purchasing additional vehicles.
- **For the City**: Reduced urban traffic congestion, lower carbon emissions, and enhanced economic productivity by making public transport a dependable alternative to private vehicles.
