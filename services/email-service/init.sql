-- Database initialization script for Email Service

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enum types
CREATE TYPE email_status AS ENUM (
    'pending', 'queued', 'sending', 'sent', 'delivered', 'failed', 'bounced', 'rejected'
);

CREATE TYPE email_priority AS ENUM ('low', 'normal', 'high', 'urgent');

CREATE TYPE email_type AS ENUM (
    'query_request', 'query_response', 'report', 'alert', 'notification', 'auto_response', 'subscription'
);

CREATE TYPE attachment_type AS ENUM ('pdf', 'csv', 'xlsx', 'html', 'png', 'jpg', 'txt', 'zip');

CREATE TYPE report_status AS ENUM ('pending', 'generating', 'completed', 'failed', 'cancelled', 'expired');

CREATE TYPE report_format AS ENUM ('html', 'pdf', 'csv', 'xlsx', 'json', 'xml');

-- Email messages table
CREATE TABLE IF NOT EXISTS email_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id VARCHAR(255) UNIQUE NOT NULL,
    thread_id UUID,
    parent_id UUID,
    
    -- Email headers
    sender_email VARCHAR(255) NOT NULL,
    sender_name VARCHAR(255),
    recipient_email VARCHAR(255) NOT NULL,
    recipient_name VARCHAR(255),
    reply_to VARCHAR(255),
    cc JSONB,
    bcc JSONB,
    
    -- Message content
    subject VARCHAR(500) NOT NULL,
    body_text TEXT,
    body_html TEXT,
    
    -- Message metadata
    email_type email_type NOT NULL,
    priority email_priority DEFAULT 'normal',
    status email_status DEFAULT 'pending',
    
    -- Processing metadata
    query_id UUID,
    user_id VARCHAR(255),
    correlation_id VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Configuration
    template_id UUID,
    metadata JSONB
);

-- Email recipients table
CREATE TABLE IF NOT EXISTS email_recipients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES email_messages(id) ON DELETE CASCADE,
    
    email_address VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    recipient_type VARCHAR(10) NOT NULL CHECK (recipient_type IN ('to', 'cc', 'bcc')),
    
    -- Delivery tracking
    status email_status DEFAULT 'pending',
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,
    opened_at TIMESTAMP WITH TIME ZONE,
    clicked_at TIMESTAMP WITH TIME ZONE,
    
    -- Error tracking
    error_message TEXT,
    bounce_reason VARCHAR(255)
);

-- Email attachments table
CREATE TABLE IF NOT EXISTS email_attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES email_messages(id) ON DELETE CASCADE,
    
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    file_size INTEGER NOT NULL,
    attachment_type attachment_type NOT NULL,
    
    -- Storage information
    file_path VARCHAR(500),
    storage_url VARCHAR(500),
    checksum VARCHAR(64),
    
    -- Metadata
    description TEXT,
    is_inline BOOLEAN DEFAULT FALSE,
    content_id VARCHAR(255),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Email templates table
CREATE TABLE IF NOT EXISTS email_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    
    -- Template content
    subject_template VARCHAR(500) NOT NULL,
    body_text_template TEXT,
    body_html_template TEXT,
    
    -- Template metadata
    email_type email_type NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    version INTEGER DEFAULT 1,
    
    -- Template variables
    variables JSONB,
    default_values JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255)
);

-- Email users table
CREATE TABLE IF NOT EXISTS email_users (
    id VARCHAR(255) PRIMARY KEY,
    email_address VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    
    -- User status
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(255),
    verified_at TIMESTAMP WITH TIME ZONE,
    
    -- Authentication context
    organization VARCHAR(255),
    department VARCHAR(255),
    roles JSONB,
    permissions JSONB,
    
    -- Splunk context
    splunk_user_id VARCHAR(255),
    accessible_indexes JSONB,
    default_indexes JSONB,
    
    -- Usage statistics
    total_emails_sent INTEGER DEFAULT 0,
    total_emails_received INTEGER DEFAULT 0,
    total_queries_sent INTEGER DEFAULT 0,
    last_activity_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- User email settings table
CREATE TABLE IF NOT EXISTS user_email_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) UNIQUE NOT NULL REFERENCES email_users(id) ON DELETE CASCADE,
    
    -- Email format preferences
    preferred_format VARCHAR(10) DEFAULT 'html' CHECK (preferred_format IN ('html', 'text')),
    enable_rich_formatting BOOLEAN DEFAULT TRUE,
    enable_inline_images BOOLEAN DEFAULT TRUE,
    
    -- Query preferences
    auto_execute_queries BOOLEAN DEFAULT FALSE,
    require_confirmation BOOLEAN DEFAULT TRUE,
    max_results_per_query INTEGER DEFAULT 1000,
    default_time_range VARCHAR(50) DEFAULT 'last_hour',
    
    -- Report preferences
    default_report_format VARCHAR(10) DEFAULT 'pdf',
    include_raw_data BOOLEAN DEFAULT TRUE,
    include_visualizations BOOLEAN DEFAULT TRUE,
    compress_attachments BOOLEAN DEFAULT TRUE,
    
    -- Notification preferences
    notify_on_completion BOOLEAN DEFAULT TRUE,
    notify_on_errors BOOLEAN DEFAULT TRUE,
    notify_on_large_results BOOLEAN DEFAULT TRUE,
    large_results_threshold INTEGER DEFAULT 10000,
    
    -- Security preferences
    require_secure_delivery BOOLEAN DEFAULT FALSE,
    allowed_sender_domains JSONB,
    blocked_sender_domains JSONB,
    
    -- Response preferences
    enable_auto_responses BOOLEAN DEFAULT TRUE,
    auto_response_template TEXT,
    response_delay_seconds INTEGER DEFAULT 5,
    
    -- Rate limiting preferences
    max_emails_per_hour INTEGER DEFAULT 50,
    max_queries_per_hour INTEGER DEFAULT 20,
    max_reports_per_day INTEGER DEFAULT 10,
    
    -- Language and localization
    language VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',
    date_format VARCHAR(20) DEFAULT 'YYYY-MM-DD',
    time_format VARCHAR(10) DEFAULT '24h',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Email reports table
