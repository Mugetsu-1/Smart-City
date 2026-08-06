import pandas as pd
import numpy as np
from sklearn.cluster import KMeans

def generate_schedule_recommendations(df_stops, df_predictions, capacity_per_bus=60):
    """
    Computes occupancy ratios, performs spatial hotspot clustering on congested stops,
    and generates automated dispatch recommendations for Nepal transit authorities.
    """
    merged = df_predictions.merge(df_stops, on='stop_id')
    merged['occupancy_ratio'] = merged['predicted_demand'] / capacity_per_bus
    
    recommendations = []
    for idx, row in merged.iterrows():
        ratio = row['occupancy_ratio']
        stop_name = row['stop_name']
        route_id = row['route_id']
        pred_demand = int(row['predicted_demand'])
        
        if ratio > 1.5:
            if "Kalanki" in stop_name:
                action = f"CRITICAL OVERCROWDING at {stop_name}: Inject 2 short-turn express buses toward Ratna Park and reduce headway by 5 minutes."
            elif "Gongabu" in stop_name or "Thankot" in stop_name:
                action = f"CRITICAL OVERCROWDING at {stop_name}: Deploy 3 high-capacity long-distance coaches for highway passenger exit."
            elif "Ratna Park" in stop_name or "Lagankhel" in stop_name:
                action = f"CRITICAL OVERCROWDING at {stop_name}: Inject 2 Sajha Yatayat buses along corridor and cut headway by 4 minutes."
            else:
                action = f"CRITICAL OVERCROWDING at {stop_name}: Inject 2 express buses immediately and decrease headway by 5 minutes."
            level = "RED"
        elif ratio > 1.0:
            action = f"HIGH DEMAND at {stop_name}: Reduce headway by 3 minutes and dispatch supplemental local microbuses."
            level = "AMBER"
        elif ratio < 0.25:
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
            'action_recommended': action,
            'alert_level': level,
            'latitude': row['latitude'],
            'longitude': row['longitude']
        })
        
    df_rec = pd.DataFrame(recommendations)
    
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
