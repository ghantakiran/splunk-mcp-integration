-- Webhook Service Database Schema
-- PostgreSQL initialization script

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create webhook_users table
CREATE TABLE IF NOT EXISTS webhook_users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_user_id VARCHAR(36) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'basic' CHECK (role IN ('basic', 'premium', 'enterprise', 'admin')),
    active BOOLEAN DEFAULT TRUE,
    verified BOOLEAN DEFAULT FALSE,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for webhook_users
CREATE INDEX IF NOT EXISTS idx_webhook_users_external_id ON webhook_users(external_user_id);
CREATE INDEX IF NOT EXISTS idx_webhook_users_email ON webhook_users(email);
CREATE INDEX IF NOT EXISTS idx_webhook_users_active ON webhook_users(active);

-- Create webhook_endpoints table
CREATE TABLE IF NOT EXISTS webhook_endpoints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    url VARCHAR(2048) NOT NULL,
    method VARCHAR(10) NOT NULL DEFAULT 'POST' CHECK (method IN ('POST', 'PUT', 'PATCH')),
    headers JSONB DEFAULT '{}',
    secret VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'suspended', 'failed')),
    event_types JSONB DEFAULT '[]',
    event_filters JSONB DEFAULT '{}',
    timeout INTEGER DEFAULT 30 CHECK (timeout > 0 AND timeout <= 300),
    retry_attempts INTEGER DEFAULT 3 CHECK (retry_attempts >= 0 AND retry_attempts <= 10),
    retry_delay INTEGER DEFAULT 300 CHECK (retry_delay >= 0 AND retry_delay <= 3600),
    total_deliveries INTEGER DEFAULT 0,
    successful_deliveries INTEGER DEFAULT 0,
    failed_deliveries INTEGER DEFAULT 0,
    last_delivery_at TIMESTAMP WITH TIME ZONE,
    last_success_at TIMESTAMP WITH TIME ZONE,
    last_failure_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for webhook_endpoints
CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_user_id ON webhook_endpoints(user_id);
CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_status ON webhook_endpoints(status);
CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_event_types ON webhook_endpoints USING GIN(event_types);
CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_created_at ON webhook_endpoints(created_at);

