-- Database initialization script for ITSM Service
-- This script creates the database and user if they don't exist

-- Create database if it doesn't exist
SELECT 'CREATE DATABASE itsm_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'itsm_db')\gexec

-- Create user if it doesn't exist
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'itsm_user') THEN

      CREATE ROLE itsm_user LOGIN PASSWORD 'itsm_password';
   END IF;
END
$do$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE itsm_db TO itsm_user;

-- Connect to the itsm_db database
\c itsm_db;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO itsm_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO itsm_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO itsm_user;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO itsm_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO itsm_user;