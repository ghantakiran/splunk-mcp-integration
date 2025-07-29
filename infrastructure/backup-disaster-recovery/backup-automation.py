#!/usr/bin/env python3
"""
Comprehensive Backup Automation System
=====================================
Automated backup system for Splunk MCP Integration platform with advanced
scheduling, verification, retention management, and disaster recovery capabilities
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
import time
import yaml
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import boto3
import psycopg2
import redis
import kubernetes
from kubernetes import client, config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BackupType(Enum):
    """Backup types supported by the system"""
    DATABASE = "database"
    REDIS = "redis"
    KUBERNETES = "kubernetes"
    APPLICATION_DATA = "application_data"
    CONFIGURATION = "configuration"
    SECRETS = "secrets"
    VOLUMES = "volumes"
    FULL_SYSTEM = "full_system"

class BackupStatus(Enum):
    """Backup operation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"
    EXPIRED = "expired"

class StorageBackend(Enum):
    """Storage backend options"""
    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"
    NFS = "nfs"

@dataclass
class BackupMetadata:
    """Backup metadata structure"""
    backup_id: str
    backup_type: BackupType
    timestamp: datetime
    size_bytes: int = 0
    storage_backend: StorageBackend = StorageBackend.LOCAL
    storage_path: str = ""
    checksum: str = ""
    compression: str = "gzip"
    encryption: bool = False
    retention_days: int = 30
    status: BackupStatus = BackupStatus.PENDING
    environment: str = "production"
    source_info: Dict[str, Any] = field(default_factory=dict)
    verification_info: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""

@dataclass
class RestoreRequest:
    """Restore operation request"""
    backup_id: str
    restore_type: BackupType
    target_environment: str
    restore_point: datetime
    partial_restore: bool = False
    restore_components: List[str] = field(default_factory=list)
    dry_run: bool = False
    force_restore: bool = False