-- Create webhook_events table
CREATE TABLE IF NOT EXISTS webhook_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    endpoint_id UUID REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN (
        'query.completed',
        'alert.triggered', 
        'dashboard.created',
        'report.generated',
        'error.occurred',
        'system.status_changed',
        'user.action',
        'data.updated'
    )),
    source VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    processed BOOLEAN DEFAULT FALSE,
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for webhook_events
CREATE INDEX IF NOT EXISTS idx_webhook_events_endpoint_id ON webhook_events(endpoint_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_event_type ON webhook_events(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_events_source ON webhook_events(source);
CREATE INDEX IF NOT EXISTS idx_webhook_events_processed ON webhook_events(processed);
CREATE INDEX IF NOT EXISTS idx_webhook_events_created_at ON webhook_events(created_at);

-- Create webhook_deliveries table
CREATE TABLE IF NOT EXISTS webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    endpoint_id UUID NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES webhook_events(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'delivered', 'failed', 'retrying', 'cancelled')),
    attempt_number INTEGER DEFAULT 1,
    max_attempts INTEGER DEFAULT 3,
    http_status INTEGER,
    response_body TEXT,
    response_headers JSONB DEFAULT '{}',
    error_message TEXT,
    scheduled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    attempted_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    response_time REAL,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for webhook_deliveries
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_endpoint_id ON webhook_deliveries(endpoint_id);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_event_id ON webhook_deliveries(event_id);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_status ON webhook_deliveries(status);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_scheduled_at ON webhook_deliveries(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_next_retry_at ON webhook_deliveries(next_retry_at);
CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_created_at ON webhook_deliveries(created_at);

-- Create webhook_subscriptions table
CREATE TABLE IF NOT EXISTS webhook_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    endpoint_id UUID NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL CHECK (event_type IN (
        'query.completed',
        'alert.triggered',
        'dashboard.created', 
        'report.generated',
        'error.occurred',
        'system.status_changed',
        'user.action',
        'data.updated'
    )),
    active BOOLEAN DEFAULT TRUE,
    filters JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for webhook_subscriptions
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_endpoint_id ON webhook_subscriptions(endpoint_id);
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_event_type ON webhook_subscriptions(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_active ON webhook_subscriptions(active);

-- Create webhook_logs table
CREATE TABLE IF NOT EXISTS webhook_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    endpoint_id UUID REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
    user_id VARCHAR(36) NOT NULL,
    action VARCHAR(255) NOT NULL,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent VARCHAR(512),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for webhook_logs
CREATE INDEX IF NOT EXISTS idx_webhook_logs_endpoint_id ON webhook_logs(endpoint_id);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_user_id ON webhook_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_action ON webhook_logs(action);
CREATE INDEX IF NOT EXISTS idx_webhook_logs_created_at ON webhook_logs(created_at);

-- Create webhook_metrics table
CREATE TABLE IF NOT EXISTS webhook_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    endpoint_id UUID REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
    metric_name VARCHAR(255) NOT NULL,
    metric_value REAL NOT NULL,
    metric_type VARCHAR(50) NOT NULL CHECK (metric_type IN ('counter', 'gauge', 'histogram')),
    tags JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    time_bucket VARCHAR(20) NOT NULL CHECK (time_bucket IN ('minute', 'hour', 'day', 'week', 'month')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for webhook_metrics
CREATE INDEX IF NOT EXISTS idx_webhook_metrics_endpoint_id ON webhook_metrics(endpoint_id);
CREATE INDEX IF NOT EXISTS idx_webhook_metrics_metric_name ON webhook_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_webhook_metrics_timestamp ON webhook_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_webhook_metrics_time_bucket ON webhook_metrics(time_bucket);

-- Create user_webhook_settings table
CREATE TABLE IF NOT EXISTS user_webhook_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES webhook_users(id) ON DELETE CASCADE,
    email_notifications BOOLEAN DEFAULT TRUE,
    delivery_failure_notifications BOOLEAN DEFAULT TRUE,
    quota_warning_notifications BOOLEAN DEFAULT TRUE,
    security_notifications BOOLEAN DEFAULT TRUE,
    default_timeout INTEGER DEFAULT 30 CHECK (default_timeout > 0 AND default_timeout <= 300),
    default_retry_attempts INTEGER DEFAULT 3 CHECK (default_retry_attempts >= 0 AND default_retry_attempts <= 10),
    default_retry_delay INTEGER DEFAULT 300 CHECK (default_retry_delay >= 0 AND default_retry_delay <= 3600),
    require_signature_verification BOOLEAN DEFAULT TRUE,
    allowed_domains JSONB DEFAULT '[]',
    blocked_domains JSONB DEFAULT '[]',
    rate_limit_notifications BOOLEAN DEFAULT TRUE,
    custom_rate_limits JSONB DEFAULT '{}',
    enable_analytics BOOLEAN DEFAULT TRUE,
    analytics_retention_days INTEGER DEFAULT 30 CHECK (analytics_retention_days >= 1 AND analytics_retention_days <= 365),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for user_webhook_settings
CREATE INDEX IF NOT EXISTS idx_user_webhook_settings_user_id ON user_webhook_settings(user_id);

-- Create user_webhook_quotas table
CREATE TABLE IF NOT EXISTS user_webhook_quotas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES webhook_users(id) ON DELETE CASCADE,
    quota_type VARCHAR(30) NOT NULL CHECK (quota_type IN ('endpoints', 'events_per_hour', 'events_per_day', 'deliveries_per_hour', 'deliveries_per_day')),
    limit_value INTEGER NOT NULL CHECK (limit_value >= 0),
    used_value INTEGER DEFAULT 0 CHECK (used_value >= 0),
    period_start TIMESTAMP WITH TIME ZONE,
    period_end TIMESTAMP WITH TIME ZONE,
    auto_reset BOOLEAN DEFAULT TRUE,
    reset_interval VARCHAR(20) CHECK (reset_interval IN ('hourly', 'daily', 'weekly', 'monthly')),
    last_reset_at TIMESTAMP WITH TIME ZONE,
    warning_threshold REAL DEFAULT 0.8 CHECK (warning_threshold >= 0.0 AND warning_threshold <= 1.0),
    warning_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for user_webhook_quotas
CREATE INDEX IF NOT EXISTS idx_user_webhook_quotas_user_id ON user_webhook_quotas(user_id);
CREATE INDEX IF NOT EXISTS idx_user_webhook_quotas_quota_type ON user_webhook_quotas(quota_type);
CREATE INDEX IF NOT EXISTS idx_user_webhook_quotas_period_end ON user_webhook_quotas(period_end);

-- Create triggers for updating updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables with updated_at columns
CREATE TRIGGER update_webhook_users_updated_at BEFORE UPDATE ON webhook_users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_webhook_endpoints_updated_at BEFORE UPDATE ON webhook_endpoints
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_webhook_deliveries_updated_at BEFORE UPDATE ON webhook_deliveries
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_webhook_subscriptions_updated_at BEFORE UPDATE ON webhook_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_webhook_settings_updated_at BEFORE UPDATE ON user_webhook_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_webhook_quotas_updated_at BEFORE UPDATE ON user_webhook_quotas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create default quota function
CREATE OR REPLACE FUNCTION create_default_quotas(user_uuid UUID, user_role VARCHAR)
RETURNS VOID AS $$
BEGIN
    -- Set quotas based on user role
    CASE user_role
        WHEN 'basic' THEN
            INSERT INTO user_webhook_quotas (user_id, quota_type, limit_value, reset_interval) VALUES
            (user_uuid, 'endpoints', 5, 'daily'),
            (user_uuid, 'events_per_hour', 100, 'hourly'),
            (user_uuid, 'events_per_day', 1000, 'daily'),
            (user_uuid, 'deliveries_per_hour', 200, 'hourly'),
            (user_uuid, 'deliveries_per_day', 2000, 'daily');
        
        WHEN 'premium' THEN
            INSERT INTO user_webhook_quotas (user_id, quota_type, limit_value, reset_interval) VALUES
            (user_uuid, 'endpoints', 25, 'daily'),
            (user_uuid, 'events_per_hour', 1000, 'hourly'),
            (user_uuid, 'events_per_day', 10000, 'daily'),
            (user_uuid, 'deliveries_per_hour', 2000, 'hourly'),
            (user_uuid, 'deliveries_per_day', 20000, 'daily');
        
        WHEN 'enterprise' THEN
            INSERT INTO user_webhook_quotas (user_id, quota_type, limit_value, reset_interval) VALUES
            (user_uuid, 'endpoints', 100, 'daily'),
            (user_uuid, 'events_per_hour', 10000, 'hourly'),
            (user_uuid, 'events_per_day', 100000, 'daily'),
            (user_uuid, 'deliveries_per_hour', 20000, 'hourly'),
            (user_uuid, 'deliveries_per_day', 200000, 'daily');
        
        WHEN 'admin' THEN
            INSERT INTO user_webhook_quotas (user_id, quota_type, limit_value, reset_interval) VALUES
            (user_uuid, 'endpoints', 500, 'daily'),
            (user_uuid, 'events_per_hour', 50000, 'hourly'),
            (user_uuid, 'events_per_day', 500000, 'daily'),
            (user_uuid, 'deliveries_per_hour', 100000, 'hourly'),
            (user_uuid, 'deliveries_per_day', 1000000, 'daily');
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to auto-create quotas for new users
CREATE OR REPLACE FUNCTION create_user_defaults()
RETURNS TRIGGER AS $$
BEGIN
    -- Create default settings
    INSERT INTO user_webhook_settings (user_id) VALUES (NEW.id);
    
    -- Create default quotas
    PERFORM create_default_quotas(NEW.id, NEW.role);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER create_webhook_user_defaults AFTER INSERT ON webhook_users
    FOR EACH ROW EXECUTE FUNCTION create_user_defaults();

-- Create function to clean up old data
CREATE OR REPLACE FUNCTION cleanup_old_webhook_data()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
    temp_count INTEGER;
BEGIN
    -- Delete old webhook events (older than 30 days)
    DELETE FROM webhook_events 
    WHERE created_at < NOW() - INTERVAL '30 days' 
    AND processed = TRUE;
    GET DIAGNOSTICS temp_count = ROW_COUNT;
    deleted_count := deleted_count + temp_count;
    
    -- Delete old webhook deliveries (older than 30 days)
    DELETE FROM webhook_deliveries 
    WHERE created_at < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS temp_count = ROW_COUNT;
    deleted_count := deleted_count + temp_count;
    
    -- Delete old webhook logs (older than 90 days)
    DELETE FROM webhook_logs 
    WHERE created_at < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS temp_count = ROW_COUNT;
    deleted_count := deleted_count + temp_count;
    
    -- Delete old webhook metrics (older than 365 days)
    DELETE FROM webhook_metrics 
    WHERE created_at < NOW() - INTERVAL '365 days';
    GET DIAGNOSTICS temp_count = ROW_COUNT;
    deleted_count := deleted_count + temp_count;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create sample data for testing (optional)
-- Uncomment the following lines to create sample data

/*
-- Sample user
INSERT INTO webhook_users (external_user_id, email, full_name, role, verified) VALUES 
('sample-user-123', 'test@example.com', 'Test User', 'premium', TRUE);

-- Sample webhook endpoint
INSERT INTO webhook_endpoints (user_id, name, description, url, event_types) VALUES 
((SELECT external_user_id FROM webhook_users WHERE email = 'test@example.com'), 
 'Test Webhook', 
 'Test webhook endpoint for development', 
 'https://webhook.site/test', 
 '["query.completed", "alert.triggered"]');
*/

-- Grant permissions (adjust as needed for your setup)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO webhook_service;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO webhook_service;