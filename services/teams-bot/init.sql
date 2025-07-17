-- Database initialization script for Microsoft Teams Bot service

-- Create tables for Teams bot functionality

-- Teams users table
CREATE TABLE IF NOT EXISTS teams_users (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255),
    aad_object_id VARCHAR(50) UNIQUE,
    tenant_id VARCHAR(50) NOT NULL,
    conversation_type VARCHAR(20) DEFAULT 'personal',
    is_admin BOOLEAN DEFAULT FALSE,
    is_bot BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User contexts for Splunk access control
CREATE TABLE IF NOT EXISTS user_contexts (
    user_id VARCHAR(50) PRIMARY KEY REFERENCES teams_users(id) ON DELETE CASCADE,
    roles TEXT[] DEFAULT ARRAY['user'],
    permissions JSONB DEFAULT '{"read": true, "search": true}',
    accessible_indexes TEXT[] DEFAULT ARRAY['*'],
    preferences JSONB DEFAULT '{}',
    access_level VARCHAR(20) DEFAULT 'standard',
    teams_tenant_id VARCHAR(50),
    aad_object_id VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Teams conversation sessions
CREATE TABLE IF NOT EXISTS teams_sessions (
    id UUID PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL REFERENCES teams_users(id) ON DELETE CASCADE,
    conversation_id VARCHAR(255) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    history JSONB DEFAULT '[]',
    context JSONB DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE
);

-- Teams activities log
CREATE TABLE IF NOT EXISTS teams_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    activity_id VARCHAR(255) UNIQUE,
    activity_type VARCHAR(50) NOT NULL,
    conversation_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(50) REFERENCES teams_users(id) ON DELETE SET NULL,
    channel_id VARCHAR(255),
    service_url TEXT NOT NULL,
    tenant_id VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    raw_activity JSONB DEFAULT '{}',
    processed BOOLEAN DEFAULT FALSE
);

-- Teams query results
CREATE TABLE IF NOT EXISTS teams_query_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES teams_sessions(id) ON DELETE CASCADE,
    user_id VARCHAR(50) NOT NULL REFERENCES teams_users(id) ON DELETE CASCADE,
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

-- Teams bot metrics
CREATE TABLE IF NOT EXISTS teams_metrics (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    conversation_id VARCHAR(255) NOT NULL,
    action_type VARCHAR(50) NOT NULL, -- query, command, interaction, invoke
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN DEFAULT TRUE,
    error_type VARCHAR(100),
    response_time FLOAT,
    query_length INTEGER,
    results_count INTEGER,
    activity_type VARCHAR(50)
);

-- Teams alert definitions
CREATE TABLE IF NOT EXISTS teams_alert_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    query TEXT NOT NULL,
    spl_query TEXT,
    condition VARCHAR(255) NOT NULL,
    threshold FLOAT,
    time_window INTEGER DEFAULT 300, -- 5 minutes
    notification_channels TEXT[] DEFAULT ARRAY['teams'],
    teams_webhook_url TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    created_by VARCHAR(50) NOT NULL REFERENCES teams_users(id) ON DELETE CASCADE,
    conversation_id VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Teams bot installations
CREATE TABLE IF NOT EXISTS teams_bot_installations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id VARCHAR(50) NOT NULL,
    team_id VARCHAR(50),
    conversation_id VARCHAR(255) NOT NULL UNIQUE,
    installer_user_id VARCHAR(50) NOT NULL,
    installation_type VARCHAR(20) NOT NULL, -- personal, team, groupChat
    scope VARCHAR(20) NOT NULL, -- personal, team, groupChat
    installed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Teams conversation references for proactive messaging
CREATE TABLE IF NOT EXISTS teams_conversation_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(50) NOT NULL REFERENCES teams_users(id) ON DELETE CASCADE,
    conversation_id VARCHAR(255) NOT NULL,
    activity_id VARCHAR(255),
    channel_id VARCHAR(255) NOT NULL,
    service_url TEXT NOT NULL,
    tenant_id VARCHAR(50),
    bot_data JSONB DEFAULT '{}',
    user_data JSONB DEFAULT '{}',
    conversation_data JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, conversation_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_teams_users_tenant_id ON teams_users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_teams_users_aad_object_id ON teams_users(aad_object_id);
CREATE INDEX IF NOT EXISTS idx_teams_sessions_user_id ON teams_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_teams_sessions_conversation_id ON teams_sessions(conversation_id);
CREATE INDEX IF NOT EXISTS idx_teams_sessions_last_activity ON teams_sessions(last_activity);
CREATE INDEX IF NOT EXISTS idx_teams_sessions_active ON teams_sessions(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_teams_activities_activity_id ON teams_activities(activity_id);
CREATE INDEX IF NOT EXISTS idx_teams_activities_conversation_id ON teams_activities(conversation_id);
CREATE INDEX IF NOT EXISTS idx_teams_activities_user_id ON teams_activities(user_id);
CREATE INDEX IF NOT EXISTS idx_teams_activities_timestamp ON teams_activities(timestamp);
CREATE INDEX IF NOT EXISTS idx_teams_activities_processed ON teams_activities(processed);
CREATE INDEX IF NOT EXISTS idx_teams_query_results_user_id ON teams_query_results(user_id);
CREATE INDEX IF NOT EXISTS idx_teams_query_results_session_id ON teams_query_results(session_id);
CREATE INDEX IF NOT EXISTS idx_teams_query_results_created_at ON teams_query_results(created_at);
CREATE INDEX IF NOT EXISTS idx_teams_metrics_user_id ON teams_metrics(user_id);
CREATE INDEX IF NOT EXISTS idx_teams_metrics_timestamp ON teams_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_teams_metrics_action_type ON teams_metrics(action_type);
CREATE INDEX IF NOT EXISTS idx_teams_alerts_created_by ON teams_alert_definitions(created_by);
CREATE INDEX IF NOT EXISTS idx_teams_alerts_enabled ON teams_alert_definitions(enabled) WHERE enabled = TRUE;
CREATE INDEX IF NOT EXISTS idx_teams_installations_tenant_id ON teams_bot_installations(tenant_id);
CREATE INDEX IF NOT EXISTS idx_teams_installations_conversation_id ON teams_bot_installations(conversation_id);
CREATE INDEX IF NOT EXISTS idx_teams_installations_active ON teams_bot_installations(is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_teams_conv_refs_user_id ON teams_conversation_references(user_id);
CREATE INDEX IF NOT EXISTS idx_teams_conv_refs_conversation_id ON teams_conversation_references(conversation_id);

-- Update triggers for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers
DROP TRIGGER IF EXISTS update_teams_users_updated_at ON teams_users;
CREATE TRIGGER update_teams_users_updated_at 
    BEFORE UPDATE ON teams_users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_contexts_updated_at ON user_contexts;
CREATE TRIGGER update_user_contexts_updated_at 
    BEFORE UPDATE ON user_contexts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_teams_alert_definitions_updated_at ON teams_alert_definitions;
CREATE TRIGGER update_teams_alert_definitions_updated_at 
    BEFORE UPDATE ON teams_alert_definitions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_teams_conversation_references_updated_at ON teams_conversation_references;
CREATE TRIGGER update_teams_conversation_references_updated_at 
    BEFORE UPDATE ON teams_conversation_references 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (optional)
-- INSERT INTO teams_users (id, name, tenant_id, is_admin) 
-- VALUES ('admin-user-id', 'Admin User', 'your-tenant-id', TRUE)
-- ON CONFLICT (id) DO NOTHING;