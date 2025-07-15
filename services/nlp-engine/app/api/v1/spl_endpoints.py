"""
FastAPI endpoints for SPL mapping and advanced translation functionality
"""

from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

from ...ai.spl_mapping import spl_mapper, SPLCommandType, FieldType
from ...ai.nlp_service import NLPService, SPLTranslationRequest, SPLTranslationResponse
from ...ai.query_constructor import QueryComplexity
from ...ai.advanced_aggregation import advanced_aggregation_handler, AggregationFunction, AggregationType
from ...ai.statistical_functions import statistical_function_mapper, StatisticalFunction, StatisticalCategory
from ...core.config import settings
from ...core.logging import get_logger, LogContext

logger = get_logger(__name__)
router = APIRouter()
nlp_service = NLPService()


# Request/Response Models
class SPLCommandInfo(BaseModel):
    """SPL command information"""
    name: str = Field(..., description="Command name")
    command_type: str = Field(..., description="Command type category")
    syntax: str = Field(..., description="Command syntax")
    description: str = Field(..., description="Command description")
    parameters: List[str] = Field(default_factory=list, description="Command parameters")
    examples: List[str] = Field(default_factory=list, description="Usage examples")
    aliases: List[str] = Field(default_factory=list, description="Command aliases")
    common_patterns: List[str] = Field(default_factory=list, description="Common usage patterns")
    performance_notes: Optional[str] = Field(None, description="Performance considerations")


class FieldMappingInfo(BaseModel):
    """Field mapping information"""
    natural_names: List[str] = Field(..., description="Natural language field names")
    splunk_field: str = Field(..., description="Actual Splunk field name")
    field_type: str = Field(..., description="Field data type")
    common_values: List[str] = Field(default_factory=list, description="Common field values")
    validation_regex: Optional[str] = Field(None, description="Validation regex pattern")


class EnhancedTranslationRequest(BaseModel):
    """Enhanced SPL translation request"""
    natural_query: str = Field(..., description="Natural language query", min_length=1)
    context: Optional[Dict[str, Any]] = Field(None, description="Query context information")
    user_preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="Conversation history")
    include_suggestions: bool = Field(True, description="Include optimization suggestions")
    validate_syntax: bool = Field(True, description="Validate SPL syntax")
    
    class Config:
        schema_extra = {
            "example": {
                "natural_query": "Show me all failed login attempts in the last 24 hours",
                "context": {
                    "user_role": "admin",
                    "available_indexes": ["security", "auth"],
                    "environment": "production"
                },
                "include_suggestions": True,
                "validate_syntax": True
            }
        }


class EnhancedTranslationResponse(BaseModel):
    """Enhanced SPL translation response"""
    spl_query: str = Field(..., description="Generated SPL query")
    confidence_score: float = Field(..., description="Translation confidence", ge=0.0, le=1.0)
    explanation: Optional[str] = Field(None, description="Query explanation")
    optimization_suggestions: Optional[List[str]] = Field(None, description="Optimization suggestions")
    syntax_valid: bool = Field(..., description="Whether SPL syntax is valid")
    syntax_errors: Optional[List[str]] = Field(None, description="Syntax errors if any")
    command_suggestions: Optional[List[Dict[str, float]]] = Field(None, description="Alternative command suggestions")
    detected_intent: Optional[str] = Field(None, description="Detected user intent")
    extracted_entities: Optional[Dict[str, Any]] = Field(None, description="Extracted entities")
    processing_time: Optional[float] = Field(None, description="Processing time in seconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class CommandSuggestionRequest(BaseModel):
    """Command suggestion request"""
    partial_query: str = Field(..., description="Partial query text", min_length=1)
    limit: int = Field(5, description="Maximum number of suggestions", ge=1, le=20)


class CommandSuggestionResponse(BaseModel):
    """Command suggestion response"""
    suggestions: List[Dict[str, Any]] = Field(..., description="Command suggestions with scores")
    total_suggestions: int = Field(..., description="Total number of suggestions")


class SPLValidationRequest(BaseModel):
    """SPL validation request"""
    spl_query: str = Field(..., description="SPL query to validate", min_length=1)
    include_optimization: bool = Field(True, description="Include optimization suggestions")


class SPLValidationResponse(BaseModel):
    """SPL validation response"""
    is_valid: bool = Field(..., description="Whether SPL syntax is valid")
    syntax_errors: List[str] = Field(default_factory=list, description="Syntax errors")
    optimization_suggestions: List[str] = Field(default_factory=list, description="Optimization suggestions")
    optimized_query: Optional[str] = Field(None, description="Optimized query suggestion")


class ComplexQueryRequest(BaseModel):
    """Complex query construction request"""
    natural_query: str = Field(..., description="Natural language query", min_length=1)
    context: Optional[Dict[str, Any]] = Field(None, description="Query context")
    include_performance_analysis: bool = Field(True, description="Include performance analysis")
    
    class Config:
        schema_extra = {
            "example": {
                "natural_query": "Show me top 10 users with most failed login attempts over time for the last week grouped by hour",
                "context": {
                    "index": "security",
                    "sourcetype": "auth_logs"
                },
                "include_performance_analysis": True
            }
        }


class ComplexQueryResponse(BaseModel):
    """Complex query construction response"""
    spl_query: str = Field(..., description="Generated complex SPL query")
    query_complexity: str = Field(..., description="Query complexity level")
    performance_analysis: Dict[str, Any] = Field(..., description="Performance analysis")
    syntax_valid: bool = Field(..., description="Whether syntax is valid")
    syntax_errors: Optional[List[str]] = Field(None, description="Syntax errors if any")
    processing_time: float = Field(..., description="Processing time in seconds")
    metadata: Dict[str, Any] = Field(..., description="Additional metadata")
    subqueries_count: int = Field(0, description="Number of subqueries detected")
    joins_count: int = Field(0, description="Number of joins detected")
    unions_count: int = Field(0, description="Number of unions detected")
    has_advanced_features: bool = Field(False, description="Whether query uses advanced features")


class QueryAnalysisRequest(BaseModel):
    """Query analysis request"""
    natural_query: str = Field(..., description="Natural language query to analyze", min_length=1)


class QueryAnalysisResponse(BaseModel):
    """Query analysis response"""
    complexity_score: int = Field(..., description="Complexity score")
    estimated_cost: str = Field(..., description="Estimated execution cost")
    has_temporal_aspect: bool = Field(..., description="Whether query has time-based analysis")
    has_aggregation: bool = Field(..., description="Whether query includes aggregation")
    has_grouping: bool = Field(..., description="Whether query includes grouping")
    has_comparison: bool = Field(..., description="Whether query includes comparisons")
    condition_count: int = Field(..., description="Number of conditions detected")
    command_indicators: List[str] = Field(..., description="Detected command indicators")
    optimization_suggestions: List[str] = Field(..., description="Optimization suggestions")
    performance_warnings: List[str] = Field(..., description="Performance warnings")


# API Endpoints

@router.get("/commands", response_model=List[SPLCommandInfo], tags=["SPL Commands"])
async def get_spl_commands(
    command_type: Optional[str] = None,
    limit: int = 50
) -> List[SPLCommandInfo]:
    """
    Get available SPL commands with detailed information
    
    Retrieve a list of supported SPL commands with syntax, examples, and usage patterns.
    """
    with LogContext(endpoint="get_spl_commands", command_type=command_type):
        try:
            logger.info("Retrieving SPL commands", command_type=command_type, limit=limit)
            
            commands = list(spl_mapper.commands.values())
            
            # Filter by command type if specified
            if command_type:
                try:
                    filter_type = SPLCommandType(command_type.lower())
                    commands = [cmd for cmd in commands if cmd.command_type == filter_type]
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid command type: {command_type}"
                    )
            
            # Limit results
            commands = commands[:limit]
            
            # Convert to response format
            result = []
            for cmd in commands:
                result.append(SPLCommandInfo(
                    name=cmd.name,
                    command_type=cmd.command_type.value,
                    syntax=cmd.syntax,
                    description=cmd.description,
                    parameters=cmd.parameters,
                    examples=cmd.examples,
                    aliases=cmd.aliases,
                    common_patterns=cmd.common_patterns,
                    performance_notes=cmd.performance_notes
                ))
            
            logger.info(f"Retrieved {len(result)} SPL commands")
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get SPL commands: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve SPL commands: {str(e)}"
            )


