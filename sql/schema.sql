-- ============================================================
-- Smart City Nepal Transit DB Schema
-- Supports: PostGIS (preferred) with earthdistance fallback
-- ============================================================

-- Step 1: Enable PostGIS if available; otherwise enable
-- cube + earthdistance for haversine proximity queries.
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS postgis;
    RAISE NOTICE 'PostGIS extension enabled.';
EXCEPTION WHEN OTHERS THEN
    BEGIN
        CREATE EXTENSION IF NOT EXISTS cube CASCADE;
        CREATE EXTENSION IF NOT EXISTS earthdistance CASCADE;
        RAISE NOTICE 'PostGIS unavailable. Cube + earthdistance fallback enabled.';
    END;
END $$;

-- Step 2: Create compatibility shim functions only when PostGIS
-- is NOT installed (i.e., the geometry type does not exist).
-- These shims allow the same INSERT/SELECT SQL to work in both modes.
DO $$
BEGIN
    -- Only create shims if postgis is not installed
    IF NOT EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'postgis'
    ) THEN
        CREATE OR REPLACE FUNCTION ST_MakePoint(lon float8, lat float8)
            RETURNS point
            LANGUAGE sql IMMUTABLE
        AS 'SELECT point($1, $2);';

        CREATE OR REPLACE FUNCTION ST_SetSRID(p point, srid integer)
            RETURNS point
            LANGUAGE sql IMMUTABLE
        AS 'SELECT $1;';

        CREATE OR REPLACE FUNCTION ST_X(p point)
            RETURNS float8
            LANGUAGE sql IMMUTABLE
        AS 'SELECT $1[0];';

        CREATE OR REPLACE FUNCTION ST_Y(p point)
            RETURNS float8
            LANGUAGE sql IMMUTABLE
        AS 'SELECT $1[1];';

        CREATE OR REPLACE FUNCTION ST_DWithin(p1 point, p2 point, meters float8)
            RETURNS boolean
            LANGUAGE sql IMMUTABLE
        AS 'SELECT earth_distance(
                ll_to_earth($1[1], $1[0]),
                ll_to_earth($2[1], $2[0])
            ) <= $3;';

        RAISE NOTICE 'PostGIS-compatibility shim functions created.';
    ELSE
        RAISE NOTICE 'PostGIS is active; skipping shim function creation.';
    END IF;
END $$;

-- ============================================================
-- 1. Bus Stops Table
-- Uses geometry(Point,4326) when PostGIS is available,
-- or native POINT when running in fallback mode.
-- ============================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
        -- PostGIS mode: proper geometry column
        CREATE TABLE IF NOT EXISTS bus_stops (
            stop_id        VARCHAR(50) PRIMARY KEY,
            stop_name      VARCHAR(100) NOT NULL,
            route_id       VARCHAR(50)  NOT NULL,
            capacity_limit INT          DEFAULT 60,
            location       geometry(Point, 4326) NOT NULL
        );
    ELSE
        -- Fallback mode: native point column
        CREATE TABLE IF NOT EXISTS bus_stops (
            stop_id        VARCHAR(50) PRIMARY KEY,
            stop_name      VARCHAR(100) NOT NULL,
            route_id       VARCHAR(50)  NOT NULL,
            capacity_limit INT          DEFAULT 60,
            location       POINT        NOT NULL
        );
    END IF;
END $$;

-- Spatial index: GIST works on PostGIS geometry; skip for native POINT
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes
             WHERE tablename = 'bus_stops'
               AND indexname = 'idx_bus_stops_location'
        ) THEN
            CREATE INDEX idx_bus_stops_location ON bus_stops USING GIST(location);
        END IF;
    END IF;
END $$;

-- ============================================================
-- 2. Passenger Tap Card Events Table
-- ============================================================
CREATE TABLE IF NOT EXISTS tap_events (
    event_id      BIGSERIAL PRIMARY KEY,
    card_id       VARCHAR(64)  NOT NULL,
    stop_id       VARCHAR(50)  REFERENCES bus_stops(stop_id),
    tap_type      VARCHAR(10)  CHECK (tap_type IN ('IN', 'OUT')),
    tap_timestamp TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tap_events_stop_time
    ON tap_events(stop_id, tap_timestamp);

-- ============================================================
-- 3. Vehicle Live GPS Ping Stream Table
-- ============================================================
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'postgis') THEN
        CREATE TABLE IF NOT EXISTS vehicle_gps (
            ping_id           BIGSERIAL PRIMARY KEY,
            vehicle_id        VARCHAR(50)    NOT NULL,
            route_id          VARCHAR(50)    NOT NULL,
            current_occupancy INT            NOT NULL,
            speed_kmh         NUMERIC(5,2),
            ping_timestamp    TIMESTAMP WITH TIME ZONE NOT NULL,
            location          geometry(Point, 4326) NOT NULL
        );
    ELSE
        CREATE TABLE IF NOT EXISTS vehicle_gps (
            ping_id           BIGSERIAL PRIMARY KEY,
            vehicle_id        VARCHAR(50)    NOT NULL,
            route_id          VARCHAR(50)    NOT NULL,
            current_occupancy INT            NOT NULL,
            speed_kmh         NUMERIC(5,2),
            ping_timestamp    TIMESTAMP WITH TIME ZONE NOT NULL,
            location          POINT          NOT NULL
        );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_vehicle_gps_timestamp ON vehicle_gps(ping_timestamp);

-- ============================================================
-- 4. Hourly Weather and Environmental Context Table
-- ============================================================
CREATE TABLE IF NOT EXISTS environmental_context (
    context_timestamp TIMESTAMP WITH TIME ZONE PRIMARY KEY,
    temperature_c     NUMERIC(4,2),
    precipitation_mm  NUMERIC(5,2),
    is_holiday        INT DEFAULT 0,
    is_saturday       INT DEFAULT 0,
    is_festival       INT DEFAULT 0
);

-- ============================================================
-- 5. Materialized View: Hourly Tap-In Demand Aggregation
-- ============================================================
DROP MATERIALIZED VIEW IF EXISTS mv_hourly_stop_demand CASCADE;

CREATE MATERIALIZED VIEW mv_hourly_stop_demand AS
SELECT
    date_trunc('hour', t.tap_timestamp AT TIME ZONE 'UTC') AS demand_hour,
    t.stop_id,
    COUNT(CASE WHEN t.tap_type = 'IN'  THEN 1 END) AS tap_in_count,
    COUNT(CASE WHEN t.tap_type = 'OUT' THEN 1 END) AS tap_out_count,
    COUNT(CASE WHEN t.tap_type = 'IN'  THEN 1 END) -
    COUNT(CASE WHEN t.tap_type = 'OUT' THEN 1 END) AS net_passenger_change
FROM tap_events t
GROUP BY 1, 2;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_hourly_demand
    ON mv_hourly_stop_demand(demand_hour, stop_id);

-- ============================================================
-- 6. View: Proximity Query for Congested Stop Clusters
-- Identifies adjacent stops within 500 m using earthdistance
-- ============================================================
DROP VIEW IF EXISTS v_congested_stop_clusters;

CREATE VIEW v_congested_stop_clusters AS
SELECT
    s1.stop_id        AS primary_stop_id,
    s1.stop_name      AS primary_stop_name,
    s2.stop_id        AS neighboring_stop_id,
    s2.stop_name      AS neighboring_stop_name,
    s1.route_id,
    ST_DWithin(s1.location, s2.location, 500) AS within_500m
FROM bus_stops s1
JOIN bus_stops s2
    ON s1.stop_id < s2.stop_id;
