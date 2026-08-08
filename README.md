# Smart City: Dynamic Transit Scheduling and Route Optimization in Nepal

An enterprise-grade data science and geospatial engineering system that transforms static urban transit timetables into an adaptive dynamic dispatch network for the Kathmandu Valley, Nepal — powered exclusively by **real government traffic data**.

## The Core Problem
Public transit in growing metropolitan areas like the Kathmandu Valley is dangerously overcrowded during peak commute hours, yet runs empty off-peak, wasting fuel, escalating operational costs, and causing severe driver burnout.

## The Solution
This project ingests **real traffic counts from the Nepal Department of Roads (DOR) SSRN public traffic portal** for 21 official Kathmandu Valley count stations, computes pressure ratios against stop capacity, identifies spatial congestion hotspots via K-Means clustering, and automatically issues dispatch instructions to transit authorities.

## Live Status — NO synthetic data
- Data source: **Department of Roads (DOR) `ssrn.dor.gov.np`** — real Annual Average Daily Traffic (AADT) in PCUs per station.
- The full **multi-year series (2011/12 – 2024/25)** is scraped live from each station's official detail page **on every app launch**; the operational snapshot uses **each station's most recently published count** (2024/25).
- A per-station **trend model forecasts the next published count window** (`src/forecast.py`) — e.g. 2024/25 → 2026/27 — trained only on the real published yearly counts.
- Real CSV snapshots (`data/dor_traffic_demand.csv`, `data/dor_traffic_stops.csv`) are written after every successful scrape; if the portal is unreachable the dashboard falls back to the last snapshot and shows an explicit OFFLINE badge.
- **No synthetic or fabricated demand values exist anywhere in this system.**

## Repository Structure

```
smart_city_transit/
├── docker-compose.yml       # Optional PostgreSQL + PostGIS stack
├── requirements.txt         # Project Python dependencies
├── README.md                # Project documentation and quickstart guide
├── system_architecture.md   # Architectural design document
├── project_description.md   # Project purpose, data overview, and stakeholder benefits
├── run.py                   # Master execution script: full real-data pipeline
├── sql/
│   └── schema.sql           # PostGIS schema and spatial indexes
├── src/
│   ├── generate_data.py     # Live-scrapes the real DOR portal, persists snapshots, optional DB ingest
│   ├── data_feeds.py        # Real DOR portal live feed + offline snapshot fallback
│   ├── forecast.py          # Per-station trend forecast of the next published window (real counts only)
│   ├── optimize.py          # Occupancy calculations, K-Means clustering, dispatch rules
│   └── test_optimize.py     # Optimization engine verification test (real data)
├── data/
│   ├── dor_traffic_stops.csv    # 21 real DOR Kathmandu Valley stations
│   └── dor_traffic_demand.csv   # Real AADT traffic counts per station
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
This live-scrapes the DOR portal (STEP 1), saves the real CSV snapshots (and optionally ingests into PostgreSQL/PostGIS if running), runs the real-count demand forecast for the next count window (STEP 2), and tests the schedule optimization engine on the real traffic counts (STEP 3).

### 3. Launch the Streamlit Control Center
```bash
.venv\Scripts\streamlit.exe run app/app.py
```
Open `http://localhost:8501` to view the interactive map, KPI metrics, dispatch control table, live operational snapshot, per-station traffic charts with a dashed forecast extension, and the next-window forecast panel. On startup the app live-scrapes the DOR portal (parallel, ~30s); use *Scrape DOR Portal Now* in the sidebar to re-scrape on demand.

## Data Sources
- **Department of Roads (DOR) — SSRN public traffic portal**: `https://ssrn.dor.gov.np/traffic_controller` (real AADT counts in PCUs, all published years 2011/12 – 2024/25)
- Offline fallback: real CSV snapshots written at each successful scrape (`data/dor_traffic_demand.csv`, `data/dor_traffic_stops.csv`)
- Optional Mirror: PostgreSQL / PostGIS (same real data, ingested in `dor_traffic_demand`)