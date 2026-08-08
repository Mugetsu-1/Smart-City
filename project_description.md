# Project Description: Smart City - Dynamic Transit Scheduling and Route Optimization in Nepal

## 1. The Fundamental Urban Problem
Public transit networks in rapidly growing urban centers like the Kathmandu Valley face a critical operational dilemma: buses are dangerously overcrowded during morning and evening peak commute hours, yet run completely empty during off-peak windows, incurring massive fuel waste and driver burnout.

Traditional public transit systems rely on rigid, fixed bus timetables published months in advance that cannot adapt to real-time fluctuations in demand on the valley's arterial roads.

## 2. The Core Objective
This project builds an enterprise-grade, data-driven dynamic dispatch system titled **"Smart City: Dynamic Transit Scheduling and Route Optimization in Nepal"**. The system replaces static timetables with an adaptive network that reads **real traffic counts from the Nepal Department of Roads (DOR)** and automatically recommends fleet adjustments.

The implementation is a **real-data system - no synthetic data**:
- Real Kathmandu traffic counts come from the **DOR SSRN public traffic portal** (`ssrn.dor.gov.np`) — 21 official Kathmandu Valley count stations with Annual Average Daily Traffic (AADT) figures in PCUs.
- The current operational snapshot is the real count year published by the government (2011/12 fiscal year).
- The dashboard reads the real snapshot (CSV cache refreshed from the portal), and can re-scrape the portal on demand.

## 3. How the System Solves the Problem

1. **Ingest Real Telemetry (Data Engineering)**:
   Scrapes the DOR traffic portal for every official Kathmandu Valley count station, parses the AADT tables, geocodes each real station with OpenStreetMap, and persists real CSV snapshots (`data/dor_traffic_demand.csv`, `data/dor_traffic_stops.csv`). A PostgreSQL/PostGIS mirror (optional) holds the same real data row-for-row.

2. **Compute Real Traffic Demand**:
   Converts the real AADT figures into a per-hour junction load (pcu/hr) per station. Each station is assigned a capacity tier derived from its real observed AADT ranking — no fabricated values.

3. **Identify Bottlenecks (Spatial Optimization)**:
   Applies demand-weighted spatial clustering (K-Means) on the real station coordinates to group localized overcrowding hotspots along the real transit corridors.

4. **Automate Fleet Dispatch (Decision Layer)**:
   Calculates junction pressure ratios (observed hourly load vs. capacity) and outputs concrete, bilingual dispatch instructions (e.g., "CRITICAL OVERCROWDING at Kalanki: Inject 2 short-turn express buses toward Ratna Park and reduce headway by 5 minutes").

5. **Visualize Operations (Dashboard)**:
   Streamlit Command Center featuring a color-coded Folium heatmap of the real stations, KPI cards, sortable dispatch tables, the live operational snapshot, and per-station traffic charts.

## 4. Who Benefits and Why It Matters

- **For Commuters**: Shorter wait times at bus stops and safer passenger density across the real corridors (Ring Road, Ratna Park - Lagankhel, Chabahil - Jorpati, Tribhuvan Rajpath, Arniko Highway).
- **For Transit Operations**: Reduced fuel consumption, minimized driver burnout, and optimal fleet utilization without purchasing additional vehicles.
- **For the City**: Reduced urban traffic congestion and lower carbon emissions by making public transport a dependable alternative to private vehicles.

## 5. Data Provenance
| Field | Value |
|-------|-------|
| Primary source | Nepal Department of Roads (DOR) — Strategic Road Network (SSRN) traffic controllers portal |
| Portal URL | https://ssrn.dor.gov.np/traffic_controller |
| Data type | Annual Average Daily Traffic (AADT), incl./excl. MC & rickshaws, in PCUs, per station, per year |
| Stations modelled | 21 official Kathmandu Valley count stations |
| Latest published year | 2011/12 (as published by the portal) |
| Geocoding | OpenStreetMap Nominatim (with curated real reference coordinates as fallback) |
| Synthetic data | None. No generated, simulated, or fabricated demand exists in any layer. |