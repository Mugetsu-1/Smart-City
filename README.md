# Smart City Transit Optimization & Dispatch System

An end-to-end data engineering and predictive machine learning pipeline that transforms raw transit telemetry (GPS, passenger tap-in/tap-out logs) and environmental context (weather, municipal events) into real-time, actionable schedule and route optimizations.

## Project Structure

```
d:/smart_city_transit/
├── docker-compose.yml       # Docker Compose for PostgreSQL 15 & PostGIS database
├── requirements.txt         # Python project dependencies
├── README.md                # Project documentation (this file)
├── run.py                   # Master script to run schema, generate/ingest data, & train model
├── sql/
│   └── schema.sql           # Database schema & materialized view definitions
├── src/
│   ├── generate_data.py     # Generates synthetic data and handles PostgreSQL ingestion
│   ├── train_model.py       # Features engineering & XGBoost model training/evaluation
│   └── optimize.py          # Occupancy calculations & K-Means hotspot clustering
└── app/
    └── app.py               # Streamlit Command Center Interactive Dashboard
```

## System Requirements

- **Operating System:** Windows, Linux, or macOS
- **Docker & Docker Compose** (for running the PostgreSQL + PostGIS database)
- **Python 3.10+** (tested up to Python 3.14)

## Getting Started

### 1. Start the Database
The project utilizes a Dockerized PostgreSQL database with the PostGIS extension. Spin up the container:
```bash
docker compose up -d
```

### 2. Set Up Virtual Environment & Install Dependencies
Create a virtual environment and install the required libraries:
```bash
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
```

### 3. Initialize Schema, Ingest Data & Train Model
Run the pipeline script to set up tables, populate them with synthetic data, and train the XGBoost model:
```bash
.venv\Scripts\python.exe run.py
```

This script will:
- Establish the PostgreSQL connection
- Run `sql/schema.sql` to initialize tables, indexes, and materialized views
- Generate 60 days of hourly synthetic transit data across 30 stops
- Ingest stops (converting lat/lon to spatial geometries), context weather data, and raw tap events (generating individual card tap records to populate the materialized view)
- Train and evaluate the XGBoost regressor, outputting performance metrics (RMSE, MAE)
- Save the trained model to `models/xgboost_transit_model.joblib`

### 4. Launch the Dashboard
Start the interactive Streamlit command center dashboard:
```bash
.venv\Scripts\streamlit.exe run app/app.py
```

Open the local URL displayed in the terminal (usually `http://localhost:8501`) to interact with the dispatch system.
