-- Excel Export Service Database Schema

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS excelservice;

-- Connect to the database
\c excelservice;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create users table
CREATE TABLE IF NOT EXISTS excel_users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    preferences JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on email
CREATE INDEX IF NOT EXISTS idx_excel_users_email ON excel_users(email);

-- Create templates table
CREATE TABLE IF NOT EXISTS excel_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    workbook_config JSONB NOT NULL,
    default_theme VARCHAR(50) DEFAULT 'office',
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES excel_users(id)
);

-- Create indexes on templates
CREATE INDEX IF NOT EXISTS idx_excel_templates_name ON excel_templates(name);
CREATE INDEX IF NOT EXISTS idx_excel_templates_created_by ON excel_templates(created_by);
CREATE INDEX IF NOT EXISTS idx_excel_templates_active ON excel_templates(is_active);

-- Create jobs table
CREATE TABLE IF NOT EXISTS excel_jobs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    job_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    workbook_config JSONB NOT NULL,
    data_source JSONB NOT NULL,
    output_format VARCHAR(10) NOT NULL DEFAULT 'xlsx',
    theme VARCHAR(50) NOT NULL DEFAULT 'office',
    file_path VARCHAR(500),
    file_size INTEGER,
    row_count INTEGER,
    worksheet_count INTEGER,
    chart_count INTEGER,
    error_message TEXT,
    generation_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES excel_users(id)
);

-- Create indexes on jobs
CREATE INDEX IF NOT EXISTS idx_excel_jobs_user_id ON excel_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_excel_jobs_status ON excel_jobs(status);
CREATE INDEX IF NOT EXISTS idx_excel_jobs_created_at ON excel_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_excel_jobs_output_format ON excel_jobs(output_format);
CREATE INDEX IF NOT EXISTS idx_excel_jobs_theme ON excel_jobs(theme);

-- Create job analytics table
CREATE TABLE IF NOT EXISTS excel_job_analytics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES excel_users(id),
    FOREIGN KEY (job_id) REFERENCES excel_jobs(id)
);

-- Create indexes on analytics
CREATE INDEX IF NOT EXISTS idx_excel_job_analytics_user_id ON excel_job_analytics(user_id);
CREATE INDEX IF NOT EXISTS idx_excel_job_analytics_job_id ON excel_job_analytics(job_id);
CREATE INDEX IF NOT EXISTS idx_excel_job_analytics_event_type ON excel_job_analytics(event_type);
CREATE INDEX IF NOT EXISTS idx_excel_job_analytics_created_at ON excel_job_analytics(created_at);

-- Create triggers for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_excel_users_updated_at 
    BEFORE UPDATE ON excel_users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_excel_templates_updated_at 
    BEFORE UPDATE ON excel_templates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default templates
INSERT INTO excel_users (email, full_name, is_active) VALUES
('system@example.com', 'System User', TRUE)
ON CONFLICT (email) DO NOTHING;

-- Get system user ID
DO $$
DECLARE
    system_user_id INTEGER;
BEGIN
    SELECT id INTO system_user_id FROM excel_users WHERE email = 'system@example.com';
    
    -- Insert default templates
    INSERT INTO excel_templates (name, description, workbook_config, default_theme, is_active, is_default, created_by) VALUES
    ('Basic Report', 'Simple report template with header and data', 
     '{
        "name": "Basic Report",
        "worksheets": [
            {
                "name": "Report",
                "data": [],
                "headers": ["Column 1", "Column 2", "Column 3"],
                "auto_filter": true,
                "freeze_panes": {"row": 2, "col": 1}
            }
        ],
        "theme": "office"
     }', 'office', TRUE, TRUE, system_user_id),
    
    ('Sales Dashboard', 'Sales dashboard with charts and metrics',
     '{
        "name": "Sales Dashboard",
        "worksheets": [
            {
                "name": "Dashboard",
                "data": [],
                "headers": ["Period", "Sales", "Targets", "Variance"],
                "auto_filter": true,
                "charts": [
                    {
                        "chart_id": "sales_trend",
                        "chart_type": "line",
                        "title": "Sales Trend",
                        "width": 600,
                        "height": 400,
                        "position": {"row": 10, "col": 1}
                    }
                ]
            }
        ],
        "theme": "modern"
     }', 'modern', TRUE, TRUE, system_user_id),
    
    ('Financial Report', 'Financial report with formatting and calculations',
     '{
        "name": "Financial Report",
        "worksheets": [
            {
                "name": "P&L",
                "data": [],
                "headers": ["Account", "Current", "Previous", "Variance", "Variance %"],
                "auto_filter": true,
                "freeze_panes": {"row": 2, "col": 1}
            },
            {
                "name": "Balance Sheet",
                "data": [],
                "headers": ["Account", "Current", "Previous"],
                "auto_filter": true
            }
        ],
        "theme": "office"
     }', 'office', TRUE, TRUE, system_user_id)
    ON CONFLICT DO NOTHING;
END $$;

-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_excel_jobs_user_status ON excel_jobs(user_id, status);
CREATE INDEX IF NOT EXISTS idx_excel_jobs_user_created ON excel_jobs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_excel_templates_user_active ON excel_templates(created_by, is_active);

-- Create cleanup function
CREATE OR REPLACE FUNCTION cleanup_old_excel_jobs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete jobs older than 30 days
    DELETE FROM excel_jobs 
    WHERE created_at < NOW() - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Delete analytics older than 90 days
    DELETE FROM excel_job_analytics 
    WHERE created_at < NOW() - INTERVAL '90 days';
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO excelservice;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO excelservice;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO excelservice;