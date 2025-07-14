"""
FastAPI endpoints for context management and conversation flow
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

from ...context import (
    conversation_manager,
    context_service,
    memory_store,
    ConversationContext,
    QueryContext,
    ContextPreferences,
    ContextualResponse,
    ConversationState,
    MessageType
)
from ...core.config import settings
from ...core.logging import get_logger, LogContext

logger = get_logger(__name__)
router = APIRouter()


# Request/Response Models
class CreateConversationRequest(BaseModel):
    """Request model for creating a new conversation"""
    user_id: str = Field(..., description="User ID for the conversation")
    title: Optional[str] = Field(None, description="Optional conversation title")
    session_id: Optional[str] = Field(None, description="Session ID for tracking")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "user_id": "user123",
                "title": "Security Analysis",
                "session_id": "session456",
                "metadata": {
                    "source": "web_app",
                    "user_agent": "Mozilla/5.0..."
                }
            }
        }


class ConversationResponse(BaseModel):
    """Response model for conversation operations"""
    conversation_id: str = Field(..., description="Unique conversation identifier")
    user_id: str = Field(..., description="User ID")
    state: str = Field(..., description="Current conversation state")
    title: Optional[str] = Field(None, description="Conversation title")
    summary: Optional[str] = Field(None, description="Conversation summary")
    message_count: int = Field(..., description="Number of messages in conversation")
    query_count: int = Field(..., description="Number of queries processed")
    last_activity: Optional[str] = Field(None, description="Last activity timestamp")
    created_at: Optional[str] = Field(None, description="Creation timestamp")


class ContextualQueryRequest(BaseModel):
    """Request model for contextual query processing"""
    conversation_id: str = Field(..., description="Conversation ID for context")
    query: str = Field(..., description="Natural language query", min_length=1)
    preferences: Optional[Dict[str, Any]] = Field(None, description="Context processing preferences")
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": "conv-123",
                "query": "Show me the same data for yesterday",
                "preferences": {
                    "include_history": True,
                    "max_context_queries": 5,
                    "suggest_follow_ups": True
                }
            }
        }


class ContextualQueryResponse(BaseModel):
    """Response model for contextual query processing"""
    spl_query: str = Field(..., description="Generated SPL query")
    confidence_score: float = Field(..., description="Translation confidence", ge=0.0, le=1.0)
    explanation: Optional[str] = Field(None, description="Query explanation")
    context_used: Optional[Dict[str, Any]] = Field(None, description="Context information used")
    resolved_references: Optional[Dict[str, str]] = Field(None, description="Resolved references")
    assumptions_made: Optional[List[str]] = Field(None, description="Assumptions made during processing")
    follow_up_suggestions: Optional[List[str]] = Field(None, description="Follow-up query suggestions")
    clarification_questions: Optional[List[str]] = Field(None, description="Clarification questions")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    context_confidence: float = Field(..., description="Context confidence score", ge=0.0, le=1.0)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AddMessageRequest(BaseModel):
    """Request model for adding messages to conversation"""
    conversation_id: str = Field(..., description="Conversation ID")
    message_type: str = Field(..., description="Type of message")
    content: str = Field(..., description="Message content", min_length=1)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Message metadata")
    
    class Config:
        schema_extra = {
            "example": {
                "conversation_id": "conv-123",
                "message_type": "user_query",
                "content": "Show me error logs from the last hour",
                "metadata": {"source": "web_ui"}
            }
        }


class ConversationHistoryResponse(BaseModel):
    """Response model for conversation history"""
    conversation_id: str = Field(..., description="Conversation ID")
    messages: List[Dict[str, Any]] = Field(..., description="Messages in conversation")
    total_messages: int = Field(..., description="Total number of messages")
    context_variables: Dict[str, Any] = Field(..., description="Current context variables")


class MemoryStatsResponse(BaseModel):
    """Response model for memory statistics"""
    conversations: int = Field(..., description="Number of active conversations")
    queries: int = Field(..., description="Number of stored queries")
    sessions: int = Field(..., description="Number of active sessions")
    redis_memory_used: str = Field(..., description="Redis memory usage")
    redis_memory_peak: str = Field(..., description="Redis peak memory usage")


# API Endpoints

@router.post("/conversations", response_model=ConversationResponse, tags=["Context"])
async def create_conversation(request: CreateConversationRequest) -> ConversationResponse:
    """
    Create a new conversation for context management
    
    This endpoint initializes a new conversation context that will track
    the user's query history and maintain context for improved NLP processing.
    """
    with LogContext(endpoint="create_conversation", user_id=request.user_id):
        try:
            logger.info("Creating new conversation", user_id=request.user_id)
            
            # Create conversation
            context = await conversation_manager.create_conversation(
                user_id=request.user_id,
                title=request.title,
                session_id=request.session_id,
                metadata=request.metadata
            )
            
            logger.info(
                "Conversation created successfully",
                conversation_id=context.conversation_id,
                user_id=request.user_id
            )
            
            return ConversationResponse(
                conversation_id=context.conversation_id,
                user_id=context.user_id,
                state=context.state.value,
                title=context.title,
                summary=context.summary,
                message_count=context.message_count,
                query_count=context.query_count,
                last_activity=context.last_activity.isoformat() if context.last_activity else None,
                created_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to create conversation: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create conversation: {str(e)}"
            )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse, tags=["Context"])
async def get_conversation(conversation_id: str) -> ConversationResponse:
    """
    Get conversation details and current context
    
    Retrieves the current state of a conversation including message counts,
    context variables, and activity information.
    """
    with LogContext(endpoint="get_conversation", conversation_id=conversation_id):
        try:
            logger.info("Retrieving conversation", conversation_id=conversation_id)
            
            context = await conversation_manager.get_conversation(conversation_id)
            if not context:
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation {conversation_id} not found"
                )
            
            # Get summary
            summary = await conversation_manager.get_conversation_summary(conversation_id)
            
            return ConversationResponse(
                conversation_id=context.conversation_id,
                user_id=context.user_id,
                state=context.state.value,
                title=context.title,
                summary=summary,
                message_count=context.message_count,
                query_count=context.query_count,
                last_activity=context.last_activity.isoformat() if context.last_activity else None
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get conversation: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get conversation: {str(e)}"
            )


@router.post("/conversations/{conversation_id}/query", response_model=ContextualQueryResponse, tags=["Context"])
async def process_contextual_query(
    conversation_id: str, 
    request: ContextualQueryRequest
) -> ContextualQueryResponse:
    """
    Process a query with full conversation context
    
    This endpoint processes natural language queries using the full conversation
    context to improve understanding, resolve references, and provide better SPL translation.
    """
    with LogContext(endpoint="contextual_query", conversation_id=conversation_id, query_length=len(request.query)):
        try:
            logger.info("Processing contextual query", conversation_id=conversation_id, query=request.query[:100])
            
            # Build context preferences
            preferences = None
            if request.preferences:
                preferences = ContextPreferences(
                    include_history=request.preferences.get("include_history", True),
                    max_context_queries=request.preferences.get("max_context_queries", 5),
                    prefer_recent_context=request.preferences.get("prefer_recent_context", True),
                    auto_resolve_references=request.preferences.get("auto_resolve_references", True),
                    context_sensitivity=request.preferences.get("context_sensitivity", "medium"),
                    include_explanations=request.preferences.get("include_explanations", True),
                    show_context_used=request.preferences.get("show_context_used", False),
                    suggest_follow_ups=request.preferences.get("suggest_follow_ups", True)
                )
            
            # Process query with context
            result = await context_service.process_contextual_query(
                conversation_id=conversation_id,
                user_query=request.query,
                preferences=preferences
            )
            
            # Add message to conversation
            await conversation_manager.add_message(
                conversation_id=conversation_id,
                message_type=MessageType.USER_QUERY,
                content=request.query,
                metadata={"query_id": str(uuid.uuid4())}
            )
            
            # Add response message
            await conversation_manager.add_message(
                conversation_id=conversation_id,
                message_type=MessageType.ASSISTANT_RESPONSE,
                content=f"Generated SPL: {result.spl_query}",
                metadata={
                    "confidence_score": result.confidence_score,
                    "context_confidence": result.context_confidence
                }
            )
            
            logger.info(
                "Contextual query processed successfully",
                conversation_id=conversation_id,
                confidence=result.confidence_score,
                context_confidence=result.context_confidence
            )
            
            return ContextualQueryResponse(
                spl_query=result.spl_query,
                confidence_score=result.confidence_score,
                explanation=result.explanation,
                context_used=result.context_used,
                resolved_references=result.resolved_references,
                assumptions_made=result.assumptions_made,
                follow_up_suggestions=result.follow_up_suggestions,
                clarification_questions=result.clarification_questions,
                processing_time=result.processing_time,
                context_confidence=result.context_confidence,
                metadata=result.metadata
            )
            
        except Exception as e:
            logger.error(f"Contextual query processing failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Query processing failed: {str(e)}"
            )


@router.post("/conversations/{conversation_id}/messages", tags=["Context"])
async def add_message_to_conversation(conversation_id: str, request: AddMessageRequest) -> Dict[str, str]:
    """
    Add a message to the conversation
    
    Adds a message to the conversation history for context tracking.
    Messages can be user queries, assistant responses, or system messages.
    """
    with LogContext(endpoint="add_message", conversation_id=conversation_id):
        try:
            logger.info("Adding message to conversation", conversation_id=conversation_id, message_type=request.message_type)
            
            # Validate message type
            try:
                message_type = MessageType(request.message_type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid message type: {request.message_type}"
                )
            
            # Add message
            success = await conversation_manager.add_message(
                conversation_id=conversation_id,
                message_type=message_type,
                content=request.content,
                metadata=request.metadata
            )
            
            if not success:
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation {conversation_id} not found or failed to add message"
                )
            
            return {"message": "Message added successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to add message: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to add message: {str(e)}"
            )


@router.get("/conversations/{conversation_id}/history", response_model=ConversationHistoryResponse, tags=["Context"])
async def get_conversation_history(conversation_id: str, limit: int = 50) -> ConversationHistoryResponse:
    """
    Get conversation message history
    
    Retrieves the message history for a conversation with optional limit.
    """
    with LogContext(endpoint="get_history", conversation_id=conversation_id):
        try:
            logger.info("Getting conversation history", conversation_id=conversation_id, limit=limit)
            
            # Get conversation memory
            memory = await memory_store.get_conversation(conversation_id)
            if not memory:
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation {conversation_id} not found"
                )
            
            # Get limited messages
            messages = memory.messages[-limit:] if limit > 0 else memory.messages
            
            return ConversationHistoryResponse(
                conversation_id=conversation_id,
                messages=messages,
                total_messages=len(memory.messages),
                context_variables=memory.context_variables
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get conversation history: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get conversation history: {str(e)}"
            )


@router.delete("/conversations/{conversation_id}", tags=["Context"])
async def end_conversation(conversation_id: str) -> Dict[str, str]:
    """
    End and archive a conversation
    
    Marks a conversation as ended and archives it for future reference.
    """
    with LogContext(endpoint="end_conversation", conversation_id=conversation_id):
        try:
            logger.info("Ending conversation", conversation_id=conversation_id)
            
            success = await conversation_manager.end_conversation(conversation_id)
            if not success:
                raise HTTPException(
                    status_code=404,
                    detail=f"Conversation {conversation_id} not found or already ended"
                )
            
            return {"message": "Conversation ended successfully"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to end conversation: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to end conversation: {str(e)}"
            )


@router.get("/conversations/user/{user_id}", tags=["Context"])
async def get_user_conversations(user_id: str, limit: int = 20) -> Dict[str, List[str]]:
    """
    Get all conversations for a user
    
    Retrieves a list of conversation IDs for the specified user.
    """
    with LogContext(endpoint="get_user_conversations", user_id=user_id):
        try:
            logger.info("Getting user conversations", user_id=user_id, limit=limit)
            
            conversations = await memory_store.get_user_conversations(user_id, limit)
            
            return {
                "conversations": conversations,
                "total": len(conversations)
            }
            
        except Exception as e:
            logger.error(f"Failed to get user conversations: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get user conversations: {str(e)}"
            )


@router.get("/memory/stats", response_model=MemoryStatsResponse, tags=["System"])
async def get_memory_stats() -> MemoryStatsResponse:
    """
    Get memory store statistics
    
    Returns statistics about the memory usage including conversation counts,
    query counts, and Redis memory usage.
    """
    try:
        stats = await memory_store.get_memory_stats()
        
        return MemoryStatsResponse(
            conversations=stats.get("conversations", 0),
            queries=stats.get("queries", 0),
            sessions=stats.get("sessions", 0),
            redis_memory_used=stats.get("redis_memory_used", "N/A"),
            redis_memory_peak=stats.get("redis_memory_peak", "N/A")
        )
        
    except Exception as e:
        logger.error(f"Failed to get memory stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get memory stats: {str(e)}"
        )


@router.get("/memory/health", tags=["System"])
async def check_memory_health() -> Dict[str, Any]:
    """
    Check memory store health
    
    Performs a health check on the Redis memory store and returns status.
    """
    try:
        health = await memory_store.health_check()
        
        return {
            "status": "healthy" if health else "unhealthy",
            "redis_connection": health,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Memory health check failed: {str(e)}")
        return {
            "status": "error",
            "redis_connection": False,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }