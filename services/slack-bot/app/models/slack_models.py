"""
Pydantic models for Slack bot data structures.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class SlackUser(BaseModel):
    """Slack user model."""
    id: str
    name: Optional[str] = None
    real_name: Optional[str] = None
    email: Optional[str] = None
    team_id: str
    is_admin: bool = False
    is_owner: bool = False
    is_bot: bool = False
    timezone: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True

class SlackChannel(BaseModel):
    """Slack channel model."""
    id: str
    name: Optional[str] = None
    is_channel: bool = True
    is_group: bool = False
    is_im: bool = False
    is_mpim: bool = False
    is_private: bool = False
    is_archived: bool = False
    team_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True

class SlackMessage(BaseModel):
    """Slack message model."""
    ts: str  # Slack timestamp
    user: str
    channel: str
    text: str
    thread_ts: Optional[str] = None
    bot_id: Optional[str] = None
    app_id: Optional[str] = None
    subtype: Optional[str] = None
    hidden: bool = False
    deleted: bool = False
    edited: Optional[Dict[str, Any]] = None
    attachments: List[Dict[str, Any]] = Field(default_factory=list)
    blocks: List[Dict[str, Any]] = Field(default_factory=list)
    reactions: List[Dict[str, Any]] = Field(default_factory=list)
    replies: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True

class SlackInteraction(BaseModel):
    """Slack interaction model (buttons, menus, etc.)."""
    type: str  # block_actions, interactive_message, etc.
    user: SlackUser
    channel: SlackChannel
    message: Optional[SlackMessage] = None
    action_ts: str
    response_url: str
    trigger_id: str
    team: Dict[str, Any]
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    callback_id: Optional[str] = None
    state: Optional[Dict[str, Any]] = None
    view: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True

class SlackEvent(BaseModel):
    """Generic Slack event model."""
    type: str
    event_ts: str
    user: Optional[str] = None
    channel: Optional[str] = None
    text: Optional[str] = None
    ts: Optional[str] = None
    thread_ts: Optional[str] = None
    team: Optional[str] = None
    api_app_id: Optional[str] = None
    authed_users: List[str] = Field(default_factory=list)
    event_id: str
    event_time: int
    token: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True

class SlackCommand(BaseModel):
    """Slack slash command model."""
    token: str
    team_id: str
    team_domain: str
    channel_id: str
    channel_name: str
    user_id: str
    user_name: str
    command: str
    text: str
    response_url: str
    trigger_id: str
    api_app_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True

class UserSession(BaseModel):
    """User session model for conversation context."""
    id: str
    user_id: str
    channel_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    history: List[Dict[str, Any]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    
    class Config:
        from_attributes = True

class QueryResult(BaseModel):
    """Query result model."""
    id: str
    session_id: str
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

class AlertDefinition(BaseModel):
    """Alert definition model."""
    name: str
    description: Optional[str] = None
    query: str
    spl_query: Optional[str] = None
    condition: str
    threshold: Optional[float] = None
    time_window: int = 300  # 5 minutes default
    notification_channels: List[str] = Field(default_factory=list)
    enabled: bool = True
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True

class BotMetrics(BaseModel):
    """Bot metrics model."""
    user_id: str
    channel_id: str
    action_type: str  # query, command, interaction
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error_type: Optional[str] = None
    response_time: Optional[float] = None
    query_length: Optional[int] = None
    results_count: Optional[int] = None
    
    class Config:
        from_attributes = True

class UserContext(BaseModel):
    """User context for Splunk access."""
    user_id: str
    roles: List[str] = Field(default_factory=list)
    permissions: Dict[str, Any] = Field(default_factory=dict)
    accessible_indexes: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    access_level: str = "standard"  # standard, admin, readonly
    
    class Config:
        from_attributes = True