CREATE TABLE IF NOT EXISTS email_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Report configuration
    query_text TEXT NOT NULL,
    spl_query TEXT,
    search_indexes JSONB,
    time_range VARCHAR(50) NOT NULL,
    
    -- Output configuration
    output_formats JSONB NOT NULL,
    include_raw_data BOOLEAN DEFAULT TRUE,
    include_visualizations BOOLEAN DEFAULT TRUE,
    include_summary BOOLEAN DEFAULT TRUE,
    max_results INTEGER DEFAULT 10000,
    
    -- Visualization configuration
    chart_types JSONB,
    chart_config JSONB,
    dashboard_config JSONB,
    
    -- Generation metadata
    status report_status DEFAULT 'pending',
    priority email_priority DEFAULT 'normal',
    
    -- Execution tracking
    requested_by VARCHAR(255) NOT NULL,
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Results metadata
    query_execution_time FLOAT,
    report_generation_time FLOAT,
    total_records INTEGER,
    file_size_bytes INTEGER,
    
    -- File storage
    file_paths JSONB,
    download_urls JSONB,
    
    -- Error handling
    error_message TEXT,
    error_details JSONB,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Email context
    email_message_id UUID,
    correlation_id VARCHAR(255),
    
    -- Additional metadata
    metadata JSONB,
    tags JSONB
);

-- Email metrics table
CREATE TABLE IF NOT EXISTS email_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Metric identification
    metric_type VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    
    -- Dimensions
    user_id VARCHAR(255),
    email_type VARCHAR(50),
    status VARCHAR(20),
    
    -- Time dimension
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    date_key VARCHAR(10) NOT NULL,
    hour_key INTEGER NOT NULL,
    
    -- Additional metadata
    metadata JSONB
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_email_messages_user_id ON email_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_email_messages_status ON email_messages(status);
CREATE INDEX IF NOT EXISTS idx_email_messages_created_at ON email_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_email_messages_type ON email_messages(email_type);
CREATE INDEX IF NOT EXISTS idx_email_messages_correlation_id ON email_messages(correlation_id);

CREATE INDEX IF NOT EXISTS idx_email_recipients_message_id ON email_recipients(message_id);
CREATE INDEX IF NOT EXISTS idx_email_recipients_email ON email_recipients(email_address);

CREATE INDEX IF NOT EXISTS idx_email_attachments_message_id ON email_attachments(message_id);

CREATE INDEX IF NOT EXISTS idx_email_templates_type ON email_templates(email_type);
CREATE INDEX IF NOT EXISTS idx_email_templates_active ON email_templates(is_active) WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_email_users_email ON email_users(email_address);
CREATE INDEX IF NOT EXISTS idx_email_users_active ON email_users(is_active) WHERE is_active = TRUE;

CREATE INDEX IF NOT EXISTS idx_email_reports_requested_by ON email_reports(requested_by);
CREATE INDEX IF NOT EXISTS idx_email_reports_status ON email_reports(status);
CREATE INDEX IF NOT EXISTS idx_email_reports_requested_at ON email_reports(requested_at);

CREATE INDEX IF NOT EXISTS idx_email_metrics_type ON email_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_email_metrics_timestamp ON email_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_email_metrics_user_id ON email_metrics(user_id);

-- Update triggers for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update triggers
DROP TRIGGER IF EXISTS update_email_templates_updated_at ON email_templates;
CREATE TRIGGER update_email_templates_updated_at 
    BEFORE UPDATE ON email_templates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_email_users_updated_at ON email_users;
CREATE TRIGGER update_email_users_updated_at 
    BEFORE UPDATE ON email_users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_email_settings_updated_at ON user_email_settings;
CREATE TRIGGER update_user_email_settings_updated_at 
    BEFORE UPDATE ON user_email_settings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default email templates
INSERT INTO email_templates (name, description, subject_template, body_html_template, email_type) VALUES
('query_response', 'Default query response template', 'Splunk Query Results: {{query_summary}}', 
 '<h2>Query Results</h2><p><strong>Query:</strong> {{query_text}}</p><p><strong>Results:</strong> {{result_count}} records</p>{{#if has_data}}<div>{{results_table}}</div>{{/if}}', 
 'query_response'),
('report_notification', 'Report generation notification', 'Report Ready: {{report_name}}',
 '<h2>Report Generated</h2><p>Your report "{{report_name}}" is ready.</p><p><strong>Format:</strong> {{format}}</p><p><strong>Records:</strong> {{record_count}}</p>',
 'report'),
('alert_notification', 'Alert notification template', 'Splunk Alert: {{alert_name}}',
 '<h2>Alert Triggered</h2><p><strong>Alert:</strong> {{alert_name}}</p><p><strong>Condition:</strong> {{condition}}</p><p><strong>Time:</strong> {{timestamp}}</p>',
 'alert')
ON CONFLICT (name) DO NOTHING;