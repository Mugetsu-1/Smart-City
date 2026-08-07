import sys
import os
import pandas as pd
from sqlalchemy import create_engine

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.optimize import generate_schedule_recommendations

DB_CONN = "postgresql://postgres:postgrespassword@localhost:5433/transit_db"


def main():
    print("Testing dynamic schedule optimization engine...")

    # Always use the full CSV demand data for optimization testing.
    # The materialized view aggregates tap-card events (10% sample, max 5 taps per record),
    # which produces artificially low demand counts not representative of actual passenger load.
    # The CSV contains the full simulated demand values used for model training.
    stops_df  = pd.read_csv("data/synthetic_transit_stops.csv")
    raw_demand = pd.read_csv("data/synthetic_transit_demand.csv")
    latest_ts = raw_demand['timestamp'].max()
    demand_df = (
        raw_demand[raw_demand['timestamp'] == latest_ts][['stop_id', 'demand']]
        .rename(columns={'demand': 'predicted_demand'})
    )
    print(f"Loaded {len(demand_df)} stops from CSV (timestamp: {latest_ts}).")

    print("Generating optimization recommendations based on demand...")
    df_rec, df_hotspots = generate_schedule_recommendations(stops_df, demand_df)

    print("\n=== Top 5 Congested Transit Stops ===")
    critical = df_rec.sort_values(by='occupancy_ratio', ascending=False).head(5)
    for _, row in critical.iterrows():
        print(f"  {row['stop_name']} ({row['route_id']})")
        print(f"    Demand    : {row['predicted_demand']} passengers/hr")
        print(f"    Occupancy : {row['occupancy_ratio']:.2f}")
        print(f"    Action    : {row['action_recommended']} [{row['alert_level']}]\n")

    red_count   = len(df_rec[df_rec['alert_level'] == 'RED'])
    amber_count = len(df_rec[df_rec['alert_level'] == 'AMBER'])
    blue_count  = len(df_rec[df_rec['alert_level'] == 'BLUE'])
    green_count = len(df_rec[df_rec['alert_level'] == 'GREEN'])
    print(f"Alert Summary: RED={red_count}  AMBER={amber_count}  GREEN={green_count}  BLUE={blue_count}")
    print(f"Total Hotspot Stops Detected (RED/AMBER): {len(df_hotspots)}")

    if (
        len(df_hotspots) > 0
        and 'hotspot_cluster' in df_hotspots.columns
        and df_hotspots['hotspot_cluster'].notnull().any()
    ):
        n_clusters = df_hotspots['hotspot_cluster'].nunique()
        print(f"Hotspots grouped into {n_clusters} spatial clusters for express routing.")


if __name__ == "__main__":
    main()
