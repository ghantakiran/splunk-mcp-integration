-- Report Scheduling Service Database Schema
-- PostgreSQL initialization script

-- Create database if not exists (run manually if needed)
-- CREATE DATABASE report_scheduling;

-- Connect to the database
\c report_scheduling;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create custom types
DO $$
BEGIN
    -- Schedule Status Enum
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'schedule_status') THEN
        CREATE TYPE schedule_status AS ENUM ('active', 'paused', 'disabled', 'error');
    END IF;
    
    -- Delivery Method Enum
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'delivery_method') THEN
        CREATE TYPE delivery_method AS ENUM ('email', 'slack', 'teams', 'webhook', 'file_storage');
    END IF;
    
    -- Report Format Enum
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'report_format') THEN
        CREATE TYPE report_format AS ENUM ('pdf', 'excel', 'powerpoint', 'word', 'csv', 'json', 'xml', 'html');
    END IF;
    
    -- Priority Enum
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'priority') THEN
        CREATE TYPE priority AS ENUM ('low', 'medium', 'high', 'urgent');
    END IF;
    
    -- Execution Status Enum
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'execution_status') THEN
        CREATE TYPE execution_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled', 'retrying');
    END IF;
END
$$;

-- Create report_schedules table
CREATE TABLE IF NOT EXISTS report_schedules (
    schedule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status schedule_status NOT NULL DEFAULT 'active',
    
    -- Schedule configuration
    cron_expression VARCHAR(255) NOT NULL,
    timezone VARCHAR(100) NOT NULL DEFAULT 'UTC',
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    max_executions INTEGER,
    allow_overlap BOOLEAN NOT NULL DEFAULT FALSE,
    priority priority NOT NULL DEFAULT 'medium',
    
    -- Report configuration
    query TEXT NOT NULL,
    query_type VARCHAR(50) NOT NULL DEFAULT 'natural',
    time_range JSONB NOT NULL,
    report_format report_format NOT NULL,
    format_options JSONB,
    visualization_config JSONB,
    data_filters JSONB,
    parameters JSONB,
    
    -- Delivery configuration
    delivery_configs JSONB NOT NULL,
    
    -- Execution tracking
    next_execution TIMESTAMPTZ,
    last_execution TIMESTAMPTZ,
    execution_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    
    -- Metadata
    tags JSONB,
    metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create schedule_executions table
CREATE TABLE IF NOT EXISTS schedule_executions (
    execution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schedule_id UUID NOT NULL REFERENCES report_schedules(schedule_id) ON DELETE CASCADE,
    status execution_status NOT NULL DEFAULT 'pending',
    
    -- Execution timing
    scheduled_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds REAL,
    
    -- Execution results
    report_file_path VARCHAR(1000),
    report_size_bytes INTEGER,
    records_processed INTEGER,
    delivery_results JSONB,
    
    -- Error handling
    error_message TEXT,
    error_details JSONB,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    
    -- Metadata
    metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create report_subscriptions table
CREATE TABLE IF NOT EXISTS report_subscriptions (
    subscription_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    schedule_id UUID NOT NULL REFERENCES report_schedules(schedule_id) ON DELETE CASCADE,
    
    -- Delivery configuration
    delivery_method delivery_method NOT NULL,
    delivery_config JSONB NOT NULL,
    
    -- Subscription settings
    active BOOLEAN NOT NULL DEFAULT TRUE,
    preferences JSONB,
    
    -- Delivery tracking
    total_deliveries INTEGER NOT NULL DEFAULT 0,
    successful_deliveries INTEGER NOT NULL DEFAULT 0,
    failed_deliveries INTEGER NOT NULL DEFAULT 0,
    last_delivery_at TIMESTAMPTZ,
    last_delivery_status VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(user_id, schedule_id)
);

-- Create delivery_attempts table
CREATE TABLE IF NOT EXISTS delivery_attempts (
    attempt_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id UUID NOT NULL REFERENCES schedule_executions(execution_id) ON DELETE CASCADE,
    subscription_id UUID NOT NULL REFERENCES report_subscriptions(subscription_id) ON DELETE CASCADE,
    
    -- Delivery details
    delivery_method delivery_method NOT NULL,
    attempt_number INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(50) NOT NULL,
    
    -- Timing
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_seconds REAL,
    
    -- Results
    success BOOLEAN NOT NULL DEFAULT FALSE,
    error_message TEXT,
    response_data JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create schedule_analytics table
CREATE TABLE IF NOT EXISTS schedule_analytics (
    analytics_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    schedule_id UUID NOT NULL REFERENCES report_schedules(schedule_id) ON DELETE CASCADE,
    
    -- Time period
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    period_type VARCHAR(20) NOT NULL, -- hour, day, week, month
    
    -- Execution metrics
    total_executions INTEGER NOT NULL DEFAULT 0,
    successful_executions INTEGER NOT NULL DEFAULT 0,
    failed_executions INTEGER NOT NULL DEFAULT 0,
    average_duration_seconds REAL,
    total_duration_seconds REAL NOT NULL DEFAULT 0,
    
    -- Report metrics
    total_records_processed INTEGER NOT NULL DEFAULT 0,
    total_report_size_bytes INTEGER NOT NULL DEFAULT 0,
    average_report_size_bytes REAL,
    
    -- Delivery metrics
    total_deliveries INTEGER NOT NULL DEFAULT 0,
    successful_deliveries INTEGER NOT NULL DEFAULT 0,
    failed_deliveries INTEGER NOT NULL DEFAULT 0,
    delivery_success_rate REAL,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(schedule_id, period_start, period_type)
);

-- Create system_metrics table
CREATE TABLE IF NOT EXISTS system_metrics (
    metric_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Time period
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    period_type VARCHAR(20) NOT NULL, -- minute, hour, day
    
    -- System metrics
    total_schedules INTEGER NOT NULL DEFAULT 0,
    active_schedules INTEGER NOT NULL DEFAULT 0,
    pending_jobs INTEGER NOT NULL DEFAULT 0,
    running_jobs INTEGER NOT NULL DEFAULT 0,
    
    -- Performance metrics
    average_execution_time REAL,
    system_cpu_percent REAL,
    system_memory_percent REAL,
    database_connections INTEGER,
    redis_memory_usage INTEGER,
    
    -- Business metrics
    total_reports_generated INTEGER NOT NULL DEFAULT 0,
    total_deliveries_sent INTEGER NOT NULL DEFAULT 0,
    delivery_success_rate REAL,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for performance

-- report_schedules indexes
CREATE INDEX IF NOT EXISTS idx_schedule_user_status ON report_schedules(user_id, status);
CREATE INDEX IF NOT EXISTS idx_schedule_next_execution ON report_schedules(next_execution, status);
CREATE INDEX IF NOT EXISTS idx_schedule_created_at ON report_schedules(created_at);
CREATE INDEX IF NOT EXISTS idx_schedule_user_id ON report_schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_schedule_status ON report_schedules(status);

-- schedule_executions indexes
CREATE INDEX IF NOT EXISTS idx_execution_schedule_status ON schedule_executions(schedule_id, status);
CREATE INDEX IF NOT EXISTS idx_execution_scheduled_at ON schedule_executions(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_execution_status_created ON schedule_executions(status, created_at);
CREATE INDEX IF NOT EXISTS idx_execution_schedule_id ON schedule_executions(schedule_id);

-- report_subscriptions indexes
CREATE INDEX IF NOT EXISTS idx_subscription_user_active ON report_subscriptions(user_id, active);
CREATE INDEX IF NOT EXISTS idx_subscription_schedule_active ON report_subscriptions(schedule_id, active);
CREATE INDEX IF NOT EXISTS idx_subscription_user_id ON report_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscription_schedule_id ON report_subscriptions(schedule_id);

-- delivery_attempts indexes
CREATE INDEX IF NOT EXISTS idx_delivery_execution_status ON delivery_attempts(execution_id, status);
CREATE INDEX IF NOT EXISTS idx_delivery_subscription_success ON delivery_attempts(subscription_id, success);
CREATE INDEX IF NOT EXISTS idx_delivery_attempted_at ON delivery_attempts(attempted_at);

-- schedule_analytics indexes
CREATE INDEX IF NOT EXISTS idx_analytics_schedule_period ON schedule_analytics(schedule_id, period_type, period_start);

-- system_metrics indexes
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp_period ON system_metrics(timestamp, period_type);

-- Create triggers for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_report_schedules_updated_at') THEN
        CREATE TRIGGER update_report_schedules_updated_at
            BEFORE UPDATE ON report_schedules
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_schedule_executions_updated_at') THEN
        CREATE TRIGGER update_schedule_executions_updated_at
            BEFORE UPDATE ON schedule_executions
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_report_subscriptions_updated_at') THEN
        CREATE TRIGGER update_report_subscriptions_updated_at
            BEFORE UPDATE ON report_subscriptions
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_schedule_analytics_updated_at') THEN
        CREATE TRIGGER update_schedule_analytics_updated_at
            BEFORE UPDATE ON schedule_analytics
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

-- Create function to clean up old data
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Clean up old execution records (older than 90 days)
    DELETE FROM schedule_executions 
    WHERE created_at < NOW() - INTERVAL '90 days';
    
    -- Clean up old delivery attempts (older than 30 days)
    DELETE FROM delivery_attempts 
    WHERE created_at < NOW() - INTERVAL '30 days';
    
    -- Clean up old analytics data (older than 1 year)
    DELETE FROM schedule_analytics 
    WHERE created_at < NOW() - INTERVAL '1 year';
    
    -- Clean up old system metrics (older than 6 months)
    DELETE FROM system_metrics 
    WHERE created_at < NOW() - INTERVAL '6 months';
    
    -- Update statistics
    ANALYZE report_schedules;
    ANALYZE schedule_executions;
    ANALYZE report_subscriptions;
    ANALYZE delivery_attempts;
    ANALYZE schedule_analytics;
    ANALYZE system_metrics;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed for your environment)
-- GRANT ALL PRIVILEGES ON DATABASE report_scheduling TO report_scheduling_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO report_scheduling_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO report_scheduling_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO report_scheduling_user;

-- Insert initial system metrics record
INSERT INTO system_metrics (period_type, total_schedules, active_schedules, pending_jobs, running_jobs)
VALUES ('hour', 0, 0, 0, 0)
ON CONFLICT DO NOTHING;

COMMIT;