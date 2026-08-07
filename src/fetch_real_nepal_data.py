import os
import json
import xml.etree.ElementTree as ET
from collections import defaultdict

import pandas as pd
import requests

YATAYAT_XML_URL = "https://raw.githubusercontent.com/monsooncollective/yatayat/gh-pages/transit.stable.xml"
DHM_URL = "https://www.dhm.gov.np/"


def fetch_yatayat_xml():
    headers = {"User-Agent": "smart-city-transit-nepal/1.0"}
    resp = requests.get(YATAYAT_XML_URL, headers=headers, timeout=180)
    resp.raise_for_status()
    return resp.text


def parse_yatayat_transit(xml_text):
    root = ET.fromstring(xml_text)
    nodes = {}
    stop_rows = []
    route_names_for_node = defaultdict(list)

    for node in root.findall("node"):
        node_id = node.attrib.get("id")
        lat = node.attrib.get("lat")
        lon = node.attrib.get("lon")
        tags = {tag.attrib.get("k"): tag.attrib.get("v") for tag in node.findall("tag")}
        name = tags.get("name") or tags.get("ref") or f"OSM_{node_id}"

        if tags.get("highway") == "bus_stop" or tags.get("public_transport") in {"platform", "stop_position"} or tags.get("amenity") == "bus_station":
            stop_rows.append(
                {
                    "stop_id": f"OSM_{node_id}",
                    "stop_name": name,
                    "route_id": tags.get("route_ref") or tags.get("network") or "Kathmandu Transit",
                    "latitude": float(lat) if lat else None,
                    "longitude": float(lon) if lon else None,
                    "source": "Yatayat / OpenStreetMap",
                }
            )

        nodes[node_id] = {
            "lat": float(lat) if lat else None,
            "lon": float(lon) if lon else None,
            "name": name,
        }

    # Build a lightweight route-to-stop association from route relations where possible.
    relation_meta = {}
    for relation in root.findall("relation"):
        tags = {tag.attrib.get("k"): tag.attrib.get("v") for tag in relation.findall("tag")}
        if tags.get("route") != "bus":
            continue
        rel_name = tags.get("name") or tags.get("ref") or tags.get("network") or "Kathmandu Bus Route"
        relation_meta[relation.attrib.get("id")] = rel_name
        for member in relation.findall("member"):
            if member.attrib.get("type") == "node":
                route_names_for_node[member.attrib.get("ref")].append(rel_name)

    for row in stop_rows:
        node_id = row["stop_id"].replace("OSM_", "")
        if route_names_for_node.get(node_id):
            row["route_id"] = route_names_for_node[node_id][0]

    df_stops = pd.DataFrame(stop_rows).drop_duplicates(subset=["stop_id"])
    return df_stops


def fetch_kathmandu_weather_snapshot():
    headers = {"User-Agent": "smart-city-transit-nepal/1.0"}
    resp = requests.get(DHM_URL, headers=headers, timeout=60)
    resp.raise_for_status()
    text = resp.text

    # Homepage text changes frequently; this is a conservative extract.
    return {
        "source": "DHM",
        "retrieved_at_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "contains_kathmandu_forecast_text": "Kathmandu" in text,
    }


def main():
    os.makedirs("data", exist_ok=True)

    xml_text = fetch_yatayat_xml()
    with open("data/yatayat_transit_stable.xml", "w", encoding="utf-8") as f:
        f.write(xml_text)

    stops = parse_yatayat_transit(xml_text)
    if stops.empty:
        raise RuntimeError("No Kathmandu transit stops were parsed from Yatayat XML.")

    stops_path = "data/kathmandu_real_stops_yatayat.csv"
    stops.to_csv(stops_path, index=False)
    print(f"Saved {len(stops)} real Kathmandu transit stops to {stops_path}")

    weather = fetch_kathmandu_weather_snapshot()
    weather_path = "data/kathmandu_real_weather_dhm.json"
    with open(weather_path, "w", encoding="utf-8") as f:
        json.dump(weather, f, indent=2)
    print(f"Saved Kathmandu weather snapshot to {weather_path}")


if __name__ == "__main__":
    main()
