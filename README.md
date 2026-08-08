# Smart City: Dynamic Transit Scheduling and Route Optimization in Nepal

An enterprise-grade data science and geospatial engineering system that transforms static urban transit timetables into an adaptive dynamic dispatch network for the Kathmandu Valley, Nepal — powered exclusively by **real government traffic data**.

## The Core Problem
Public transit in growing metropolitan areas like the Kathmandu Valley is dangerously overcrowded during peak commute hours, yet runs empty off-peak, wasting fuel, escalating operational costs, and causing severe driver burnout.

## The Solution
This project ingests **real traffic counts from the Nepal Department of Roads (DOR) SSRN public traffic portal** for 21 official Kathmandu Valley count stations, computes pressure ratios against stop capacity, identifies spatial congestion hotspots via K-Means clustering, and automatically issues dispatch instructions to transit authorities.

## Live Status — NO synthetic data
- Data source: **Department of Roads (DOR) `ssrn.dor.gov.np`** — real Annual Average Daily Traffic (AADT) in PCUs per station.
- The full **multi-year series (2011/12 – 2024/25)** is scraped from each station's official detail page; the operational snapshot uses **each station's most recently published count** (2024/25).
- Data is cached as real CSV snapshots (`data/dor_traffic_demand.csv`, `data/dor_traffic_stops.csv`); the dashboard refreshes automatically and can force a fresh scrape from the portal.
- **No synthetic or fabricated demand values exist anywhere in this system.**

## Repository Structure

```
smart_city_transit/
├── docker-compose.yml       # Optional PostgreSQL + PostGIS stack
├── requirements.txt         # Project Python dependencies
├── README.md                # Project documentation and quickstart guide
├── system_architecture.md   # Architectural design document
├── project_description.md   # Project purpose, data overview, and stakeholder benefits
├── run.py                   # Master execution script for the real-data pipeline
├── sql/
│   └── schema.sql           # PostGIS schema and spatial indexes
├── src/
│   ├── generate_data.py     # Scrapes the real DOR portal and persists snapshots
│   ├── data_feeds.py        # Real DOR portal feed + local snapshot cache logic
│   ├── optimize.py          # Occupancy calculations, K-Means clustering, dispatch rules
│   └── test_optimize.py     # Optimization engine verification test (real data)
├── data/
│   ├── dor_traffic_stops.csv    # 21 real DOR Kathmandu Valley stations
│   └── dor_traffic_demand.csv    # Real AADT traffic counts per station
└── app/
    └── app.py               # Streamlit Command Center Interactive Dashboard
```

## Key Kathmandu Corridors Covered (real DOR stations)
- **Ring Road Corridor**: Manohara Bridge, Balkhu East, Sinamangal, Narayan Gopal Chowk, Banasthali, Balaju Bypass, Kalanki
- **Ratna Park - Lagankhel Corridor**: Satdobato North, Satdobato Junction, Satdobato South, Gwarko, Byasi Chowk
- **Chabahil - Jorpati Corridor**: Chabahil East, Jorpati North, Gangalal Hospital
- **Tribhuvan Rajpath Corridor**: Taudaha, Nagdhunga
- **Arniko Highway Corridor**: Manohara Bridge, Kharipati, Hanumante Bridge

## Quickstart Guide

### 1. Environment Setup
```bash
.venv\Scripts\pip.exe install -r requirements.txt
```

### 2. Fetch Real Data & Test the Pipeline
```bash
.venv\Scripts\python.exe run.py
```
This scrapes the DOR portal, saves the real CSV snapshots (and optionally ingests into PostgreSQL/PostGIS if running), then tests the schedule optimization engine on the real traffic counts.

### 3. Launch the Streamlit Control Center
```bash
.venv\Scripts\streamlit.exe run app/app.py
```
Open `http://localhost:8501` to view the interactive map, KPI metrics, dispatch control table, live operational snapshot, and per-station traffic charts.

## Data Sources
- **Department of Roads (DOR) — SSRN public traffic portal**: `https://ssrn.dor.gov.np/traffic_controller` (real AADT counts in PCUs, all published years 2011/12 – 2024/25)
- **OpenStreetMap Nominatim**: geocoding for the real station names
- Optional Mirror: PostgreSQL / PostGIS (same real data, ingested in `dor_traffic_demand`)