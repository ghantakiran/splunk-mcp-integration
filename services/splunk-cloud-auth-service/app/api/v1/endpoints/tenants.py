"""
Multi-tenant endpoints for Splunk Cloud Authentication Service
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
import logging
import uuid

from app.core.database import get_db
from app.models.tenant_models import (
    Tenant,
    TenantCloudInstance,
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantCloudInstanceCreate,
    TenantCloudInstanceResponse,
    TenantStatus
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new tenant"""
    
    try:
        # Check if slug already exists
        result = await db.execute(
            select(Tenant).where(Tenant.slug == tenant_data.slug)
        )
        existing_tenant = result.scalar_one_or_none()
        
        if existing_tenant:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "slug_already_exists",
                    "message": f"Tenant with slug '{tenant_data.slug}' already exists"
                }
            )
        
        # Create new tenant
        tenant = Tenant(
            id=str(uuid.uuid4()),
            name=tenant_data.name,
            slug=tenant_data.slug,
            domain=tenant_data.domain,
            admin_email=tenant_data.admin_email,
            contact_name=tenant_data.contact_name,
            contact_phone=tenant_data.contact_phone,
            plan=tenant_data.plan,
            address_line1=tenant_data.address_line1,
            address_line2=tenant_data.address_line2,
            city=tenant_data.city,
            state=tenant_data.state,
            postal_code=tenant_data.postal_code,
            country=tenant_data.country,
            status=TenantStatus.PENDING
        )
        
        # Set quotas based on plan or custom values
        quota_map = {
            "free": {"users": 10, "api_requests": 1000, "storage": 1, "instances": 1},
            "basic": {"users": 100, "api_requests": 10000, "storage": 10, "instances": 5},
            "premium": {"users": 500, "api_requests": 50000, "storage": 50, "instances": 15},
            "enterprise": {"users": 2000, "api_requests": 200000, "storage": 200, "instances": 50},
            "custom": {"users": 100, "api_requests": 10000, "storage": 10, "instances": 5}
        }
        
        plan_quotas = quota_map.get(tenant_data.plan.value, quota_map["basic"])
        
        tenant.quota_users = tenant_data.quota_users or plan_quotas["users"]
        tenant.quota_api_requests_per_hour = tenant_data.quota_api_requests_per_hour or plan_quotas["api_requests"]
        tenant.quota_storage_gb = tenant_data.quota_storage_gb or plan_quotas["storage"]
        tenant.quota_cloud_instances = tenant_data.quota_cloud_instances or plan_quotas["instances"]
        
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)
        
        logger.info(f"Created tenant: {tenant.slug} ({tenant.id})")
        
        return TenantResponse.from_orm(tenant)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tenant: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "tenant_creation_failed",
                "message": "Failed to create tenant"
            }
        )


@router.get("/", response_model=List[TenantResponse])
async def list_tenants(
    status: Optional[TenantStatus] = Query(None),
    plan: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List tenants with optional filtering"""
    
    try:
        query = select(Tenant).where(Tenant.is_active == True)
        
        if status:
            query = query.where(Tenant.status == status)
        
        if plan:
            query = query.where(Tenant.plan == plan)
        
        query = query.offset(offset).limit(limit)
        
        result = await db.execute(query)
        tenants = result.scalars().all()
        
        return [TenantResponse.from_orm(tenant) for tenant in tenants]
        
    except Exception as e:
        logger.error(f"Error listing tenants: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "tenant_list_failed",
                "message": "Failed to retrieve tenants"
            }
        )


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get tenant by ID"""
    
    try:
        result = await db.execute(
            select(Tenant).where(
                and_(
                    Tenant.id == tenant_id,
                    Tenant.is_active == True
                )
            )
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "tenant_not_found",
                    "message": f"Tenant with ID '{tenant_id}' not found"
                }
            )
        
        return TenantResponse.from_orm(tenant)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "tenant_get_failed",
                "message": "Failed to retrieve tenant"
            }
        )


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    tenant_update: TenantUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update tenant"""
    
    try:
        result = await db.execute(
            select(Tenant).where(
                and_(
                    Tenant.id == tenant_id,
                    Tenant.is_active == True
                )
            )
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "tenant_not_found",
                    "message": f"Tenant with ID '{tenant_id}' not found"
                }
            )
        
        # Update fields
        update_data = tenant_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)
        
        await db.commit()
        await db.refresh(tenant)
        
        logger.info(f"Updated tenant: {tenant.slug} ({tenant.id})")
        
        return TenantResponse.from_orm(tenant)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tenant {tenant_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "tenant_update_failed",
                "message": "Failed to update tenant"
            }
        )


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete tenant (soft delete)"""
    
    try:
        result = await db.execute(
            select(Tenant).where(
                and_(
                    Tenant.id == tenant_id,
                    Tenant.is_active == True
                )
            )
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "tenant_not_found",
                    "message": f"Tenant with ID '{tenant_id}' not found"
                }
            )
        
        # Soft delete
        tenant.is_active = False
        tenant.status = TenantStatus.DEACTIVATED
        
        await db.commit()
        
        logger.info(f"Deleted tenant: {tenant.slug} ({tenant.id})")
        
        return {"message": "Tenant deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tenant {tenant_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "tenant_delete_failed",
                "message": "Failed to delete tenant"
            }
        )


