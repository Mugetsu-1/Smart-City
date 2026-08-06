# Kathmandu Transit Optimization & Dispatch System

An end-to-end data engineering and predictive machine learning pipeline that transforms raw transit telemetry (passenger tap-in/tap-out logs) and environmental context (weather, temporal patterns) into real-time, actionable schedule and route optimizations for Kathmandu Valley.

## Project Structure

```
d:/smart_city_transit/
├── docker-compose.yml       # Docker Compose for PostgreSQL 15 & PostGIS database
├── requirements.txt         # Python project dependencies
├── README.md                # Project documentation
├── system_architecture.md   # System Architecture & Design Document
├── project_description.md   # Detailed Project Purpose & Data Overview
├── run.py                   # Master script to run schema, generate/ingest data, & train model
├── sql/
│   └── schema.sql           # Database schema & materialized view definitions
├── src/
│   ├── generate_data.py     # Generates Kathmandu synthetic data and handles PostgreSQL ingestion
│   ├── train_model.py       # Feature engineering & XGBoost model training/evaluation
│   └── optimize.py          # Occupancy calculations & headway optimization recommendations
└── app/
    └── app.py               # Streamlit Command Center Interactive Dashboard
```

## Key Kathmandu Corridors Covered
- **Ring Road Corridor**: Gongabu, Maharajgunj, Chabahil, Gaushala, Koteshwor, Satdobato, Balkhu, Kalanki, Swayambhu, Balaju
- **Ratna Park - Lagankhel Corridor**: Ratna Park, Maitighar, Thapathali, Kupondole, Pulchowk, Jawalakhel, Lagankhel
- **Arniko Highway Corridor**: New Baneshwor, Tinkune, Jadibuti, Lokanthali, Kaushaltar, Gatapatha, Suryabinayak
- **Tribhuvan Rajpath Corridor**: Kalanki Central, Gurjudhara, Thankot, Nagdhunga

## System Requirements

- **Operating System:** Windows, Linux, or macOS
- **Docker & Docker Compose** (for running the PostgreSQL + PostGIS database)
- **Python 3.10+**

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
Run the pipeline script to set up tables, populate them with Kathmandu synthetic data, and train the XGBoost model:
```bash
.venv\Scripts\python.exe run.py
```

### 4. Launch the Dashboard
Start the interactive Streamlit command center dashboard:
```bash
.venv\Scripts\python.exe -m streamlit run app/app.py
```

Open the local URL displayed in the terminal (`http://localhost:8501`) to interact with the dispatch system.
