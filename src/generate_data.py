import os
import io
import re
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

DB_CONN = "postgresql://postgres:postgrespassword@localhost:5433/transit_db"

def generate_synthetic_transit_data():
    print("Generating synthetic transit data for Kathmandu Valley...")

    # 30 Major Bus Stops in Kathmandu Valley across 5 Key Corridors
    kathmandu_stops = [
        # 1. Ring Road Corridor
        {"stop_id": "KTM_STOP_01", "stop_name": "Gongabu Bus Park",       "route_id": "Ring Road Corridor",              "latitude": 27.7333, "longitude": 85.3130, "capacity_limit": 60},
        {"stop_id": "KTM_STOP_02", "stop_name": "Maharajgunj Chowk",      "route_id": "Ring Road Corridor",              "latitude": 27.7360, "longitude": 85.3300, "capacity_limit": 40},
        {"stop_id": "KTM_STOP_03", "stop_name": "Chabahil Chowk",         "route_id": "Ring Road Corridor",              "latitude": 27.7175, "longitude": 85.3465, "capacity_limit": 50},
        {"stop_id": "KTM_STOP_04", "stop_name": "Gaushala",               "route_id": "Ring Road Corridor",              "latitude": 27.7088, "longitude": 85.3480, "capacity_limit": 45},
        {"stop_id": "KTM_STOP_05", "stop_name": "Koteshwor Chowk",        "route_id": "Ring Road Corridor",              "latitude": 27.6755, "longitude": 85.3459, "capacity_limit": 60},
        {"stop_id": "KTM_STOP_06", "stop_name": "Satdobato Chowk",        "route_id": "Ring Road Corridor",              "latitude": 27.6536, "longitude": 85.3235, "capacity_limit": 45},
        {"stop_id": "KTM_STOP_07", "stop_name": "Balkhu Chowk",           "route_id": "Ring Road Corridor",              "latitude": 27.6830, "longitude": 85.2970, "capacity_limit": 40},
        {"stop_id": "KTM_STOP_08", "stop_name": "Kalanki Chowk",          "route_id": "Ring Road Corridor",              "latitude": 27.6931, "longitude": 85.2806, "capacity_limit": 60},
        {"stop_id": "KTM_STOP_09", "stop_name": "Swayambhu Ringroad",     "route_id": "Ring Road Corridor",              "latitude": 27.7140, "longitude": 85.2860, "capacity_limit": 35},
        {"stop_id": "KTM_STOP_10", "stop_name": "Balaju Chowk",           "route_id": "Ring Road Corridor",              "latitude": 27.7310, "longitude": 85.3000, "capacity_limit": 45},
        # 2. Ratna Park - Lagankhel Corridor
        {"stop_id": "KTM_STOP_11", "stop_name": "Ratna Park Bus Park",    "route_id": "Ratna Park - Lagankhel Corridor", "latitude": 27.7061, "longitude": 85.3155, "capacity_limit": 60},
        {"stop_id": "KTM_STOP_12", "stop_name": "Lainchaur Chowk",        "route_id": "Ratna Park - Lagankhel Corridor", "latitude": 27.7170, "longitude": 85.3160, "capacity_limit": 40},
        {"stop_id": "KTM_STOP_13", "stop_name": "Maitighar Mandala",      "route_id": "Ratna Park - Lagankhel Corridor", "latitude": 27.6940, "longitude": 85.3200, "capacity_limit": 40},
        {"stop_id": "KTM_STOP_14", "stop_name": "Thapathali Chowk",       "route_id": "Ratna Park - Lagankhel Corridor", "latitude": 27.6890, "longitude": 85.3180, "capacity_limit": 35},
        {"stop_id": "KTM_STOP_15", "stop_name": "Kupondole",              "route_id": "Ratna Park - Lagankhel Corridor", "latitude": 27.6835, "longitude": 85.3160, "capacity_limit": 30},
        {"stop_id": "KTM_STOP_16", "stop_name": "Pulchowk",               "route_id": "Ratna Park - Lagankhel Corridor", "latitude": 27.6780, "longitude": 85.3140, "capacity_limit": 40},
        {"stop_id": "KTM_STOP_17", "stop_name": "Jawalakhel Chowk",       "route_id": "Ratna Park - Lagankhel Corridor", "latitude": 27.6725, "longitude": 85.3120, "capacity_limit": 45},
        {"stop_id": "KTM_STOP_18", "stop_name": "Lagankhel Bus Park",     "route_id": "Ratna Park - Lagankhel Corridor", "latitude": 27.6660, "longitude": 85.3230, "capacity_limit": 55},
        # 3. Arniko Highway Corridor (Kathmandu - Bhaktapur)
        {"stop_id": "KTM_STOP_19", "stop_name": "New Baneshwor Chowk",   "route_id": "Arniko Highway Corridor",         "latitude": 27.6915, "longitude": 85.3340, "capacity_limit": 50},
        {"stop_id": "KTM_STOP_20", "stop_name": "Tinkune Chowk",          "route_id": "Arniko Highway Corridor",         "latitude": 27.6830, "longitude": 85.3450, "capacity_limit": 45},
        {"stop_id": "KTM_STOP_21", "stop_name": "Jadibuti Chowk",         "route_id": "Arniko Highway Corridor",         "latitude": 27.6710, "longitude": 85.3560, "capacity_limit": 40},
        {"stop_id": "KTM_STOP_22", "stop_name": "Lokanthali",             "route_id": "Arniko Highway Corridor",         "latitude": 27.6690, "longitude": 85.3670, "capacity_limit": 30},
        {"stop_id": "KTM_STOP_23", "stop_name": "Kaushaltar",             "route_id": "Arniko Highway Corridor",         "latitude": 27.6700, "longitude": 85.3780, "capacity_limit": 30},
        {"stop_id": "KTM_STOP_24", "stop_name": "Gatthaghar",             "route_id": "Arniko Highway Corridor",         "latitude": 27.6715, "longitude": 85.3900, "capacity_limit": 35},
        {"stop_id": "KTM_STOP_25", "stop_name": "Suryabinayak Bus Stop",  "route_id": "Arniko Highway Corridor",         "latitude": 27.6710, "longitude": 85.4240, "capacity_limit": 50},
        # 4. Tribhuvan Rajpath Corridor (Highway Exit Corridor)
        {"stop_id": "KTM_STOP_26", "stop_name": "Kalanki Central",        "route_id": "Tribhuvan Rajpath Corridor",      "latitude": 27.6931, "longitude": 85.2806, "capacity_limit": 60},
        {"stop_id": "KTM_STOP_27", "stop_name": "Gurjudhara",             "route_id": "Tribhuvan Rajpath Corridor",      "latitude": 27.6880, "longitude": 85.2500, "capacity_limit": 30},
        {"stop_id": "KTM_STOP_28", "stop_name": "Thankot Bus Park",       "route_id": "Tribhuvan Rajpath Corridor",      "latitude": 27.6850, "longitude": 85.2200, "capacity_limit": 55},
        {"stop_id": "KTM_STOP_29", "stop_name": "Nagdhunga Checkpost",    "route_id": "Tribhuvan Rajpath Corridor",      "latitude": 27.6830, "longitude": 85.2000, "capacity_limit": 40},
        # 5. Chabahil - Jorpati - Sankhu Corridor
        {"stop_id": "KTM_STOP_30", "stop_name": "Jorpati Chowk",          "route_id": "Chabahil - Jorpati Corridor",     "latitude": 27.7215, "longitude": 85.3780, "capacity_limit": 40},
    ]

    df_stops = pd.DataFrame(kathmandu_stops)

    # Generate 60 days of hourly data (1440 hours) for 30 stops = 43,200 records
    np.random.seed(42)
    start_date = datetime.now() - timedelta(days=60)
    timestamps = [start_date + timedelta(hours=i) for i in range(1440)]

    hourly_records = []
    hourly_context = []

    for day_idx in range(60):
        is_dashain = 1 if 40 <= day_idx <= 45 else 0
        is_tihar   = 1 if 55 <= day_idx <= 57 else 0

        for hour_in_day in range(24):
            idx  = day_idx * 24 + hour_in_day
            ts   = timestamps[idx]
            hour = ts.hour
            is_saturday = 1 if ts.weekday() == 5 else 0
            is_holiday  = is_saturday or is_dashain or is_tihar

            temp   = 18 + 9 * np.sin((hour - 6) * np.pi / 12) + np.random.normal(0, 1.5)
            precip = np.random.exponential(1.2) if np.random.rand() < 0.20 else 0.0
            is_heavy_monsoon = 1 if precip > 2.0 else 0

            hourly_context.append({
                'context_timestamp': ts,
                'temperature_c':     round(temp, 1),
                'precipitation_mm':  round(precip, 1),
                'is_holiday':        int(is_holiday),
                'is_saturday':       int(is_saturday),
                'is_festival':       int(is_dashain or is_tihar)
            })

            if hour in [7, 8, 9]:
                base_mult = 2.5
            elif hour in [17, 18, 19]:
                base_mult = 2.8
            elif 22 <= hour or hour <= 5:
                base_mult = 0.2
            else:
                base_mult = 1.1

            if is_saturday:
                base_mult *= 0.65
            if is_heavy_monsoon:
                base_mult *= 1.4

            for _, stop in df_stops.iterrows():
                stop_bias = np.random.uniform(0.85, 1.25)
                if "Bus Park" in stop['stop_name'] or "Chowk" in stop['stop_name']:
                    stop_bias *= 1.35
                if is_dashain and stop['stop_name'] in [
                    "Gongabu Bus Park", "Kalanki Chowk", "Kalanki Central", "Thankot Bus Park"
                ]:
                    stop_bias *= 3.2
                if is_tihar and stop['stop_name'] in [
                    "Ratna Park Bus Park", "New Baneshwor Chowk", "Jawalakhel Chowk"
                ]:
                    stop_bias *= 2.1

                demand = max(2, int(np.random.poisson(28 * base_mult * stop_bias)))

                hourly_records.append({
                    'timestamp':        ts,
                    'stop_id':          stop['stop_id'],
                    'demand':           demand,
                    'is_saturday':      int(is_saturday),
                    'is_holiday':       int(is_holiday),
                    'is_festival':      int(is_dashain or is_tihar),
                    'temperature_c':    round(temp, 1),
                    'precipitation_mm': round(precip, 1),
                    'is_heavy_monsoon': is_heavy_monsoon
                })

    df_demand  = pd.DataFrame(hourly_records)
    df_context = pd.DataFrame(hourly_context).drop_duplicates(subset=['context_timestamp'])

    os.makedirs("data", exist_ok=True)
    df_stops.to_csv("data/synthetic_transit_stops.csv", index=False)
    df_demand.to_csv("data/synthetic_transit_demand.csv", index=False)
    print(f"Generated {len(df_demand):,} hourly records across {len(df_stops)} Kathmandu stops.")
    print("Fallback CSV files saved successfully.")

    try:
        print("Initializing database schema on PostgreSQL...")
        engine = create_engine(DB_CONN)
        _execute_schema(engine)
        print("Database schema initialized successfully.")

        # Ingest Bus Stops
        print("Ingesting bus stops...")
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE bus_stops CASCADE;"))
            conn.commit()
            for _, row in df_stops.iterrows():
                conn.execute(
                    text("""
                        INSERT INTO bus_stops (stop_id, stop_name, route_id, capacity_limit, location)
                        VALUES (:sid, :sname, :rid, :cap, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
                    """),
                    {
                        "sid":   row['stop_id'],
                        "sname": row['stop_name'],
                        "rid":   row['route_id'],
                        "cap":   int(row['capacity_limit']),
                        "lon":   row['longitude'],
                        "lat":   row['latitude'],
                    }
                )
            conn.commit()
        print("Bus stops ingested successfully.")

        # Ingest Environmental Context via COPY
        print("Ingesting environmental context...")
        raw_conn = engine.raw_connection()
        try:
            with raw_conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE environmental_context CASCADE;")
                s_buf = io.StringIO()
                df_context.to_csv(s_buf, index=False, header=False)
                s_buf.seek(0)
                cur.copy_expert("COPY environmental_context FROM STDIN WITH CSV", s_buf)
            raw_conn.commit()
        finally:
            raw_conn.close()
        print("Environmental context ingested successfully.")

        # Ingest Tap Events
        print("Generating and ingesting raw passenger tap events...")
        ingest_tap_events(engine, df_demand)

        # Refresh materialized view
        print("Refreshing materialized view mv_hourly_stop_demand...")
        with engine.connect() as conn:
            conn.execute(text("REFRESH MATERIALIZED VIEW mv_hourly_stop_demand;"))
            conn.commit()
        print("Materialized view refreshed successfully.")

        engine.dispose()
        print("PostgreSQL database ingestion completed successfully.")

    except Exception as e:
        print(f"PostgreSQL Ingestion Warning: {e}")
        print("System will operate using fallback CSV datasets.")


