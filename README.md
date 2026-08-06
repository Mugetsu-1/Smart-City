# Smart City: Dynamic Transit Scheduling and Route Optimization in Nepal

An enterprise-grade data science, geospatial engineering, and machine learning system that transforms static urban transit timetables into an adaptive dynamic dispatch network for the Kathmandu Valley, Nepal.

## The Core Problem
Public transit buses in growing metropolitan areas like the Kathmandu Valley are dangerously overcrowded during peak commute hours, yet run completely empty off-peak, wasting fuel, escalating operational costs, and causing severe driver burnout.

## The Solution
This project ingests transit telemetry, forecasts passenger demand 1 to 24 hours in advance using XGBoost, identifies spatial congestion hotspots via K-Means clustering, and automatically issues real-time fleet dispatch instructions to transit authorities.

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
│   ├── generate_data.py     # Kathmandu synthetic dataset generator and DB ingestor
│   ├── train_model.py       # Nepal feature engineering and XGBoost training pipeline
│   ├── optimize.py          # Occupancy calculations, K-Means clustering, and dispatch rules
│   └── test_optimize.py     # Optimization engine verification test script
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
Run the master script to generate the synthetic Kathmandu dataset, set up PostgreSQL/PostGIS schema (or CSV fallback), train the XGBoost demand forecasting model, and test the schedule optimization engine:
```bash
.venv\Scripts\python.exe run.py
```

### 3. Launch the Streamlit Control Center
Start the interactive command center dashboard:
```bash
.venv\Scripts\streamlit.exe run app/app.py
```
Open `http://localhost:8501` in your browser to view the interactive map, KPI metrics, dispatch control table, and forecast trend charts.
