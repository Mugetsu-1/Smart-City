import os
import re
import time
from datetime import datetime

import requests
import pandas as pd

# ---------------------------------------------------------------
# Real Nepal data sources only.
# Primary source: Department of Roads (DOR) SSRN public traffic
# count portal. No synthetic data is used anywhere in this project.
# ---------------------------------------------------------------
DOR_TRAFFIC_SUMMARY_URL = "https://ssrn.dor.gov.np/traffic_controller/get_summary"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
STOPS_CACHE_PATH = os.path.join(DATA_DIR, "dor_traffic_stops.csv")
DEMAND_CACHE_PATH = os.path.join(DATA_DIR, "dor_traffic_demand.csv")

HEADERS = {
    "User-Agent": "smart-city-transit-nepal/1.0 (Kathmandu transit dashboard, public DOR data)"
}
CACHE_MAX_AGE_HOURS = 12

# Official Kathmandu Valley count station names exactly as listed in the
# DOR SSRN portal dropdown (options 58-74, 157-160 on the portal).
KATHMANDU_TRAFFIC_LOCATIONS = [
    "Ring Road (Manohara Bridge)",
    "Ring Road (Balkhu East)",
    "Ring Road (Sinamangal)",
    "Ring Road (Narayan Gopal Chowk)",
    "Ring Road (Banasthali)",
    "Chabahil East",
    "Jorpati North",
    "Gangalal Hospital North",
    "Balaju Bypass North",
    "T.U. Gate",
    "Taudaha",
    "Kalanki",
    "Gwarko East",
    "Byasi Chowk North",
    "Satdobato North",
    "Satdobato South (Chapagaun)",
    "Satdobato Junction South",
    "Manohara Bridge",
    "Kharipati",
    "Hanumante Bridge",
    "Nagdhunga",
]

DOR_FETCH_DELAY_SECONDS = 1.2
DOR_MIN_STATIONS = 10


def _strip_html(text):
    return re.sub(r"<[^>]+>", "", text)


def _extract_yearly_traffic_rows(html_text):
    """Parse the DOR get_summary HTML table into yearly traffic rows."""
    rows = []
    pattern = re.compile(
        r"<tr>\s*<td>(\d+)</td>\s*<td>([^<]+)</td>\s*<td>([^<]+)</td>\s*"
        r"<td>([\d,]+)</td>\s*<td>([\d,]+)</td>\s*<td>([\d,]+)</td>\s*"
        r"<td>([\d,]+)</td>\s*<td>([^<]+)</td>\s*<td><a href=\"([^\"]+)\"",
        re.S,
    )
    for match in pattern.finditer(html_text):
        rows.append(
            {
                "station_no": int(match.group(1)),
                "road_link": _strip_html(match.group(2)).strip(),
                "location": _strip_html(match.group(3)).strip(),
                "aadt": int(match.group(4).replace(",", "")),
                "aadt_excluding_mc": int(match.group(5).replace(",", "")),
                "aadt_pcu": int(match.group(6).replace(",", "")),
                "aadt_pcu_excluding_mc": int(match.group(7).replace(",", "")),
                "year": _strip_html(match.group(8)).strip(),
                "detail_url": match.group(9),
            }
        )
    return rows


_CELL_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def _extract_detail_rows(html_text):
    """Parse the DOR station detail page, which contains one row per fiscal
    year for the station (the summary page only shows the first of these).
    Returns the full multi-year series as a list of dicts."""
    rows = []
    table = re.search(r'<table class="[-a-z ]*link-table.*?</table>', html_text, re.S)
    if not table:
        return rows
    for part in re.split(r"</tr>", table.group(0)):
        if "<th" in part:
            continue
        cells = [re.sub(r"\s+", " ", c).strip() for c in _CELL_RE.findall(part)]
        if len(cells) < 9:
            continue
        year_cell = cells[7].strip()
        if not re.fullmatch(r"\d{4}/\d{2}", year_cell):
            continue
        try:
            station_no = int(cells[0])
            aadt = int(cells[3].replace(",", ""))
            aadt_pcu = int(cells[5].replace(",", ""))
        except ValueError:
            continue
        url_match = re.search(r'href="([^"]+)"', cells[8])
        rows.append(
            {
                "station_no": station_no,
                "road_link": cells[1].replace("&amp;", "&").strip(),
                "location": cells[2].replace("&amp;", "&").strip(),
                "aadt": aadt,
                "aadt_excluding_mc": int(cells[4].replace(",", "")),
                "aadt_pcu": aadt_pcu,
                "aadt_pcu_excluding_mc": int(cells[6].replace(",", "")),
                "year": year_cell,
                "detail_url": url_match.group(1) if url_match else "",
            }
        )
    return rows


