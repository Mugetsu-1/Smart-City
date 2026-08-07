import pandas as pd
import numpy as np
from sklearn.cluster import KMeans

def generate_schedule_recommendations(df_stops, df_predictions, capacity_per_bus=60):
    """
    Computes occupancy ratios, performs spatial hotspot clustering on congested stops,
    and generates automated dispatch recommendations for Nepal transit authorities.
    """
    merged = df_predictions.merge(df_stops, on='stop_id', how='inner')
    if merged.empty:
        empty_rec = pd.DataFrame(columns=[
            'stop_id', 'stop_name', 'route_id', 'predicted_demand', 'occupancy_ratio',
            'effective_capacity', 'recommended_additional_buses', 'recommended_headway_change_min',
            'action_recommended', 'alert_level', 'latitude', 'longitude'
        ])
        empty_hotspots = pd.DataFrame(columns=list(empty_rec.columns) + ['hotspot_cluster'])
        return empty_rec, empty_hotspots
    merged['predicted_demand'] = pd.to_numeric(merged['predicted_demand'], errors='coerce').fillna(0)
    if 'capacity_limit' in merged.columns:
        merged['effective_capacity'] = pd.to_numeric(merged['capacity_limit'], errors='coerce').fillna(capacity_per_bus)
    else:
        merged['effective_capacity'] = capacity_per_bus
    merged['effective_capacity'] = merged['effective_capacity'].clip(lower=max(15, capacity_per_bus * 0.5))
    merged['occupancy_ratio'] = (merged['predicted_demand'] / merged['effective_capacity']).fillna(0)
    merged['fleet_pressure'] = (merged['occupancy_ratio'] * (merged['predicted_demand'] / merged['predicted_demand'].clip(lower=1).mean())).fillna(0)
    
    recommendations = []
    for idx, row in merged.iterrows():
        ratio = float(row['occupancy_ratio']) if pd.notna(row['occupancy_ratio']) else 0.0
        effective_capacity = float(row['effective_capacity']) if pd.notna(row['effective_capacity']) else float(capacity_per_bus)
        stop_name = row['stop_name']
        route_id = row['route_id']
        pred_demand = int(max(0, round(float(row['predicted_demand']))))
        headway_delta = 0
        extra_buses = 0
        
        if ratio >= 1.8:
            extra_buses = max(1, int(np.ceil((pred_demand - effective_capacity) / capacity_per_bus)))
            headway_delta = -max(5, int(round((ratio - 1.0) * 4)))
            if "Kalanki" in stop_name:
                action = f"CRITICAL OVERCROWDING at {stop_name}: Inject 2 short-turn express buses toward Ratna Park and reduce headway by 5 minutes."
            elif "Gongabu" in stop_name or "Thankot" in stop_name:
                action = f"CRITICAL OVERCROWDING at {stop_name}: Deploy 3 high-capacity long-distance coaches for highway passenger exit."
            elif "Ratna Park" in stop_name or "Lagankhel" in stop_name:
                action = f"CRITICAL OVERCROWDING at {stop_name}: Inject 2 Sajha Yatayat buses along corridor and cut headway by 4 minutes."
            else:
                action = f"CRITICAL OVERCROWDING at {stop_name}: Inject 2 express buses immediately and decrease headway by 5 minutes."
            level = "RED"
        elif ratio >= 1.1:
            extra_buses = max(1, int(np.ceil((pred_demand - effective_capacity) / capacity_per_bus)))
            headway_delta = -max(3, int(round((ratio - 1.0) * 3)))
            action = f"HIGH DEMAND at {stop_name}: Reduce headway by 3 minutes and dispatch supplemental local microbuses."
            level = "AMBER"
        elif ratio <= 0.55:
            headway_delta = max(5, int(round((0.55 - ratio) * 12)))
            action = f"UNDERUTILIZED at {stop_name}: Extend headway by 10 minutes or re-route fleet to congested Ring Road hubs."
            level = "BLUE"
        else:
            action = f"NORMAL OPERATION at {stop_name}: Maintain scheduled timetable."
            level = "GREEN"
            
        recommendations.append({
            'stop_id': row['stop_id'],
            'stop_name': stop_name,
            'route_id': route_id,
            'predicted_demand': pred_demand,
            'occupancy_ratio': round(ratio, 2),
            'effective_capacity': int(round(effective_capacity)),
            'recommended_additional_buses': int(extra_buses),
            'recommended_headway_change_min': int(headway_delta),
            'action_recommended': action,
            'alert_level': level,
            'latitude': row['latitude'],
            'longitude': row['longitude']
        })
        
    df_rec = pd.DataFrame(recommendations)

    # Corridor-level dispatch summary so operations can act on a route, not just a stop.
    if len(df_rec) > 0:
        route_summary = (
            df_rec.groupby('route_id', as_index=False)
            .agg(
                corridor_predicted_demand=('predicted_demand', 'sum'),
                corridor_avg_occupancy=('occupancy_ratio', 'mean'),
                corridor_peak_occupancy=('occupancy_ratio', 'max'),
                critical_stops=('alert_level', lambda s: int(s.isin(['RED', 'AMBER']).sum())),
                stops_in_cascade=('stop_id', 'count')
            )
        )
        route_summary['corridor_recommended_buses'] = np.ceil(
            route_summary['corridor_predicted_demand'] / float(capacity_per_bus)
        ).astype(int)
        route_summary['corridor_headway_change_min'] = np.select(
            [
                route_summary['corridor_peak_occupancy'] >= 1.8,
                route_summary['corridor_peak_occupancy'] >= 1.1,
                route_summary['corridor_peak_occupancy'] <= 0.55,
            ],
            [-5, -3, 8],
            default=0
        )
        route_summary['corridor_action'] = np.where(
            route_summary['corridor_peak_occupancy'] >= 1.8,
            'Deploy express reinforcement and hold short-turn service on this corridor.',
            np.where(
                route_summary['corridor_peak_occupancy'] >= 1.1,
                'Add supplemental buses and tighten headway across the corridor.',
                np.where(
                    route_summary['corridor_peak_occupancy'] <= 0.55,
                    'Reduce frequency and redeploy idle buses to higher-pressure corridors.',
                    'Maintain scheduled service with monitoring.'
                )
            )
        )
        df_rec = df_rec.merge(route_summary, on='route_id', how='left')
    
    # Perform Spatial Hotspot Clustering on High-Demand Stops (RED and AMBER)
    high_demand_stops = df_rec[df_rec['alert_level'].isin(['RED', 'AMBER'])].copy()
    
    if len(high_demand_stops) >= 3:
        try:
            # Weighted coordinates by demand for K-Means clustering
            coords = high_demand_stops[['latitude', 'longitude']].values
            weights = high_demand_stops['predicted_demand'].values
            n_clusters = min(3, len(high_demand_stops))
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            kmeans.fit(coords, sample_weight=weights)
            high_demand_stops['hotspot_cluster'] = kmeans.labels_
        except Exception as e:
            high_demand_stops['hotspot_cluster'] = [i % 3 for i in range(len(high_demand_stops))]
    else:
        high_demand_stops['hotspot_cluster'] = None
        
    return df_rec, high_demand_stops
