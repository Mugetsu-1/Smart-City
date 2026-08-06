# Project Description: Smart City Transit Optimization

## 1. Project Purpose
The primary purpose of the **Smart City Transit Optimization** project is to modernize public transportation networks by transitioning from static, rigid schedules to a dynamic, data-driven dispatch system. 

By predicting passenger demand before it happens, transit agencies can proactively deploy vehicles where they are needed most, reducing passenger wait times, alleviating overcrowding (hotspots), and minimizing empty "ghost buses" that waste fuel and resources.

## 2. Key Objectives
*   **Predictive Forecasting**: Accurately forecast passenger demand at individual bus stops up to 24 hours in advance using Machine Learning.
*   **Dynamic Dispatching**: Generate actionable recommendations for transit operators (e.g., "Deploy extra bus to ROUTE_1", "Reduce frequency on ROUTE_3").
*   **Spatial Hotspot Detection**: Automatically group congested bus stops into geographic clusters to identify localized transit bottlenecks.
*   **Real-time Visibility**: Provide a centralized Command Center dashboard for operators to monitor the health of the entire transit network at a glance.

## 3. Dataset Overview
**What dataset is used for this project?**
This project relies on **Synthetic Data Generation**. Because real-world transit tap-in/tap-out data is highly sensitive and restricted by privacy laws, this system includes a custom Python script (`src/generate_data.py`) that computationally generates realistic transit data. 

The synthetic dataset includes:
1.  **Bus Stops**: Randomly distributed geographic coordinates acting as transit stations across predefined routes.
2.  **Tap Events**: Millions of simulated passenger tap-ins and tap-outs. The generator uses logical patterns (e.g., heavy inbound traffic during morning rush hours, lower traffic on weekends, and weather-dependent variations) to mimic real human behavior.
3.  **Contextual Data**: Simulated historical weather patterns (precipitation, temperature) which influence the machine learning model's predictions.

## 4. How It Works (The Workflow)
1.  **Ingestion**: The system continuously logs passenger tap events (synthetic) into the PostgreSQL database.
2.  **Aggregation**: A materialized view runs periodically to aggregate these individual taps into hourly totals per bus stop.
3.  **Prediction**: The XGBoost Machine Learning model ingests these hourly totals, looks at the time of day, day of the week, and weather, and predicts the *future* passenger count.
4.  **Recommendation**: The application compares the predicted passenger count against the maximum capacity of a standard bus. If the ratio exceeds 85%, it triggers a `RED` alert and recommends dispatching an extra vehicle.
5.  **Visualization**: All of this data is rendered on an interactive map and data tables for the human operator to review and approve.
