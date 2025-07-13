"""Initial migration with all models

Revision ID: 001
Revises: 
Create Date: 2025-07-13 12:34:56.789012

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema"""
    
    # Create schemas
    op.execute('CREATE SCHEMA IF NOT EXISTS auth')
    op.execute('CREATE SCHEMA IF NOT EXISTS chat')
    op.execute('CREATE SCHEMA IF NOT EXISTS spl')
    op.execute('CREATE SCHEMA IF NOT EXISTS viz')
    op.execute('CREATE SCHEMA IF NOT EXISTS alerts')
    op.execute('CREATE SCHEMA IF NOT EXISTS audit')
    
    # Enable UUID extension for PostgreSQL
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    
    # Create auth.users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=255), nullable=True),
        sa.Column('last_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('splunk_user_id', sa.String(length=255), nullable=True),
        sa.Column('roles', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('login_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('timezone', sa.String(length=50), nullable=True, server_default='UTC'),
        sa.Column('language', sa.String(length=10), nullable=True, server_default='en'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        schema='auth'
    )
    op.create_index(op.f('ix_auth_users_email'), 'users', ['email'], unique=True, schema='auth')
    op.create_index(op.f('ix_auth_users_username'), 'users', ['username'], unique=True, schema='auth')
    op.create_index(op.f('ix_auth_users_splunk_user_id'), 'users', ['splunk_user_id'], unique=False, schema='auth')
    
    # Create chat.conversations table
    op.create_table('conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='chat'
    )
    op.create_index(op.f('ix_chat_conversations_user_id'), 'conversations', ['user_id'], unique=False, schema='chat')
    op.create_index(op.f('ix_chat_conversations_created_at'), 'conversations', ['created_at'], unique=False, schema='chat')
    
    # Create chat.messages table
    op.create_table('messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('message_type', sa.Enum('USER', 'ASSISTANT', 'SYSTEM', name='messagetype'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('parent_message_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['conversation_id'], ['chat.conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_message_id'], ['chat.messages.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema='chat'
    )
    op.create_index(op.f('ix_chat_messages_conversation_id'), 'messages', ['conversation_id'], unique=False, schema='chat')
    op.create_index(op.f('ix_chat_messages_user_id'), 'messages', ['user_id'], unique=False, schema='chat')
    op.create_index(op.f('ix_chat_messages_message_type'), 'messages', ['message_type'], unique=False, schema='chat')
    op.create_index(op.f('ix_chat_messages_created_at'), 'messages', ['created_at'], unique=False, schema='chat')
    
    # Create spl.queries table
    op.create_table('queries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('natural_language_query', sa.Text(), nullable=False),
        sa.Column('generated_spl', sa.Text(), nullable=True),
        sa.Column('optimized_spl', sa.Text(), nullable=True),
        sa.Column('final_spl', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'TRANSLATING', 'TRANSLATED', 'VALIDATING', 'EXECUTING', 'COMPLETED', 'FAILED', 'CANCELLED', name='querystatus'), nullable=False),
        sa.Column('validation_status', sa.Enum('PENDING', 'VALID', 'INVALID', 'WARNING', name='validationstatus'), nullable=False),
        sa.Column('validation_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('validation_warnings', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.Column('result_count', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('translation_time_ms', sa.Integer(), nullable=True),
        sa.Column('validation_time_ms', sa.Integer(), nullable=True),
        sa.Column('splunk_job_id', sa.String(length=255), nullable=True),
        sa.Column('splunk_search_id', sa.String(length=255), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('query_type', sa.String(length=50), nullable=True),
        sa.Column('complexity_score', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['conversation_id'], ['chat.conversations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema='spl'
    )
    op.create_index(op.f('ix_spl_queries_user_id'), 'queries', ['user_id'], unique=False, schema='spl')
    op.create_index(op.f('ix_spl_queries_conversation_id'), 'queries', ['conversation_id'], unique=False, schema='spl')
    op.create_index(op.f('ix_spl_queries_status'), 'queries', ['status'], unique=False, schema='spl')
    op.create_index(op.f('ix_spl_queries_validation_status'), 'queries', ['validation_status'], unique=False, schema='spl')
    op.create_index(op.f('ix_spl_queries_splunk_job_id'), 'queries', ['splunk_job_id'], unique=False, schema='spl')
    op.create_index(op.f('ix_spl_queries_query_type'), 'queries', ['query_type'], unique=False, schema='spl')
    op.create_index(op.f('ix_spl_queries_created_at'), 'queries', ['created_at'], unique=False, schema='spl')
    
    # Create spl.query_results table
    op.create_table('query_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('query_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('result_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('result_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('execution_stats', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('cached_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('format_type', sa.String(length=50), nullable=True),
        sa.Column('result_size_bytes', sa.Integer(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('column_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['query_id'], ['spl.queries.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='spl'
    )
    op.create_index(op.f('ix_spl_query_results_query_id'), 'query_results', ['query_id'], unique=False, schema='spl')
    op.create_index(op.f('ix_spl_query_results_cached_until'), 'query_results', ['cached_until'], unique=False, schema='spl')
    
    # Create viz.dashboards table
    op.create_table('dashboards',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('layout', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('panels', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_template', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('last_accessed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema='viz'
    )
    op.create_index(op.f('ix_viz_dashboards_user_id'), 'dashboards', ['user_id'], unique=False, schema='viz')
    op.create_index(op.f('ix_viz_dashboards_is_public'), 'dashboards', ['is_public'], unique=False, schema='viz')
    op.create_index(op.f('ix_viz_dashboards_created_at'), 'dashboards', ['created_at'], unique=False, schema='viz')
    
    # Create viz.charts table
    op.create_table('charts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('dashboard_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('query_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('chart_type', sa.String(length=100), nullable=False),
        sa.Column('configuration', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('data_source', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('position', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['dashboard_id'], ['viz.dashboards.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['query_id'], ['spl.queries.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema='viz'
    )
    op.create_index(op.f('ix_viz_charts_dashboard_id'), 'charts', ['dashboard_id'], unique=False, schema='viz')
    op.create_index(op.f('ix_viz_charts_query_id'), 'charts', ['query_id'], unique=False, schema='viz')
    
    # Create alerts.alert_rules table
    op.create_table('alert_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('query_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('notification_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('schedule_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_triggered', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['query_id'], ['spl.queries.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema='alerts'
    )
    op.create_index(op.f('ix_alerts_alert_rules_user_id'), 'alert_rules', ['user_id'], unique=False, schema='alerts')
    op.create_index(op.f('ix_alerts_alert_rules_is_active'), 'alert_rules', ['is_active'], unique=False, schema='alerts')
    
    # Create alerts.alert_incidents table
    op.create_table('alert_incidents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('alert_rule_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('acknowledged_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('resolved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='alertseverity'), nullable=False),
        sa.Column('status', sa.Enum('OPEN', 'ACKNOWLEDGED', 'RESOLVED', name='alertstatus'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('trigger_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['auth.users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['alert_rule_id'], ['alerts.alert_rules.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by'], ['auth.users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema='alerts'
    )
    op.create_index(op.f('ix_alerts_alert_incidents_alert_rule_id'), 'alert_incidents', ['alert_rule_id'], unique=False, schema='alerts')
    op.create_index(op.f('ix_alerts_alert_incidents_severity'), 'alert_incidents', ['severity'], unique=False, schema='alerts')
    op.create_index(op.f('ix_alerts_alert_incidents_status'), 'alert_incidents', ['status'], unique=False, schema='alerts')
    op.create_index(op.f('ix_alerts_alert_incidents_created_at'), 'alert_incidents', ['created_at'], unique=False, schema='alerts')
    
    # Create audit.activity_logs table
    op.create_table('activity_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=True),
        sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema='audit'
    )
    op.create_index(op.f('ix_audit_activity_logs_user_id'), 'activity_logs', ['user_id'], unique=False, schema='audit')
    op.create_index(op.f('ix_audit_activity_logs_action'), 'activity_logs', ['action'], unique=False, schema='audit')
    op.create_index(op.f('ix_audit_activity_logs_resource_type'), 'activity_logs', ['resource_type'], unique=False, schema='audit')
    op.create_index(op.f('ix_audit_activity_logs_resource_id'), 'activity_logs', ['resource_id'], unique=False, schema='audit')
    op.create_index(op.f('ix_audit_activity_logs_created_at'), 'activity_logs', ['created_at'], unique=False, schema='audit')
    
    # Create audit.security_events table
    op.create_table('security_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='securityeventseverity'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema='audit'
    )
    op.create_index(op.f('ix_audit_security_events_user_id'), 'security_events', ['user_id'], unique=False, schema='audit')
    op.create_index(op.f('ix_audit_security_events_event_type'), 'security_events', ['event_type'], unique=False, schema='audit')
    op.create_index(op.f('ix_audit_security_events_severity'), 'security_events', ['severity'], unique=False, schema='audit')
    op.create_index(op.f('ix_audit_security_events_created_at'), 'security_events', ['created_at'], unique=False, schema='audit')
    
    # Insert default admin user
    op.execute("""
        INSERT INTO auth.users (
            username, email, password_hash, first_name, last_name, 
            is_active, is_verified, roles
        ) VALUES (
            'admin', 'admin@splunk-mcp.local', 
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewSByrFYovkwKeCe',
            'System', 'Administrator', 
            true, true, ARRAY['admin', 'user']
        )
    """)
    
    # Log the database initialization
    op.execute("""
        INSERT INTO audit.activity_logs (action, resource_type, details) VALUES (
            'database_initialized', 'system', 
            '{"version": "1.0.0", "schemas_created": ["auth", "chat", "spl", "viz", "alerts", "audit"]}'::jsonb
        )
    """)


def downgrade() -> None:
    """Downgrade database schema"""
    
    # Drop all tables in reverse dependency order
    op.drop_table('security_events', schema='audit')
    op.drop_table('activity_logs', schema='audit')
    op.drop_table('alert_incidents', schema='alerts')
    op.drop_table('alert_rules', schema='alerts')
    op.drop_table('charts', schema='viz')
    op.drop_table('dashboards', schema='viz')
    op.drop_table('query_results', schema='spl')
    op.drop_table('queries', schema='spl')
    op.drop_table('messages', schema='chat')
    op.drop_table('conversations', schema='chat')
    op.drop_table('users', schema='auth')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS securityeventseverity')
    op.execute('DROP TYPE IF EXISTS alertstatus')
    op.execute('DROP TYPE IF EXISTS alertseverity')
    op.execute('DROP TYPE IF EXISTS validationstatus')
    op.execute('DROP TYPE IF EXISTS querystatus')
    op.execute('DROP TYPE IF EXISTS messagetype')
    
    # Drop schemas
    op.execute('DROP SCHEMA IF EXISTS audit CASCADE')
    op.execute('DROP SCHEMA IF EXISTS alerts CASCADE')
    op.execute('DROP SCHEMA IF EXISTS viz CASCADE')
    op.execute('DROP SCHEMA IF EXISTS spl CASCADE')
    op.execute('DROP SCHEMA IF EXISTS chat CASCADE')
    op.execute('DROP SCHEMA IF EXISTS auth CASCADE')