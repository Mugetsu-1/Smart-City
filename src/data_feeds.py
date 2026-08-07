import os
import pandas as pd

from src.fetch_real_nepal_data import fetch_kathmandu_weather_snapshot

REAL_STOPS_PATHS = [
    "data/kathmandu_real_stops_yatayat.csv",
    "data/kathmandu_real_stops_osm.csv",
]

LIVE_DEMAND_PATHS = [
    "data/live_operator_demand.csv",
    "data/live_demand.csv",
]

MODELLED_DEMAND_PATHS = [
    "data/synthetic_transit_demand.csv",
]

MODELLED_STOPS_PATH = "data/synthetic_transit_stops.csv"


def _load_first_existing_csv(paths, parse_dates=None):
    for path in paths:
        if os.path.exists(path):
            return pd.read_csv(path, parse_dates=parse_dates)
    return None


def load_transit_stops():
    df = _load_first_existing_csv(REAL_STOPS_PATHS)
    if df is not None:
        if 'route_id' not in df.columns:
            df['route_id'] = 'Kathmandu Transit'
        if 'capacity_limit' not in df.columns:
            df['capacity_limit'] = 60
        df['data_source'] = 'real_network'
        return df

    df = pd.read_csv(MODELLED_STOPS_PATH)
    df['data_source'] = 'modeled_network'
    return df


def load_weather_snapshot():
    return fetch_kathmandu_weather_snapshot()


def load_demand_feed():
    """
    Priority order:
    1. live_operator_demand.csv or live_demand.csv if a real feed is dropped in
    2. the existing modeled historical demand
    """
    df = _load_first_existing_csv(LIVE_DEMAND_PATHS, parse_dates=['timestamp'])
    if df is not None:
        df['data_source'] = 'live_operator'
        return df

    df = _load_first_existing_csv(MODELLED_DEMAND_PATHS, parse_dates=['timestamp'])
    if df is not None:
        df['data_source'] = 'modeled_history'
        return df

    raise FileNotFoundError("No demand feed found.")


def annotate_demand_source(df, source_label):
    if df is None:
        return df
    df = df.copy()
    df['data_source'] = source_label
    return df


def load_operational_bundle():
    return {
        "stops": load_transit_stops(),
        "demand": load_demand_feed(),
        "weather": load_weather_snapshot(),
    }
