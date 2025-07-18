"""
Database connection and management for PDF Export Service.
"""

import asyncio
from typing import Optional, AsyncGenerator
import asyncpg
from asyncpg import Pool
import structlog
from contextlib import asynccontextmanager

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Global database pool
_db_pool: Optional[Pool] = None


async def create_db_pool() -> Pool:
    """Create database connection pool."""
    global _db_pool
    
    if _db_pool is not None:
        return _db_pool
    
    logger.info("Creating database connection pool", database_url=settings.DATABASE_URL.split("@")[1])
    
    try:
        _db_pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=5,
            max_size=settings.DATABASE_POOL_SIZE,
            max_queries=50000,
            max_inactive_connection_lifetime=300,
            timeout=settings.DATABASE_POOL_TIMEOUT,
            command_timeout=60,
            server_settings={
                'application_name': 'pdf-export-service',
                'jit': 'off'
            }
        )
        
        # Test connection
        async with _db_pool.acquire() as conn:
            await conn.execute("SELECT 1")
        
        logger.info("Database connection pool created successfully")
        return _db_pool
        
    except Exception as e:
        logger.error("Failed to create database pool", error=str(e))
        raise


async def close_db_pool():
    """Close database connection pool."""
    global _db_pool
    
    if _db_pool is not None:
        logger.info("Closing database connection pool")
        await _db_pool.close()
        _db_pool = None
        logger.info("Database connection pool closed")


def get_db_pool() -> Optional[Pool]:
    """Get the database connection pool."""
    return _db_pool


@asynccontextmanager
async def get_db_connection():
    """Get database connection from pool."""
    if _db_pool is None:
        await create_db_pool()
    
    async with _db_pool.acquire() as connection:
        try:
            yield connection
        except Exception as e:
            logger.error("Database connection error", error=str(e))
            raise


async def execute_query(query: str, *args, fetch: bool = False, fetchrow: bool = False, fetchval: bool = False):
    """Execute a database query."""
    async with get_db_connection() as conn:
        try:
            if fetchval:
                return await conn.fetchval(query, *args)
            elif fetchrow:
                return await conn.fetchrow(query, *args)
            elif fetch:
                return await conn.fetch(query, *args)
            else:
                return await conn.execute(query, *args)
        except Exception as e:
            logger.error("Query execution error", query=query, error=str(e))
            raise


async def execute_many(query: str, args_list: list):
    """Execute many queries with different parameters."""
    async with get_db_connection() as conn:
        try:
            return await conn.executemany(query, args_list)
        except Exception as e:
            logger.error("Execute many error", query=query, error=str(e))
            raise


async def init_database():
    """Initialize database tables and indexes."""
    logger.info("Initializing database schema")
    
    # Create tables
    create_tables_sql = """
    -- PDF Export Users table
    CREATE TABLE IF NOT EXISTS pdf_users (
        id SERIAL PRIMARY KEY,
        external_id VARCHAR(255) UNIQUE NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        name VARCHAR(255) NOT NULL,
        role VARCHAR(50) NOT NULL DEFAULT 'user',
        permissions JSONB DEFAULT '{}',
        preferences JSONB DEFAULT '{}',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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
    """
    
    # Create indexes
    create_indexes_sql = """
    -- Performance indexes
    CREATE INDEX IF NOT EXISTS idx_pdf_users_external_id ON pdf_users(external_id);
    CREATE INDEX IF NOT EXISTS idx_pdf_users_email ON pdf_users(email);
    CREATE INDEX IF NOT EXISTS idx_pdf_templates_type ON pdf_templates(template_type);
    CREATE INDEX IF NOT EXISTS idx_pdf_templates_active ON pdf_templates(is_active);
    CREATE INDEX IF NOT EXISTS idx_pdf_export_jobs_user_id ON pdf_export_jobs(user_id);
    CREATE INDEX IF NOT EXISTS idx_pdf_export_jobs_status ON pdf_export_jobs(status);
    CREATE INDEX IF NOT EXISTS idx_pdf_export_jobs_created_at ON pdf_export_jobs(created_at);
    CREATE INDEX IF NOT EXISTS idx_pdf_export_analytics_user_id ON pdf_export_analytics(user_id);
    CREATE INDEX IF NOT EXISTS idx_pdf_export_analytics_date_bucket ON pdf_export_analytics(date_bucket);
    CREATE INDEX IF NOT EXISTS idx_pdf_export_analytics_template_type ON pdf_export_analytics(template_type);
    CREATE INDEX IF NOT EXISTS idx_pdf_export_logs_job_id ON pdf_export_logs(job_id);
    CREATE INDEX IF NOT EXISTS idx_pdf_export_logs_created_at ON pdf_export_logs(created_at);
    
    -- Composite indexes for common queries
    CREATE INDEX IF NOT EXISTS idx_pdf_jobs_user_status ON pdf_export_jobs(user_id, status);
    CREATE INDEX IF NOT EXISTS idx_pdf_analytics_user_date ON pdf_export_analytics(user_id, date_bucket);
    """
    
    # Create triggers for updated_at
    create_triggers_sql = """
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
    """
    
    try:
        # Execute schema creation
        await execute_query(create_tables_sql)
        logger.info("Database tables created successfully")
        
        await execute_query(create_indexes_sql)
        logger.info("Database indexes created successfully")
        
        await execute_query(create_triggers_sql)
        logger.info("Database triggers created successfully")
        
        # Insert default templates
        await _insert_default_templates()
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        raise


