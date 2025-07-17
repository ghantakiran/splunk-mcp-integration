"""
Pydantic models for Microsoft Teams bot data structures.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class TeamsUser(BaseModel):
    """Microsoft Teams user model."""
    id: str
    name: Optional[str] = None
    email: Optional[str] = None
    aad_object_id: Optional[str] = None
    tenant_id: str
    conversation_type: str = "personal"  # personal, channel, groupChat
    is_admin: bool = False
    is_bot: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True

class TeamsChannel(BaseModel):
    """Microsoft Teams channel model."""
    id: str
    name: Optional[str] = None
    team_id: Optional[str] = None
    tenant_id: str
    conversation_type: str  # channel, groupChat, personal
    is_group: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True

class TeamsMessage(BaseModel):
    """Microsoft Teams message model."""
    id: str
    conversation_id: str
    user_id: str
    text: str
    message_type: str = "message"
    activity_id: Optional[str] = None
    channel_id: Optional[str] = None
    thread_id: Optional[str] = None
    reply_to_id: Optional[str] = None
    mentions: List[Dict[str, Any]] = Field(default_factory=list)
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True

class TeamsActivity(BaseModel):
    """Microsoft Teams activity model."""
    id: str
    activity_type: str  # message, invoke, memberAdded, etc.
    conversation_id: str
    user_id: Optional[str] = None
    channel_id: Optional[str] = None
    service_url: str
    tenant_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    raw_activity: Dict[str, Any] = Field(default_factory=dict)
    processed: bool = False
    
    class Config:
        from_attributes = True

class TeamsSession(BaseModel):
    """Teams conversation session model."""
    id: str
    user_id: str
    conversation_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    history: List[Dict[str, Any]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    
    class Config:
        from_attributes = True

class QueryResult(BaseModel):
    """Teams query result model."""
    id: str
    session_id: str
    user_id: str
    query: str
    spl_query: Optional[str] = None
    results: List[Dict[str, Any]] = Field(default_factory=list)
    execution_time: Optional[float] = None
    error: Optional[str] = None
    confidence_score: Optional[float] = None
    visualization_type: Optional[str] = None
    visualizations: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True

class TeamsAlertDefinition(BaseModel):
    """Teams alert definition model."""
    id: str
    name: str
    description: Optional[str] = None
    query: str
    spl_query: Optional[str] = None
    condition: str
    threshold: Optional[float] = None
    time_window: int = 300  # 5 minutes default
    notification_channels: List[str] = Field(default_factory=list)
    teams_webhook_url: Optional[str] = None
    enabled: bool = True
    created_by: str
    conversation_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True

class TeamsMetrics(BaseModel):
    """Teams bot metrics model."""
    user_id: str
    conversation_id: str
    action_type: str  # query, command, interaction, invoke
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_type: Optional[str] = None
    response_time: Optional[float] = None
    query_length: Optional[int] = None
    results_count: Optional[int] = None
    activity_type: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserContext(BaseModel):
    """User context for Splunk access via Teams."""
    user_id: str
    roles: List[str] = Field(default_factory=list)
    permissions: Dict[str, Any] = Field(default_factory=dict)
    accessible_indexes: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    access_level: str = "standard"  # standard, admin, readonly
    teams_tenant_id: Optional[str] = None
    aad_object_id: Optional[str] = None
    
    class Config:
        from_attributes = True

class TeamsInvokeRequest(BaseModel):
    """Teams invoke request model."""
    name: str  # invoke name (e.g., adaptiveCard/action, task/fetch)
    value: Dict[str, Any] = Field(default_factory=dict)
    user_id: str
    conversation_id: str
    activity_id: str
    
    class Config:
        from_attributes = True

class TeamsInvokeResponse(BaseModel):
    """Teams invoke response model."""
    status: int = 200
    body: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class TeamsTaskInfo(BaseModel):
    """Teams task module info model."""
    title: str
    height: Optional[int] = None
    width: Optional[int] = None
    url: Optional[str] = None
    card: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True

class TeamsComposeExtensionQuery(BaseModel):
    """Teams messaging extension query model."""
    command_id: Optional[str] = None
    parameters: List[Dict[str, str]] = Field(default_factory=list)
    query_options: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        from_attributes = True

class TeamsComposeExtensionResult(BaseModel):
    """Teams messaging extension result model."""
    attachment_layout: str = "list"  # list, grid
    type: str = "result"
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    
    class Config:
        from_attributes = True

class TeamsBotInstallation(BaseModel):
    """Teams bot installation model."""
    id: str
    tenant_id: str
    team_id: Optional[str] = None
    conversation_id: str
    installer_user_id: str
    installation_type: str  # personal, team, groupChat
    scope: str  # personal, team, groupChat
    installed_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    
    class Config:
        from_attributes = True

class TeamsConversationReference(BaseModel):
    """Teams conversation reference for proactive messaging."""
    activity_id: Optional[str] = None
    user: Dict[str, Any]
    bot: Dict[str, Any]
    conversation: Dict[str, Any]
    channel_id: str
    service_url: str
    tenant_id: Optional[str] = None
    
    class Config:
        from_attributes = True