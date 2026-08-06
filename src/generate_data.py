import os
import io
import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB_CONN = "postgresql://postgres:postgrespassword@localhost:5433/transit_db"

def generate_synthetic_transit_data():
    print("Generating synthetic transit data for Kathmandu Valley...")
    
    # 30 Major Bus Stops in Kathmandu Valley across 5 Key Corridors
    kathmandu_stops = [
        # 1. Ring Road Corridor
        {"stop_id": "KTM_STOP_01", "stop_name": "Gongabu Bus Park", "route_id": "Ring Road Corridor", "latitude": 27.7333, "longitude": 85.3130, "capacity_limit": 60},
        {"stop_id": "KTM_STOP_02", "stop_name": "Maharajgunj Chowk", "route_id": "Ring Road Corridor", "latitude": 27.7360, "longitude": 85.3300, "capacity_limit": 40},
        {"stop_id": "KTM_STOP_03", "stop_name": "Chabahil Chowk", "route_id": "Ring Road Corridor", "latitude": 27.7175, "longitude": 85.3465, "capacity_limit": 50},
        {"stop_id": "KTM_STOP_04", "stop_name": "Gaushala", "route_id": "Ring Road Corridor", "latitude": 27.7088, "longitude": 85.3480, "capacity_limit": 45},
        {"stop_id": "KTM_STOP_05", "stop_name": "Koteshwor Chowk", "route_id": "Ring Road Corridor", "latitude": 27.6755, "longitude": 85.3459, "capacity_limit": 60},
        {"stop_id": "KTM_STOP_06", "stop_name": "Satdobato Chowk", "route_id": "Ring Road Corridor", "latitude": 27.6536, "longitude": 85.3235, "capacity_limit": 45},
        {"stop_id": "KTM_STOP_07", "stop_name": "Balkhu Chowk", "route_id": "Ring Road Corridor", "latitude": 27.6830, "longitude": 85.2970, "capacity_limit": 40},
        {"stop_id": "KTM_STOP_08", "stop_name": "Kalanki Chowk", "route_id": "Ring Road Corridor", "latitude": 27.6931, "longitude": 85.2806, "capacity_limit": 60},
        {"stop_id": "KTM_STOP_09", "stop_name": "Swayambhu Ringroad", "route_id": "Ring Road Corridor", "latitude": 27.7140, "longitude": 85.2860, "capacity_limit": 35},
        {"stop_id": "KTM_STOP_10", "stop_name": "Balaju Chowk", "route_id": "Ring Road Corridor", "latitude": 27.7310, "longitude": 85.3000, "capacity_limit": 45},
        
        # 2. Ratna Park - Lagankhel Corridor
        {"stop_id": "KTM_STOP_11", "stop_name": "Ratna Park Bus Park", "route_id": "Ratna Park - Lagankhel Corridor", "latitude": 27.7061, "longitude": 85.3155, "capacity_limit": 60},
        {"stop_id": "KTM_STOP_12", "stop_name": "Lainchaur Chowk", "route_id": "Ratna Park - Lagankhel Corridor", "latitude": 27.7170, "longitude": 85.3160, "capacity_limit": 40},
        {"stop_id": "KTM_STOP_13", "stop_name": "Maitighar Mandala", "route_id": "Ratna Park - Lagankhel Corridor", "latitude": 27.6940, "longitude": 85.3200, "capacity_limit": 40},
        {"stop_id": "KTM_STOP_14", "stop_name": "Thapathali Chowk", "route_id": "Ratna Park - Lagankhel Corridor", "latitude": 27.6890, "longitude": 85.3180, "capacity_limit": 35},
        {"stop_id": "KTM_STOP_15", "stop_name": "Kupondole", "route_id": "Ratna Park - Lagankhel Corridor", "latitude": 27.6835, "longitude": 85.3160, "capacity_limit": 30},
        {"stop_id": "KTM_STOP_16", "stop_name": "Pulchowk", "route_id": "Ratna Park - Lagankhel Corridor", "latitude": 27.6780, "longitude": 85.3140, "capacity_limit": 40},
        {"stop_id": "KTM_STOP_17", "stop_name": "Jawalakhel Chowk", "route_id": "Ratna Park - Lagankhel Corridor", "latitude": 27.6725, "longitude": 85.3120, "capacity_limit": 45},
        {"stop_id": "KTM_STOP_18", "stop_name": "Lagankhel Bus Park", "route_id": "Ratna Park - Lagankhel Corridor", "latitude": 27.6660, "longitude": 85.3230, "capacity_limit": 55},
        
        # 3. Arniko Highway Corridor (Kathmandu - Bhaktapur)
        {"stop_id": "KTM_STOP_19", "stop_name": "New Baneshwor Chowk", "route_id": "Arniko Highway Corridor", "latitude": 27.6915, "longitude": 85.3340, "capacity_limit": 50},
        {"stop_id": "KTM_STOP_20", "stop_name": "Tinkune Chowk", "route_id": "Arniko Highway Corridor", "latitude": 27.6830, "longitude": 85.3450, "capacity_limit": 45},
        {"stop_id": "KTM_STOP_21", "stop_name": "Jadibuti Chowk", "route_id": "Arniko Highway Corridor", "latitude": 27.6710, "longitude": 85.3560, "capacity_limit": 40},
        {"stop_id": "KTM_STOP_22", "stop_name": "Lokanthali", "route_id": "Arniko Highway Corridor", "latitude": 27.6690, "longitude": 85.3670, "capacity_limit": 30},
        {"stop_id": "KTM_STOP_23", "stop_name": "Kaushaltar", "route_id": "Arniko Highway Corridor", "latitude": 27.6700, "longitude": 85.3780, "capacity_limit": 30},
        {"stop_id": "KTM_STOP_24", "stop_name": "Gatthaghar", "route_id": "Arniko Highway Corridor", "latitude": 27.6715, "longitude": 85.3900, "capacity_limit": 35},
        {"stop_id": "KTM_STOP_25", "stop_name": "Suryabinayak Bus Stop", "route_id": "Arniko Highway Corridor", "latitude": 27.6710, "longitude": 85.4240, "capacity_limit": 50},
        
        # 4. Tribhuvan Rajpath Corridor (Highway Exit Corridor)
        {"stop_id": "KTM_STOP_26", "stop_name": "Kalanki Central", "route_id": "Tribhuvan Rajpath Corridor", "latitude": 27.6931, "longitude": 85.2806, "capacity_limit": 60},
        {"stop_id": "KTM_STOP_27", "stop_name": "Gurjudhara", "route_id": "Tribhuvan Rajpath Corridor", "latitude": 27.6880, "longitude": 85.2500, "capacity_limit": 30},
        {"stop_id": "KTM_STOP_28", "stop_name": "Thankot Bus Park", "route_id": "Tribhuvan Rajpath Corridor", "latitude": 27.6850, "longitude": 85.2200, "capacity_limit": 55},
        {"stop_id": "KTM_STOP_29", "stop_name": "Nagdhunga Checkpost", "route_id": "Tribhuvan Rajpath Corridor", "latitude": 27.6830, "longitude": 85.2000, "capacity_limit": 40},
        
        # 5. Chabahil - Jorpati - Sankhu Corridor
        {"stop_id": "KTM_STOP_30", "stop_name": "Jorpati Chowk", "route_id": "Chabahil - Jorpati Corridor", "latitude": 27.7215, "longitude": 85.3780, "capacity_limit": 40}
    ]
    
    df_stops = pd.DataFrame(kathmandu_stops)

    # Generate 60 days of hourly data (1440 hours) for 30 stops = 43,200 records
    np.random.seed(42)
    start_date = datetime.now() - timedelta(days=60)
    timestamps = [start_date + timedelta(hours=i) for i in range(1440)]
    
    hourly_records = []
    hourly_context = []

    for day_idx in range(60):
        # Mark days 40-45 as Dashain festival season (mass outbound travel from Gongabu & Kalanki)
        is_dashain = 1 if 40 <= day_idx <= 45 else 0
        # Mark days 55-57 as Tihar festival season
        is_tihar = 1 if 55 <= day_idx <= 57 else 0
        
        for hour_in_day in range(24):
            idx = day_idx * 24 + hour_in_day
            ts = timestamps[idx]
            hour = ts.hour
            # Nepal weekend structure: Saturday is the weekly holiday (weekday == 5)
            is_saturday = 1 if ts.weekday() == 5 else 0
            is_sunday = 1 if ts.weekday() == 6 else 0
            is_holiday = is_saturday or is_dashain or is_tihar
            
            # Simulate Kathmandu diurnal temperature & monsoon weather patterns
            temp = 18 + 9 * np.sin((hour - 6) * np.pi / 12) + np.random.normal(0, 1.5)
            # Monsoon precipitation: heavy rain (>2.0mm) during monsoon simulation
            precip = np.random.exponential(1.2) if np.random.rand() < 0.20 else 0.0
            is_heavy_monsoon = 1 if precip > 2.0 else 0
            
            hourly_context.append({
                'context_timestamp': ts,
                'temperature_c': round(temp, 1),
                'precipitation_mm': round(precip, 1),
                'is_holiday': int(is_holiday),
                'is_saturday': int(is_saturday),
                'is_festival': int(is_dashain or is_tihar)
            })

            # Rush hour multipliers for Kathmandu (7-9 AM morning rush, 5-7 PM evening rush)
            if hour in [7, 8, 9]:
                base_mult = 2.5
            elif hour in [17, 18, 19]:
                base_mult = 2.8
            elif 22 <= hour or hour <= 5:
                base_mult = 0.2
            else:
                base_mult = 1.1

            # Saturday traffic drops in business corridors, but stays active in shopping hubs
            if is_saturday:
                base_mult *= 0.65

            # Heavy monsoon rainfall severely increases bus stop waiting crowds due to vehicle slowdowns
            if is_heavy_monsoon:
                base_mult *= 1.4

            for _, stop in df_stops.iterrows():
                stop_bias = np.random.uniform(0.85, 1.25)
                
                # Major interchange hubs get higher baseline passenger demand
                if "Bus Park" in stop['stop_name'] or "Chowk" in stop['stop_name']:
                    stop_bias *= 1.35

                # Dashain festival surge: Massive outbound exit at Gongabu, Kalanki, Thankot
                if is_dashain and stop['stop_name'] in ["Gongabu Bus Park", "Kalanki Chowk", "Kalanki Central", "Thankot Bus Park"]:
                    stop_bias *= 3.2

                # Tihar festival surge: Localized shopping spikes at Ratna Park, New Baneshwor
                if is_tihar and stop['stop_name'] in ["Ratna Park Bus Park", "New Baneshwor Chowk", "Jawalakhel Chowk"]:
                    stop_bias *= 2.1

                demand = max(2, int(np.random.poisson(28 * base_mult * stop_bias)))
                
                hourly_records.append({
                    'timestamp': ts,
                    'stop_id': stop['stop_id'],
                    'demand': demand,
                    'is_saturday': int(is_saturday),
                    'is_holiday': int(is_holiday),
                    'is_festival': int(is_dashain or is_tihar),
                    'temperature_c': round(temp, 1),
                    'precipitation_mm': round(precip, 1),
                    'is_heavy_monsoon': is_heavy_monsoon
                })

    df_demand = pd.DataFrame(hourly_records)
    df_context = pd.DataFrame(hourly_context).drop_duplicates(subset=['context_timestamp'])

    # Save Fallback CSV Files
    os.makedirs("data", exist_ok=True)
    df_stops.to_csv("data/synthetic_transit_stops.csv", index=False)
    df_demand.to_csv("data/synthetic_transit_demand.csv", index=False)
    print("Generated 43200 hourly records across 30 Kathmandu stops.")
    print("Fallback CSV files saved successfully.")

    # Ingest into PostgreSQL Database if connection succeeds
    try:
        print("Initializing database schema on PostgreSQL...")
        conn = psycopg2.connect(DB_CONN)
        conn.autocommit = True
        with conn.cursor() as cur:
            schema_path = os.path.join(os.path.dirname(__file__), "..", "sql", "schema.sql")
            with open(schema_path, "r") as f:
                cur.execute(f.read())
        print("Database schema initialized successfully.")

        # Ingest Bus Stops
        print("Ingesting bus stops...")
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE bus_stops CASCADE;")
            for _, row in df_stops.iterrows():
                cur.execute("""
                    INSERT INTO bus_stops (stop_id, stop_name, route_id, capacity_limit, location)
                    VALUES (%s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326));
                """, (row['stop_id'], row['stop_name'], row['route_id'], int(row['capacity_limit']), row['longitude'], row['latitude']))
        print("Bus stops ingested successfully.")

        # Ingest Environmental Context
        print("Ingesting environmental context...")
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE environmental_context CASCADE;")
            s_buf = io.StringIO()
            df_context.to_csv(s_buf, index=False, header=False)
            s_buf.seek(0)
            cur.copy_expert("COPY environmental_context FROM STDIN WITH CSV", s_buf)
        print("Environmental context ingested successfully.")

        # Ingest Tap Events
        print("Generating and ingesting raw passenger tap events...")
        ingest_tap_events(conn, df_demand)

        # Refresh Materialized View
        print("Refreshing materialized view mv_hourly_stop_demand...")
        with conn.cursor() as cur:
            cur.execute("REFRESH MATERIALIZED VIEW mv_hourly_stop_demand;")
        print("Passenger tap events ingested and materialized view refreshed successfully.")

        conn.close()
        print("PostgreSQL database ingestion completed successfully.")

    except Exception as e:
        print(f"PostgreSQL Ingestion Warning: {e}")
        print("System will operate using fallback CSV datasets.")

def ingest_tap_events(conn, df_demand):
    df_sample = df_demand.sample(frac=0.10, random_state=42)
    events = []
    
    for idx, row in df_sample.iterrows():
        n_taps = max(1, int(row['demand']))
        for _ in range(min(n_taps, 5)):
            minute = np.random.randint(0, 60)
            second = np.random.randint(0, 60)
            tap_time = row['timestamp'] + timedelta(minutes=minute, seconds=second)
            card_id = f"NEPAL_CARD_{np.random.randint(10000, 99999)}"
            events.append((card_id, row['stop_id'], 'IN', tap_time))

    df_events = pd.DataFrame(events, columns=['card_id', 'stop_id', 'tap_type', 'tap_timestamp'])
    
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE tap_events CASCADE;")
        s_buf = io.StringIO()
        df_events.to_csv(s_buf, index=False, header=False)
        s_buf.seek(0)
        cur.copy_expert("COPY tap_events (card_id, stop_id, tap_type, tap_timestamp) FROM STDIN WITH CSV", s_buf)

if __name__ == "__main__":
    generate_synthetic_transit_data()