@router.post("/{tenant_id}/cloud-instances", response_model=TenantCloudInstanceResponse)
async def create_cloud_instance(
    tenant_id: str,
    instance_data: TenantCloudInstanceCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create cloud instance for tenant"""
    
    try:
        # Verify tenant exists and is active
        tenant_result = await db.execute(
            select(Tenant).where(
                and_(
                    Tenant.id == tenant_id,
                    Tenant.is_active == True,
                    Tenant.status == TenantStatus.ACTIVE
                )
            )
        )
        tenant = tenant_result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "tenant_not_found_or_inactive",
                    "message": f"Active tenant with ID '{tenant_id}' not found"
                }
            )
        
        # Check cloud instance quota
        instance_count_result = await db.execute(
            select(TenantCloudInstance).where(
                and_(
                    TenantCloudInstance.tenant_id == tenant_id,
                    TenantCloudInstance.is_active == True
                )
            )
        )
        current_instances = len(instance_count_result.scalars().all())
        
        if current_instances >= tenant.quota_cloud_instances:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "quota_exceeded",
                    "message": f"Cloud instance quota exceeded. Current: {current_instances}, Limit: {tenant.quota_cloud_instances}"
                }
            )
        
        # Create cloud instance
        cloud_instance = TenantCloudInstance(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            instance_name=instance_data.instance_name,
            instance_url=instance_data.instance_url,
            instance_region=instance_data.instance_region,
            instance_stack=instance_data.instance_stack,
            auth_method=instance_data.auth_method,
            client_id=instance_data.client_id,
            configuration=instance_data.configuration
        )
        
        # Encrypt client secret if provided
        if instance_data.client_secret:
            # In a real implementation, this would use proper encryption
            cloud_instance.client_secret_encrypted = f"encrypted_{instance_data.client_secret}"
        
        db.add(cloud_instance)
        
        # Update tenant's current instance count
        tenant.current_cloud_instances = current_instances + 1
        
        await db.commit()
        await db.refresh(cloud_instance)
        
        logger.info(f"Created cloud instance: {instance_data.instance_name} for tenant: {tenant_id}")
        
        return TenantCloudInstanceResponse.from_orm(cloud_instance)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating cloud instance for tenant {tenant_id}: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error": "cloud_instance_creation_failed",
                "message": "Failed to create cloud instance"
            }
        )


@router.get("/{tenant_id}/cloud-instances", response_model=List[TenantCloudInstanceResponse])
async def list_cloud_instances(
    tenant_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List cloud instances for tenant"""
    
    try:
        result = await db.execute(
            select(TenantCloudInstance).where(
                and_(
                    TenantCloudInstance.tenant_id == tenant_id,
                    TenantCloudInstance.is_active == True
                )
            )
        )
        instances = result.scalars().all()
        
        return [TenantCloudInstanceResponse.from_orm(instance) for instance in instances]
        
    except Exception as e:
        logger.error(f"Error listing cloud instances for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "cloud_instance_list_failed",
                "message": "Failed to retrieve cloud instances"
            }
        )


@router.get("/by-slug/{slug}", response_model=TenantResponse)
async def get_tenant_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get tenant by slug"""
    
    try:
        result = await db.execute(
            select(Tenant).where(
                and_(
                    Tenant.slug == slug,
                    Tenant.is_active == True
                )
            )
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "tenant_not_found",
                    "message": f"Tenant with slug '{slug}' not found"
                }
            )
        
        return TenantResponse.from_orm(tenant)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tenant by slug {slug}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "tenant_get_failed",
                "message": "Failed to retrieve tenant"
            }
        )