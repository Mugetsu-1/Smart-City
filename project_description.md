# Project Description: Smart City - Dynamic Transit Scheduling and Route Optimization in Nepal

## 1. The Fundamental Urban Problem
Public transit networks in rapidly growing urban centers like the Kathmandu Valley face a critical operational dilemma: buses are dangerously overcrowded during morning and evening peak commute hours, yet run completely empty during off-peak windows, incurring massive fuel waste and driver burnout.

Traditional public transit systems rely on rigid, fixed bus timetables published months in advance that cannot adapt to real-time fluctuations in demand on the valley's arterial roads.

## 2. The Core Objective
This project builds an enterprise-grade, data-driven dynamic dispatch system titled **"Smart City: Dynamic Transit Scheduling and Route Optimization in Nepal"**. The system replaces static timetables with an adaptive network that reads **real traffic counts from the Nepal Department of Roads (DOR)** and automatically recommends fleet adjustments.

The implementation is a **real-data system - no synthetic data**:
- Real Kathmandu traffic counts come from the **DOR SSRN public traffic portal** (`ssrn.dor.gov.np`) — 21 official Kathmandu Valley count stations.
- The full **published multi-year series (2011/12 – 2024/25)** per station is scraped live from each station's official detail page at every launch; the operational snapshot uses **each station's most recently published count (2024/25)**.
- A per-station trend model (`src/forecast.py`) projects the **next published count window** (e.g. 2024/25 → 2026/27) from the real yearly series alone.
- The app live-scrapes the portal at startup; real CSV snapshots written after each successful scrape keep the dashboard working offline (with an explicit OFFLINE badge), and re-scraping on demand is one click.

## 3. How the System Solves the Problem

1. **Ingest Real Telemetry (Data Engineering)**:
   Live-scrapes the DOR traffic portal for every official Kathmandu Valley count station, parses the AADT tables (coordinates from the official station metadata), and persists real CSV snapshots (`data/dor_traffic_demand.csv`, `data/dor_traffic_stops.csv`). A PostgreSQL/PostGIS mirror (optional) holds the same real data row-for-row.

2. **Compute Real Traffic Demand**:
   Converts the real AADT figures into a per-hour junction load (pcu/hr) per station. Each station is assigned a capacity tier derived from its real observed AADT ranking — no fabricated values.

3. **Forecast Demand Trends (Prediction Layer)**:
   Fits a linear trend model per station on the real published yearly counts (≥4 observed years) and forecasts the next count window, reporting per-station residuals as uncertainty. This tells operators where counts will grow *before* the next window is published.

4. **Identify Bottlenecks (Spatial Optimization)**:
   Applies demand-weighted spatial clustering (K-Means) on the real station coordinates to group localized overcrowding hotspots along the real transit corridors.

5. **Automate Fleet Dispatch (Decision Layer)**:
   Calculates junction pressure ratios (observed hourly load vs. capacity) and outputs concrete, bilingual dispatch instructions (e.g., "CRITICAL OVERCROWDING at Kalanki: Inject 2 short-turn express buses toward Ratna Park and reduce headway by 5 minutes").

6. **Visualize Operations (Dashboard)**:
   Streamlit Command Center featuring a color-coded Folium heatmap of the real stations, KPI cards, sortable dispatch tables, the live operational snapshot, per-station traffic charts with a dashed forecast extension, and a next-window forecast panel.

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
| Published years | 2011/12 – 2024/25 (10 count years per station) |
| Operational snapshot | Each station's most recently published count (2024/25) |
| Forecast | Linear trend fitted only on the real published yearly counts (next window e.g. 2026/27) |
| Coordinates | Official station metadata from the scraped DOR tables |
| Synthetic data | None. No generated, simulated, or fabricated demand exists in any layer. |