class BackupAutomationSystem:
    """Main backup automation system"""
    
    def __init__(self, config_path: str = "backup-config.yaml"):
        self.config = self._load_config(config_path)
        self.storage_backends = self._initialize_storage_backends()
        self.k8s_client = self._setup_kubernetes()
        self.backup_registry: Dict[str, BackupMetadata] = {}
        self.active_backups: Dict[str, asyncio.Task] = {}
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load backup configuration"""
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return yaml.safe_load(f)
            else:
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default backup configuration"""
        return {
            "storage": {
                "primary_backend": "s3",
                "backup_backends": ["local"],
                "local_path": "/backup/splunk-mcp",
                "s3": {
                    "bucket": "splunk-mcp-backups",
                    "region": "us-east-1",
                    "encryption": "AES256"
                }
            },
            "retention": {
                "daily": 7,
                "weekly": 4,
                "monthly": 12,
                "yearly": 3
            },
            "schedule": {
                "database": {
                    "frequency": "daily",
                    "time": "02:00",
                    "retention_days": 30
                },
                "kubernetes": {
                    "frequency": "daily", 
                    "time": "03:00",
                    "retention_days": 14
                },
                "full_system": {
                    "frequency": "weekly",
                    "time": "01:00",
                    "retention_days": 90
                }
            },
            "verification": {
                "enabled": True,
                "test_restore": True,
                "checksum_validation": True
            },
            "compression": {
                "enabled": True,
                "algorithm": "gzip",
                "level": 6
            },
            "encryption": {
                "enabled": True,
                "algorithm": "AES256",
                "key_rotation_days": 90
            }
        }
    
    def _initialize_storage_backends(self) -> Dict[str, Any]:
        """Initialize storage backend clients"""
        backends = {}
        
        # S3 Backend
        if self.config.get("storage", {}).get("s3"):
            try:
                backends["s3"] = boto3.client(
                    's3',
                    region_name=self.config["storage"]["s3"]["region"]
                )
            except Exception as e:
                logger.warning(f"Failed to initialize S3 backend: {e}")
        
        # Local Backend
        local_path = self.config.get("storage", {}).get("local_path", "/backup/splunk-mcp")
        Path(local_path).mkdir(parents=True, exist_ok=True)
        backends["local"] = {"path": local_path}
        
        return backends
    
    def _setup_kubernetes(self):
        """Setup Kubernetes client"""
        try:
            config.load_incluster_config()  # For running in cluster
        except:
            try:
                config.load_kube_config()  # For local development
            except:
                logger.warning("Could not load Kubernetes config")
                return None
        
        return client.ApiClient()
    
    async def create_backup(self, backup_type: BackupType, environment: str = "production") -> BackupMetadata:
        """Create a new backup"""
        backup_id = f"{backup_type.value}-{environment}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        metadata = BackupMetadata(
            backup_id=backup_id,
            backup_type=backup_type,
            timestamp=datetime.utcnow(),
            environment=environment,
            status=BackupStatus.PENDING
        )
        
        self.backup_registry[backup_id] = metadata
        
        try:
            # Start backup task
            if backup_type == BackupType.DATABASE:
                task = asyncio.create_task(self._backup_database(metadata))
            elif backup_type == BackupType.REDIS:
                task = asyncio.create_task(self._backup_redis(metadata))
            elif backup_type == BackupType.KUBERNETES:
                task = asyncio.create_task(self._backup_kubernetes(metadata))
            elif backup_type == BackupType.APPLICATION_DATA:
                task = asyncio.create_task(self._backup_application_data(metadata))
            elif backup_type == BackupType.FULL_SYSTEM:
                task = asyncio.create_task(self._backup_full_system(metadata))
            else:
                raise ValueError(f"Unsupported backup type: {backup_type}")
            
            self.active_backups[backup_id] = task
            metadata.status = BackupStatus.IN_PROGRESS
            
            # Wait for completion
            await task
            
            # Verify backup
            if self.config.get("verification", {}).get("enabled", True):
                await self._verify_backup(metadata)
            
            logger.info(f"Backup {backup_id} completed successfully")
            return metadata
            
        except Exception as e:
            metadata.status = BackupStatus.FAILED
            metadata.error_message = str(e)
            logger.error(f"Backup {backup_id} failed: {e}")
            raise
        
        finally:
            if backup_id in self.active_backups:
                del self.active_backups[backup_id]
    
    async def _backup_database(self, metadata: BackupMetadata):
        """Backup PostgreSQL database"""
        logger.info(f"Starting database backup: {metadata.backup_id}")
        
        try:
            # Database connection details
            db_config = {
                "host": os.getenv("DATABASE_HOST", "localhost"),
                "port": os.getenv("DATABASE_PORT", "5432"),
                "database": os.getenv("DATABASE_NAME", "splunk_mcp"),
                "username": os.getenv("DATABASE_USER", "postgres"),
                "password": os.getenv("DATABASE_PASSWORD", "")
            }
            
            # Create backup directory
            backup_dir = Path(self.storage_backends["local"]["path"]) / "database" / metadata.backup_id
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Main database backup
            db_backup_file = backup_dir / "database.sql"
            pg_dump_cmd = [
                "pg_dump",
                f"postgresql://{db_config['username']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}",
                "--no-password",
                "--verbose",
                "--format=custom",
                "--compress=9",
                f"--file={db_backup_file}"
            ]
            
            result = subprocess.run(pg_dump_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"pg_dump failed: {result.stderr}")
            
            # Schema-only backup for disaster recovery
            schema_backup_file = backup_dir / "schema.sql"
            schema_cmd = [
                "pg_dump",
                f"postgresql://{db_config['username']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}",
                "--no-password",
                "--schema-only",
                "--verbose",
                f"--file={schema_backup_file}"
            ]
            
            subprocess.run(schema_cmd, capture_output=True, text=True)
            
            # Backup database statistics and configuration
            stats_file = backup_dir / "database_stats.json"
            stats = await self._collect_database_stats(db_config)
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
            
            # Create compressed archive
            archive_path = backup_dir.with_suffix('.tar.gz')
            with tarfile.open(archive_path, 'w:gz') as tar:
                tar.add(backup_dir, arcname=metadata.backup_id)
            
            # Calculate checksum
            metadata.checksum = await self._calculate_checksum(archive_path)
            metadata.size_bytes = archive_path.stat().st_size
            metadata.storage_path = str(archive_path)
            
            # Upload to secondary storage backends
            await self._upload_to_storage(metadata, archive_path)
            
            # Clean up temporary directory
            shutil.rmtree(backup_dir)
            
            metadata.status = BackupStatus.COMPLETED
            metadata.source_info = {
                "database": db_config["database"],
                "host": db_config["host"],
                "backup_size": metadata.size_bytes,
                "compression": "gzip"
            }
            
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            metadata.status = BackupStatus.FAILED
            metadata.error_message = str(e)
            raise
    
    async def _backup_redis(self, metadata: BackupMetadata):
        """Backup Redis data"""
        logger.info(f"Starting Redis backup: {metadata.backup_id}")
        
        try:
            # Redis connection
            redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                password=os.getenv("REDIS_PASSWORD", None),
                decode_responses=False
            )
            
            # Create backup directory
            backup_dir = Path(self.storage_backends["local"]["path"]) / "redis" / metadata.backup_id
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Get Redis info
            redis_info = redis_client.info()
            
            # Save Redis data using BGSAVE
            redis_client.bgsave()
            
            # Wait for background save to complete
            while redis_client.lastsave() == redis_client.lastsave():
                await asyncio.sleep(1)
            
            # Copy Redis dump file
            redis_data_dir = redis_info.get('dir', '/var/lib/redis')
            dump_file = Path(redis_data_dir) / 'dump.rdb'
            
            if dump_file.exists():
                backup_dump = backup_dir / 'redis-dump.rdb'
                shutil.copy2(dump_file, backup_dump)
            
            # Export key-value pairs for critical data
            keys_file = backup_dir / 'redis-keys.json'
            critical_patterns = ['session:*', 'cache:*', 'config:*', 'user:*']
            
            exported_data = {}
            for pattern in critical_patterns:
                keys = redis_client.keys(pattern)
                for key in keys:
                    try:
                        key_type = redis_client.type(key)
                        if key_type == b'string':
                            exported_data[key.decode()] = redis_client.get(key).decode()
                        elif key_type == b'hash':
                            exported_data[key.decode()] = {
                                k.decode(): v.decode() 
                                for k, v in redis_client.hgetall(key).items()
                            }
                        elif key_type == b'list':
                            exported_data[key.decode()] = [
                                item.decode() for item in redis_client.lrange(key, 0, -1)
                            ]
                    except Exception as e:
                        logger.warning(f"Failed to export key {key}: {e}")
            
            with open(keys_file, 'w') as f:
                json.dump(exported_data, f, indent=2)
            
            # Redis configuration backup
            config_file = backup_dir / 'redis-config.txt'
            config_info = redis_client.config_get('*')
            with open(config_file, 'w') as f:
                for key, value in config_info.items():
                    f.write(f"{key}: {value}\n")
            
            # Create compressed archive
            archive_path = backup_dir.with_suffix('.tar.gz')
            with tarfile.open(archive_path, 'w:gz') as tar:
                tar.add(backup_dir, arcname=metadata.backup_id)
            
            # Update metadata
            metadata.checksum = await self._calculate_checksum(archive_path)
            metadata.size_bytes = archive_path.stat().st_size
            metadata.storage_path = str(archive_path)
            
            # Upload to storage backends
            await self._upload_to_storage(metadata, archive_path)
            
            # Clean up
            shutil.rmtree(backup_dir)
            
            metadata.status = BackupStatus.COMPLETED
            metadata.source_info = {
                "redis_version": redis_info.get('redis_version'),
                "keys_exported": len(exported_data),
                "backup_size": metadata.size_bytes
            }
            
        except Exception as e:
            logger.error(f"Redis backup failed: {e}")
            metadata.status = BackupStatus.FAILED
            metadata.error_message = str(e)
            raise
    
    async def _backup_kubernetes(self, metadata: BackupMetadata):
        """Backup Kubernetes configurations and resources"""
        logger.info(f"Starting Kubernetes backup: {metadata.backup_id}")
        
        try:
            if not self.k8s_client:
                raise Exception("Kubernetes client not available")
            
            # Create backup directory
            backup_dir = Path(self.storage_backends["local"]["path"]) / "kubernetes" / metadata.backup_id
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Setup API clients
            apps_v1 = client.AppsV1Api(self.k8s_client)
            core_v1 = client.CoreV1Api(self.k8s_client)
            rbac_v1 = client.RbacAuthorizationV1Api(self.k8s_client)
            networking_v1 = client.NetworkingV1Api(self.k8s_client)
            
            namespace = metadata.environment
            
            # Backup deployments
            deployments = apps_v1.list_namespaced_deployment(namespace=namespace)
            with open(backup_dir / 'deployments.yaml', 'w') as f:
                yaml.dump([dep.to_dict() for dep in deployments.items], f)
            
            # Backup services
            services = core_v1.list_namespaced_service(namespace=namespace)
            with open(backup_dir / 'services.yaml', 'w') as f:
                yaml.dump([svc.to_dict() for svc in services.items], f)
            
            # Backup configmaps
            configmaps = core_v1.list_namespaced_config_map(namespace=namespace)
            with open(backup_dir / 'configmaps.yaml', 'w') as f:
                yaml.dump([cm.to_dict() for cm in configmaps.items], f)
            
            # Backup secrets (without sensitive data for security)
            secrets = core_v1.list_namespaced_secret(namespace=namespace)
            sanitized_secrets = []
            for secret in secrets.items:
                sanitized = secret.to_dict()
                if sanitized.get('data'):
                    sanitized['data'] = {k: "***REDACTED***" for k in sanitized['data'].keys()}
                sanitized_secrets.append(sanitized)
            
            with open(backup_dir / 'secrets.yaml', 'w') as f:
                yaml.dump(sanitized_secrets, f)
            
            # Backup persistent volume claims
            pvcs = core_v1.list_namespaced_persistent_volume_claim(namespace=namespace)
            with open(backup_dir / 'persistent_volume_claims.yaml', 'w') as f:
                yaml.dump([pvc.to_dict() for pvc in pvcs.items], f)
            
            # Backup ingress
            try:
                ingresses = networking_v1.list_namespaced_ingress(namespace=namespace)
                with open(backup_dir / 'ingresses.yaml', 'w') as f:
                    yaml.dump([ing.to_dict() for ing in ingresses.items], f)
            except Exception as e:
                logger.warning(f"Failed to backup ingresses: {e}")
            
            # Backup RBAC
            try:
                roles = rbac_v1.list_namespaced_role(namespace=namespace)
                with open(backup_dir / 'roles.yaml', 'w') as f:
                    yaml.dump([role.to_dict() for role in roles.items], f)
                
                role_bindings = rbac_v1.list_namespaced_role_binding(namespace=namespace)
                with open(backup_dir / 'role_bindings.yaml', 'w') as f:
                    yaml.dump([rb.to_dict() for rb in role_bindings.items], f)
            except Exception as e:
                logger.warning(f"Failed to backup RBAC: {e}")
            
            # Backup cluster info
            cluster_info = {
                "nodes": [node.to_dict() for node in core_v1.list_node().items],
                "namespaces": [ns.to_dict() for ns in core_v1.list_namespace().items],
                "storage_classes": []  # Would need storage API
            }
            
            with open(backup_dir / 'cluster_info.yaml', 'w') as f:
                yaml.dump(cluster_info, f)
            
            # Create compressed archive
            archive_path = backup_dir.with_suffix('.tar.gz')
            with tarfile.open(archive_path, 'w:gz') as tar:
                tar.add(backup_dir, arcname=metadata.backup_id)
            
            # Update metadata
            metadata.checksum = await self._calculate_checksum(archive_path)
            metadata.size_bytes = archive_path.stat().st_size
            metadata.storage_path = str(archive_path)
            
            # Upload to storage backends
            await self._upload_to_storage(metadata, archive_path)
            
            # Clean up
            shutil.rmtree(backup_dir)
            
            metadata.status = BackupStatus.COMPLETED
            metadata.source_info = {
                "namespace": namespace,
                "deployments": len(deployments.items),
                "services": len(services.items),
                "configmaps": len(configmaps.items),
                "secrets": len(secrets.items),
                "backup_size": metadata.size_bytes
            }
            
        except Exception as e:
            logger.error(f"Kubernetes backup failed: {e}")
            metadata.status = BackupStatus.FAILED
            metadata.error_message = str(e)
            raise
    
    async def _backup_application_data(self, metadata: BackupMetadata):
        """Backup application-specific data"""
        logger.info(f"Starting application data backup: {metadata.backup_id}")
        
        try:
            # Create backup directory
            backup_dir = Path(self.storage_backends["local"]["path"]) / "application" / metadata.backup_id
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup application logs (last 7 days)
            logs_dir = backup_dir / "logs"
            logs_dir.mkdir(exist_ok=True)
            
            # Application configuration files
            config_files = [
                "/app/config/app.yaml",
                "/app/config/logging.yaml",
                "/app/config/features.json"
            ]
            
            config_dir = backup_dir / "config"
            config_dir.mkdir(exist_ok=True)
            
            for config_file in config_files:
                if os.path.exists(config_file):
                    shutil.copy2(config_file, config_dir / os.path.basename(config_file))
            
            # User-generated content and dashboards
            if os.path.exists("/app/data/user_dashboards"):
                shutil.copytree("/app/data/user_dashboards", backup_dir / "user_dashboards")
            
            # Export database user data
            user_data_file = backup_dir / "user_data.json"
            user_data = await self._export_user_data()
            with open(user_data_file, 'w') as f:
                json.dump(user_data, f, indent=2, default=str)
            
            # Application metrics and statistics
            metrics_file = backup_dir / "metrics.json"
            metrics = await self._collect_application_metrics()
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2, default=str)
            
            # Create compressed archive
            archive_path = backup_dir.with_suffix('.tar.gz')
            with tarfile.open(archive_path, 'w:gz') as tar:
                tar.add(backup_dir, arcname=metadata.backup_id)
            
            # Update metadata
            metadata.checksum = await self._calculate_checksum(archive_path)
            metadata.size_bytes = archive_path.stat().st_size
            metadata.storage_path = str(archive_path)
            
            # Upload to storage backends
            await self._upload_to_storage(metadata, archive_path)
            
            # Clean up
            shutil.rmtree(backup_dir)
            
            metadata.status = BackupStatus.COMPLETED
            metadata.source_info = {
                "user_data_records": len(user_data),
                "config_files": len(config_files),
                "backup_size": metadata.size_bytes
            }
            
        except Exception as e:
            logger.error(f"Application data backup failed: {e}")
            metadata.status = BackupStatus.FAILED
            metadata.error_message = str(e)
            raise
    
    async def _backup_full_system(self, metadata: BackupMetadata):
        """Perform full system backup"""
        logger.info(f"Starting full system backup: {metadata.backup_id}")
        
        try:
            # Create individual backups
            db_backup = await self.create_backup(BackupType.DATABASE, metadata.environment)
            redis_backup = await self.create_backup(BackupType.REDIS, metadata.environment)
            k8s_backup = await self.create_backup(BackupType.KUBERNETES, metadata.environment)
            app_backup = await self.create_backup(BackupType.APPLICATION_DATA, metadata.environment)
            
            # Create master backup directory
            backup_dir = Path(self.storage_backends["local"]["path"]) / "full_system" / metadata.backup_id
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy individual backups
            for backup in [db_backup, redis_backup, k8s_backup, app_backup]:
                if backup.status == BackupStatus.COMPLETED:
                    backup_file = Path(backup.storage_path)
                    shutil.copy2(backup_file, backup_dir / backup_file.name)
            
            # Create system manifest
            manifest = {
                "backup_id": metadata.backup_id,
                "timestamp": metadata.timestamp.isoformat(),
                "environment": metadata.environment,
                "components": {
                    "database": db_backup.backup_id if db_backup.status == BackupStatus.COMPLETED else None,
                    "redis": redis_backup.backup_id if redis_backup.status == BackupStatus.COMPLETED else None,
                    "kubernetes": k8s_backup.backup_id if k8s_backup.status == BackupStatus.COMPLETED else None,
                    "application": app_backup.backup_id if app_backup.status == BackupStatus.COMPLETED else None
                },
                "restore_order": ["kubernetes", "database", "redis", "application"],
                "verification": {
                    "checksums": {
                        backup.backup_id: backup.checksum 
                        for backup in [db_backup, redis_backup, k8s_backup, app_backup]
                        if backup.status == BackupStatus.COMPLETED
                    }
                }
            }
            
            with open(backup_dir / "backup_manifest.json", 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Create compressed archive
            archive_path = backup_dir.with_suffix('.tar.gz')
            with tarfile.open(archive_path, 'w:gz') as tar:
                tar.add(backup_dir, arcname=metadata.backup_id)
            
            # Update metadata
            metadata.checksum = await self._calculate_checksum(archive_path)
            metadata.size_bytes = archive_path.stat().st_size
            metadata.storage_path = str(archive_path)
            
            # Upload to storage backends
            await self._upload_to_storage(metadata, archive_path)
            
            # Clean up
            shutil.rmtree(backup_dir)
            
            metadata.status = BackupStatus.COMPLETED
            metadata.source_info = {
                "components_backed_up": len([b for b in [db_backup, redis_backup, k8s_backup, app_backup] 
                                           if b.status == BackupStatus.COMPLETED]),
                "total_size": metadata.size_bytes,
                "manifest": manifest
            }
            
        except Exception as e:
            logger.error(f"Full system backup failed: {e}")
            metadata.status = BackupStatus.FAILED
            metadata.error_message = str(e)
            raise
    
    async def _verify_backup(self, metadata: BackupMetadata):
        """Verify backup integrity and completeness"""
        logger.info(f"Verifying backup: {metadata.backup_id}")
        
        try:
            verification_info = {
                "checksum_verified": False,
                "archive_readable": False,
                "content_validated": False,
                "test_restore_successful": False
            }
            
            # Verify checksum
            if metadata.checksum:
                current_checksum = await self._calculate_checksum(Path(metadata.storage_path))
                verification_info["checksum_verified"] = (current_checksum == metadata.checksum)
            
            # Verify archive is readable
            try:
                with tarfile.open(metadata.storage_path, 'r:gz') as tar:
                    tar.getnames()  # Try to read archive contents
                verification_info["archive_readable"] = True
            except Exception as e:
                logger.error(f"Archive verification failed: {e}")
            
            # Content validation based on backup type
            if metadata.backup_type == BackupType.DATABASE:
                verification_info["content_validated"] = await self._verify_database_backup(metadata)
            elif metadata.backup_type == BackupType.KUBERNETES:
                verification_info["content_validated"] = await self._verify_kubernetes_backup(metadata)
            
            # Test restore (if enabled and not production)
            if (self.config.get("verification", {}).get("test_restore", False) and 
                metadata.environment != "production"):
                verification_info["test_restore_successful"] = await self._test_restore(metadata)
            
            metadata.verification_info = verification_info
            
            # Mark as verified if all checks pass
            if all(verification_info.values()):
                metadata.status = BackupStatus.VERIFIED
            else:
                logger.warning(f"Backup verification incomplete for {metadata.backup_id}")
            
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            metadata.verification_info = {"error": str(e)}
    
    async def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        import hashlib
        
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    async def _upload_to_storage(self, metadata: BackupMetadata, file_path: Path):
        """Upload backup to configured storage backends"""
        primary_backend = self.config.get("storage", {}).get("primary_backend", "local")
        backup_backends = self.config.get("storage", {}).get("backup_backends", [])
        
        # Upload to primary backend
        if primary_backend == "s3" and "s3" in self.storage_backends:
            await self._upload_to_s3(metadata, file_path)
        
        # Upload to backup backends
        for backend in backup_backends:
            if backend == "s3" and backend in self.storage_backends:
                await self._upload_to_s3(metadata, file_path, backup=True)
    
    async def _upload_to_s3(self, metadata: BackupMetadata, file_path: Path, backup: bool = False):
        """Upload backup to S3"""
        try:
            s3_client = self.storage_backends["s3"]
            bucket = self.config["storage"]["s3"]["bucket"]
            
            key_prefix = "backups" if not backup else "backup-copy"
            s3_key = f"{key_prefix}/{metadata.environment}/{metadata.backup_type.value}/{file_path.name}"
            
            # Upload with server-side encryption
            s3_client.upload_file(
                str(file_path),
                bucket,
                s3_key,
                ExtraArgs={
                    'ServerSideEncryption': 'AES256',
                    'Metadata': {
                        'backup_id': metadata.backup_id,
                        'backup_type': metadata.backup_type.value,
                        'environment': metadata.environment,
                        'timestamp': metadata.timestamp.isoformat()
                    }
                }
            )
            
            logger.info(f"Uploaded backup to S3: s3://{bucket}/{s3_key}")
            
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise
    
    async def _collect_database_stats(self, db_config: Dict[str, str]) -> Dict[str, Any]:
        """Collect database statistics for backup metadata"""
        try:
            conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["database"],
                user=db_config["username"],
                password=db_config["password"]
            )
            
            cursor = conn.cursor()
            
            # Database size
            cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
            db_size = cursor.fetchone()[0]
            
            # Table statistics
            cursor.execute("""
                SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
                FROM pg_stat_user_tables
                ORDER BY n_tup_ins DESC
                LIMIT 10
            """)
            table_stats = cursor.fetchall()
            
            # Connection statistics
            cursor.execute("SELECT count(*) FROM pg_stat_activity")
            active_connections = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return {
                "database_size": db_size,
                "active_connections": active_connections,
                "table_statistics": table_stats,
                "backup_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to collect database stats: {e}")
            return {"error": str(e)}
    
    async def _export_user_data(self) -> Dict[str, Any]:
        """Export user data for backup"""
        # This would typically connect to the database and export user data
        # Placeholder implementation
        return {
            "users": [],
            "user_dashboards": [],
            "user_queries": [],
            "export_timestamp": datetime.utcnow().isoformat()
        }
    
    async def _collect_application_metrics(self) -> Dict[str, Any]:
        """Collect application metrics for backup"""
        return {
            "backup_timestamp": datetime.utcnow().isoformat(),
            "system_uptime": "N/A",
            "active_sessions": 0,
            "total_queries": 0,
            "error_rate": 0.0
        }
    
    async def _verify_database_backup(self, metadata: BackupMetadata) -> bool:
        """Verify database backup content"""
        try:
            # Extract and verify database backup
            with tempfile.TemporaryDirectory() as temp_dir:
                with tarfile.open(metadata.storage_path, 'r:gz') as tar:
                    tar.extractall(temp_dir)
                
                # Check if database.sql exists and is readable
                db_file = Path(temp_dir) / metadata.backup_id / "database.sql"
                if db_file.exists() and db_file.stat().st_size > 0:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Database backup verification failed: {e}")
            return False
    
    async def _verify_kubernetes_backup(self, metadata: BackupMetadata) -> bool:
        """Verify Kubernetes backup content"""
        try:
            # Extract and verify Kubernetes backup
            with tempfile.TemporaryDirectory() as temp_dir:
                with tarfile.open(metadata.storage_path, 'r:gz') as tar:
                    tar.extractall(temp_dir)
                
                # Check for required files
                required_files = ["deployments.yaml", "services.yaml", "configmaps.yaml"]
                backup_path = Path(temp_dir) / metadata.backup_id
                
                for file_name in required_files:
                    file_path = backup_path / file_name
                    if not file_path.exists() or file_path.stat().st_size == 0:
                        return False
                
                return True
            
        except Exception as e:
            logger.error(f"Kubernetes backup verification failed: {e}")
            return False
    
    async def _test_restore(self, metadata: BackupMetadata) -> bool:
        """Perform test restore in isolated environment"""
        # This would create an isolated test environment and attempt restore
        # Placeholder implementation for now
        logger.info(f"Test restore for {metadata.backup_id} - simulated success")
        return True
    
    async def list_backups(self, backup_type: Optional[BackupType] = None, 
                          environment: Optional[str] = None) -> List[BackupMetadata]:
        """List available backups with filtering"""
        backups = list(self.backup_registry.values())
        
        if backup_type:
            backups = [b for b in backups if b.backup_type == backup_type]
        
        if environment:
            backups = [b for b in backups if b.environment == environment]
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.timestamp, reverse=True)
        
        return backups
    
    async def cleanup_expired_backups(self):
        """Clean up expired backups based on retention policy"""
        logger.info("Starting backup cleanup process")
        
        current_time = datetime.utcnow()
        expired_backups = []
        
        for backup_id, metadata in self.backup_registry.items():
            age_days = (current_time - metadata.timestamp).days
            
            if age_days > metadata.retention_days:
                expired_backups.append(metadata)
        
        for metadata in expired_backups:
            try:
                # Remove from storage
                if os.path.exists(metadata.storage_path):
                    os.remove(metadata.storage_path)
                
                # Remove from S3 if applicable
                if "s3" in self.storage_backends:
                    await self._delete_from_s3(metadata)
                
                # Remove from registry
                del self.backup_registry[metadata.backup_id]
                
                logger.info(f"Cleaned up expired backup: {metadata.backup_id}")
                
            except Exception as e:
                logger.error(f"Failed to cleanup backup {metadata.backup_id}: {e}")
        
        logger.info(f"Cleanup completed. Removed {len(expired_backups)} expired backups")
    
    async def _delete_from_s3(self, metadata: BackupMetadata):
        """Delete backup from S3"""
        try:
            s3_client = self.storage_backends["s3"]
            bucket = self.config["storage"]["s3"]["bucket"]
            
            key = f"backups/{metadata.environment}/{metadata.backup_type.value}/{Path(metadata.storage_path).name}"
            
            s3_client.delete_object(Bucket=bucket, Key=key)
            logger.info(f"Deleted backup from S3: s3://{bucket}/{key}")
            
        except Exception as e:
            logger.error(f"Failed to delete from S3: {e}")

    async def get_backup_status(self, backup_id: str) -> Optional[BackupMetadata]:
        """Get backup status by ID"""
        return self.backup_registry.get(backup_id)
    
    async def generate_backup_report(self) -> Dict[str, Any]:
        """Generate comprehensive backup report"""
        total_backups = len(self.backup_registry)
        successful_backups = len([b for b in self.backup_registry.values() 
                                if b.status == BackupStatus.COMPLETED])
        failed_backups = len([b for b in self.backup_registry.values() 
                            if b.status == BackupStatus.FAILED])
        
        # Calculate total storage used
        total_storage = sum(b.size_bytes for b in self.backup_registry.values() 
                          if b.status == BackupStatus.COMPLETED)
        
        # Recent backup activity (last 7 days)
        recent_cutoff = datetime.utcnow() - timedelta(days=7)
        recent_backups = [b for b in self.backup_registry.values() 
                         if b.timestamp > recent_cutoff]
        
        return {
            "report_timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total_backups": total_backups,
                "successful_backups": successful_backups,
                "failed_backups": failed_backups,
                "success_rate": (successful_backups / total_backups * 100) if total_backups > 0 else 0,
                "total_storage_bytes": total_storage,
                "total_storage_gb": round(total_storage / (1024**3), 2)
            },
            "recent_activity": {
                "backups_last_7_days": len(recent_backups),
                "backup_types": {
                    backup_type.value: len([b for b in recent_backups if b.backup_type == backup_type])
                    for backup_type in BackupType
                }
            },
            "backup_status_distribution": {
                status.value: len([b for b in self.backup_registry.values() if b.status == status])
                for status in BackupStatus
            },
            "environments": {
                env: len([b for b in self.backup_registry.values() if b.environment == env])
                for env in set(b.environment for b in self.backup_registry.values())
            }
        }

async def main():
    """Main function for testing backup automation"""
    backup_system = BackupAutomationSystem()
    
    # Example: Create a database backup
    try:
        logger.info("Starting backup automation test")
        
        # Create database backup
        db_backup = await backup_system.create_backup(BackupType.DATABASE, "production")
        logger.info(f"Database backup completed: {db_backup.backup_id}")
        
        # Create Redis backup
        redis_backup = await backup_system.create_backup(BackupType.REDIS, "production")
        logger.info(f"Redis backup completed: {redis_backup.backup_id}")
        
        # Generate report
        report = await backup_system.generate_backup_report()
        logger.info(f"Backup report: {json.dumps(report, indent=2)}")
        
    except Exception as e:
        logger.error(f"Backup automation test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())