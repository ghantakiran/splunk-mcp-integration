-- Splunk MCP Integration Database Schema
-- Initial database setup and schema creation

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS chat;
CREATE SCHEMA IF NOT EXISTS spl;
CREATE SCHEMA IF NOT EXISTS viz;
CREATE SCHEMA IF NOT EXISTS alerts;
CREATE SCHEMA IF NOT EXISTS audit;

-- Users and Authentication Tables
CREATE TABLE auth.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    splunk_user_id VARCHAR(255),
    roles TEXT[] DEFAULT '{}',
    permissions JSONB DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE TABLE auth.user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT true
);

-- Chat and Conversation Tables
CREATE TABLE chat.conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    context JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE chat.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES chat.conversations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    message_type VARCHAR(50) CHECK (message_type IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    parent_message_id UUID REFERENCES chat.messages(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    edited_at TIMESTAMP WITH TIME ZONE,
    is_deleted BOOLEAN DEFAULT false
);

-- SPL Translation Tables
CREATE TABLE spl.queries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES chat.conversations(id) ON DELETE SET NULL,
    natural_language_query TEXT NOT NULL,
    generated_spl TEXT,
    optimized_spl TEXT,
    validation_status VARCHAR(50) DEFAULT 'pending',
    validation_errors JSONB DEFAULT '[]',
    execution_time_ms INTEGER,
    result_count INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    executed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE spl.query_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query_id UUID REFERENCES spl.queries(id) ON DELETE CASCADE,
    result_data JSONB,
    result_metadata JSONB DEFAULT '{}',
    execution_stats JSONB DEFAULT '{}',
    cached_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Visualization Tables
CREATE TABLE viz.dashboards (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    layout JSONB NOT NULL DEFAULT '{}',
    panels JSONB NOT NULL DEFAULT '[]',
    permissions JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    is_public BOOLEAN DEFAULT false,
    is_template BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_accessed TIMESTAMP WITH TIME ZONE
);

CREATE TABLE viz.charts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dashboard_id UUID REFERENCES viz.dashboards(id) ON DELETE CASCADE,
    query_id UUID REFERENCES spl.queries(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    chart_type VARCHAR(100) NOT NULL,
    configuration JSONB NOT NULL DEFAULT '{}',
    data_source JSONB DEFAULT '{}',
    position JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Alert Management Tables
CREATE TABLE alerts.alert_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    query_id UUID REFERENCES spl.queries(id) ON DELETE SET NULL,
    conditions JSONB NOT NULL DEFAULT '{}',
    notification_config JSONB NOT NULL DEFAULT '{}',
    schedule_config JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_triggered TIMESTAMP WITH TIME ZONE
);

CREATE TABLE alerts.alert_incidents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_rule_id UUID REFERENCES alerts.alert_rules(id) ON DELETE CASCADE,
    severity VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'acknowledged', 'resolved')),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    trigger_data JSONB DEFAULT '{}',
    acknowledged_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit and Logging Tables
CREATE TABLE audit.activity_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE audit.security_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    description TEXT,
    metadata JSONB DEFAULT '{}',
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_users_username ON auth.users(username);
CREATE INDEX idx_users_email ON auth.users(email);
CREATE INDEX idx_users_splunk_user_id ON auth.users(splunk_user_id);
CREATE INDEX idx_user_sessions_user_id ON auth.user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON auth.user_sessions(session_token);
CREATE INDEX idx_user_sessions_expires_at ON auth.user_sessions(expires_at);

CREATE INDEX idx_conversations_user_id ON chat.conversations(user_id);
CREATE INDEX idx_conversations_created_at ON chat.conversations(created_at);
CREATE INDEX idx_messages_conversation_id ON chat.messages(conversation_id);
CREATE INDEX idx_messages_user_id ON chat.messages(user_id);
CREATE INDEX idx_messages_created_at ON chat.messages(created_at);
CREATE INDEX idx_messages_type ON chat.messages(message_type);

CREATE INDEX idx_queries_user_id ON spl.queries(user_id);
CREATE INDEX idx_queries_conversation_id ON spl.queries(conversation_id);
CREATE INDEX idx_queries_created_at ON spl.queries(created_at);
CREATE INDEX idx_queries_validation_status ON spl.queries(validation_status);
CREATE INDEX idx_query_results_query_id ON spl.query_results(query_id);
CREATE INDEX idx_query_results_cached_until ON spl.query_results(cached_until);

CREATE INDEX idx_dashboards_user_id ON viz.dashboards(user_id);
CREATE INDEX idx_dashboards_created_at ON viz.dashboards(created_at);
CREATE INDEX idx_dashboards_is_public ON viz.dashboards(is_public);
CREATE INDEX idx_dashboards_tags ON viz.dashboards USING GIN(tags);
CREATE INDEX idx_charts_dashboard_id ON viz.charts(dashboard_id);
CREATE INDEX idx_charts_query_id ON viz.charts(query_id);

CREATE INDEX idx_alert_rules_user_id ON alerts.alert_rules(user_id);
CREATE INDEX idx_alert_rules_is_active ON alerts.alert_rules(is_active);
CREATE INDEX idx_alert_incidents_rule_id ON alerts.alert_incidents(alert_rule_id);
CREATE INDEX idx_alert_incidents_status ON alerts.alert_incidents(status);
CREATE INDEX idx_alert_incidents_severity ON alerts.alert_incidents(severity);
CREATE INDEX idx_alert_incidents_created_at ON alerts.alert_incidents(created_at);

CREATE INDEX idx_activity_logs_user_id ON audit.activity_logs(user_id);
CREATE INDEX idx_activity_logs_action ON audit.activity_logs(action);
CREATE INDEX idx_activity_logs_created_at ON audit.activity_logs(created_at);
CREATE INDEX idx_security_events_user_id ON audit.security_events(user_id);
CREATE INDEX idx_security_events_event_type ON audit.security_events(event_type);
CREATE INDEX idx_security_events_severity ON audit.security_events(severity);
CREATE INDEX idx_security_events_created_at ON audit.security_events(created_at);

-- Create functions for updated_at triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON auth.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON chat.conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_dashboards_updated_at BEFORE UPDATE ON viz.dashboards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_charts_updated_at BEFORE UPDATE ON viz.charts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alert_rules_updated_at BEFORE UPDATE ON alerts.alert_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (password: admin123)
INSERT INTO auth.users (
    username, 
    email, 
    password_hash, 
    first_name, 
    last_name, 
    is_active, 
    is_verified, 
    roles
) VALUES (
    'admin',
    'admin@splunk-mcp.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewSByrFYovkwKeCe', -- admin123
    'System',
    'Administrator',
    true,
    true,
    ARRAY['admin', 'user']
);

-- Insert sample data for development
INSERT INTO chat.conversations (user_id, title, context) VALUES (
    (SELECT id FROM auth.users WHERE username = 'admin'),
    'Sample Conversation',
    '{"last_query": "show me failed logins", "context_summary": "Security analysis"}'::jsonb
);

-- Log the database initialization
INSERT INTO audit.activity_logs (action, resource_type, details, created_at) VALUES (
    'database_initialized',
    'system',
    '{"version": "1.0.0", "schemas_created": ["auth", "chat", "spl", "viz", "alerts", "audit"]}'::jsonb,
    NOW()
);