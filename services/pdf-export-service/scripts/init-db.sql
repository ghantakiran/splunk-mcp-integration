-- PDF Export Service Database initialization script
-- This script creates the database schema and initial data

-- Create database (if running in environment where this is needed)
-- CREATE DATABASE pdfservice;

-- Connect to the database
\c pdfservice;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS pdf_export;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set search path
SET search_path = pdf_export, public;

-- PDF Export Users table
CREATE TABLE IF NOT EXISTS pdf_users (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    permissions JSONB DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- PDF Templates table
CREATE TABLE IF NOT EXISTS pdf_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    template_type VARCHAR(50) NOT NULL,
    description TEXT,
    template_content TEXT NOT NULL,
    css_content TEXT,
    variables JSONB DEFAULT '{}',
    layout_config JSONB DEFAULT '{}',
    created_by INTEGER REFERENCES pdf_users(id),
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- PDF Export Jobs table
CREATE TABLE IF NOT EXISTS pdf_export_jobs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES pdf_users(id),
    template_id INTEGER REFERENCES pdf_templates(id),
    job_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    parameters JSONB DEFAULT '{}',
    data_source JSONB DEFAULT '{}',
    output_format VARCHAR(20) DEFAULT 'pdf',
    file_path VARCHAR(500),
    file_size INTEGER,
    page_count INTEGER,
    error_message TEXT,
    generation_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- PDF Export Analytics table
CREATE TABLE IF NOT EXISTS pdf_export_analytics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES pdf_users(id),
    job_id INTEGER REFERENCES pdf_export_jobs(id),
    template_type VARCHAR(50),
    output_format VARCHAR(20),
    generation_time_ms INTEGER,
    file_size INTEGER,
    page_count INTEGER,
    success BOOLEAN NOT NULL,
    error_code VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    date_bucket DATE GENERATED ALWAYS AS (DATE(created_at)) STORED
);

-- PDF Export Preferences table
CREATE TABLE IF NOT EXISTS pdf_export_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES pdf_users(id) UNIQUE,
    default_template_id INTEGER REFERENCES pdf_templates(id),
    default_format VARCHAR(20) DEFAULT 'pdf',
    default_page_size VARCHAR(20) DEFAULT 'a4',
    default_orientation VARCHAR(20) DEFAULT 'portrait',
    default_dpi INTEGER DEFAULT 300,
    custom_css TEXT,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- PDF Export Logs table
CREATE TABLE IF NOT EXISTS pdf_export_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES pdf_users(id),
    job_id INTEGER REFERENCES pdf_export_jobs(id),
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_pdf_users_external_id ON pdf_users(external_id);
CREATE INDEX IF NOT EXISTS idx_pdf_users_email ON pdf_users(email);
CREATE INDEX IF NOT EXISTS idx_pdf_users_role ON pdf_users(role);
CREATE INDEX IF NOT EXISTS idx_pdf_users_status ON pdf_users(status);

CREATE INDEX IF NOT EXISTS idx_pdf_templates_type ON pdf_templates(template_type);
CREATE INDEX IF NOT EXISTS idx_pdf_templates_active ON pdf_templates(is_active);
CREATE INDEX IF NOT EXISTS idx_pdf_templates_default ON pdf_templates(is_default);
CREATE INDEX IF NOT EXISTS idx_pdf_templates_created_by ON pdf_templates(created_by);

CREATE INDEX IF NOT EXISTS idx_pdf_export_jobs_user_id ON pdf_export_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_pdf_export_jobs_template_id ON pdf_export_jobs(template_id);
CREATE INDEX IF NOT EXISTS idx_pdf_export_jobs_status ON pdf_export_jobs(status);
CREATE INDEX IF NOT EXISTS idx_pdf_export_jobs_created_at ON pdf_export_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_pdf_export_jobs_output_format ON pdf_export_jobs(output_format);

CREATE INDEX IF NOT EXISTS idx_pdf_export_analytics_user_id ON pdf_export_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_pdf_export_analytics_job_id ON pdf_export_analytics(job_id);
CREATE INDEX IF NOT EXISTS idx_pdf_export_analytics_date_bucket ON pdf_export_analytics(date_bucket);
CREATE INDEX IF NOT EXISTS idx_pdf_export_analytics_template_type ON pdf_export_analytics(template_type);
CREATE INDEX IF NOT EXISTS idx_pdf_export_analytics_success ON pdf_export_analytics(success);

CREATE INDEX IF NOT EXISTS idx_pdf_export_preferences_user_id ON pdf_export_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_pdf_export_preferences_template_id ON pdf_export_preferences(default_template_id);

