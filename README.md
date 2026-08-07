# Smart City: Dynamic Transit Scheduling and Route Optimization in Nepal

An enterprise-grade data science, geospatial engineering, and machine learning system that transforms static urban transit timetables into an adaptive dynamic dispatch network for the Kathmandu Valley, Nepal.

## The Core Problem
Public transit buses in growing metropolitan areas like the Kathmandu Valley are dangerously overcrowded during peak commute hours, yet run completely empty off-peak, wasting fuel, escalating operational costs, and causing severe driver burnout.

## The Solution
This project ingests real Kathmandu transit network data and live weather inputs, forecasts passenger demand 1 to 24 hours in advance using XGBoost, identifies spatial congestion hotspots via K-Means clustering, and automatically issues dispatch instructions to transit authorities.

## Live Status
This is a **hybrid real-time transit command center**:
- Real Kathmandu transit network geometry is loaded from the Yatayat/OpenStreetMap export.
- Weather is pulled from the Department of Hydrology and Meteorology.
- The dashboard refreshes automatically.
- Passenger-demand forecasting still uses the best available modeled historical demand layer until a live operator telemetry feed is connected.

## Repository Structure

```
smart_city_transit/
├── docker-compose.yml       # PostgreSQL 15 & PostGIS database stack definition
├── requirements.txt         # Project Python dependencies
├── README.md                # Project documentation and quickstart guide
├── system_architecture.md   # Architectural design document
├── project_description.md   # Project purpose, data overview, and stakeholder benefits
├── run.py                   # Master execution script for complete pipeline
├── sql/
│   └── schema.sql           # PostGIS schema, indexes, and materialized view definitions
├── src/
│   ├── fetch_real_nepal_data.py  # Downloads Kathmandu transit network data and weather snapshot
│   ├── generate_data.py          # Modeled fallback dataset generator and DB ingestor
│   ├── data_feeds.py             # Real/live/modeled feed loader with priority order
│   ├── train_model.py            # Nepal feature engineering and XGBoost training pipeline
│   ├── optimize.py               # Occupancy calculations, K-Means clustering, and dispatch rules
│   └── test_optimize.py          # Optimization engine verification test script
└── app/
    └── app.py               # Streamlit Command Center Interactive Dashboard
```

## Key Kathmandu Corridors Covered
- **Ring Road Corridor**: Gongabu, Maharajgunj, Chabahil, Gaushala, Koteshwor, Satdobato, Balkhu, Kalanki, Swayambhu, Balaju
- **Ratna Park - Lagankhel Corridor**: Ratna Park, Lainchaur, Maitighar, Thapathali, Kupondole, Pulchowk, Jawalakhel, Lagankhel
- **Arniko Highway Corridor**: New Baneshwor, Tinkune, Jadibuti, Lokanthali, Kaushaltar, Gatthaghar, Suryabinayak
- **Tribhuvan Rajpath Corridor**: Kalanki Central, Gurjudhara, Thankot, Nagdhunga
- **Chabahil - Jorpati Corridor**: Jorpati Chowk

## Quickstart Guide

### 1. Environment Setup
Install required Python dependencies:
```bash
.venv\Scripts\pip.exe install -r requirements.txt
```

### 2. Execute Data Generation & Model Training Pipeline
Run the master script to generate the modeled fallback dataset if needed, set up PostgreSQL/PostGIS schema (or CSV fallback), train the XGBoost demand forecasting model, and test the schedule optimization engine:
```bash
.venv\Scripts\python.exe run.py
```

### 3. Launch the Streamlit Control Center
Start the interactive command center dashboard:
```bash
.venv\Scripts\streamlit.exe run app/app.py
```
Open `http://localhost:8501` in your browser to view the interactive map, KPI metrics, dispatch control table, live operational snapshot, and forecast trend charts.

## Real Feed Drop-In
If you have a live Nepal operator feed, place a CSV at one of these paths and the app will pick it up automatically:
- `data/live_operator_demand.csv`
- `data/live_demand.csv`

Required columns:
- `timestamp`
- `stop_id`
- `demand`

Optional columns:
- `temperature_c` or `temp_c`
- `precipitation_mm`
- `is_saturday`
- `is_holiday`
- `is_festival`
