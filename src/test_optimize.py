import sys
import os

import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from src.optimize import generate_schedule_recommendations
from src.data_feeds import load_demand_feed, load_transit_stops


def main():
    print("Testing dynamic schedule optimization engine (real DOR traffic feed)...")

    demand_raw = load_demand_feed()
    stops_df = load_transit_stops()

    latest_ts = demand_raw["timestamp"].max()
    demand_df = (
        demand_raw.sort_values("timestamp")
        .groupby("stop_id", as_index=False)
        .tail(1)[["stop_id", "demand"]]
        .rename(columns={"demand": "predicted_demand"})
        .copy()
    )
    print(f"Loaded {len(demand_df)} real stations (latest published year: {latest_ts.year}).")

    print("Generating optimization recommendations based on demand...")
    df_rec, df_hotspots = generate_schedule_recommendations(stops_df, demand_df)

    print("\n=== Top 5 Congested Transit Stops ===")
    critical = df_rec.sort_values(by="occupancy_ratio", ascending=False).head(5)
    for _, row in critical.iterrows():
        print(f"  {row['stop_name']} ({row['route_id']})")
        print(f"    Demand    : {row['predicted_demand']} pcu/hr")
        print(f"    Occupancy : {row['occupancy_ratio']:.2f}")
        print(f"    Action    : {row['action_recommended']} [{row['alert_level']}]\n")

    red_count = len(df_rec[df_rec["alert_level"] == "RED"])
    amber_count = len(df_rec[df_rec["alert_level"] == "AMBER"])
    blue_count = len(df_rec[df_rec["alert_level"] == "BLUE"])
    green_count = len(df_rec[df_rec["alert_level"] == "GREEN"])
    print(f"Alert Summary: RED={red_count}  AMBER={amber_count}  GREEN={green_count}  BLUE={blue_count}")
    print(f"Total Hotspot Stops Detected (RED/AMBER): {len(df_hotspots)}")

    if (
        len(df_hotspots) > 0
        and "hotspot_cluster" in df_hotspots.columns
        and df_hotspots["hotspot_cluster"].notnull().any()
    ):
        n_clusters = df_hotspots["hotspot_cluster"].nunique()
        print(f"Hotspots grouped into {n_clusters} spatial clusters for express routing.")


if __name__ == "__main__":
    main()