CREATE INDEX IF NOT EXISTS idx_pdf_export_logs_user_id ON pdf_export_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_pdf_export_logs_job_id ON pdf_export_logs(job_id);
CREATE INDEX IF NOT EXISTS idx_pdf_export_logs_level ON pdf_export_logs(level);
CREATE INDEX IF NOT EXISTS idx_pdf_export_logs_created_at ON pdf_export_logs(created_at);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_pdf_jobs_user_status ON pdf_export_jobs(user_id, status);
CREATE INDEX IF NOT EXISTS idx_pdf_jobs_user_created ON pdf_export_jobs(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_pdf_analytics_user_date ON pdf_export_analytics(user_id, date_bucket);
CREATE INDEX IF NOT EXISTS idx_pdf_analytics_template_success ON pdf_export_analytics(template_type, success);

-- Text search indexes
CREATE INDEX IF NOT EXISTS idx_pdf_templates_name_search ON pdf_templates USING gin(to_tsvector('english', name));
CREATE INDEX IF NOT EXISTS idx_pdf_templates_content_search ON pdf_templates USING gin(to_tsvector('english', template_content));
CREATE INDEX IF NOT EXISTS idx_pdf_jobs_name_search ON pdf_export_jobs USING gin(to_tsvector('english', job_name));

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
DROP TRIGGER IF EXISTS update_pdf_users_updated_at ON pdf_users;
CREATE TRIGGER update_pdf_users_updated_at
    BEFORE UPDATE ON pdf_users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_pdf_templates_updated_at ON pdf_templates;
CREATE TRIGGER update_pdf_templates_updated_at
    BEFORE UPDATE ON pdf_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_pdf_export_preferences_updated_at ON pdf_export_preferences;
CREATE TRIGGER update_pdf_export_preferences_updated_at
    BEFORE UPDATE ON pdf_export_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically create analytics record
CREATE OR REPLACE FUNCTION create_analytics_record()
RETURNS TRIGGER AS $$
BEGIN
    -- Only create analytics record when job is completed or failed
    IF NEW.status IN ('completed', 'failed') AND OLD.status != NEW.status THEN
        INSERT INTO pdf_export_analytics (
            user_id, job_id, template_type, output_format, generation_time_ms,
            file_size, page_count, success, error_code
        )
        SELECT 
            NEW.user_id,
            NEW.id,
            pt.template_type,
            NEW.output_format,
            NEW.generation_time_ms,
            NEW.file_size,
            NEW.page_count,
            CASE WHEN NEW.status = 'completed' THEN TRUE ELSE FALSE END,
            CASE WHEN NEW.status = 'failed' THEN 'GENERATION_ERROR' ELSE NULL END
        FROM pdf_templates pt
        WHERE pt.id = NEW.template_id;
    END IF;
    
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for analytics creation
DROP TRIGGER IF EXISTS create_analytics_on_job_completion ON pdf_export_jobs;
CREATE TRIGGER create_analytics_on_job_completion
    AFTER UPDATE ON pdf_export_jobs
    FOR EACH ROW
    EXECUTE FUNCTION create_analytics_record();

-- Insert default user roles
INSERT INTO pdf_users (external_id, email, name, role, permissions) VALUES 
('system', 'system@example.com', 'System User', 'admin', '{"admin": true}')
ON CONFLICT (external_id) DO NOTHING;

-- Insert default templates
INSERT INTO pdf_templates (name, template_type, description, template_content, css_content, variables, layout_config, created_by, is_default) VALUES 
(
    'Standard Report',
    'report',
    'Standard report template with header, content, and footer',
    '<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
        <p>Generated on {{ generation_date }}</p>
    </div>
    <div class="content">
        {{ content }}
    </div>
    <div class="footer">
        <p>Generated by Splunk MCP Platform</p>
    </div>
</body>
</html>',
    'body { font-family: Arial, sans-serif; margin: 40px; }
.header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; }
.content { margin: 30px 0; }
.footer { text-align: center; border-top: 1px solid #ccc; padding-top: 20px; }',
    '{"title": "Report Title", "generation_date": "auto", "content": "Report content"}',
    '{"page_size": "a4", "orientation": "portrait"}',
    1,
    TRUE
),
(
    'Dashboard Template',
    'dashboard',
    'Template for dashboard exports with multiple charts',
    '<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ dashboard_title }}</title>
</head>
<body>
    <div class="dashboard-header">
        <h1>{{ dashboard_title }}</h1>
        <p>{{ dashboard_description }}</p>
        <p>Generated on {{ generation_date }}</p>
    </div>
    <div class="dashboard-grid">
        {% for chart in charts %}
        <div class="chart-container">
            <div class="chart-title">{{ chart.title }}</div>
            {{ chart.content }}
        </div>
        {% endfor %}
    </div>
</body>
</html>',
    'body { font-family: Arial, sans-serif; margin: 20px; }
.dashboard-header { text-align: center; margin-bottom: 30px; }
.dashboard-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.chart-container { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
.chart-title { font-weight: bold; margin-bottom: 10px; }',
    '{"dashboard_title": "Dashboard", "dashboard_description": "Dashboard description", "charts": []}',
    '{"page_size": "a4", "orientation": "landscape"}',
    1,
    TRUE
)
ON CONFLICT DO NOTHING;

-- Create audit schema tables
CREATE TABLE IF NOT EXISTS audit.pdf_export_audit (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    operation VARCHAR(20) NOT NULL,
    user_id INTEGER,
    old_values JSONB,
    new_values JSONB,
    changed_fields TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_table_name ON audit.pdf_export_audit(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_operation ON audit.pdf_export_audit(operation);
CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit.pdf_export_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit.pdf_export_audit(created_at);

-- Grant permissions
GRANT USAGE ON SCHEMA pdf_export TO pdfservice;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA pdf_export TO pdfservice;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA pdf_export TO pdfservice;
GRANT USAGE ON SCHEMA audit TO pdfservice;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA audit TO pdfservice;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA audit TO pdfservice;

-- Create summary views
CREATE OR REPLACE VIEW pdf_export_summary AS
SELECT 
    u.name as user_name,
    u.email as user_email,
    u.role as user_role,
    COUNT(j.id) as total_jobs,
    COUNT(CASE WHEN j.status = 'completed' THEN 1 END) as completed_jobs,
    COUNT(CASE WHEN j.status = 'failed' THEN 1 END) as failed_jobs,
    COUNT(CASE WHEN j.status = 'pending' THEN 1 END) as pending_jobs,
    COUNT(CASE WHEN j.status = 'processing' THEN 1 END) as processing_jobs,
    AVG(j.generation_time_ms) as avg_generation_time,
    SUM(j.file_size) as total_file_size,
    SUM(j.page_count) as total_pages,
    MIN(j.created_at) as first_job,
    MAX(j.created_at) as last_job
FROM pdf_users u
LEFT JOIN pdf_export_jobs j ON u.id = j.user_id
GROUP BY u.id, u.name, u.email, u.role;

CREATE OR REPLACE VIEW template_usage_summary AS
SELECT 
    t.id as template_id,
    t.name as template_name,
    t.template_type,
    t.is_active,
    t.is_default,
    COUNT(j.id) as total_usage,
    COUNT(CASE WHEN j.status = 'completed' THEN 1 END) as successful_usage,
    COUNT(CASE WHEN j.status = 'failed' THEN 1 END) as failed_usage,
    AVG(j.generation_time_ms) as avg_generation_time,
    AVG(j.file_size) as avg_file_size,
    AVG(j.page_count) as avg_page_count,
    MIN(j.created_at) as first_used,
    MAX(j.created_at) as last_used
FROM pdf_templates t
LEFT JOIN pdf_export_jobs j ON t.id = j.template_id
GROUP BY t.id, t.name, t.template_type, t.is_active, t.is_default;

-- Create function for cleanup old records
CREATE OR REPLACE FUNCTION cleanup_old_records(retention_days INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete old completed jobs
    DELETE FROM pdf_export_jobs 
    WHERE completed_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * retention_days
    AND status IN ('completed', 'failed');
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Delete old analytics records
    DELETE FROM pdf_export_analytics 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * retention_days;
    
    -- Delete old logs
    DELETE FROM pdf_export_logs 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * retention_days;
    
    -- Delete old audit records
    DELETE FROM audit.pdf_export_audit 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * retention_days;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create function for database statistics
CREATE OR REPLACE FUNCTION get_database_stats()
RETURNS TABLE (
    table_name TEXT,
    row_count BIGINT,
    table_size TEXT,
    index_size TEXT,
    total_size TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        schemaname||'.'||tablename as table_name,
        n_tup_ins - n_tup_del as row_count,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as table_size,
        pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as index_size,
        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) + pg_indexes_size(schemaname||'.'||tablename)) as total_size
    FROM pg_stat_user_tables 
    WHERE schemaname IN ('pdf_export', 'audit')
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
END;
$$ LANGUAGE plpgsql;

COMMIT;