"""
Database migration utilities and helpers
"""

import asyncio
from pathlib import Path
from typing import Optional
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import inspect, text

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class MigrationManager:
    """Database migration manager"""
    
    def __init__(self):
        self.alembic_cfg_path = Path(__file__).parent.parent.parent / "alembic.ini"
        self.alembic_cfg = Config(str(self.alembic_cfg_path))
        self.alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    
    def init_alembic(self) -> None:
        """Initialize Alembic if not already initialized"""
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            if script_dir.get_current_head() is None:
                logger.info("Initializing Alembic")
                command.init(self.alembic_cfg, "alembic")
        except Exception as e:
            logger.warning("Alembic may already be initialized", error=str(e))
    
    def create_migration(
        self, 
        message: str, 
        autogenerate: bool = True,
        head: str = "head"
    ) -> str:
        """Create a new migration"""
        try:
            logger.info("Creating migration", message=message, autogenerate=autogenerate)
            
            if autogenerate:
                command.revision(
                    self.alembic_cfg,
                    message=message,
                    autogenerate=True,
                    head=head
                )
            else:
                command.revision(
                    self.alembic_cfg,
                    message=message,
                    head=head
                )
            
            # Get the latest revision
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            head_revision = script_dir.get_current_head()
            
            logger.info("Migration created successfully", revision=head_revision)
            return head_revision
            
        except Exception as e:
            logger.error("Failed to create migration", error=str(e), exc_info=True)
            raise
    
    def upgrade_database(self, revision: str = "head") -> None:
        """Upgrade database to specified revision"""
        try:
            logger.info("Upgrading database", revision=revision)
            command.upgrade(self.alembic_cfg, revision)
            logger.info("Database upgrade completed", revision=revision)
        except Exception as e:
            logger.error("Failed to upgrade database", error=str(e), exc_info=True)
            raise
    
    def downgrade_database(self, revision: str) -> None:
        """Downgrade database to specified revision"""
        try:
            logger.info("Downgrading database", revision=revision)
            command.downgrade(self.alembic_cfg, revision)
            logger.info("Database downgrade completed", revision=revision)
        except Exception as e:
            logger.error("Failed to downgrade database", error=str(e), exc_info=True)
            raise
    
    async def get_current_revision(self) -> Optional[str]:
        """Get current database revision"""
        try:
            engine = create_async_engine(settings.database_url)
            
            async with engine.connect() as connection:
                # Check if alembic_version table exists
                result = await connection.run_sync(
                    lambda sync_conn: inspect(sync_conn).has_table("alembic_version")
                )
                
                if not result:
                    await engine.dispose()
                    return None
                
                # Get current revision
                result = await connection.execute(
                    text("SELECT version_num FROM alembic_version")
                )
                row = result.fetchone()
                current_revision = row[0] if row else None
                
            await engine.dispose()
            return current_revision
            
        except Exception as e:
            logger.error("Failed to get current revision", error=str(e))
            return None
    
    async def get_migration_history(self) -> list:
        """Get migration history"""
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            revisions = []
            
            for revision in script_dir.walk_revisions():
                revisions.append({
                    "revision": revision.revision,
                    "down_revision": revision.down_revision,
                    "doc": revision.doc,
                    "branch_labels": revision.branch_labels,
                })
            
            return revisions
            
        except Exception as e:
            logger.error("Failed to get migration history", error=str(e))
            return []
    
    async def check_migration_status(self) -> dict:
        """Check database migration status"""
        try:
            current_revision = await self.get_current_revision()
            script_dir = ScriptDirectory.from_config(self.alembic_cfg)
            head_revision = script_dir.get_current_head()
            
            status = {
                "current_revision": current_revision,
                "head_revision": head_revision,
                "is_up_to_date": current_revision == head_revision,
                "needs_upgrade": current_revision != head_revision,
            }
            
            if current_revision:
                # Get pending migrations
                pending = []
                for revision in script_dir.iterate_revisions(current_revision, head_revision):
                    if revision.revision != current_revision:
                        pending.append({
                            "revision": revision.revision,
                            "doc": revision.doc
                        })
                status["pending_migrations"] = pending
            else:
                status["pending_migrations"] = []
            
            return status
            
        except Exception as e:
            logger.error("Failed to check migration status", error=str(e))
            return {
                "current_revision": None,
                "head_revision": None,
                "is_up_to_date": False,
                "needs_upgrade": True,
                "pending_migrations": [],
                "error": str(e)
            }
    
    def show_current_revision(self) -> None:
        """Show current revision"""
        command.current(self.alembic_cfg)
    
    def show_migration_history(self) -> None:
        """Show migration history"""
        command.history(self.alembic_cfg)
    
    def stamp_database(self, revision: str = "head") -> None:
        """Stamp database with revision without running migrations"""
        try:
            logger.info("Stamping database", revision=revision)
            command.stamp(self.alembic_cfg, revision)
            logger.info("Database stamped successfully", revision=revision)
        except Exception as e:
            logger.error("Failed to stamp database", error=str(e), exc_info=True)
            raise


