"""
Pydantic models for Microsoft Teams bot.
"""

from .teams_models import (
    TeamsUser,
    TeamsChannel,
    TeamsMessage,
    TeamsActivity,
    TeamsSession,
    QueryResult,
    TeamsAlertDefinition,
    TeamsMetrics,
    UserContext,
    TeamsInvokeRequest,
    TeamsInvokeResponse,
    TeamsTaskInfo,
    TeamsComposeExtensionQuery,
    TeamsComposeExtensionResult,
    TeamsBotInstallation,
    TeamsConversationReference
)

__all__ = [
    "TeamsUser",
    "TeamsChannel",
    "TeamsMessage", 
    "TeamsActivity",
    "TeamsSession",
    "QueryResult",
    "TeamsAlertDefinition",
    "TeamsMetrics",
    "UserContext",
    "TeamsInvokeRequest",
    "TeamsInvokeResponse",
    "TeamsTaskInfo",
    "TeamsComposeExtensionQuery",
    "TeamsComposeExtensionResult",
    "TeamsBotInstallation",
    "TeamsConversationReference"
]