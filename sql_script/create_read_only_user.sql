-- 1. Create the AI user safely (Idempotent)
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'ai_agent_user') THEN
      CREATE USER ai_agent_user WITH PASSWORD 'ai_password_123';
   END IF;
END
$$;

-- 2. Give access to schemas
GRANT USAGE ON SCHEMA analytics_marts TO ai_agent_user;

-- 3. Give read-only access to all current and future tables
GRANT SELECT ON ALL TABLES IN SCHEMA analytics_marts TO ai_agent_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics_marts GRANT SELECT ON TABLES TO ai_agent_user;

-- 4. Create the Chat History Table with inline constraints
CREATE TABLE IF NOT EXISTS analytics_marts.ai_query_history (
    id SERIAL PRIMARY KEY,
    question TEXT,
    sql_query TEXT,
    insight TEXT,
    chart_type VARCHAR(50) DEFAULT 'table',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Give the AI user permission to insert data into this table
GRANT INSERT, SELECT ON analytics_marts.ai_query_history TO ai_agent_user;
GRANT USAGE, SELECT ON SEQUENCE analytics_marts.ai_query_history_id_seq TO ai_agent_user;

-- 5. Create the Auto-Insight Table with inline UNIQUE constraint
CREATE TABLE IF NOT EXISTS analytics_marts.ai_auto_insights (
    id SERIAL PRIMARY KEY,
    title TEXT UNIQUE, -- The UNIQUE constraint is now elegantly inline
    sql_query TEXT,
    insight TEXT,
    chart_type VARCHAR(50) DEFAULT 'table',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Give the AI user permission to insert data into this table
GRANT INSERT, SELECT ON analytics_marts.ai_auto_insights TO ai_agent_user;
GRANT USAGE, SELECT ON SEQUENCE analytics_marts.ai_auto_insights_id_seq TO ai_agent_user;