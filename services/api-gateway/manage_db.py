#!/usr/bin/env python3
"""
Database management CLI script for Splunk MCP Integration
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.migrations import migration_manager
from app.core.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)


async def main():
    """Main CLI function"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == "init":
            await cmd_init()
        elif command == "create":
            await cmd_create()
        elif command == "upgrade":
            await cmd_upgrade()
        elif command == "downgrade":
            await cmd_downgrade()
        elif command == "current":
            await cmd_current()
        elif command == "history":
            await cmd_history()
        elif command == "status":
            await cmd_status()
        elif command == "stamp":
            await cmd_stamp()
        elif command == "reset":
            await cmd_reset()
        else:
            print(f"Unknown command: {command}")
            print_usage()
            sys.exit(1)
    except Exception as e:
        logger.error(f"Command failed: {e}", exc_info=True)
        sys.exit(1)


def print_usage():
    """Print usage information"""
    print("Database Management CLI for Splunk MCP Integration")
    print()
    print("Usage: python manage_db.py <command> [options]")
    print()
    print("Commands:")
    print("  init                    Initialize Alembic (first time setup)")
    print("  create <message>        Create a new migration")
    print("  upgrade [revision]      Upgrade to revision (default: head)")
    print("  downgrade <revision>    Downgrade to revision")
    print("  current                 Show current revision")
    print("  history                 Show migration history")
    print("  status                  Show migration status")
    print("  stamp [revision]        Stamp database with revision (default: head)")
    print("  reset                   Reset database (WARNING: destroys all data)")
    print()
    print("Examples:")
    print("  python manage_db.py init")
    print("  python manage_db.py create 'Add user preferences table'")
    print("  python manage_db.py upgrade")
    print("  python manage_db.py status")


async def cmd_init():
    """Initialize Alembic"""
    print("Initializing Alembic...")
    migration_manager.init_alembic()
    print("✅ Alembic initialized successfully")


async def cmd_create():
    """Create a new migration"""
    if len(sys.argv) < 3:
        print("❌ Error: Migration message is required")
        print("Usage: python manage_db.py create <message>")
        sys.exit(1)
    
    message = " ".join(sys.argv[2:])
    print(f"Creating migration: {message}")
    
    try:
        revision = migration_manager.create_migration(message, autogenerate=True)
        print(f"✅ Migration created successfully: {revision}")
    except Exception as e:
        print(f"❌ Failed to create migration: {e}")
        raise


async def cmd_upgrade():
    """Upgrade database"""
    revision = sys.argv[2] if len(sys.argv) > 2 else "head"
    print(f"Upgrading database to: {revision}")
    
    try:
        migration_manager.upgrade_database(revision)
        print(f"✅ Database upgraded to: {revision}")
    except Exception as e:
        print(f"❌ Failed to upgrade database: {e}")
        raise


async def cmd_downgrade():
    """Downgrade database"""
    if len(sys.argv) < 3:
        print("❌ Error: Target revision is required")
        print("Usage: python manage_db.py downgrade <revision>")
        sys.exit(1)
    
    revision = sys.argv[2]
    print(f"Downgrading database to: {revision}")
    
    try:
        migration_manager.downgrade_database(revision)
        print(f"✅ Database downgraded to: {revision}")
    except Exception as e:
        print(f"❌ Failed to downgrade database: {e}")
        raise


async def cmd_current():
    """Show current revision"""
    print("Current database revision:")
    try:
        current = await migration_manager.get_current_revision()
        if current:
            print(f"📍 Current: {current}")
        else:
            print("❌ No revision found (database not initialized)")
    except Exception as e:
        print(f"❌ Failed to get current revision: {e}")
        raise


async def cmd_history():
    """Show migration history"""
    print("Migration history:")
    try:
        history = await migration_manager.get_migration_history()
        if history:
            for i, revision in enumerate(history):
                print(f"  {i+1}. {revision['revision']} - {revision['doc']}")
        else:
            print("❌ No migration history found")
    except Exception as e:
        print(f"❌ Failed to get migration history: {e}")
        raise


async def cmd_status():
    """Show migration status"""
    print("Migration status:")
    try:
        status = await migration_manager.check_migration_status()
        
        print(f"📍 Current revision: {status['current_revision'] or 'None'}")
        print(f"🎯 Head revision: {status['head_revision'] or 'None'}")
        print(f"✅ Up to date: {status['is_up_to_date']}")
        
        if status['pending_migrations']:
            print(f"⏳ Pending migrations ({len(status['pending_migrations'])}):")
            for migration in status['pending_migrations']:
                print(f"  - {migration['revision']}: {migration['doc']}")
        else:
            print("✅ No pending migrations")
        
        if status.get('error'):
            print(f"❌ Error: {status['error']}")
            
    except Exception as e:
        print(f"❌ Failed to get migration status: {e}")
        raise


async def cmd_stamp():
    """Stamp database with revision"""
    revision = sys.argv[2] if len(sys.argv) > 2 else "head"
    print(f"Stamping database with revision: {revision}")
    
    try:
        migration_manager.stamp_database(revision)
        print(f"✅ Database stamped with: {revision}")
    except Exception as e:
        print(f"❌ Failed to stamp database: {e}")
        raise


async def cmd_reset():
    """Reset database (WARNING: destroys all data)"""
    print("⚠️  WARNING: This will destroy ALL data in the database!")
    print("This action cannot be undone.")
    
    confirm = input("Type 'CONFIRM' to proceed: ")
    if confirm != "CONFIRM":
        print("❌ Operation cancelled")
        return
    
    try:
        from app.db.session import create_engine
        from app.db.base import Base
        
        print("Dropping all tables...")
        engine = await create_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        print("Recreating all tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        await engine.dispose()
        
        print("Stamping database with head revision...")
        migration_manager.stamp_database("head")
        
        print("✅ Database reset completed")
        
    except Exception as e:
        print(f"❌ Failed to reset database: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())