def _execute_schema(engine):
    """
    Read schema.sql and execute each top-level SQL statement individually.
    This handles DO-blocks, CREATE TABLE, CREATE INDEX, and CREATE VIEW
    statements that cannot be batched as a single text() block in SQLAlchemy 2.x.
    """
    schema_path = os.path.join(os.path.dirname(__file__), "..", "sql", "schema.sql")
    with open(schema_path, "r") as f:
        raw_sql = f.read()

    # Strip line comments but preserve DO $$ ... $$ blocks intact
    # Split on semicolons that are NOT inside dollar-quoted blocks
    statements = _split_sql(raw_sql)

    with engine.connect() as conn:
        for stmt in statements:
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        conn.commit()


def _split_sql(sql):
    """
    Split a SQL script into individual statements on semicolons while
    correctly preserving dollar-quoted DO-blocks as atomic units.
    Empty statements (e.g., from consecutive semicolons or trailing comments)
    are discarded.
    """
    statements = []
    buf        = []
    in_dollar  = False
    dollar_tag = None
    i          = 0
    n          = len(sql)

    while i < n:
        ch = sql[i]

        # Detect single-line comment (-- ...) outside dollar-quote: skip to newline
        if not in_dollar and ch == '-' and i + 1 < n and sql[i + 1] == '-':
            j = sql.find('\n', i)
            if j == -1:
                break
            buf.append(sql[i:j + 1])
            i = j + 1
            continue

        # Detect opening of a dollar-quoted block
        if not in_dollar and ch == '$':
            j = sql.find('$', i + 1)
            if j != -1:
                tag        = sql[i:j + 1]
                in_dollar  = True
                dollar_tag = tag
                buf.append(tag)
                i = j + 1
                continue

        # Detect closing of a dollar-quoted block
        if in_dollar and dollar_tag and sql[i:i + len(dollar_tag)] == dollar_tag:
            buf.append(dollar_tag)
            i         += len(dollar_tag)
            in_dollar  = False
            dollar_tag = None
            continue

        # Statement terminator outside a dollar-quoted block
        if not in_dollar and ch == ';':
            stmt = ''.join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i  += 1
            continue

        buf.append(ch)
        i += 1

    # Flush any trailing content
    remaining = ''.join(buf).strip()
    if remaining:
        statements.append(remaining)

    return statements


