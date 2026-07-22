-- Enable PostGIS spatial extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Bus Stops Table
CREATE TABLE IF NOT EXISTS bus_stops (
    stop_id VARCHAR(50) PRIMARY KEY,
    stop_name VARCHAR(100) NOT NULL,
    route_id VARCHAR(50) NOT NULL,
    capacity_limit INT DEFAULT 100,
    location GEOMETRY(Point, 4326) NOT NULL
);

-- Spatial index for rapid proximity queries
CREATE INDEX IF NOT EXISTS idx_bus_stops_location ON bus_stops USING GIST(location);

-- 2. Passenger Tap Card Events
CREATE TABLE IF NOT EXISTS tap_events (
    event_id BIGSERIAL PRIMARY KEY,
    card_id VARCHAR(64) NOT NULL,
    stop_id VARCHAR(50) REFERENCES bus_stops(stop_id),
    tap_type VARCHAR(10) CHECK (tap_type IN ('IN', 'OUT')),
    tap_timestamp TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tap_events_stop_time ON tap_events(stop_id, tap_timestamp);

-- 3. Vehicle Live GPS Ping Stream
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

-- 4. Hourly Weather & Context Data
CREATE TABLE IF NOT EXISTS hourly_context (
    context_timestamp TIMESTAMP WITH TIME ZONE PRIMARY KEY,
    temperature_c NUMERIC(4,2),
    precipitation_mm NUMERIC(5,2),
    is_holiday BOOLEAN DEFAULT FALSE,
    special_event_flag BOOLEAN DEFAULT FALSE
);

-- 5. SQL Materialized View for Hourly Demand Aggregation
-- Drop the view if it exists so we can recreate it easily
DROP MATERIALIZED VIEW IF EXISTS mv_hourly_stop_demand;

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
