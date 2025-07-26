-- Cloud Connection Manager Database Initialization Script

-- Create database if it doesn't exist
-- This will be run by Docker's postgres container

-- Note: The actual tables will be created by SQLAlchemy when the service starts
-- This script is for any additional database setup if needed

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create any custom functions or procedures if needed
-- (Currently none required)

-- Initial data could be inserted here
-- For now, we'll let the application handle initial data creation