def ingest_tap_events(engine, df_demand):
    """
    Sample 10% of demand records and generate synthetic tap-card events.
    Uses PostgreSQL COPY for bulk ingestion throughput.
    """
    df_sample = df_demand.sample(frac=0.10, random_state=42)
    events = []

    for _, row in df_sample.iterrows():
        n_taps = max(1, int(row['demand']))
        for _ in range(min(n_taps, 5)):
            minute   = np.random.randint(0, 60)
            second   = np.random.randint(0, 60)
            tap_time = row['timestamp'] + timedelta(minutes=int(minute), seconds=int(second))
            card_id  = f"NEPAL_CARD_{np.random.randint(10000, 99999)}"
            events.append((card_id, row['stop_id'], 'IN', tap_time))

    df_events = pd.DataFrame(events, columns=['card_id', 'stop_id', 'tap_type', 'tap_timestamp'])

    raw_conn = engine.raw_connection()
    try:
        with raw_conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE tap_events CASCADE;")
            s_buf = io.StringIO()
            df_events.to_csv(s_buf, index=False, header=False)
            s_buf.seek(0)
            cur.copy_expert(
                "COPY tap_events (card_id, stop_id, tap_type, tap_timestamp) FROM STDIN WITH CSV",
                s_buf
            )
        raw_conn.commit()
    finally:
        raw_conn.close()
    print(f"Tap events ingested: {len(df_events):,} records.")


if __name__ == "__main__":
    generate_synthetic_transit_data()