@router.get("/fields", response_model=List[FieldMappingInfo], tags=["Field Mapping"])
async def get_field_mappings(limit: int = 50) -> List[FieldMappingInfo]:
    """
    Get field mappings between natural language and Splunk field names
    
    Retrieve mappings that help translate natural language field references
    to actual Splunk field names.
    """
    with LogContext(endpoint="get_field_mappings", limit=limit):
        try:
            logger.info("Retrieving field mappings", limit=limit)
            
            mappings = list(spl_mapper.field_mappings.values())[:limit]
            
            result = []
            for mapping in mappings:
                result.append(FieldMappingInfo(
                    natural_names=mapping.natural_names,
                    splunk_field=mapping.splunk_field,
                    field_type=mapping.field_type.value,
                    common_values=mapping.common_values,
                    validation_regex=mapping.validation_regex
                ))
            
            logger.info(f"Retrieved {len(result)} field mappings")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get field mappings: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to retrieve field mappings: {str(e)}"
            )


@router.post("/translate/enhanced", response_model=EnhancedTranslationResponse, tags=["SPL Translation"])
async def translate_to_spl_enhanced(request: EnhancedTranslationRequest) -> EnhancedTranslationResponse:
    """
    Translate natural language to SPL with enhanced mapping features
    
    Advanced translation service that uses comprehensive SPL command mapping,
    intent classification, entity extraction, and syntax validation.
    """
    with LogContext(endpoint="translate_enhanced", query_length=len(request.natural_query)):
        try:
            logger.info("Processing enhanced SPL translation", query=request.natural_query[:100])
            
            # Convert to NLP service request format
            nlp_request = SPLTranslationRequest(
                natural_query=request.natural_query,
                context=request.context,
                user_preferences=request.user_preferences,
                conversation_history=request.conversation_history
            )
            
            # Get enhanced translation
            response = await nlp_service.translate_to_spl(nlp_request)
            
            # Format command suggestions
            command_suggestions = None
            if response.command_suggestions:
                command_suggestions = [
                    {"command": cmd, "score": score}
                    for cmd, score in response.command_suggestions
                ]
            
            logger.info(
                "Enhanced SPL translation completed",
                confidence=response.confidence_score,
                syntax_valid=response.syntax_valid
            )
            
            return EnhancedTranslationResponse(
                spl_query=response.spl_query,
                confidence_score=response.confidence_score,
                explanation=response.explanation,
                optimization_suggestions=response.optimization_suggestions,
                syntax_valid=response.syntax_valid,
                syntax_errors=response.syntax_errors,
                command_suggestions=command_suggestions,
                detected_intent=response.metadata.get("detected_intent") if response.metadata else None,
                extracted_entities=response.metadata.get("extracted_entities") if response.metadata else None,
                processing_time=response.processing_time,
                metadata=response.metadata
            )
            
        except Exception as e:
            logger.error(f"Enhanced SPL translation failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Translation failed: {str(e)}"
            )


@router.post("/commands/suggest", response_model=CommandSuggestionResponse, tags=["SPL Commands"])
async def suggest_commands(request: CommandSuggestionRequest) -> CommandSuggestionResponse:
    """
    Get SPL command suggestions based on partial query
    
    Analyze partial natural language input and suggest relevant SPL commands
    with confidence scores.
    """
    with LogContext(endpoint="suggest_commands", query_length=len(request.partial_query)):
        try:
            logger.info("Getting command suggestions", query=request.partial_query)
            
            suggestions = spl_mapper.get_command_suggestions(request.partial_query)
            
            # Limit results
            suggestions = suggestions[:request.limit]
            
            # Format response
            formatted_suggestions = []
            for command, score in suggestions:
                cmd_info = spl_mapper.get_command_by_name(command)
                formatted_suggestions.append({
                    "command": command,
                    "score": score,
                    "description": cmd_info.description if cmd_info else "",
                    "syntax": cmd_info.syntax if cmd_info else "",
                    "command_type": cmd_info.command_type.value if cmd_info else ""
                })
            
            logger.info(f"Generated {len(formatted_suggestions)} command suggestions")
            
            return CommandSuggestionResponse(
                suggestions=formatted_suggestions,
                total_suggestions=len(formatted_suggestions)
            )
            
        except Exception as e:
            logger.error(f"Command suggestion failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Command suggestion failed: {str(e)}"
            )


