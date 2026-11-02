-- =========================================================
-- MASTER DATABASE SETUP SCRIPT (Production-Grade)
-- =========================================================

-- ---------------------------------------------------------
-- 1. SETUP: AI Text-to-SQL User (Read-only for Marts + Write History)
-- ---------------------------------------------------------
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ai_agent_user') THEN
      CREATE USER ai_agent_user WITH PASSWORD 'ai_password_123';
   END IF;
END
$$;

-- Give read-only access to marts
GRANT USAGE ON SCHEMA analytics_marts TO ai_agent_user;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics_marts TO ai_agent_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics_marts GRANT SELECT ON TABLES TO ai_agent_user;

-- Create Chat History Table
CREATE TABLE IF NOT EXISTS analytics_marts.ai_query_history (
    id SERIAL PRIMARY KEY,
    question TEXT,
    sql_query TEXT,
    insight TEXT,
    chart_type VARCHAR(50) DEFAULT 'table',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
GRANT INSERT, SELECT ON analytics_marts.ai_query_history TO ai_agent_user;
GRANT USAGE, SELECT ON SEQUENCE analytics_marts.ai_query_history_id_seq TO ai_agent_user;

-- Create Auto-Insight Table
CREATE TABLE IF NOT EXISTS analytics_marts.ai_auto_insights (
    id SERIAL PRIMARY KEY,
    title TEXT UNIQUE,
    sql_query TEXT,
    insight TEXT,
    chart_type VARCHAR(50) DEFAULT 'table',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
GRANT INSERT, SELECT ON analytics_marts.ai_auto_insights TO ai_agent_user;
GRANT USAGE, SELECT ON SEQUENCE analytics_marts.ai_auto_insights_id_seq TO ai_agent_user;


-- ---------------------------------------------------------
-- 2. SETUP: Auto-DBT Co-Pilot User (Read raw + Full Access to Staging/Marts)
-- ---------------------------------------------------------
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'dbt_agent_user') THEN
      CREATE USER dbt_agent_user WITH PASSWORD 'dbt_agent_password_123';
   END IF;
END
$$;

-- Allow connection to the database
GRANT CONNECT ON DATABASE olist_warehouse TO dbt_agent_user;

-- Raw Schema: READ ONLY (Protects raw data from AI hallucinations)
GRANT USAGE ON SCHEMA raw TO dbt_agent_user;
GRANT SELECT ON ALL TABLES IN SCHEMA raw TO dbt_agent_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT ON TABLES TO dbt_agent_user;

-- Transformation Schemas: FULL ACCESS (To create views, tables, and drop them if needed)
GRANT USAGE, CREATE ON SCHEMA analytics_staging TO dbt_agent_user;
GRANT USAGE, CREATE ON SCHEMA analytics_marts TO dbt_agent_user;
GRANT USAGE, CREATE ON SCHEMA snapshots TO dbt_agent_user;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics_staging TO dbt_agent_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics_marts TO dbt_agent_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA snapshots TO dbt_agent_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA analytics_staging GRANT ALL PRIVILEGES ON TABLES TO dbt_agent_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics_marts GRANT ALL PRIVILEGES ON TABLES TO dbt_agent_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA snapshots GRANT ALL PRIVILEGES ON TABLES TO dbt_agent_user;