def _fetch_station_series(location):
    """Fetch every published year for a DOR station. The summary endpoint
    only reveals the first year row; the detail page holds the full
    multi-year series (2011/12 .. most recently published)."""
    resp = requests.post(
        DOR_TRAFFIC_SUMMARY_URL,
        data={"location": location},
        headers=HEADERS,
        timeout=120,
    )
    resp.raise_for_status()
    summary_rows = _extract_yearly_traffic_rows(resp.text)
    if not summary_rows:
        return []
    detail_url = summary_rows[0]["detail_url"]
    try:
        detail_resp = requests.get(detail_url, headers=HEADERS, timeout=120)
        detail_resp.raise_for_status()
        series = _extract_detail_rows(detail_resp.text)
        if series:
            return series
    except Exception:
        pass
    return summary_rows


# Curated reference coordinates for the real DOR stations. These are the
# known geographic locations (lat, lon) of the official count stations;
# they exist to place real station data on the map when the geocoding
# service is unavailable. No demand values are fabricated.
STATION_REFERENCE_COORDS = {
    "Ring Road (Manohara Bridge)": (27.7045, 85.3715),
    "Ring Road (Balkhu East)": (27.6766, 85.2830),
    "Ring Road (Sinamangal)": (27.6988, 85.3541),
    "Ring Road (Narayan Gopal Chowk)": (27.7410, 85.3330),
    "Ring Road (Banasthali)": (27.7260, 85.2985),
    "Chabahil East": (27.7185, 85.3465),
    "Jorpati North": (27.7340, 85.3740),
    "Gangalal Hospital North": (27.7170, 85.3445),
    "Balaju Bypass North": (27.7325, 85.3055),
    "T.U. Gate": (27.7160, 85.3190),
    "Taudaha": (27.6350, 85.2925),
    "Kalanki": (27.6931, 85.2806),
    "Gwarko East": (27.6802, 85.3410),
    "Byasi Chowk North": (27.6860, 85.3085),
    "Satdobato North": (27.6578, 85.3241),
    "Satdobato South (Chapagaun)": (27.6380, 85.3330),
    "Satdobato Junction South": (27.6680, 85.3300),
    "Manohara Bridge": (27.7100, 85.3690),
    "Kharipati": (27.6719, 85.4090),
    "Hanumante Bridge": (27.6739, 85.4120),
    "Nagdhunga": (27.6920, 85.2320),
}


def _geocode_location(query):
    """Geocode a real DOR station name. Several query phrasings are tried;
    falls back to the curated reference coordinates from above the
    service is unreachable."""
    fallback = STATION_REFERENCE_COORDS.get(query)
    phrasings = [
        f"{query}, Kathmandu, Nepal",
        f"{query}, Nepal",
        f"{query.replace(' (', ', ').replace(')', '')}, Kathmandu",
    ]
    for q in phrasings:
        params = {"q": q, "format": "jsonv2", "limit": 1}
        try:
            resp = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=45)
            resp.raise_for_status()
            data = resp.json()
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception:
            return fallback if fallback else (27.7172, 85.3240)
    return fallback if fallback else (27.7172, 85.3240)


def _map_kathmandu_route(location):
    lowered = location.lower()
    if "ring road" in lowered or "kalanki" in lowered or "balkhu" in lowered or "balaju" in lowered:
        return "Ring Road Corridor"
    if "chabahil" in lowered or "jorpati" in lowered or "gangalal" in lowered:
        return "Chabahil - Jorpati Corridor"
    if "satdobato" in lowered or "gwarko" in lowered or "byasi" in lowered:
        return "Ratna Park - Lagankhel Corridor"
    if "nagdhunga" in lowered or "taudaha" in lowered:
        return "Tribhuvan Rajpath Corridor"
    if "kharipati" in lowered or "hanumante" in lowered or "manohara" in lowered:
        return "Arniko Highway Corridor"
    return "Kathmandu Valley Corridor"


def _set_station_capacities(df):
    """Map each station onto one of five capacity tiers (250-2500 pax/hr)
    ranked by its MOST RECENTLY PUBLISHED real AADT. The tier value is then
    broadcast to every historical row of that station so the dashboard
    snapshot and the multi-year history stay consistent."""
    df = df.copy()
    latest = df.sort_values("timestamp").groupby("stop_id", as_index=False).tail(1)
    latest = latest.copy()
    latest["capacity_tier"] = pd.qcut(
        latest["aadt_pcu"], 5, labels=False, duplicates="drop"
    )
    cap_map = {0: 250, 1: 500, 2: 900, 3: 1500, 4: 2500}
    cap_by_stop = latest.set_index("stop_id")["capacity_tier"].map(cap_map).astype(int)
    df["capacity_limit"] = df["stop_id"].map(cap_by_stop).fillna(250).astype(int)
    return df.drop(columns=[c for c in ["sort_key"] if c in df.columns])


