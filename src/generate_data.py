import io
import os
import sys

import pandas as pd
from sqlalchemy import create_engine, text

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from src.data_feeds import fetch_dor_kathmandu_traffic, load_transit_stops

DB_CONN_CANDIDATES = [
    "postgresql://postgres:postgrespassword@localhost:5433/transit_db",
    "postgresql://postgres:postgrespassword@localhost:5432/transit_db",
]


def refresh_real_data():
    """
    Refresh the real Kathmandu traffic dataset from the Department of Roads
    (DOR) SSRN public traffic portal and persist it as CSV snapshots.
    No synthetic data is generated anywhere in this pipeline.
    """
    print("Refreshing real traffic data from the DOR Kathmandu portal...")
    demand = fetch_dor_kathmandu_traffic(force_refresh=True)
    print(f"Captured {len(demand)} real station rows from the DOR portal.")

    print("\n--- Real DOR Kathmandu Traffic Snapshot (AADT, PCU) ---")
    summary = (
        demand[["location", "year", "aadt_pcu", "demand", "capacity_limit", "route_id"]]
        .sort_values("aadt_pcu", ascending=False)
    )
    print(summary.to_string(index=False))
    print(f"\nTotal observed daily traffic (PCU): {demand['aadt_pcu'].sum():,}")
    print(f"Total hourly system demand        : {demand['demand'].sum():,} pcu/hr")
    print("CSV snapshots saved to data/dor_traffic_demand.csv and data/dor_traffic_stops.csv")


def _find_db_engine():
    for conn_str in DB_CONN_CANDIDATES:
        try:
            engine = create_engine(conn_str)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except Exception:
            continue
    return None


def _execute_schema(engine):
    schema_path = os.path.join(os.path.dirname(__file__), "..", "sql", "schema.sql")
    with open(schema_path, "r") as f:
        raw_sql = f.read()
    for stmt in _split_sql(raw_sql):
        stmt = stmt.strip()
        if stmt:
            with engine.connect() as conn:
                conn.execute(text(stmt))
                conn.commit()


def _split_sql(sql):
    statements = []
    buf = []
    in_dollar = False
    dollar_tag = None
    i = 0
    n = len(sql)
    while i < n:
        ch = sql[i]
        if not in_dollar and ch == "-" and i + 1 < n and sql[i + 1] == "-":
            j = sql.find("\n", i)
            if j == -1:
                break
            buf.append(sql[i:j + 1])
            i = j + 1
            continue
        if not in_dollar and ch == "$":
            j = sql.find("$", i + 1)
            if j != -1:
                tag = sql[i:j + 1]
                in_dollar = True
                dollar_tag = tag
                buf.append(tag)
                i = j + 1
                continue
        if in_dollar and dollar_tag and sql[i:i + len(dollar_tag)] == dollar_tag:
            buf.append(dollar_tag)
            i += len(dollar_tag)
            in_dollar = False
            dollar_tag = None
            continue
        if not in_dollar and ch == ";":
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    remaining = "".join(buf).strip()
    if remaining:
        statements.append(remaining)
    return statements


def _ingest_to_postgres():
    print("\nAttempting to ingest real DOR data into PostgreSQL/PostGIS...")
    engine = _find_db_engine()
    if engine is None:
        print("PostgreSQL unavailable (checked :5433 and :5432).")
        print("The dashboard will run from the real CSV snapshots instead.")
        return

    try:
        _execute_schema(engine)

        stops = load_transit_stops()
        demand = fetch_dor_kathmandu_traffic()

        print("  Ingesting real bus stops...")
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE bus_stops CASCADE;"))
            for _, row in stops.iterrows():
                conn.execute(
                    text("""
                        INSERT INTO bus_stops (stop_id, stop_name, route_id, capacity_limit, location)
                        VALUES (:sid, :sname, :rid, :cap, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
                    """),
                    {
                        "sid": row["stop_id"],
                        "sname": row["stop_name"],
                        "rid": row["route_id"],
                        "cap": int(row["capacity_limit"]),
                        "lon": float(row["longitude"]),
                        "lat": float(row["latitude"]),
                    },
                )
            conn.commit()
        print(f"  Ingested {len(stops)} real bus stops.")

        print("  Ingesting real DOR traffic counts...")
        with engine.connect() as conn:
            conn.execute(text("TRUNCATE TABLE dor_traffic_demand;"))
            conn.commit()

        cols = ["station_no", "year", "location", "road_link", "aadt",
                "aadt_excluding_mc", "aadt_pcu", "aadt_pcu_excluding_mc",
                "demand", "capacity_limit", "route_id", "latitude", "longitude"]
        payload = demand[cols].copy()
        raw_conn = engine.raw_connection()
        try:
            with raw_conn.cursor() as cur:
                s_buf = io.StringIO()
                payload.to_csv(s_buf, index=False, header=False)
                s_buf.seek(0)
                cur.copy_expert(
                    "COPY dor_traffic_demand (station_no, year, location, road_link, aadt, "
                    "aadt_excluding_mc, aadt_pcu, aadt_pcu_excluding_mc, demand, capacity_limit, "
                    "route_id, latitude, longitude) FROM STDIN WITH CSV",
                    s_buf,
                )
            raw_conn.commit()
        finally:
            raw_conn.close()
        print(f"  Ingested {len(payload)} real traffic count rows.")
        engine.dispose()
        print("PostgreSQL ingestion completed (real DOR data only).")
    except Exception as exc:
        print(f"PostgreSQL ingestion skipped ({exc}).")
        print("The dashboard will run from the real CSV snapshots instead.")


if __name__ == "__main__":
    refresh_real_data()
    _ingest_to_postgres()
    print("\nBootstrap complete. Launch the dashboard with:")
    print("  .venv\\Scripts\\streamlit.exe run app/app.py")