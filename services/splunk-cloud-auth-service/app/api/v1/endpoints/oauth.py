"""
OAuth 2.0 endpoints for Splunk Cloud Authentication Service
"""

from fastapi import APIRouter, Depends, HTTPException, Form, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import logging
from urllib.parse import urlencode

from app.core.database import get_db
from app.services.oauth_service import OAuthService
from app.models.auth_models import (
    OAuthClientCreate,
    OAuthClientResponse,
    TokenResponse,
    TokenIntrospectionResponse
)

router = APIRouter()
logger = logging.getLogger(__name__)

oauth_service = OAuthService()


@router.post("/clients", response_model=OAuthClientResponse)
async def create_oauth_client(
    client_data: OAuthClientCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new OAuth 2.0 client"""
    
    try:
        client = await oauth_service.create_client(
            db=db,
            client_name=client_data.client_name,
            redirect_uris=client_data.redirect_uris,
            allowed_scopes=client_data.allowed_scopes,
            allowed_grant_types=client_data.allowed_grant_types,
            tenant_id=client_data.tenant_id,
            require_pkce=client_data.require_pkce,
            is_confidential=client_data.is_confidential
        )
        
        # Return response with client secret (only time it's available)
        response = OAuthClientResponse.from_orm(client)
        # Add client secret to response for initial setup
        response.client_secret = client.client_secret
        
        return response
        
    except Exception as e:
        logger.error(f"Error creating OAuth client: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "client_creation_failed",
                "message": "Failed to create OAuth client"
            }
        )


@router.get("/authorize")
async def authorize(
    response_type: str = Query(...),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query(default="openid profile email"),
    state: Optional[str] = Query(None),
    code_challenge: Optional[str] = Query(None),
    code_challenge_method: str = Query(default="S256"),
    db: AsyncSession = Depends(get_db)
):
    """OAuth 2.0 authorization endpoint"""
    
    # Validate response type
    if response_type != "code":
        error_params = {
            "error": "unsupported_response_type",
            "error_description": "Only authorization code flow is supported",
            "state": state
        }
        return RedirectResponse(
            url=f"{redirect_uri}?{urlencode(error_params)}",
            status_code=302
        )
    
    # Validate client
    client = await oauth_service.validate_client(db, client_id)
    if not client:
        error_params = {
            "error": "invalid_client",
            "error_description": "Invalid client_id",
            "state": state
        }
        return RedirectResponse(
            url=f"{redirect_uri}?{urlencode(error_params)}",
            status_code=302
        )
    
    # Validate redirect URI
    if redirect_uri not in client.redirect_uris:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_redirect_uri",
                "message": "Redirect URI not registered for this client"
            }
        )
    
    # PKCE validation for public clients
    if client.require_pkce and not code_challenge:
        error_params = {
            "error": "invalid_request",
            "error_description": "PKCE code challenge required",
            "state": state
        }
        return RedirectResponse(
            url=f"{redirect_uri}?{urlencode(error_params)}",
            status_code=302
        )
    
    # For demo purposes, we'll redirect to a login page
    # In a real implementation, this would show a login form
    # and then call create_authorization_code after successful auth
    
    login_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method
    }
    
    # Redirect to login page (this would be your login UI)
    login_url = f"/login?{urlencode(login_params)}"
    return RedirectResponse(url=login_url, status_code=302)


@router.post("/token", response_model=TokenResponse)
async def token_endpoint(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """OAuth 2.0 token endpoint"""
    
    try:
        if grant_type == "authorization_code":
            if not all([code, redirect_uri]):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_request",
                        "error_description": "Missing required parameters for authorization code grant"
                    }
                )
            
            token_response = await oauth_service.exchange_code_for_tokens(
                db=db,
                code=code,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                code_verifier=code_verifier
            )
            
            if not token_response:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_grant",
                        "error_description": "Invalid authorization code"
                    }
                )
            
            return token_response
        
        elif grant_type == "refresh_token":
            if not refresh_token:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_request",
                        "error_description": "Missing refresh_token parameter"
                    }
                )
            
            token_response = await oauth_service.refresh_access_token(
                db=db,
                refresh_token=refresh_token,
                client_id=client_id,
                client_secret=client_secret
            )
            
            if not token_response:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "invalid_grant",
                        "error_description": "Invalid refresh token"
                    }
                )
            
            return token_response
        
        elif grant_type == "client_credentials":
            # For service-to-service authentication
            # This would typically be used for machine-to-machine communication
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "unsupported_grant_type",
                    "error_description": "Client credentials grant not yet implemented"
                }
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "unsupported_grant_type",
                    "error_description": f"Grant type '{grant_type}' is not supported"
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in token endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "server_error",
                "error_description": "Internal server error"
            }
        )


@router.post("/introspect", response_model=TokenIntrospectionResponse)
async def token_introspection(
    token: str = Form(...),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """OAuth 2.0 token introspection endpoint (RFC 7662)"""
    
    try:
        introspection_result = await oauth_service.introspect_token(
            db=db,
            token=token,
            client_id=client_id,
            client_secret=client_secret
        )
        
        return introspection_result
    
    except Exception as e:
        logger.error(f"Error in token introspection: {e}")
        # Return inactive token response for any error
        return TokenIntrospectionResponse(active=False)


@router.post("/revoke")
async def token_revocation(
    token: str = Form(...),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """OAuth 2.0 token revocation endpoint (RFC 7009)"""
    
    try:
        success = await oauth_service.revoke_token(
            db=db,
            token=token,
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Always return 200 OK per RFC 7009, regardless of success
        return {"revoked": success}
    
    except Exception as e:
        logger.error(f"Error in token revocation: {e}")
        # Return 200 OK even on error per RFC 7009
        return {"revoked": False}


@router.get("/userinfo")
async def userinfo_endpoint(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """OAuth 2.0 UserInfo endpoint (OpenID Connect)"""
    
    # Extract access token from Authorization header
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_token",
                "error_description": "Missing or invalid authorization header"
            }
        )
    
    access_token = authorization[7:]  # Remove "Bearer " prefix
    
    try:
        # For now, return a simple introspection response
        # In a full implementation, this would return user profile information
        introspection = await oauth_service.introspect_token(
            db=db,
            token=access_token,
            client_id="introspection",  # Special client for introspection
            client_secret=None
        )
        
        if not introspection.active:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_token",
                    "error_description": "Token is not active"
                }
            )
        
        # Return basic user info
        return {
            "sub": introspection.sub,
            "preferred_username": introspection.username,
            "scope": introspection.scope,
            "client_id": introspection.client_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in userinfo endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "server_error",
                "error_description": "Internal server error"
            }
        )


@router.get("/cloud/authorize/{instance_id}")
async def cloud_instance_authorize(
    instance_id: str,
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query(default="openid profile email"),
    state: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Initiate OAuth flow with specific Splunk Cloud instance"""
    
    # This endpoint would be used to initiate OAuth with a specific
    # Splunk Cloud instance for a tenant
    
    # In a real implementation, this would:
    # 1. Look up the cloud instance configuration for the tenant
    # 2. Validate the client_id and redirect_uri
    # 3. Generate the appropriate OAuth URL for the Splunk Cloud instance
    # 4. Redirect the user to the Splunk Cloud OAuth endpoint
    
    # For now, return a placeholder response
    return {
        "message": f"Cloud instance OAuth for {instance_id}",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state
    }