@router.post("/validate", response_model=SPLValidationResponse, tags=["SPL Validation"])
async def validate_spl_query(request: SPLValidationRequest) -> SPLValidationResponse:
    """
    Validate SPL query syntax and provide optimization suggestions
    
    Check SPL query for syntax errors and provide suggestions for
    performance optimization.
    """
    with LogContext(endpoint="validate_spl", query_length=len(request.spl_query)):
        try:
            logger.info("Validating SPL query", query=request.spl_query[:100])
            
            # Validate syntax
            is_valid, syntax_errors = spl_mapper.validate_spl_syntax(request.spl_query)
            
            # Get optimization suggestions
            optimization_suggestions = []
            optimized_query = None
            
            if request.include_optimization:
                optimized_query, optimization_suggestions = spl_mapper.optimize_spl_query(request.spl_query)
            
            logger.info(
                "SPL validation completed",
                is_valid=is_valid,
                error_count=len(syntax_errors),
                suggestion_count=len(optimization_suggestions)
            )
            
            return SPLValidationResponse(
                is_valid=is_valid,
                syntax_errors=syntax_errors,
                optimization_suggestions=optimization_suggestions,
                optimized_query=optimized_query if optimized_query != request.spl_query else None
            )
            
        except Exception as e:
            logger.error(f"SPL validation failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"SPL validation failed: {str(e)}"
            )


