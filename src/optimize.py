import pandas as pd
from sklearn.cluster import KMeans

def generate_schedule_recommendations(df_stops, df_predictions, capacity_per_bus=60):
    """
    Computes occupancy ratio and generates schedule recommendations for each stop.
    Performs K-Means clustering on high-demand hotspots.
    """
    # Merge predictions with stops info to get names and coordinates
    merged = df_predictions.merge(df_stops, on='stop_id')
    merged['occupancy_ratio'] = merged['predicted_demand'] / capacity_per_bus
    
    recommendations = []
    for idx, row in merged.iterrows():
        ratio = row['occupancy_ratio']
        if ratio > 1.5:
            action = "CRITICAL OVERCROWDING: Inject 2 Express Buses immediately & reduce headway by 5 mins."
            level = "RED"
        elif ratio > 1.0:
            action = "HIGH DEMAND: Reduce headway by 3 mins or deploy high-capacity double-decker."
            level = "AMBER"
        elif ratio < 0.25:
            action = "UNDERUTILIZED: Extend headway by 10 mins or re-route fleet to priority corridor."
            level = "GREEN"
        else:
            action = "NORMAL OPERATION: Maintain scheduled timetable."
            level = "NORMAL"
            
        recommendations.append({
            'stop_id': row['stop_id'],
            'stop_name': row['stop_name'],
            'route_id': row['route_id'],
            'predicted_demand': int(row['predicted_demand']),
            'occupancy_ratio': round(ratio, 2),
            'action_recommended': action,
            'alert_level': level,
            'latitude': row['latitude'],
            'longitude': row['longitude']
        })
        
    df_rec = pd.DataFrame(recommendations)
    
    # Cluster High Demand Hotspots
    high_demand_stops = df_rec[df_rec['alert_level'].isin(['RED', 'AMBER'])].copy()
    
    if len(high_demand_stops) >= 3:
        kmeans = KMeans(n_clusters=min(3, len(high_demand_stops)), random_state=42)
        high_demand_stops['hotspot_cluster'] = kmeans.fit_predict(
            high_demand_stops[['latitude', 'longitude']]
        )
    else:
        # Create an empty column if there are not enough stops to cluster
        high_demand_stops['hotspot_cluster'] = None
        
    return df_rec, high_demand_stops
