import os
import io
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB_CONN = "postgresql://postgres:postgrespassword@localhost:5432/transit_db"

def generate_synthetic_transit_data():
    print("Generating synthetic transit data...")
    np.random.seed(42)
    
    # 1. Stops Generation
    num_stops = 30
    stops = []
    base_lat, base_lon = 1.3521, 103.8198 # Coordinate base
    for i in range(1, num_stops + 1):
        stops.append({
            'stop_id': f"STOP_{i:03d}",
            'stop_name': f"Station Alpha-{i}",
            'route_id': f"ROUTE_{((i-1)//10)+1}",
            'latitude': base_lat + np.random.uniform(-0.05, 0.05),
            'longitude': base_lon + np.random.uniform(-0.05, 0.05)
        })
    df_stops = pd.DataFrame(stops)

    # 2. Hourly Demand Generation for 60 Days
    start_date = datetime(2026, 5, 1)
    hours = 60 * 24
    time_series = [start_date + timedelta(hours=i) for i in range(hours)]
    records = []
    
    for dt in time_series:
        hour = dt.hour
        is_weekend = dt.weekday() >= 5
        
        # Demand pattern: double peak on weekdays (8-9 AM, 5-6 PM)
        if not is_weekend:
            if hour in [7, 8, 9]:
                base_demand = np.random.randint(120, 250)
            elif hour in [17, 18, 19]:
                base_demand = np.random.randint(150, 280)
            elif 0 <= hour <= 5:
                base_demand = np.random.randint(0, 15)
            else:
                base_demand = np.random.randint(30, 80)
        else:
            base_demand = np.random.randint(20, 90) if 8 <= hour <= 22 else np.random.randint(0, 10)

        rain = np.random.choice([0.0, 0.0, 0.0, 2.5, 12.0], p=[0.7, 0.15, 0.05, 0.07, 0.03])
        if rain > 5.0:
            base_demand = int(base_demand * 1.35) # Rain increases bus demand

        for stop in df_stops['stop_id']:
            stop_mult = np.random.uniform(0.7, 1.3)
            final_demand = int(base_demand * stop_mult)
            records.append({
                'timestamp': dt,
                'stop_id': stop,
                'demand': final_demand,
                'precipitation_mm': rain,
                'temp_c': np.random.uniform(26.0, 33.0),
                'is_weekend': int(is_weekend)
            })
            
    df_demand = pd.DataFrame(records)
    print(f"Generated {len(df_demand)} hourly records across {num_stops} stops.")
    return df_stops, df_demand

def run_schema():
    print("Running database schema initialization...")
    schema_path = os.path.join(os.path.dirname(__file__), "..", "sql", "schema.sql")
    with open(schema_path, "r") as f:
        schema_sql = f.read()
    
    conn = psycopg2.connect(DB_CONN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(schema_sql)
    conn.close()
    print("Schema initialized successfully.")

def ingest_stops(df_stops):
    print("Ingesting bus stops...")
    conn = psycopg2.connect(DB_CONN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE bus_stops CASCADE;")
        for _, row in df_stops.iterrows():
            cur.execute("""
                INSERT INTO bus_stops (stop_id, stop_name, route_id, capacity_limit, location)
                VALUES (%s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326));
            """, (row['stop_id'], row['stop_name'], row['route_id'], 100, float(row['longitude']), float(row['latitude'])))
    conn.close()
    print("Bus stops ingested successfully.")

def ingest_hourly_context(df_demand):
    print("Ingesting hourly context...")
    df_context = df_demand[['timestamp', 'temp_c', 'precipitation_mm']].drop_duplicates(subset=['timestamp'])
    
    conn = psycopg2.connect(DB_CONN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE hourly_context CASCADE;")
        
        f = io.StringIO()
        for _, row in df_context.iterrows():
            ts = row['timestamp'].isoformat()
            temp = row['temp_c']
            precip = row['precipitation_mm']
            f.write(f"{ts}\t{temp:.2f}\t{precip:.2f}\tFalse\tFalse\n")
        f.seek(0)
        cur.copy_from(f, 'hourly_context', sep='\t', columns=('context_timestamp', 'temperature_c', 'precipitation_mm', 'is_holiday', 'special_event_flag'))
    conn.close()
    print("Hourly context ingested successfully.")

def ingest_tap_events(df_demand):
    print("Generating and ingesting raw passenger tap events (this might take a few seconds)...")
    conn = psycopg2.connect(DB_CONN)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE tap_events CASCADE;")
        
        f = io.StringIO()
        rng = np.random.default_rng(42)
        
        for _, row in df_demand.iterrows():
            dt = row['timestamp']
            stop_id = row['stop_id']
            demand = int(row['demand'])
            
            if demand <= 0:
                continue
            
            # Generate D 'IN' events
            for _ in range(demand):
                offset = rng.integers(0, 3600)
                ts = (dt + timedelta(seconds=int(offset))).isoformat()
                card_id = f"CARD_{rng.integers(100000, 999999)}"
                f.write(f"{card_id}\t{stop_id}\tIN\t{ts}\n")
                
            # Generate ~85% 'OUT' events
            out_count = int(demand * rng.uniform(0.8, 0.9))
            for _ in range(out_count):
                offset = rng.integers(0, 3600)
                ts = (dt + timedelta(seconds=int(offset))).isoformat()
                card_id = f"CARD_{rng.integers(100000, 999999)}"
                f.write(f"{card_id}\t{stop_id}\tOUT\t{ts}\n")
                
        f.seek(0)
        cur.copy_from(f, 'tap_events', sep='\t', columns=('card_id', 'stop_id', 'tap_type', 'tap_timestamp'))
        
        print("Refreshing materialized view...")
        cur.execute("REFRESH MATERIALIZED VIEW mv_hourly_stop_demand;")
        
    conn.close()
    print("Passenger tap events ingested and materialized view refreshed successfully.")

if __name__ == "__main__":
    stops_df, demand_df = generate_synthetic_transit_data()
    
    # Save fallback CSVs
    os.makedirs("data", exist_ok=True)
    demand_df.to_csv("data/synthetic_transit_demand.csv", index=False)
    stops_df.to_csv("data/synthetic_transit_stops.csv", index=False)
    print("Fallback CSV files saved successfully.")
    
    try:
        run_schema()
        ingest_stops(stops_df)
        ingest_hourly_context(demand_df)
        ingest_tap_events(demand_df)
        print("Database ingestion completed successfully.")
    except Exception as e:
        print(f"Failed to ingest data into the database: {e}")
        print("Ensure the PostgreSQL Docker container is running and healthy.")