async def _insert_default_templates():
    """Insert default PDF templates."""
    default_templates = [
        {
            "name": "Standard Report",
            "template_type": "report",
            "description": "Standard report template with header, content, and footer",
            "template_content": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 20px; }
        .content { margin: 30px 0; }
        .footer { text-align: center; border-top: 1px solid #ccc; padding-top: 20px; }
        .chart { text-align: center; margin: 20px 0; }
        .table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .table th, .table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .table th { background-color: #f2f2f2; }
    </style>
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
</html>
            """,
            "css_content": "",
            "variables": {"title": "Report Title", "generation_date": "auto", "content": "Report content"},
            "layout_config": {"page_size": "a4", "orientation": "portrait"},
            "is_default": True
        },
        {
            "name": "Dashboard Template",
            "template_type": "dashboard",
            "description": "Template for dashboard exports with multiple charts",
            "template_content": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ dashboard_title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .dashboard-header { text-align: center; margin-bottom: 30px; }
        .dashboard-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
        .chart-container { border: 1px solid #ddd; padding: 15px; border-radius: 5px; }
        .chart-title { font-weight: bold; margin-bottom: 10px; }
        .single-chart { grid-column: 1 / -1; }
    </style>
</head>
<body>
    <div class="dashboard-header">
        <h1>{{ dashboard_title }}</h1>
        <p>{{ dashboard_description }}</p>
        <p>Generated on {{ generation_date }}</p>
    </div>
    <div class="dashboard-grid">
        {% for chart in charts %}
        <div class="chart-container {{ 'single-chart' if chart.full_width else '' }}">
            <div class="chart-title">{{ chart.title }}</div>
            {{ chart.content }}
        </div>
        {% endfor %}
    </div>
</body>
</html>
            """,
            "css_content": "",
            "variables": {"dashboard_title": "Dashboard", "dashboard_description": "Dashboard description", "charts": []},
            "layout_config": {"page_size": "a4", "orientation": "landscape"},
            "is_default": True
        }
    ]
    
    # Check if default templates already exist
    existing_count = await execute_query(
        "SELECT COUNT(*) FROM pdf_templates WHERE is_default = TRUE",
        fetchval=True
    )
    
    if existing_count == 0:
        for template in default_templates:
            await execute_query(
                """
                INSERT INTO pdf_templates (name, template_type, description, template_content, 
                                         css_content, variables, layout_config, is_default)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                template["name"],
                template["template_type"],
                template["description"],
                template["template_content"],
                template["css_content"],
                template["variables"],
                template["layout_config"],
                template["is_default"]
            )
        
        logger.info("Default PDF templates inserted successfully")
    else:
        logger.info("Default PDF templates already exist, skipping insertion")


async def health_check() -> dict:
    """Check database health."""
    try:
        start_time = asyncio.get_event_loop().time()
        await execute_query("SELECT 1", fetchval=True)
        response_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        return {
            "status": "healthy",
            "response_time_ms": round(response_time, 2),
            "pool_size": _db_pool.get_size() if _db_pool else 0,
            "pool_used": _db_pool.get_size() - _db_pool.get_idle_size() if _db_pool else 0
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }