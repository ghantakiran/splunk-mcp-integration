-- PowerPoint Export Service Database Schema
-- This script initializes the database schema for the PowerPoint export service

-- Enable UUID extension for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table for service-specific user data
CREATE TABLE IF NOT EXISTS ppt_users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    roles TEXT[] NOT NULL DEFAULT '{}',
    permissions TEXT[] NOT NULL DEFAULT '{}',
    preferences JSONB DEFAULT '{}',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index on email for faster lookups
CREATE INDEX IF NOT EXISTS idx_ppt_users_email ON ppt_users(email);
CREATE INDEX IF NOT EXISTS idx_ppt_users_active ON ppt_users(is_active);

-- Create export jobs table
CREATE TABLE IF NOT EXISTS ppt_export_jobs (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(255) NOT NULL,
    user_id INTEGER NOT NULL REFERENCES ppt_users(id) ON DELETE CASCADE,
    presentation_config JSONB NOT NULL,
    data_source JSONB NOT NULL,
    output_format VARCHAR(10) NOT NULL DEFAULT 'pptx',
    theme VARCHAR(20) NOT NULL DEFAULT 'office',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    file_path TEXT,
    file_size BIGINT,
    slide_count INTEGER,
    chart_count INTEGER,
    animation_count INTEGER,
    error_message TEXT,
    generation_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_ppt_export_jobs_user_id ON ppt_export_jobs(user_id);
CREATE INDEX IF NOT EXISTS idx_ppt_export_jobs_status ON ppt_export_jobs(status);
CREATE INDEX IF NOT EXISTS idx_ppt_export_jobs_created_at ON ppt_export_jobs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ppt_export_jobs_expires_at ON ppt_export_jobs(expires_at);
CREATE INDEX IF NOT EXISTS idx_ppt_export_jobs_output_format ON ppt_export_jobs(output_format);
CREATE INDEX IF NOT EXISTS idx_ppt_export_jobs_theme ON ppt_export_jobs(theme);

-- Create templates table for reusable presentation templates
CREATE TABLE IF NOT EXISTS ppt_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    theme VARCHAR(20) NOT NULL DEFAULT 'office',
    template_data JSONB NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_by INTEGER REFERENCES ppt_users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for templates
CREATE INDEX IF NOT EXISTS idx_ppt_templates_name ON ppt_templates(name);
CREATE INDEX IF NOT EXISTS idx_ppt_templates_theme ON ppt_templates(theme);
CREATE INDEX IF NOT EXISTS idx_ppt_templates_is_default ON ppt_templates(is_default);
CREATE INDEX IF NOT EXISTS idx_ppt_templates_is_active ON ppt_templates(is_active);
CREATE INDEX IF NOT EXISTS idx_ppt_templates_created_by ON ppt_templates(created_by);

-- Create job metrics table for detailed analytics
CREATE TABLE IF NOT EXISTS ppt_job_metrics (
    id SERIAL PRIMARY KEY,
    job_id INTEGER NOT NULL REFERENCES ppt_export_jobs(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    metric_value NUMERIC,
    metric_unit VARCHAR(20),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for metrics
CREATE INDEX IF NOT EXISTS idx_ppt_job_metrics_job_id ON ppt_job_metrics(job_id);
CREATE INDEX IF NOT EXISTS idx_ppt_job_metrics_name ON ppt_job_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_ppt_job_metrics_recorded_at ON ppt_job_metrics(recorded_at);

-- Create user settings table for user preferences
CREATE TABLE IF NOT EXISTS ppt_user_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES ppt_users(id) ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL,
    setting_value JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, setting_key)
);

-- Create indexes for user settings
CREATE INDEX IF NOT EXISTS idx_ppt_user_settings_user_id ON ppt_user_settings(user_id);
CREATE INDEX IF NOT EXISTS idx_ppt_user_settings_key ON ppt_user_settings(setting_key);

-- Create audit log table for security and compliance
CREATE TABLE IF NOT EXISTS ppt_audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES ppt_users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id INTEGER,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for audit logs
CREATE INDEX IF NOT EXISTS idx_ppt_audit_logs_user_id ON ppt_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_ppt_audit_logs_action ON ppt_audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_ppt_audit_logs_resource ON ppt_audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_ppt_audit_logs_created_at ON ppt_audit_logs(created_at DESC);

-- Create function to automatically update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
DROP TRIGGER IF EXISTS update_ppt_users_updated_at ON ppt_users;
CREATE TRIGGER update_ppt_users_updated_at 
    BEFORE UPDATE ON ppt_users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_ppt_templates_updated_at ON ppt_templates;
CREATE TRIGGER update_ppt_templates_updated_at 
    BEFORE UPDATE ON ppt_templates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_ppt_user_settings_updated_at ON ppt_user_settings;
CREATE TRIGGER update_ppt_user_settings_updated_at 
    BEFORE UPDATE ON ppt_user_settings 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create function for cleanup of expired jobs
CREATE OR REPLACE FUNCTION cleanup_expired_jobs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Delete expired jobs and their associated files
    DELETE FROM ppt_export_jobs 
    WHERE expires_at IS NOT NULL 
    AND expires_at < CURRENT_TIMESTAMP;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Log the cleanup operation
    INSERT INTO ppt_audit_logs (action, details)
    VALUES ('cleanup_expired_jobs', jsonb_build_object('deleted_count', deleted_count));
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create function for job statistics
CREATE OR REPLACE FUNCTION get_job_statistics(
    p_user_id INTEGER DEFAULT NULL,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    total_jobs BIGINT,
    successful_jobs BIGINT,
    failed_jobs BIGINT,
    pending_jobs BIGINT,
    processing_jobs BIGINT,
    avg_generation_time NUMERIC,
    avg_file_size NUMERIC,
    avg_slide_count NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_jobs,
        COUNT(CASE WHEN j.status = 'completed' THEN 1 END) as successful_jobs,
        COUNT(CASE WHEN j.status = 'failed' THEN 1 END) as failed_jobs,
        COUNT(CASE WHEN j.status = 'pending' THEN 1 END) as pending_jobs,
        COUNT(CASE WHEN j.status = 'processing' THEN 1 END) as processing_jobs,
        AVG(CASE WHEN j.generation_time_ms IS NOT NULL THEN j.generation_time_ms END) as avg_generation_time,
        AVG(CASE WHEN j.file_size IS NOT NULL THEN j.file_size END) as avg_file_size,
        AVG(CASE WHEN j.slide_count IS NOT NULL THEN j.slide_count END) as avg_slide_count
    FROM ppt_export_jobs j
    WHERE (p_user_id IS NULL OR j.user_id = p_user_id)
    AND j.created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days' % p_days;
END;
$$ LANGUAGE plpgsql;

-- Insert default templates
INSERT INTO ppt_templates (name, description, theme, template_data, is_default, is_active) VALUES
(
    'Basic Report',
    'A simple template for basic reports with title and content slides',
    'office',
    '{
        "metadata": {
            "title": "Report Template",
            "author": "PowerPoint Export Service",
            "description": "Basic report template"
        },
        "slides": [
            {
                "title": "Report Title",
                "slide_type": "title",
                "layout": "title_slide",
                "content": {
                    "texts": [],
                    "images": [],
                    "charts": [],
                    "tables": []
                }
            },
            {
                "title": "Content Slide",
                "slide_type": "content",
                "layout": "title_and_content",
                "content": {
                    "texts": [],
                    "images": [],
                    "charts": [],
                    "tables": []
                }
            }
        ]
    }',
    true,
    true
),
(
    'Dashboard Template',
    'Template with multiple charts and visualizations',
    'modern',
    '{
        "metadata": {
            "title": "Dashboard Template",
            "author": "PowerPoint Export Service",
            "description": "Dashboard template with charts"
        },
        "slides": [
            {
                "title": "Dashboard Overview",
                "slide_type": "title",
                "layout": "title_slide",
                "content": {
                    "texts": [],
                    "images": [],
                    "charts": [],
                    "tables": []
                }
            },
            {
                "title": "Key Metrics",
                "slide_type": "chart",
                "layout": "title_and_content",
                "content": {
                    "texts": [],
                    "images": [],
                    "charts": [
                        {
                            "data": {
                                "labels": ["Q1", "Q2", "Q3", "Q4"],
                                "datasets": [
                                    {
                                        "label": "Revenue",
                                        "data": [100, 150, 200, 250]
                                    }
                                ]
                            },
                            "config": {
                                "chart_type": "column",
                                "title": "Quarterly Revenue",
                                "show_legend": true
                            },
                            "position": {
                                "x": 1,
                                "y": 2,
                                "width": 8,
                                "height": 5
                            }
                        }
                    ],
                    "tables": []
                }
            }
        ]
    }',
    true,
    true
);