@router.get("/aggregations", tags=["SPL Functions"])
async def get_aggregation_functions() -> Dict[str, Any]:
    """
    Get available aggregation functions and their mappings
    
    Retrieve natural language to SPL aggregation function mappings.
    """
    try:
        logger.info("Retrieving aggregation functions")
        
        return {
            "aggregation_mappings": spl_mapper.aggregation_mappings,
            "total_functions": len(spl_mapper.aggregation_mappings),
            "categories": {
                "counting": ["count", "number", "total"],
                "mathematical": ["sum", "avg", "min", "max"],
                "statistical": ["stdev", "var", "median", "perc", "range"]
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get aggregation functions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve aggregation functions: {str(e)}"
        )


@router.get("/time-expressions", tags=["Time Mapping"])
async def get_time_expressions() -> Dict[str, Any]:
    """
    Get time expression mappings
    
    Retrieve natural language to SPL time expression mappings.
    """
    try:
        logger.info("Retrieving time expressions")
        
        return {
            "time_mappings": spl_mapper.time_mappings,
            "total_expressions": len(spl_mapper.time_mappings),
            "categories": {
                "relative": ["now", "today", "yesterday"],
                "hour_based": ["last hour", "last 2 hours", "last 24 hours"],
                "day_based": ["last day", "last 7 days", "last 30 days"],
                "minute_based": ["last 15 minutes", "last 30 minutes"],
                "real_time": ["real time", "live"]
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get time expressions: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve time expressions: {str(e)}"
        )


@router.get("/operators", tags=["Operators"])
async def get_operators() -> Dict[str, Any]:
    """
    Get operator mappings
    
    Retrieve natural language to SPL operator mappings.
    """
    try:
        logger.info("Retrieving operators")
        
        return {
            "operator_mappings": spl_mapper.operator_mappings,
            "total_operators": len(spl_mapper.operator_mappings),
            "categories": {
                "equality": ["equals", "is", "not equal", "not"],
                "comparison": ["greater than", "less than", "above", "below"],
                "pattern_matching": ["contains", "includes", "matches", "starts with"]
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get operators: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve operators: {str(e)}"
        )


@router.get("/stats", tags=["System"])
async def get_mapping_stats() -> Dict[str, Any]:
    """
    Get SPL mapping system statistics
    
    Retrieve comprehensive statistics about the mapping system.
    """
    try:
        logger.info("Retrieving mapping statistics")
        
        return {
            "total_commands": len(spl_mapper.commands),
            "commands_by_type": {
                cmd_type.value: len(spl_mapper.get_commands_by_type(cmd_type))
                for cmd_type in SPLCommandType
            },
            "total_field_mappings": len(spl_mapper.field_mappings),
            "fields_by_type": {
                field_type.value: sum(
                    1 for mapping in spl_mapper.field_mappings.values()
                    if mapping.field_type == field_type
                )
                for field_type in FieldType
            },
            "total_intent_patterns": len(spl_mapper.intent_patterns),
            "total_aggregation_mappings": len(spl_mapper.aggregation_mappings),
            "total_time_mappings": len(spl_mapper.time_mappings),
            "total_operator_mappings": len(spl_mapper.operator_mappings),
            "system_version": "1.0.0",
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get mapping stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve mapping statistics: {str(e)}"
        )


@router.post("/translate/complex", response_model=ComplexQueryResponse, tags=["Complex Query Construction"])
async def construct_complex_query(request: ComplexQueryRequest) -> ComplexQueryResponse:
    """
    Construct complex SPL queries with advanced features
    
    Build sophisticated multi-step SPL queries with complex logical structures,
    aggregations, joins, and performance optimizations.
    """
    with LogContext(endpoint="construct_complex_query", query_length=len(request.natural_query)):
        try:
            logger.info("Constructing complex SPL query", query=request.natural_query[:100])
            
            # Convert to NLP service request format
            nlp_request = SPLTranslationRequest(
                natural_query=request.natural_query,
                context=request.context
            )
            
            # Get complex query construction
            result = await nlp_service.construct_complex_query(nlp_request)
            
            if "error" in result:
                raise HTTPException(
                    status_code=500,
                    detail=f"Complex query construction failed: {result['error']}"
                )
            
            logger.info(
                "Complex query construction completed",
                complexity=result["query_complexity"],
                processing_time=result["processing_time"]
            )
            
            # Extract additional metadata
            metadata = result["metadata"]
            subqueries_count = metadata.get("has_subqueries", 0) if isinstance(metadata.get("has_subqueries"), int) else (1 if metadata.get("has_subqueries") else 0)
            joins_count = metadata.get("has_joins", 0) if isinstance(metadata.get("has_joins"), int) else (1 if metadata.get("has_joins") else 0)
            unions_count = metadata.get("has_unions", 0) if isinstance(metadata.get("has_unions"), int) else (1 if metadata.get("has_unions") else 0)
            has_advanced_features = subqueries_count > 0 or joins_count > 0 or unions_count > 0
            
            return ComplexQueryResponse(
                spl_query=result["spl_query"],
                query_complexity=result["query_complexity"],
                performance_analysis=result["performance_analysis"],
                syntax_valid=result["syntax_valid"],
                syntax_errors=result.get("syntax_errors"),
                processing_time=result["processing_time"],
                metadata=result["metadata"],
                subqueries_count=subqueries_count,
                joins_count=joins_count,
                unions_count=unions_count,
                has_advanced_features=has_advanced_features
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Complex query construction failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Complex query construction failed: {str(e)}"
            )


@router.post("/analyze", response_model=QueryAnalysisResponse, tags=["Query Analysis"])
async def analyze_query_structure(request: QueryAnalysisRequest) -> QueryAnalysisResponse:
    """
    Analyze natural language query structure and complexity
    
    Examine the structure of a natural language query to determine complexity,
    required features, and provide optimization suggestions.
    """
    with LogContext(endpoint="analyze_query", query_length=len(request.natural_query)):
        try:
            logger.info("Analyzing query structure", query=request.natural_query[:100])
            
            # Import query constructor for analysis
            from ...ai.query_constructor import query_constructor
            
            # Analyze query structure
            analysis = query_constructor._analyze_query_structure(request.natural_query)
            complexity = query_constructor._determine_complexity(analysis)
            
            # Build a simple complex query to get performance analysis
            nlp_request = SPLTranslationRequest(natural_query=request.natural_query)
            complex_query_result = await nlp_service.construct_complex_query(nlp_request)
            
            performance_analysis = complex_query_result.get("performance_analysis", {})
            
            logger.info(
                "Query analysis completed",
                complexity=complexity.value,
                condition_count=analysis["condition_count"]
            )
            
            return QueryAnalysisResponse(
                complexity_score=performance_analysis.get("complexity_score", 0),
                estimated_cost=performance_analysis.get("estimated_cost", "unknown"),
                has_temporal_aspect=analysis["has_temporal_aspect"],
                has_aggregation=analysis["has_aggregation"],
                has_grouping=analysis["has_grouping"],
                has_comparison=analysis["has_comparison"],
                condition_count=analysis["condition_count"],
                command_indicators=analysis["command_indicators"],
                optimization_suggestions=performance_analysis.get("optimization_suggestions", []),
                performance_warnings=performance_analysis.get("performance_warnings", [])
            )
            
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Query analysis failed: {str(e)}"
            )


@router.get("/complexity/levels", tags=["Query Analysis"])
async def get_complexity_levels() -> Dict[str, Any]:
    """
    Get available query complexity levels and their characteristics
    
    Retrieve information about different query complexity levels and
    what features each level supports.
    """
    try:
        logger.info("Retrieving complexity levels")
        
        return {
            "complexity_levels": {
                "simple": {
                    "name": "Simple",
                    "description": "Single command queries with basic filtering",
                    "max_commands": 1,
                    "supports_subqueries": False,
                    "supports_joins": False,
                    "max_conditions": 3,
                    "examples": [
                        "search error",
                        "search index=main status=500"
                    ]
                },
                "moderate": {
                    "name": "Moderate", 
                    "description": "Multi-command pipelines with transformations",
                    "max_commands": 3,
                    "supports_subqueries": False,
                    "supports_joins": False,
                    "max_conditions": 5,
                    "examples": [
                        "search error | stats count by host",
                        "search failed | dedup user | sort _time"
                    ]
                },
                "complex": {
                    "name": "Complex",
                    "description": "Advanced queries with subqueries and multiple aggregations",
                    "max_commands": 6,
                    "supports_subqueries": True,
                    "supports_joins": False,
                    "max_conditions": 10,
                    "examples": [
                        "search error | stats count by host | where count > 10 | sort -count",
                        "search failed login | timechart span=1h count by user"
                    ]
                },
                "advanced": {
                    "name": "Advanced",
                    "description": "Enterprise-grade queries with joins, unions, and complex logic",
                    "max_commands": "unlimited",
                    "supports_subqueries": True,
                    "supports_joins": True,
                    "max_conditions": "unlimited",
                    "examples": [
                        "multisearch queries with joins",
                        "complex event correlation with multiple data sources"
                    ]
                }
            },
            "performance_guidelines": {
                "simple": "Excellent performance, suitable for real-time dashboards",
                "moderate": "Good performance, suitable for regular reporting",
                "complex": "Moderate performance, may require optimization for large datasets",
                "advanced": "Resource intensive, requires careful optimization and monitoring"
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get complexity levels: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve complexity levels: {str(e)}"
        )


# Advanced Aggregation API Models
class AggregationDetectionRequest(BaseModel):
    """Advanced aggregation detection request"""
    natural_query: str = Field(..., description="Natural language query to analyze for aggregations", min_length=1)
    
    class Config:
        schema_extra = {
            "example": {
                "natural_query": "Show me the 95th percentile of response time and average count of errors by host over the last 24 hours"
            }
        }


class AggregationInfo(BaseModel):
    """Information about a detected aggregation"""
    function: str = Field(..., description="Aggregation function name")
    fields: List[str] = Field(..., description="Fields involved in aggregation")
    alias: Optional[str] = Field(None, description="Alias for the aggregation result")
    aggregation_type: str = Field(..., description="Type of aggregation")
    parameters: List[Dict[str, Any]] = Field(default_factory=list, description="Function parameters")
    conditions: List[Dict[str, Any]] = Field(default_factory=list, description="Conditional filters")
    time_window: Optional[str] = Field(None, description="Time window for temporal aggregations")
    generated_spl: str = Field(..., description="Generated SPL for this aggregation")


class AggregationDetectionResponse(BaseModel):
    """Advanced aggregation detection response"""
    detected_aggregations: List[AggregationInfo] = Field(..., description="List of detected aggregations")
    aggregation_count: int = Field(..., description="Total number of aggregations found")
    complexity_level: str = Field(..., description="Overall complexity level of aggregations")
    combined_spl: str = Field(..., description="Combined SPL query for all aggregations")
    optimization_suggestions: List[str] = Field(..., description="Optimization suggestions")
    processing_time: float = Field(..., description="Processing time in seconds")


class AggregationTypesResponse(BaseModel):
    """Response with available aggregation types and functions"""
    aggregation_functions: Dict[str, Dict[str, Any]] = Field(..., description="Available aggregation functions")
    aggregation_types: Dict[str, Dict[str, Any]] = Field(..., description="Types of aggregations supported")
    statistical_functions: Dict[str, Dict[str, Any]] = Field(..., description="Statistical aggregation functions")
    temporal_functions: Dict[str, Dict[str, Any]] = Field(..., description="Temporal aggregation functions")
    conditional_functions: Dict[str, Dict[str, Any]] = Field(..., description="Conditional aggregation functions")


# Advanced Aggregation API Endpoints
@router.post("/aggregations/detect", response_model=AggregationDetectionResponse, tags=["Advanced Aggregations"])
async def detect_advanced_aggregations(request: AggregationDetectionRequest) -> AggregationDetectionResponse:
    """
    Detect advanced aggregations from natural language query
    
    Analyze a natural language query to identify sophisticated aggregation patterns
    including statistical functions, conditional aggregations, temporal aggregations,
    and multi-field aggregations.
    """
    with LogContext(endpoint="detect_aggregations", query_length=len(request.natural_query)):
        try:
            start_time = datetime.now()
            logger.info("Detecting advanced aggregations", query=request.natural_query[:100])
            
            # Detect aggregations using advanced handler
            detected_aggs = advanced_aggregation_handler.detect_aggregations(request.natural_query)
            
            # Convert to response format
            aggregation_infos = []
            for agg in detected_aggs:
                # Generate SPL for individual aggregation
                individual_spl = agg.to_spl()
                
                aggregation_infos.append(AggregationInfo(
                    function=agg.function.value,
                    fields=agg.fields,
                    alias=agg.alias,
                    aggregation_type=agg.aggregation_type.value,
                    parameters=[{"name": p.name, "value": p.value, "type": p.parameter_type} for p in agg.parameters],
                    conditions=[{"field": c.field, "operator": c.operator, "value": c.value} for c in agg.conditions],
                    time_window=agg.time_window,
                    generated_spl=individual_spl
                ))
            
            # Generate combined SPL
            combined_spl = ""
            if detected_aggs:
                # Extract by_fields from query
                by_fields = []
                by_pattern = r"(?:by|group by)\s+(\w+(?:\s*,\s*\w+)*)"
                by_match = re.search(by_pattern, request.natural_query, re.IGNORECASE)
                if by_match:
                    by_fields = [f.strip() for f in by_match.group(1).split(',')]
                
                combined_spl = advanced_aggregation_handler.generate_aggregation_spl(detected_aggs, by_fields)
            
            # Determine complexity level
            complexity_level = "simple"
            if len(detected_aggs) > 1:
                complexity_level = "complex"
            elif any(agg.aggregation_type in [AggregationType.STATISTICAL, AggregationType.CONDITIONAL, AggregationType.TEMPORAL] for agg in detected_aggs):
                complexity_level = "advanced"
            elif any(agg.aggregation_type in [AggregationType.MULTI_FIELD, AggregationType.MULTI_FUNCTION] for agg in detected_aggs):
                complexity_level = "moderate"
            
            # Generate optimization suggestions
            optimization_suggestions = []
            optimized_aggs = advanced_aggregation_handler.optimize_aggregations(detected_aggs)
            
            if len(optimized_aggs) > 3:
                optimization_suggestions.append("Consider breaking down complex aggregations into multiple queries")
            
            if any(agg.aggregation_type == AggregationType.CONDITIONAL for agg in detected_aggs):
                optimization_suggestions.append("Use field filters before aggregation to improve performance")
            
            if any(agg.aggregation_type == AggregationType.STATISTICAL for agg in detected_aggs):
                optimization_suggestions.append("Statistical functions may be resource-intensive on large datasets")
            
            if not by_fields and len(detected_aggs) > 1:
                optimization_suggestions.append("Consider adding grouping fields to organize results")
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(
                "Advanced aggregation detection completed",
                aggregation_count=len(detected_aggs),
                complexity_level=complexity_level,
                processing_time=processing_time
            )
            
            return AggregationDetectionResponse(
                detected_aggregations=aggregation_infos,
                aggregation_count=len(detected_aggs),
                complexity_level=complexity_level,
                combined_spl=combined_spl,
                optimization_suggestions=optimization_suggestions,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Advanced aggregation detection failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Aggregation detection failed: {str(e)}"
            )


@router.get("/aggregations/types", response_model=AggregationTypesResponse, tags=["Advanced Aggregations"])
async def get_aggregation_types() -> AggregationTypesResponse:
    """
    Get available aggregation types and functions
    
    Retrieve comprehensive information about all supported aggregation functions,
    types, and their capabilities for advanced query construction.
    """
    try:
        logger.info("Retrieving aggregation types and functions")
        
        # Basic aggregation functions
        aggregation_functions = {
            "count": {
                "description": "Count of records or field values",
                "supports_fields": True,
                "supports_conditions": True,
                "examples": ["count", "count(user)", "count if status=error"]
            },
            "sum": {
                "description": "Sum of numeric field values",
                "supports_fields": True,
                "supports_conditions": True,
                "examples": ["sum(bytes)", "sum(price) where category=electronics"]
            },
            "avg": {
                "description": "Average of numeric field values",
                "supports_fields": True,
                "supports_conditions": True,
                "examples": ["avg(response_time)", "average(score) by department"]
            },
            "max": {
                "description": "Maximum value in field",
                "supports_fields": True,
                "supports_conditions": False,
                "examples": ["max(temperature)", "highest(score) by team"]
            },
            "min": {
                "description": "Minimum value in field",
                "supports_fields": True,
                "supports_conditions": False,
                "examples": ["min(latency)", "lowest(price) by category"]
            }
        }
        
        # Aggregation types
        aggregation_types = {
            "simple": {
                "description": "Single field, single function aggregations",
                "complexity": "low",
                "examples": ["count of users", "sum of bytes", "average response time"]
            },
            "multi_field": {
                "description": "Multiple fields with single function",
                "complexity": "medium",
                "examples": ["sum of price and tax", "count of users and sessions"]
            },
            "multi_function": {
                "description": "Multiple functions on single field",
                "complexity": "medium",
                "examples": ["sum and average of bytes", "min and max of temperature"]
            },
            "complex": {
                "description": "Multiple fields with multiple functions",
                "complexity": "high",
                "examples": ["sum of price and count of items by category"]
            },
            "conditional": {
                "description": "Aggregations with conditions",
                "complexity": "high",
                "examples": ["count of users where status=active", "sum of bytes if error=true"]
            },
            "temporal": {
                "description": "Time-based aggregations",
                "complexity": "medium",
                "examples": ["rate of events per hour", "latest value of temperature"]
            },
            "statistical": {
                "description": "Advanced statistical functions",
                "complexity": "high",
                "examples": ["95th percentile of response time", "standard deviation of scores"]
            }
        }
        
        # Statistical functions
        statistical_functions = {
            "percentile": {
                "description": "Nth percentile of field values",
                "parameters": ["percentile_value"],
                "examples": ["95th percentile", "perc90(response_time)"]
            },
            "stdev": {
                "description": "Standard deviation of field values",
                "parameters": [],
                "examples": ["standard deviation of scores", "stdev(temperature)"]
            },
            "variance": {
                "description": "Variance of field values",
                "parameters": [],
                "examples": ["variance of measurements", "var(latency)"]
            },
            "median": {
                "description": "Median value of field",
                "parameters": [],
                "examples": ["median response time", "median(price)"]
            },
            "range": {
                "description": "Range (max - min) of field values",
                "parameters": [],
                "examples": ["range of temperatures", "range(scores)"]
            }
        }
        
        # Temporal functions
        temporal_functions = {
            "rate": {
                "description": "Rate of events per time unit",
                "parameters": ["time_unit"],
                "examples": ["rate per second", "events per hour"]
            },
            "earliest": {
                "description": "Earliest value in time range",
                "parameters": [],
                "examples": ["earliest(temperature)", "first value of status"]
            },
            "latest": {
                "description": "Latest value in time range",
                "parameters": [],
                "examples": ["latest(cpu_usage)", "last value of connection"]
            },
            "first": {
                "description": "First occurrence of value",
                "parameters": [],
                "examples": ["first(user_login)", "first occurrence of error"]
            },
            "last": {
                "description": "Last occurrence of value",
                "parameters": [],
                "examples": ["last(logout_time)", "last occurrence of success"]
            }
        }
        
        # Conditional functions
        conditional_functions = {
            "count_if": {
                "description": "Count records matching condition",
                "parameters": ["condition"],
                "examples": ["count if status=error", "count of users where active=true"]
            },
            "sum_if": {
                "description": "Sum values matching condition",
                "parameters": ["field", "condition"],
                "examples": ["sum of bytes if method=POST", "sum of price where category=electronics"]
            },
            "avg_if": {
                "description": "Average values matching condition",
                "parameters": ["field", "condition"],
                "examples": ["average of score if grade>B", "avg of response_time where status=200"]
            }
        }
        
        return AggregationTypesResponse(
            aggregation_functions=aggregation_functions,
            aggregation_types=aggregation_types,
            statistical_functions=statistical_functions,
            temporal_functions=temporal_functions,
            conditional_functions=conditional_functions
        )
        
    except Exception as e:
        logger.error(f"Failed to get aggregation types: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve aggregation types: {str(e)}"
        )


# Statistical Functions API Models
class StatisticalFunctionRequest(BaseModel):
    """Statistical function analysis request"""
    natural_query: str = Field(..., description="Natural language query to analyze for statistical functions", min_length=1)
    confidence_level: Optional[float] = Field(0.95, description="Confidence level for statistical inference", ge=0.0, le=1.0)
    
    class Config:
        schema_extra = {
            "example": {
                "natural_query": "Calculate the 95th percentile of response time and correlation between cpu usage and memory usage",
                "confidence_level": 0.95
            }
        }


class StatisticalFunctionInfo(BaseModel):
    """Information about a detected statistical function"""
    function: str = Field(..., description="Statistical function name")
    category: str = Field(..., description="Statistical function category")
    fields: List[str] = Field(..., description="Fields involved in the statistical function")
    parameters: List[Dict[str, Any]] = Field(default_factory=list, description="Function parameters")
    confidence_level: Optional[float] = Field(None, description="Confidence level if applicable")
    generated_spl: str = Field(..., description="Generated SPL for this statistical function")
    description: str = Field(..., description="Description of the statistical function")
    complexity: str = Field(..., description="Complexity level of the function")


class StatisticalFunctionResponse(BaseModel):
    """Statistical function analysis response"""
    detected_functions: List[StatisticalFunctionInfo] = Field(..., description="List of detected statistical functions")
    function_count: int = Field(..., description="Total number of statistical functions found")
    categories: List[str] = Field(..., description="Categories of statistical functions detected")
    combined_spl: str = Field(..., description="Combined SPL query for all statistical functions")
    validation_errors: List[str] = Field(default_factory=list, description="Validation errors if any")
    processing_time: float = Field(..., description="Processing time in seconds")


class StatisticalFunctionCatalogResponse(BaseModel):
    """Response with available statistical functions catalog"""
    descriptive_statistics: Dict[str, Dict[str, Any]] = Field(..., description="Descriptive statistics functions")
    inferential_statistics: Dict[str, Dict[str, Any]] = Field(..., description="Inferential statistics functions")
    time_series_analysis: Dict[str, Dict[str, Any]] = Field(..., description="Time series analysis functions")
    regression_analysis: Dict[str, Dict[str, Any]] = Field(..., description="Regression analysis functions")
    distribution_analysis: Dict[str, Dict[str, Any]] = Field(..., description="Distribution analysis functions")
    outlier_detection: Dict[str, Dict[str, Any]] = Field(..., description="Outlier detection functions")
    correlation_analysis: Dict[str, Dict[str, Any]] = Field(..., description="Correlation analysis functions")
    hypothesis_testing: Dict[str, Dict[str, Any]] = Field(..., description="Hypothesis testing functions")


class StatisticalFunctionSuggestionsRequest(BaseModel):
    """Request for statistical function suggestions"""
    partial_query: str = Field(..., description="Partial query to get suggestions for", min_length=1)
    limit: int = Field(5, description="Maximum number of suggestions", ge=1, le=20)
    category_filter: Optional[str] = Field(None, description="Filter by statistical category")


class StatisticalFunctionSuggestionsResponse(BaseModel):
    """Response with statistical function suggestions"""
    suggestions: List[Dict[str, Any]] = Field(..., description="Statistical function suggestions with scores")
    total_suggestions: int = Field(..., description="Total number of suggestions")
    category_breakdown: Dict[str, int] = Field(..., description="Breakdown by statistical category")


# Statistical Functions API Endpoints
@router.post("/statistical/analyze", response_model=StatisticalFunctionResponse, tags=["Statistical Functions"])
async def analyze_statistical_functions(request: StatisticalFunctionRequest) -> StatisticalFunctionResponse:
    """
    Analyze natural language query for statistical functions
    
    Detect and analyze statistical functions in natural language queries including
    descriptive statistics, inferential statistics, time series analysis, regression,
    and advanced statistical operations.
    """
    with LogContext(endpoint="analyze_statistical_functions", query_length=len(request.natural_query)):
        try:
            start_time = datetime.now()
            logger.info("Analyzing statistical functions", query=request.natural_query[:100])
            
            # Detect statistical functions
            detected_functions = statistical_function_mapper.detect_statistical_functions(request.natural_query)
            
            # Convert to response format
            function_infos = []
            combined_spl_parts = []
            categories = set()
            validation_errors = []
            
            for stat_func in detected_functions:
                # Generate SPL for individual statistical function
                individual_spl = statistical_function_mapper.generate_spl_for_statistical_function(stat_func)
                combined_spl_parts.append(individual_spl)
                
                # Validate function
                is_valid, errors = statistical_function_mapper.validate_statistical_function(stat_func)
                if not is_valid:
                    validation_errors.extend(errors)
                
                # Get function info
                func_info = statistical_function_mapper.get_statistical_function_info(stat_func)
                categories.add(func_info["category"])
                
                function_infos.append(StatisticalFunctionInfo(
                    function=stat_func.function.value,
                    category=func_info["category"],
                    fields=stat_func.fields,
                    parameters=[{"name": p.name, "value": p.value, "type": p.parameter_type} for p in stat_func.parameters],
                    confidence_level=stat_func.confidence_level,
                    generated_spl=individual_spl,
                    description=func_info["description"],
                    complexity=func_info["complexity"]
                ))
            
            # Generate combined SPL
            if combined_spl_parts:
                combined_spl = " | ".join(combined_spl_parts)
            else:
                combined_spl = "# No statistical functions detected"
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return StatisticalFunctionResponse(
                detected_functions=function_infos,
                function_count=len(function_infos),
                categories=list(categories),
                combined_spl=combined_spl,
                validation_errors=validation_errors,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Statistical function analysis failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Statistical function analysis failed: {str(e)}"
            )


@router.get("/statistical/catalog", response_model=StatisticalFunctionCatalogResponse, tags=["Statistical Functions"])
async def get_statistical_function_catalog() -> StatisticalFunctionCatalogResponse:
    """
    Get comprehensive catalog of available statistical functions
    
    Retrieve detailed information about all supported statistical functions
    organized by category including descriptions, parameters, and examples.
    """
    try:
        logger.info("Getting statistical function catalog")
        
        # Descriptive statistics
        descriptive_statistics = {
            "mean": {
                "description": "Calculate the arithmetic mean (average) of values",
                "parameters": [],
                "examples": ["mean of response_time", "average cpu usage"],
                "spl_function": "avg",
                "complexity": "simple"
            },
            "median": {
                "description": "Calculate the median (middle value) of values",
                "parameters": [],
                "examples": ["median of scores", "median response time"],
                "spl_function": "median",
                "complexity": "simple"
            },
            "mode": {
                "description": "Find the most frequently occurring value",
                "parameters": [],
                "examples": ["mode of status codes", "most common error type"],
                "spl_function": "mode",
                "complexity": "intermediate"
            },
            "standard_deviation": {
                "description": "Calculate the standard deviation of values",
                "parameters": [],
                "examples": ["standard deviation of latency", "stdev of temperatures"],
                "spl_function": "stdev",
                "complexity": "simple"
            },
            "variance": {
                "description": "Calculate the variance of values",
                "parameters": [],
                "examples": ["variance of measurements", "var of response times"],
                "spl_function": "var",
                "complexity": "simple"
            },
            "range": {
                "description": "Calculate the range (max - min) of values",
                "parameters": [],
                "examples": ["range of temperatures", "range of scores"],
                "spl_function": "range",
                "complexity": "simple"
            },
            "percentile": {
                "description": "Calculate the nth percentile of values",
                "parameters": ["percentile_value"],
                "examples": ["95th percentile", "perc90(response_time)"],
                "spl_function": "perc",
                "complexity": "intermediate"
            },
            "quartile": {
                "description": "Calculate quartiles of values",
                "parameters": ["quartile_number"],
                "examples": ["first quartile", "third quartile"],
                "spl_function": "perc25/perc75",
                "complexity": "intermediate"
            },
            "iqr": {
                "description": "Calculate the interquartile range (Q3 - Q1)",
                "parameters": [],
                "examples": ["interquartile range of scores", "iqr of response times"],
                "spl_function": "perc75 - perc25",
                "complexity": "intermediate"
            },
            "skewness": {
                "description": "Calculate the skewness (asymmetry) of distribution",
                "parameters": [],
                "examples": ["skewness of response times", "distribution asymmetry"],
                "spl_function": "custom calculation",
                "complexity": "advanced"
            },
            "kurtosis": {
                "description": "Calculate the kurtosis (tail heaviness) of distribution",
                "parameters": [],
                "examples": ["kurtosis of error rates", "distribution tail analysis"],
                "spl_function": "custom calculation",
                "complexity": "advanced"
            }
        }
        
        # Inferential statistics
        inferential_statistics = {
            "confidence_interval": {
                "description": "Calculate confidence interval for mean",
                "parameters": ["confidence_level"],
                "examples": ["95% confidence interval", "confidence interval for mean"],
                "spl_function": "custom calculation",
                "complexity": "advanced"
            },
            "sample_size": {
                "description": "Calculate required sample size for analysis",
                "parameters": ["confidence_level", "margin_of_error"],
                "examples": ["sample size for 95% confidence", "required sample size"],
                "spl_function": "custom calculation",
                "complexity": "advanced"
            },
            "bootstrap": {
                "description": "Bootstrap sampling for statistical inference",
                "parameters": ["sample_size", "iterations"],
                "examples": ["bootstrap confidence interval", "bootstrap sampling"],
                "spl_function": "custom calculation",
                "complexity": "advanced"
            }
        }
        
        # Time series analysis
        time_series_analysis = {
            "moving_average": {
                "description": "Calculate moving average over a window",
                "parameters": ["window_size"],
                "examples": ["5-day moving average", "rolling average"],
                "spl_function": "streamstats avg",
                "complexity": "intermediate"
            },
            "trend": {
                "description": "Analyze trend direction and magnitude",
                "parameters": ["method"],
                "examples": ["linear trend", "trend analysis"],
                "spl_function": "custom calculation",
                "complexity": "advanced"
            },
            "seasonality": {
                "description": "Detect seasonal patterns in time series",
                "parameters": ["period"],
                "examples": ["seasonal patterns", "cyclical behavior"],
                "spl_function": "custom calculation",
                "complexity": "advanced"
            },
            "exponential_smoothing": {
                "description": "Apply exponential smoothing to time series",
                "parameters": ["smoothing_factor"],
                "examples": ["exponential smoothing", "smoothed values"],
                "spl_function": "custom calculation",
                "complexity": "advanced"
            }
        }
        
        # Regression analysis
        regression_analysis = {
            "linear_regression": {
                "description": "Perform linear regression analysis",
                "parameters": ["dependent_var", "independent_var"],
                "examples": ["linear regression", "predict y from x"],
                "spl_function": "custom calculation",
                "complexity": "advanced"
            },
            "polynomial_regression": {
                "description": "Perform polynomial regression analysis",
                "parameters": ["dependent_var", "independent_var", "degree"],
                "examples": ["polynomial regression", "quadratic fit"],
                "spl_function": "custom calculation",
                "complexity": "advanced"
            }
        }
        
        # Distribution analysis
        distribution_analysis = {
            "normal_distribution": {
                "description": "Test for normal distribution",
                "parameters": ["significance_level"],
                "examples": ["test for normality", "normal distribution test"],
                "spl_function": "custom calculation",
                "complexity": "advanced"
            },
            "poisson_distribution": {
                "description": "Test for Poisson distribution",
                "parameters": ["lambda"],
                "examples": ["Poisson distribution test", "event rate analysis"],
                "spl_function": "custom calculation",
                "complexity": "advanced"
            }
        }
        
        # Outlier detection
        outlier_detection = {
            "outliers": {
                "description": "Detect outliers using statistical methods",
                "parameters": ["method", "threshold"],
                "examples": ["detect outliers", "outlier analysis"],
                "spl_function": "custom calculation",
                "complexity": "intermediate"
            },
            "anomalies": {
                "description": "Detect anomalies in data patterns",
                "parameters": ["method", "sensitivity"],
                "examples": ["anomaly detection", "unusual patterns"],
                "spl_function": "custom calculation",
                "complexity": "advanced"
            },
            "z_score": {
                "description": "Calculate z-score (standard score) of values",
                "parameters": [],
                "examples": ["z-score analysis", "standardized values"],
                "spl_function": "custom calculation",
                "complexity": "intermediate"
            }
        }
        
        # Correlation analysis
        correlation_analysis = {
            "correlation": {
                "description": "Calculate correlation coefficient between variables",
                "parameters": ["variable1", "variable2"],
                "examples": ["correlation between x and y", "Pearson correlation"],
                "spl_function": "custom calculation",
                "complexity": "intermediate"
            },
            "covariance": {
                "description": "Calculate covariance between variables",
                "parameters": ["variable1", "variable2"],
                "examples": ["covariance between x and y", "variable relationship"],
                "spl_function": "custom calculation",
                "complexity": "intermediate"
            }
        }
        
        # Hypothesis testing
        hypothesis_testing = {
            "t_test": {
                "description": "Perform t-test for means",
                "parameters": ["sample1", "sample2", "alpha"],
                "examples": ["t-test for means", "compare two groups"],
                "spl_function": "custom calculation",
                "complexity": "advanced"
            },
            "chi_square": {
                "description": "Perform chi-square test",
                "parameters": ["observed", "expected"],
                "examples": ["chi-square test", "goodness of fit"],
                "spl_function": "custom calculation",
                "complexity": "advanced"
            },
            "anova": {
                "description": "Perform analysis of variance",
                "parameters": ["groups", "alpha"],
                "examples": ["ANOVA test", "compare multiple groups"],
                "spl_function": "custom calculation",
                "complexity": "advanced"
            }
        }
        
        return StatisticalFunctionCatalogResponse(
            descriptive_statistics=descriptive_statistics,
            inferential_statistics=inferential_statistics,
            time_series_analysis=time_series_analysis,
            regression_analysis=regression_analysis,
            distribution_analysis=distribution_analysis,
            outlier_detection=outlier_detection,
            correlation_analysis=correlation_analysis,
            hypothesis_testing=hypothesis_testing
        )
        
    except Exception as e:
        logger.error(f"Failed to get statistical function catalog: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve statistical function catalog: {str(e)}"
        )


@router.post("/statistical/suggestions", response_model=StatisticalFunctionSuggestionsResponse, tags=["Statistical Functions"])
async def get_statistical_function_suggestions(request: StatisticalFunctionSuggestionsRequest) -> StatisticalFunctionSuggestionsResponse:
    """
    Get statistical function suggestions based on partial query
    
    Analyze a partial query to suggest relevant statistical functions
    with confidence scores and category breakdown.
    """
    with LogContext(endpoint="get_statistical_suggestions", query_length=len(request.partial_query)):
        try:
            logger.info("Getting statistical function suggestions", query=request.partial_query[:100])
            
            # Get suggestions from mapper
            suggestions = statistical_function_mapper.get_statistical_function_suggestions(request.partial_query)
            
            # Apply limit
            limited_suggestions = suggestions[:request.limit]
            
            # Convert to response format
            suggestion_list = []
            category_breakdown = {}
            
            for natural_func, score in limited_suggestions:
                # Get function info
                if natural_func in statistical_function_mapper.function_mappings:
                    stat_func = statistical_function_mapper.function_mappings[natural_func]
                    category = statistical_function_mapper.category_mappings.get(stat_func, StatisticalCategory.DESCRIPTIVE)
                    
                    # Apply category filter if specified
                    if request.category_filter and category.value != request.category_filter:
                        continue
                    
                    # Count category
                    category_breakdown[category.value] = category_breakdown.get(category.value, 0) + 1
                    
                    suggestion_list.append({
                        "function": natural_func,
                        "statistical_function": stat_func.value,
                        "category": category.value,
                        "score": score,
                        "description": statistical_function_mapper._get_function_description(stat_func),
                        "complexity": statistical_function_mapper._get_function_complexity(stat_func)
                    })
            
            return StatisticalFunctionSuggestionsResponse(
                suggestions=suggestion_list,
                total_suggestions=len(suggestion_list),
                category_breakdown=category_breakdown
            )
            
        except Exception as e:
            logger.error(f"Failed to get statistical function suggestions: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get statistical function suggestions: {str(e)}"
            )