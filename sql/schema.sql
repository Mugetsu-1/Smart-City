-- Enable PostGIS spatial extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Bus Stops Table
CREATE TABLE IF NOT EXISTS bus_stops (
    stop_id VARCHAR(50) PRIMARY KEY,
    stop_name VARCHAR(100) NOT NULL,
    route_id VARCHAR(50) NOT NULL,
    capacity_limit INT DEFAULT 60,
    location GEOMETRY(Point, 4326) NOT NULL
);

-- Spatial index for rapid proximity queries
CREATE INDEX IF NOT EXISTS idx_bus_stops_location ON bus_stops USING GIST(location);

-- 2. Passenger Tap Card Events Table
CREATE TABLE IF NOT EXISTS tap_events (
    event_id BIGSERIAL PRIMARY KEY,
    card_id VARCHAR(64) NOT NULL,
    stop_id VARCHAR(50) REFERENCES bus_stops(stop_id),
    tap_type VARCHAR(10) CHECK (tap_type IN ('IN', 'OUT')),
    tap_timestamp TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tap_events_stop_time ON tap_events(stop_id, tap_timestamp);

-- 3. Vehicle Live GPS Ping Stream Table
CREATE TABLE IF NOT EXISTS vehicle_gps (
    ping_id BIGSERIAL PRIMARY KEY,
    vehicle_id VARCHAR(50) NOT NULL,
    route_id VARCHAR(50) NOT NULL,
    current_occupancy INT NOT NULL,
    speed_kmh NUMERIC(5,2),
    ping_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    location GEOMETRY(Point, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_vehicle_gps_location ON vehicle_gps USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_vehicle_gps_timestamp ON vehicle_gps(ping_timestamp);

-- 4. Hourly Weather & Environmental Context Table
CREATE TABLE IF NOT EXISTS environmental_context (
    context_timestamp TIMESTAMP WITH TIME ZONE PRIMARY KEY,
    temperature_c NUMERIC(4,2),
    precipitation_mm NUMERIC(5,2),
    is_holiday INT DEFAULT 0,
    is_saturday INT DEFAULT 0,
    is_festival INT DEFAULT 0
);

-- 5. SQL Materialized View for Hourly Demand Aggregation
DROP MATERIALIZED VIEW IF EXISTS mv_hourly_stop_demand CASCADE;

CREATE MATERIALIZED VIEW mv_hourly_stop_demand AS
SELECT
    date_trunc('hour', t.tap_timestamp) AS demand_hour,
    t.stop_id,
    COUNT(CASE WHEN t.tap_type = 'IN' THEN 1 END) AS tap_in_count,
    COUNT(CASE WHEN t.tap_type = 'OUT' THEN 1 END) AS tap_out_count,
    COUNT(CASE WHEN t.tap_type = 'IN' THEN 1 END) -
    COUNT(CASE WHEN t.tap_type = 'OUT' THEN 1 END) AS net_passenger_change
FROM tap_events t
GROUP BY 1, 2;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_hourly_demand ON mv_hourly_stop_demand(demand_hour, stop_id);

-- 6. Spatial Query: Proximity Query Using ST_DWithin to Identify High-Congestion Clusters
-- Finds adjacent bus stops within 500 meters (~0.005 degrees) along major Nepal transit arteries
CREATE OR REPLACE VIEW v_congested_stop_clusters AS
SELECT 
    s1.stop_id AS primary_stop_id,
    s1.stop_name AS primary_stop_name,
    s2.stop_id AS neighboring_stop_id,
    s2.stop_name AS neighboring_stop_name,
    s1.route_id,
    ST_Distance(s1.location::geography, s2.location::geography) AS distance_meters
FROM bus_stops s1
JOIN bus_stops s2 
    ON s1.stop_id < s2.stop_id 
    AND ST_DWithin(s1.location::geography, s2.location::geography, 500)
ORDER BY distance_meters ASC;