def _build_station_frame():
    """Scrape the public DOR portal and return the full multi-year Kathmandu
    traffic count series (one row per station per published fiscal year)."""
    print("Scraping Department of Roads (DOR) Kathmandu traffic portal (all published years)...")
    collected = []
    for location in KATHMANDU_TRAFFIC_LOCATIONS:
        try:
            series = _fetch_station_series(location)
            if series:
                collected.extend(series)
                years = sorted({r["year"] for r in series})
                print(
                    f"  DOR: {location} -> {len(series)} counts "
                    f"(latest {series[-1]['year']}: {series[-1]['aadt_pcu']} PCU)"
                )
        except Exception as exc:
            print(f"  DOR: {location} failed ({exc})")
        time.sleep(DOR_FETCH_DELAY_SECONDS)

    if len(collected) < DOR_MIN_STATIONS:
        raise RuntimeError(
            f"DOR portal returned only {len(collected)} Kathmandu station rows "
            f"(minimum {DOR_MIN_STATIONS}). Check network access to ssrn.dor.gov.np."
        )

    df = pd.DataFrame(collected)
    df = (
        df.sort_values(["station_no", "year"])
        .drop_duplicates(subset=["station_no", "year"])
        .reset_index(drop=True)
    )

    # Timestamp = 1 January of the fiscal year end (DOR fiscal-year counts).
    df["timestamp"] = pd.to_datetime(
        (df["year"].str[:4].astype(int) + 1).astype(str), format="%Y", errors="coerce"
    ).dt.normalize()
    df["sort_key"] = df["year"].str[:4].astype(int)
    df["demand"] = (df["aadt_pcu"] / 24.0).round().astype(int)
    df["stop_id"] = df["location"].str.replace(r"[^A-Za-z0-9]+", "_", regex=True).str.strip("_")
    df["stop_name"] = df["location"]
    df["route_id"] = df["location"].apply(_map_kathmandu_route)
    df["data_source"] = "dor_traffic_portal"
    df["traffic_year"] = df["year"]
    df["traffic_station_no"] = df["station_no"]
    df["traffic_road_link"] = df["road_link"]
    df["traffic_aadt"] = df["aadt"]
    df["traffic_aadt_pcu"] = df["aadt_pcu"]

    stations = df[["station_no", "location", "stop_name"]].drop_duplicates("station_no")
    print(f"Geocoding {len(stations)} real stations via OpenStreetMap Nominatim...")
    coords_by_location = {}
    for _, row in stations.iterrows():
        coords_by_location[row["location"]] = _geocode_location(row["location"])
        time.sleep(1.0)
    df["latitude"] = df["location"].map(lambda loc: coords_by_location[loc][0])
    df["longitude"] = df["location"].map(lambda loc: coords_by_location[loc][1])

    df = _set_station_capacities(df)
    df["fetched_at"] = pd.Timestamp.now(tz="Asia/Katmandu").isoformat()
    return df


def _cache_is_fresh():
    if not os.path.exists(DEMAND_CACHE_PATH):
        return False
    age_hours = (
        datetime.now() - datetime.fromtimestamp(os.path.getmtime(DEMAND_CACHE_PATH))
    ).total_seconds() / 3600.0
    return age_hours <= CACHE_MAX_AGE_HOURS


def _store_cache(df):
    os.makedirs(DATA_DIR, exist_ok=True)
    stops = (
        df[["stop_id", "stop_name", "route_id", "capacity_limit", "latitude", "longitude"]]
        .drop_duplicates(subset=["stop_id"])
        .copy()
    )
    stops["data_source"] = "dor_traffic_portal"
    df.to_csv(DEMAND_CACHE_PATH, index=False)
    stops.to_csv(STOPS_CACHE_PATH, index=False)


def _load_cache():
    try:
        demand = pd.read_csv(DEMAND_CACHE_PATH, parse_dates=["timestamp"])
        if demand.empty:
            return None
        return demand
    except Exception:
        return None


def fetch_dor_kathmandu_traffic(force_refresh=False):
    """Real Kathmandu traffic counts from the DOR portal.

    Uses the on-disk real snapshot (fast, no network) unless
    force_refresh=True, which re-scrapes the government portal and
    refreshes the snapshot files.
    """
    if not force_refresh and _cache_is_fresh():
        cached = _load_cache()
        if cached is not None:
            return cached
    df = _build_station_frame()
    _store_cache(df)
    return df


def load_transit_stops(force_refresh=False):
    df = fetch_dor_kathmandu_traffic(force_refresh=force_refresh)
    return (
        df[["stop_id", "stop_name", "route_id", "capacity_limit", "latitude", "longitude"]]
        .drop_duplicates(subset=["stop_id"])
        .copy()
    )


def load_demand_feed(force_refresh=False):
    return fetch_dor_kathmandu_traffic(force_refresh=force_refresh)