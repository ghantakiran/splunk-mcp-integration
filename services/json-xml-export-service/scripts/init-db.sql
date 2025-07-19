-- JSON/XML Export Service Database Schema

-- Create database if it doesn't exist
-- Note: This runs in docker-entrypoint-initdb.d, so the database is already created

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types
CREATE TYPE export_status AS ENUM ('pending', 'processing', 'completed', 'failed', 'cancelled');
CREATE TYPE export_format AS ENUM ('json', 'xml', 'jsonl', 'custom-json', 'custom-xml');

-- Export jobs table
CREATE TABLE IF NOT EXISTS json_xml_export_jobs (
    id SERIAL PRIMARY KEY,
    job_id UUID UNIQUE NOT NULL DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    status export_status NOT NULL DEFAULT 'pending',
    format export_format NOT NULL,
    filename VARCHAR(500),
    file_path TEXT,
    file_size BIGINT,
    records_processed INTEGER,
    error_message TEXT,
    
    -- Configuration
    export_config JSONB,
    data_source_config JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT valid_file_size CHECK (file_size >= 0),
    CONSTRAINT valid_records CHECK (records_processed >= 0),
    CONSTRAINT valid_timestamps CHECK (
        (started_at IS NULL OR started_at >= created_at) AND
        (completed_at IS NULL OR completed_at >= started_at OR completed_at >= created_at)
    )
);

-- User profiles table
CREATE TABLE IF NOT EXISTS json_xml_export_users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(255),
    email VARCHAR(255),
    roles TEXT[] DEFAULT '{}',
    permissions TEXT[] DEFAULT '{}',
    
    -- Settings
    preferences JSONB DEFAULT '{}',
    settings JSONB DEFAULT '{}',
    
    -- Quotas and limits
    max_concurrent_jobs INTEGER DEFAULT 5,
    max_file_size_mb INTEGER DEFAULT 100,
    daily_export_limit INTEGER DEFAULT 100,
    
    -- Statistics
    total_exports INTEGER DEFAULT 0,
    successful_exports INTEGER DEFAULT 0,
    failed_exports INTEGER DEFAULT 0,
    total_data_exported BIGINT DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT valid_quotas CHECK (
        max_concurrent_jobs > 0 AND
        max_file_size_mb > 0 AND
        daily_export_limit > 0
    ),
    CONSTRAINT valid_stats CHECK (
        total_exports >= 0 AND
        successful_exports >= 0 AND
        failed_exports >= 0 AND
        total_data_exported >= 0 AND
        successful_exports + failed_exports <= total_exports
    )
);

-- Export analytics table
CREATE TABLE IF NOT EXISTS json_xml_export_analytics (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    job_id UUID NOT NULL,
    
    -- Analytics data
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB DEFAULT '{}',
    
    -- Performance metrics
    processing_time_ms INTEGER,
    queue_wait_time_ms INTEGER,
    file_generation_time_ms INTEGER,
    
    -- Resource usage
    memory_usage_mb DECIMAL(10,2),
    cpu_usage_percent DECIMAL(5,2),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Foreign key
    FOREIGN KEY (job_id) REFERENCES json_xml_export_jobs(job_id) ON DELETE CASCADE,
    
    -- Constraints
    CONSTRAINT valid_metrics CHECK (
        processing_time_ms >= 0 AND
        queue_wait_time_ms >= 0 AND
        file_generation_time_ms >= 0 AND
        memory_usage_mb >= 0 AND
        cpu_usage_percent >= 0 AND cpu_usage_percent <= 100
    )
);

-- Daily usage tracking
CREATE TABLE IF NOT EXISTS json_xml_export_daily_usage (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    date DATE NOT NULL,
    
    -- Daily statistics
    exports_count INTEGER DEFAULT 0,
    successful_exports INTEGER DEFAULT 0,
    failed_exports INTEGER DEFAULT 0,
    total_file_size BIGINT DEFAULT 0,
    total_records INTEGER DEFAULT 0,
    
    -- Format distribution
    json_exports INTEGER DEFAULT 0,
    xml_exports INTEGER DEFAULT 0,
    jsonl_exports INTEGER DEFAULT 0,
    
    -- Performance
    avg_processing_time_ms INTEGER DEFAULT 0,
    max_processing_time_ms INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint
    UNIQUE(user_id, date),
    
    -- Constraints
    CONSTRAINT valid_daily_stats CHECK (
        exports_count >= 0 AND
        successful_exports >= 0 AND
        failed_exports >= 0 AND
        total_file_size >= 0 AND
        total_records >= 0 AND
        json_exports >= 0 AND
        xml_exports >= 0 AND
        jsonl_exports >= 0 AND
        avg_processing_time_ms >= 0 AND
        max_processing_time_ms >= 0 AND
        successful_exports + failed_exports <= exports_count
    )
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_export_jobs_user_id ON json_xml_export_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_export_jobs_status ON json_xml_export_jobs(status);
CREATE INDEX IF NOT EXISTS idx_export_jobs_created_at ON json_xml_export_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_export_jobs_job_id ON json_xml_export_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_export_jobs_expires_at ON json_xml_export_jobs(expires_at);

CREATE INDEX IF NOT EXISTS idx_export_users_user_id ON json_xml_export_users(user_id);
CREATE INDEX IF NOT EXISTS idx_export_users_email ON json_xml_export_users(email);
CREATE INDEX IF NOT EXISTS idx_export_users_last_active ON json_xml_export_users(last_active_at);

CREATE INDEX IF NOT EXISTS idx_export_analytics_user_id ON json_xml_export_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_export_analytics_job_id ON json_xml_export_analytics(job_id);
CREATE INDEX IF NOT EXISTS idx_export_analytics_event_type ON json_xml_export_analytics(event_type);
CREATE INDEX IF NOT EXISTS idx_export_analytics_created_at ON json_xml_export_analytics(created_at);

CREATE INDEX IF NOT EXISTS idx_daily_usage_user_date ON json_xml_export_daily_usage(user_id, date);
CREATE INDEX IF NOT EXISTS idx_daily_usage_date ON json_xml_export_daily_usage(date);

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_json_xml_export_users_updated_at
    BEFORE UPDATE ON json_xml_export_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_json_xml_export_daily_usage_updated_at
    BEFORE UPDATE ON json_xml_export_daily_usage
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create function to cleanup expired jobs
CREATE OR REPLACE FUNCTION cleanup_expired_export_jobs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM json_xml_export_jobs 
    WHERE expires_at < NOW() 
    AND status IN ('completed', 'failed', 'cancelled');
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Insert default user for testing
INSERT INTO json_xml_export_users (
    user_id, 
    username, 
    email, 
    roles, 
    permissions,
    preferences
) VALUES (
    'test-user-123',
    'testuser',
    'test@example.com',
    ARRAY['user'],
    ARRAY['json_xml_export:create', 'json_xml_export:read', 'json_xml_export:delete'],
    '{"default_format": "json", "include_metadata": true}'
) ON CONFLICT (user_id) DO NOTHING;

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_app_user;