# Global migration manager instance
migration_manager = MigrationManager()


async def init_database_with_migrations():
    """Initialize database with migrations"""
    try:
        logger.info("Initializing database with migrations")
        
        # Check migration status
        status = await migration_manager.check_migration_status()
        logger.info("Migration status", status=status)
        
        if status["current_revision"] is None:
            # Database not initialized - run all migrations
            logger.info("Database not initialized, running all migrations")
            migration_manager.upgrade_database()
        elif status["needs_upgrade"]:
            # Database needs upgrade
            logger.info("Database needs upgrade, running pending migrations")
            migration_manager.upgrade_database()
        else:
            # Database is up to date
            logger.info("Database is up to date")
        
        # Verify final status
        final_status = await migration_manager.check_migration_status()
        logger.info("Final migration status", status=final_status)
        
    except Exception as e:
        logger.error("Failed to initialize database with migrations", error=str(e), exc_info=True)
        raise


# CLI helpers
async def create_initial_migration():
    """Create initial migration with all models"""
    try:
        logger.info("Creating initial migration")
        revision = migration_manager.create_migration(
            "Initial migration with all models",
            autogenerate=True
        )
        logger.info("Initial migration created", revision=revision)
        return revision
    except Exception as e:
        logger.error("Failed to create initial migration", error=str(e))
        raise


async def upgrade_to_head():
    """Upgrade database to head revision"""
    try:
        await init_database_with_migrations()
    except Exception as e:
        logger.error("Failed to upgrade to head", error=str(e))
        raise


if __name__ == "__main__":
    # CLI interface for migration operations
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python migrations.py <command>")
        print("Commands: init, create, upgrade, downgrade, current, history, status")
        sys.exit(1)
    
    command_name = sys.argv[1]
    
    if command_name == "init":
        migration_manager.init_alembic()
    elif command_name == "create":
        if len(sys.argv) < 3:
            print("Usage: python migrations.py create <message>")
            sys.exit(1)
        message = " ".join(sys.argv[2:])
        migration_manager.create_migration(message)
    elif command_name == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        migration_manager.upgrade_database(revision)
    elif command_name == "downgrade":
        if len(sys.argv) < 3:
            print("Usage: python migrations.py downgrade <revision>")
            sys.exit(1)
        revision = sys.argv[2]
        migration_manager.downgrade_database(revision)
    elif command_name == "current":
        migration_manager.show_current_revision()
    elif command_name == "history":
        migration_manager.show_migration_history()
    elif command_name == "status":
        status = asyncio.run(migration_manager.check_migration_status())
        print(f"Migration Status: {status}")
    else:
        print(f"Unknown command: {command_name}")
        sys.exit(1)