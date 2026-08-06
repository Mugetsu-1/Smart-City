import sys
import os
import pandas as pd
import psycopg2

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.optimize import generate_schedule_recommendations

DB_CONN = "postgresql://postgres:postgrespassword@localhost:5433/transit_db"

def main():
    print("Testing dynamic schedule optimization engine...")
    try:
        conn = psycopg2.connect(DB_CONN)
        stops_df = pd.read_sql_query("SELECT stop_id, stop_name, route_id, ST_Y(location) as latitude, ST_X(location) as longitude FROM bus_stops", conn)
        demand_df = pd.read_sql_query("""
            SELECT mv.stop_id, mv.tap_in_count as predicted_demand
            FROM mv_hourly_stop_demand mv
            WHERE mv.demand_hour = (SELECT MAX(demand_hour) FROM mv_hourly_stop_demand)
        """, conn)
        conn.close()
        print("Loaded data from PostgreSQL database.")
    except Exception as e:
        print(f"PostgreSQL connection bypass ({e}). Loading fallback CSV datasets.")
        stops_df = pd.read_csv("data/synthetic_transit_stops.csv")
        raw_demand = pd.read_csv("data/synthetic_transit_demand.csv")
        latest_ts = raw_demand['timestamp'].max()
        demand_df = raw_demand[raw_demand['timestamp'] == latest_ts][['stop_id', 'demand']].rename(columns={'demand': 'predicted_demand'})

    print("Generating optimization recommendations based on demand...")
    df_rec, df_hotspots = generate_schedule_recommendations(stops_df, demand_df)
    
    print("\n=== Top 5 Congested Transit Stops ===")
    critical = df_rec.sort_values(by='occupancy_ratio', ascending=False).head(5)
    for _, row in critical.iterrows():
        print(f"- {row['stop_name']} ({row['route_id']})")
        print(f"  Demand: {row['predicted_demand']} passengers | Occupancy: {row['occupancy_ratio']:.2f}")
        print(f"  Action: {row['action_recommended']} [{row['alert_level']}]\n")
        
    print(f"Total Hotspot Stops Detected (RED/AMBER): {len(df_hotspots)}")
    if len(df_hotspots) > 0 and 'hotspot_cluster' in df_hotspots.columns and df_hotspots['hotspot_cluster'].notnull().any():
        print(f"Hotspots grouped into {df_hotspots['hotspot_cluster'].nunique()} spatial clusters for express routing.")

if __name__ == "__main__":
    main()
