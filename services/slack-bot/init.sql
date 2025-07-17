-- Database initialization script for Slack Bot service

-- Create tables for Slack bot functionality

-- Slack users table
CREATE TABLE IF NOT EXISTS slack_users (
    id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(255),
    real_name VARCHAR(255),
    email VARCHAR(255),
    team_id VARCHAR(20) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    is_owner BOOLEAN DEFAULT FALSE,
    is_bot BOOLEAN DEFAULT FALSE,
    timezone VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User contexts for Splunk access control
CREATE TABLE IF NOT EXISTS user_contexts (
    user_id VARCHAR(20) PRIMARY KEY REFERENCES slack_users(id) ON DELETE CASCADE,
    roles TEXT[] DEFAULT ARRAY['user'],
    permissions JSONB DEFAULT '{"read": true, "search": true}',
    accessible_indexes TEXT[] DEFAULT ARRAY['*'],
    preferences JSONB DEFAULT '{}',
    access_level VARCHAR(20) DEFAULT 'standard',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User sessions for conversation tracking
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL REFERENCES slack_users(id) ON DELETE CASCADE,
    channel_id VARCHAR(20) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    history JSONB DEFAULT '[]',
    context JSONB DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE
);

-- Query results for tracking and analytics
CREATE TABLE IF NOT EXISTS query_results (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES user_sessions(id) ON DELETE CASCADE,
    user_id VARCHAR(20) NOT NULL REFERENCES slack_users(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    spl_query TEXT,
    results JSONB DEFAULT '[]',
    execution_time FLOAT,
    error TEXT,
    confidence_score FLOAT,
    visualization_type VARCHAR(50),
    visualizations JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Bot metrics for monitoring
CREATE TABLE IF NOT EXISTS bot_metrics (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(20) NOT NULL,
    channel_id VARCHAR(20) NOT NULL,
    action_type VARCHAR(50) NOT NULL, -- query, command, interaction
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    error_type VARCHAR(100),
    response_time FLOAT,
    query_length INTEGER,
    results_count INTEGER
);

-- Alert definitions created via Slack
CREATE TABLE IF NOT EXISTS slack_alert_definitions (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    query TEXT NOT NULL,
    spl_query TEXT,
    condition VARCHAR(255) NOT NULL,
    threshold FLOAT,
    time_window INTEGER DEFAULT 300, -- 5 minutes
    notification_channels TEXT[] DEFAULT ARRAY['email'],
    enabled BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(20) NOT NULL REFERENCES slack_users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_slack_users_team_id ON slack_users(team_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_channel_id ON user_sessions(channel_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_last_activity ON user_sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_user_sessions_active ON user_sessions(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_query_results_user_id ON query_results(user_id);
CREATE INDEX IF NOT EXISTS idx_query_results_session_id ON query_results(session_id);
CREATE INDEX IF NOT EXISTS idx_query_results_created_at ON query_results(created_at);
CREATE INDEX IF NOT EXISTS idx_bot_metrics_user_id ON bot_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_bot_metrics_timestamp ON bot_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_bot_metrics_action_type ON bot_metrics(action_type);
CREATE INDEX IF NOT EXISTS idx_slack_alerts_created_by ON slack_alert_definitions(created_by);
CREATE INDEX IF NOT EXISTS idx_slack_alerts_enabled ON slack_alert_definitions(enabled) WHERE enabled = TRUE;

-- Update triggers for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers
DROP TRIGGER IF EXISTS update_slack_users_updated_at ON slack_users;
CREATE TRIGGER update_slack_users_updated_at 
    BEFORE UPDATE ON slack_users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_contexts_updated_at ON user_contexts;
CREATE TRIGGER update_user_contexts_updated_at 
    BEFORE UPDATE ON user_contexts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_slack_alert_definitions_updated_at ON slack_alert_definitions;
CREATE TRIGGER update_slack_alert_definitions_updated_at 
    BEFORE UPDATE ON slack_alert_definitions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (optional)
-- INSERT INTO slack_users (id, name, real_name, team_id, is_admin, access_level) 
-- VALUES ('U0000000000', 'admin', 'Admin User', 'T0000000000', TRUE, 'admin')
-- ON CONFLICT (id) DO NOTHING;