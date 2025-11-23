-- PostgreSQL initialization script for Banking Security Training Application
-- This script sets up the database with proper permissions and extensions

-- Create database if it doesn't exist (this is handled by POSTGRES_DB environment variable)
-- CREATE DATABASE IF NOT EXISTS banking;

-- -- Connect to the banking database
\c cryptoflux;

-- Create extensions that might be useful
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Grant necessary permissions to the user
GRANT ALL PRIVILEGES ON DATABASE cryptoflux TO cryptouser;
GRANT ALL ON SCHEMA public TO cryptouser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cryptouser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cryptouser;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO cryptouser;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO cryptouser;

-- Create a function to display database info
CREATE OR REPLACE FUNCTION show_db_info() 
RETURNS TABLE(
    property TEXT,
    value TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'Database Name'::TEXT, current_database()::TEXT
    UNION ALL
    SELECT 'PostgreSQL Version'::TEXT, version()::TEXT
    UNION ALL
    SELECT 'Current User'::TEXT, current_user::TEXT
    UNION ALL
    SELECT 'Connection Info'::TEXT, 
           ('Host: ' || inet_server_addr() || ' Port: ' || inet_server_port())::TEXT
    UNION ALL
    SELECT 'Database Size'::TEXT, 
           pg_size_pretty(pg_database_size(current_database()))::TEXT;
END;
$$ LANGUAGE plpgsql;

-- Display initialization success message
DO $$
BEGIN
    RAISE NOTICE 'Cryptoflux Database initialized successfully!';
    RAISE NOTICE 'Database: cryptoflux';
    RAISE NOTICE 'User: cryptouser';
    RAISE NOTICE 'Ready for Flask application connection.';
END $$;