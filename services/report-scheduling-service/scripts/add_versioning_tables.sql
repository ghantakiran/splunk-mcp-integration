-- Migration script to add versioning and history tables
-- Report Scheduling Service - Version Control & History

-- Add versioning-related enum types
DO $$ BEGIN
    CREATE TYPE version_action AS ENUM ('created', 'updated', 'deleted', 'restored', 'archived');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE change_type AS ENUM ('schedule_config', 'query', 'format', 'delivery', 'metadata', 'status');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE history_event_type AS ENUM ('execution', 'version_change', 'subscription_change', 'delivery_attempt', 'error', 'system');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create schedule_versions table
CREATE TABLE IF NOT EXISTS schedule_versions (
    version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID NOT NULL REFERENCES report_schedules(schedule_id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    version_name VARCHAR(255),
    description TEXT,
    
    -- Version metadata
    action version_action NOT NULL DEFAULT 'created',
    changes JSONB NOT NULL DEFAULT '[]',
    change_notes TEXT,
    tags JSONB,
    
    -- Configuration snapshot
    schedule_config JSONB NOT NULL,
    
    -- Version tracking
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    parent_version_id UUID REFERENCES schedule_versions(version_id),
    checksum VARCHAR(64) NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    
    -- User context
    created_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_schedule_version_number UNIQUE (schedule_id, version_number)
);

-- Create indexes for schedule_versions
CREATE INDEX IF NOT EXISTS idx_version_schedule_current ON schedule_versions(schedule_id, is_current);
CREATE INDEX IF NOT EXISTS idx_version_created_by ON schedule_versions(created_by);
CREATE INDEX IF NOT EXISTS idx_version_action ON schedule_versions(action);
CREATE INDEX IF NOT EXISTS idx_version_created_at ON schedule_versions(created_at);

-- Create schedule_history table
CREATE TABLE IF NOT EXISTS schedule_history (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID NOT NULL REFERENCES report_schedules(schedule_id) ON DELETE CASCADE,
    event_type history_event_type NOT NULL,
    event_title VARCHAR(255) NOT NULL,
    event_description TEXT,
    
    -- Event context
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    correlation_id VARCHAR(255),
    
    -- Event data
    event_data JSONB NOT NULL DEFAULT '{}',
    metadata JSONB,
    
    -- Relationships to other entities
    version_id UUID REFERENCES schedule_versions(version_id),
    execution_id UUID REFERENCES schedule_executions(execution_id),
    
    -- Timing
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes for schedule_history
CREATE INDEX IF NOT EXISTS idx_history_schedule_type ON schedule_history(schedule_id, event_type);
CREATE INDEX IF NOT EXISTS idx_history_user_occurred ON schedule_history(user_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_history_correlation ON schedule_history(correlation_id);
CREATE INDEX IF NOT EXISTS idx_history_occurred_at ON schedule_history(occurred_at);
CREATE INDEX IF NOT EXISTS idx_history_event_type_occurred ON schedule_history(event_type, occurred_at);

-- Create version_metrics table
CREATE TABLE IF NOT EXISTS version_metrics (
    metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID NOT NULL REFERENCES report_schedules(schedule_id) ON DELETE CASCADE,
    
    -- Time period
    date TIMESTAMP WITH TIME ZONE NOT NULL,
    period_type VARCHAR(20) NOT NULL,
    
    -- Version activity metrics
    versions_created INTEGER NOT NULL DEFAULT 0,
    versions_updated INTEGER NOT NULL DEFAULT 0,
    versions_restored INTEGER NOT NULL DEFAULT 0,
    versions_archived INTEGER NOT NULL DEFAULT 0,
    
    -- User activity
    unique_users INTEGER NOT NULL DEFAULT 0,
    most_active_user VARCHAR(255),
    user_activity JSONB,
    
    -- Size metrics
    total_size_bytes INTEGER NOT NULL DEFAULT 0,
    average_size_bytes FLOAT,
    largest_version_size INTEGER NOT NULL DEFAULT 0,
    
    -- Change metrics
    changes_by_type JSONB,
    most_common_change VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_schedule_date_period_metrics UNIQUE (schedule_id, date, period_type)
);

-- Create indexes for version_metrics
CREATE INDEX IF NOT EXISTS idx_version_metrics_date_period ON version_metrics(date, period_type);

-- Create function to automatically create initial version when schedule is created
CREATE OR REPLACE FUNCTION create_initial_schedule_version()
RETURNS TRIGGER AS $$
BEGIN
    -- Create initial version
    INSERT INTO schedule_versions (
        schedule_id,
        version_number,
        version_name,
        description,
        action,
        changes,
        schedule_config,
        is_current,
        checksum,
        size_bytes,
        created_by
    ) VALUES (
        NEW.schedule_id,
        1,
        'Initial version',
        'Automatically created initial version',
        'created',
        '["schedule_config"]',
        jsonb_build_object(
            'name', NEW.name,
            'description', NEW.description,
            'status', NEW.status,
            'cron_expression', NEW.cron_expression,
            'timezone', NEW.timezone,
            'start_date', NEW.start_date,
            'end_date', NEW.end_date,
            'max_executions', NEW.max_executions,
            'allow_overlap', NEW.allow_overlap,
            'priority', NEW.priority,
            'query', NEW.query,
            'query_type', NEW.query_type,
            'time_range', NEW.time_range,
            'report_format', NEW.report_format,
            'format_options', NEW.format_options,
            'visualization_config', NEW.visualization_config,
            'data_filters', NEW.data_filters,
            'parameters', NEW.parameters,
            'delivery_configs', NEW.delivery_configs,
            'tags', NEW.tags,
            'metadata', NEW.metadata
        ),
        true,
        encode(sha256(NEW.schedule_id::text::bytea), 'hex'),
        1024, -- Approximate size
        NEW.user_id
    );
    
    -- Create history event
    INSERT INTO schedule_history (
        schedule_id,
        event_type,
        event_title,
        event_description,
        user_id,
        event_data
    ) VALUES (
        NEW.schedule_id,
        'version_change',
        'Schedule created',
        'Initial schedule creation with version 1',
        NEW.user_id,
        jsonb_build_object(
            'action', 'created',
            'version_number', 1,
            'schedule_name', NEW.name
        )
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic version creation
DROP TRIGGER IF EXISTS trigger_create_initial_version ON report_schedules;
CREATE TRIGGER trigger_create_initial_version
    AFTER INSERT ON report_schedules
    FOR EACH ROW
    EXECUTE FUNCTION create_initial_schedule_version();

-- Create function to log history events for executions
CREATE OR REPLACE FUNCTION log_execution_history()
RETURNS TRIGGER AS $$
BEGIN
    -- Log execution events
    INSERT INTO schedule_history (
        schedule_id,
        event_type,
        event_title,
        event_description,
        execution_id,
        event_data
    ) VALUES (
        NEW.schedule_id,
        'execution',
        CASE 
            WHEN NEW.status = 'pending' THEN 'Execution started'
            WHEN NEW.status = 'running' THEN 'Execution in progress'
            WHEN NEW.status = 'completed' THEN 'Execution completed'
            WHEN NEW.status = 'failed' THEN 'Execution failed'
            WHEN NEW.status = 'cancelled' THEN 'Execution cancelled'
            ELSE 'Execution status changed'
        END,
        CASE 
            WHEN NEW.status = 'failed' AND NEW.error_message IS NOT NULL THEN NEW.error_message
            ELSE NULL
        END,
        NEW.execution_id,
        jsonb_build_object(
            'status', NEW.status,
            'scheduled_at', NEW.scheduled_at,
            'started_at', NEW.started_at,
            'completed_at', NEW.completed_at,
            'duration_seconds', NEW.duration_seconds,
            'records_processed', NEW.records_processed,
            'report_size_bytes', NEW.report_size_bytes,
            'retry_count', NEW.retry_count
        )
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for execution history logging
DROP TRIGGER IF EXISTS trigger_log_execution_history ON schedule_executions;
CREATE TRIGGER trigger_log_execution_history
    AFTER INSERT OR UPDATE ON schedule_executions
    FOR EACH ROW
    EXECUTE FUNCTION log_execution_history();

-- Create function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for updated_at in version_metrics
DROP TRIGGER IF EXISTS trigger_update_version_metrics_updated_at ON version_metrics;
CREATE TRIGGER trigger_update_version_metrics_updated_at
    BEFORE UPDATE ON version_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data for testing (optional)
-- This can be removed in production

-- Grant necessary permissions (adjust as needed for your setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON schedule_versions TO report_scheduling_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON schedule_history TO report_scheduling_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON version_metrics TO report_scheduling_user;

COMMIT;