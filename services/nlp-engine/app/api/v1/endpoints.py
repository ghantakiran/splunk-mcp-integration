"""
FastAPI endpoints for NLP Engine service
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import time

from ...ai import (
    SPLTranslationRequest,
    SPLTranslationResponse,
    IntentClassificationResult,
    EntityExtractionResult,
    nlp_service,
    ai_manager
)
from ...core.config import settings
from ...core.logging import get_logger, LogContext
from .ai_endpoints import router as ai_router

logger = get_logger(__name__)
router = APIRouter()

# Include AI endpoints
router.include_router(ai_router, prefix="/ai", tags=["AI Features"])


# Request/Response Models
class TranslateRequest(BaseModel):
    """Request model for SPL translation"""
    query: str = Field(..., description="Natural language query to translate", min_length=1)
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context for translation")
    user_preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="Previous conversation")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Show me all failed login attempts in the last 24 hours",
                "context": {
                    "user_role": "admin",
                    "available_indexes": ["security", "auth"]
                },
                "user_preferences": {
                    "include_explanations": True,
                    "optimization_level": "performance"
                }
            }
        }


class TranslateResponse(BaseModel):
    """Response model for SPL translation"""
    spl_query: str = Field(..., description="Generated SPL search query")
    confidence_score: float = Field(..., description="Confidence in translation quality", ge=0.0, le=1.0)
    explanation: Optional[str] = Field(None, description="Explanation of the generated query")
    suggested_improvements: Optional[List[str]] = Field(None, description="Suggested query improvements")
    alternative_queries: Optional[List[str]] = Field(None, description="Alternative SPL queries")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class IntentRequest(BaseModel):
    """Request model for intent classification"""
    query: str = Field(..., description="Natural language query to classify", min_length=1)
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Count the number of errors by source in the last hour"
            }
        }


class IntentResponse(BaseModel):
    """Response model for intent classification"""
    primary_intent: str = Field(..., description="Primary classified intent")
    confidence_score: float = Field(..., description="Confidence in classification", ge=0.0, le=1.0)
    secondary_intents: Optional[List[Dict[str, float]]] = Field(None, description="Secondary intents with scores")
    entities: Optional[Dict[str, List[str]]] = Field(None, description="Extracted entities")


class EntityRequest(BaseModel):
    """Request model for entity extraction"""
    query: str = Field(..., description="Natural language query for entity extraction", min_length=1)
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Show me errors from host web01 in the last 2 hours for user john.doe"
            }
        }


class EntityResponse(BaseModel):
    """Response model for entity extraction"""
    entities: Dict[str, List[str]] = Field(..., description="Extracted entities by type")
    entity_types: Dict[str, str] = Field(..., description="Entity type mapping")
    confidence_scores: Dict[str, float] = Field(..., description="Confidence scores for entities")


class EnhanceRequest(BaseModel):
    """Request model for query enhancement"""
    query: str = Field(..., description="Natural language query to enhance", min_length=1)
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "Find security incidents from yesterday",
                "context": {
                    "user_role": "security_analyst",
                    "environment": "production"
                }
            }
        }


class EnhanceResponse(BaseModel):
    """Response model for query enhancement"""
    original_query: str = Field(..., description="Original query")
    intent: Dict[str, Any] = Field(..., description="Intent classification results")
    entities: Dict[str, Any] = Field(..., description="Entity extraction results")
    context: Dict[str, Any] = Field(..., description="Provided context")


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field(..., description="Service version")
    ai_providers: Dict[str, Dict[str, Any]] = Field(..., description="Available AI providers")


# API Endpoints
@router.post("/translate", response_model=TranslateResponse, tags=["NLP"])
async def translate_to_spl(request: TranslateRequest) -> TranslateResponse:
    """
    Translate natural language query to SPL search
    
    This endpoint converts a natural language query into a Splunk SPL search command,
    providing confidence scoring and explanations.
    """
    with LogContext(endpoint="translate", query_length=len(request.query)):
        try:
            logger.info("Starting SPL translation", query=request.query[:100])
            
            # Create translation request
            translation_request = SPLTranslationRequest(
                natural_query=request.query,
                context=request.context,
                user_preferences=request.user_preferences,
                conversation_history=request.conversation_history
            )
            
            # Perform translation
            result = await nlp_service.translate_to_spl(translation_request)
            
            logger.info(
                "SPL translation completed",
                confidence=result.confidence_score,
                processing_time=result.processing_time
            )
            
            return TranslateResponse(
                spl_query=result.spl_query,
                confidence_score=result.confidence_score,
                explanation=result.explanation,
                suggested_improvements=result.suggested_improvements,
                alternative_queries=result.alternative_queries,
                processing_time=result.processing_time,
                metadata=result.metadata
            )
            
        except Exception as e:
            logger.error(f"SPL translation failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Translation failed: {str(e)}"
            )


@router.post("/intent", response_model=IntentResponse, tags=["NLP"])
async def classify_intent(request: IntentRequest) -> IntentResponse:
    """
    Classify the intent of a natural language query
    
    This endpoint analyzes the user's intent to help optimize search processing
    and provide better user experience.
    """
    with LogContext(endpoint="intent", query_length=len(request.query)):
        try:
            logger.info("Starting intent classification", query=request.query[:100])
            
            result = await nlp_service.classify_intent(request.query)
            
            logger.info(
                "Intent classification completed",
                primary_intent=result.primary_intent,
                confidence=result.confidence_score
            )
            
            # Convert secondary intents to expected format
            secondary_intents = None
            if result.secondary_intents:
                secondary_intents = [
                    {"intent": intent, "score": score} 
                    for intent, score in result.secondary_intents
                ]
            
            return IntentResponse(
                primary_intent=result.primary_intent,
                confidence_score=result.confidence_score,
                secondary_intents=secondary_intents,
                entities=result.entities
            )
            
        except Exception as e:
            logger.error(f"Intent classification failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Intent classification failed: {str(e)}"
            )


@router.post("/entities", response_model=EntityResponse, tags=["NLP"])
async def extract_entities(request: EntityRequest) -> EntityResponse:
    """
    Extract entities from a natural language query
    
    This endpoint identifies and extracts relevant entities like time ranges,
    field names, values, and other Splunk-specific terms.
    """
    with LogContext(endpoint="entities", query_length=len(request.query)):
        try:
            logger.info("Starting entity extraction", query=request.query[:100])
            
            result = await nlp_service.extract_entities(request.query)
            
            logger.info(
                "Entity extraction completed",
                entity_count=len(result.entities),
                entity_types=list(result.entities.keys())
            )
            
            return EntityResponse(
                entities=result.entities,
                entity_types=result.entity_types,
                confidence_scores=result.confidence_scores
            )
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Entity extraction failed: {str(e)}"
            )


@router.post("/enhance", response_model=EnhanceResponse, tags=["NLP"])
async def enhance_query(request: EnhanceRequest) -> EnhanceResponse:
    """
    Enhance query with intent classification and entity extraction
    
    This endpoint performs comprehensive analysis including intent classification
    and entity extraction in a single request.
    """
    with LogContext(endpoint="enhance", query_length=len(request.query)):
        try:
            logger.info("Starting query enhancement", query=request.query[:100])
            
            result = await nlp_service.enhance_query(request.query, request.context)
            
            logger.info(
                "Query enhancement completed",
                primary_intent=result["intent"]["primary"],
                entity_count=len(result["entities"]["extracted"])
            )
            
            return EnhanceResponse(**result)
            
        except Exception as e:
            logger.error(f"Query enhancement failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Query enhancement failed: {str(e)}"
            )


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint
    
    Returns the current status of the NLP engine service and available AI providers.
    """
    try:
        ai_providers = ai_manager.get_all_provider_info()
        
        return HealthResponse(
            status="healthy",
            timestamp=str(time.time()),
            version=settings.app_version,
            ai_providers=ai_providers
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: {str(e)}"
        )


@router.get("/providers", tags=["System"])
async def get_ai_providers() -> Dict[str, Any]:
    """
    Get information about available AI providers
    
    Returns detailed information about configured AI providers and their capabilities.
    """
    try:
        return {
            "available_providers": ai_manager.get_all_provider_info(),
            "default_provider": settings.default_ai_provider
        }
        
    except Exception as e:
        logger.error(f"Failed to get provider info: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get provider information: {str(e)}"
        )


@router.get("/metrics", tags=["System"])
async def get_metrics() -> Dict[str, Any]:
    """
    Get service metrics and statistics
    
    Returns operational metrics for monitoring and observability.
    """
    try:
        # This would typically connect to a metrics store
        # For now, return basic service information
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "ai_providers_count": len(ai_manager.providers),
            "default_provider": settings.default_ai_provider
        }
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics: {str(e)}"
        )