-- Insert some sample metrics for demonstration
INSERT INTO ppt_job_metrics (job_id, metric_name, metric_value, metric_unit) 
SELECT 
    1, 
    'generation_time', 
    random() * 10000, 
    'ms'
WHERE EXISTS (SELECT 1 FROM ppt_export_jobs WHERE id = 1);

-- Create view for job summary statistics
CREATE OR REPLACE VIEW ppt_job_summary AS
SELECT 
    j.id,
    j.job_name,
    j.user_id,
    u.email as user_email,
    j.status,
    j.output_format,
    j.theme,
    j.file_size,
    j.slide_count,
    j.chart_count,
    j.animation_count,
    j.generation_time_ms,
    j.created_at,
    j.completed_at,
    j.expires_at,
    CASE 
        WHEN j.expires_at IS NOT NULL AND j.expires_at < CURRENT_TIMESTAMP THEN true
        ELSE false
    END as is_expired
FROM ppt_export_jobs j
LEFT JOIN ppt_users u ON j.user_id = u.id;

-- Grant appropriate permissions (adjust as needed for your security model)
-- These should be customized based on your application's user roles

-- Create a role for the application
-- CREATE ROLE ppt_app_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO ppt_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO ppt_app_user;

-- Create comments for documentation
COMMENT ON TABLE ppt_users IS 'Users table for PowerPoint export service';
COMMENT ON TABLE ppt_export_jobs IS 'PowerPoint export jobs with generation status and metadata';
COMMENT ON TABLE ppt_templates IS 'Reusable PowerPoint presentation templates';
COMMENT ON TABLE ppt_job_metrics IS 'Detailed metrics for export job performance analysis';
COMMENT ON TABLE ppt_user_settings IS 'User-specific settings and preferences';
COMMENT ON TABLE ppt_audit_logs IS 'Audit trail for security and compliance monitoring';

COMMENT ON COLUMN ppt_export_jobs.presentation_config IS 'JSON configuration for the presentation structure and content';
COMMENT ON COLUMN ppt_export_jobs.data_source IS 'JSON configuration for data source (query, file, or static)';
COMMENT ON COLUMN ppt_export_jobs.generation_time_ms IS 'Time taken to generate the presentation in milliseconds';

-- Create indexes for better performance on large datasets
CREATE INDEX IF NOT EXISTS idx_ppt_jobs_user_status_created 
ON ppt_export_jobs(user_id, status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_ppt_jobs_status_expires 
ON ppt_export_jobs(status, expires_at) 
WHERE expires_at IS NOT NULL;

-- Ensure database is ready
SELECT 'PowerPoint Export Service database initialized successfully' as status;