"""
NLP Service for natural language processing and SPL translation
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import re
import json

from .providers import AIRequest, AIResponse, ai_manager
from ..core.config import settings
from ..core.logging import get_logger, NLPMetrics

logger = get_logger(__name__)
nlp_metrics = NLPMetrics(logger)


@dataclass
class SPLTranslationRequest:
    """Request for SPL translation"""
    natural_query: str
    context: Optional[Dict[str, Any]] = None
    user_preferences: Optional[Dict[str, Any]] = None
    conversation_history: Optional[List[Dict[str, str]]] = None


@dataclass
class SPLTranslationResponse:
    """Response from SPL translation"""
    spl_query: str
    confidence_score: float
    explanation: Optional[str] = None
    suggested_improvements: Optional[List[str]] = None
    alternative_queries: Optional[List[str]] = None
    processing_time: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class IntentClassificationResult:
    """Result from intent classification"""
    primary_intent: str
    confidence_score: float
    secondary_intents: Optional[List[Tuple[str, float]]] = None
    entities: Optional[Dict[str, List[str]]] = None


@dataclass
class EntityExtractionResult:
    """Result from entity extraction"""
    entities: Dict[str, List[str]]
    entity_types: Dict[str, str]
    confidence_scores: Dict[str, float]


class NLPService:
    """Core NLP service for natural language processing"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.metrics = NLPMetrics(self.logger)
        
        # Load prompts and configurations
        self._load_prompts()
        self._load_entity_patterns()
        self._load_intent_patterns()
    
    def _load_prompts(self):
        """Load system prompts for different NLP tasks"""
        self.spl_translation_prompt = """
You are an expert Splunk SPL (Search Processing Language) translator. Your job is to convert natural language queries into accurate, efficient SPL searches.

## Guidelines:
1. Generate syntactically correct SPL that follows best practices
2. Use appropriate search commands, functions, and operators
3. Include proper field names, time ranges, and filters
4. Optimize for performance when possible
5. Provide clear explanations for complex queries
6. Consider security and data access permissions

## SPL Commands Reference:
- search: Basic search functionality
- stats: Statistical calculations
- eval: Field calculations and transformations
- where: Filtering results
- sort: Ordering results
- dedup: Remove duplicates
- rex: Regular expression field extraction
- lookup: External data correlation
- join: Combining searches
- timechart: Time-based visualization
- chart: Data visualization
- transaction: Event correlation

## Common Patterns:
- Time ranges: earliest=-24h@h latest=now
- Field searches: field_name="value" OR field_name=value
- Wildcards: field_name="prefix*" OR field_name=*suffix*
- Boolean logic: (condition1 AND condition2) OR condition3
- Statistical functions: count, sum, avg, min, max, values, list

## Response Format:
Generate a JSON response with:
- "spl_query": The SPL search string
- "confidence": Confidence score (0.0-1.0)
- "explanation": Brief explanation of the query
- "suggestions": List of potential improvements or alternatives

Convert the following natural language query to SPL:
"""
        
        self.intent_classification_prompt = """
You are an expert at classifying user intents for Splunk search queries. Analyze the user's natural language input and classify it into one of these intent categories:

## Intent Categories:
1. SEARCH_EVENTS: Looking for specific events or logs
2. AGGREGATE_DATA: Calculating statistics, counts, sums, averages
3. FILTER_DATA: Filtering or narrowing down results
4. VISUALIZE_DATA: Creating charts, graphs, or visual representations
5. CORRELATE_EVENTS: Finding relationships between events
6. MONITOR_ALERTS: Setting up monitoring or alerting
7. INVESTIGATE_ISSUE: Troubleshooting or investigating problems
8. EXTRACT_FIELDS: Extracting or parsing specific fields
9. COMPARE_METRICS: Comparing values across time or categories
10. EXPORT_DATA: Extracting or exporting search results

## Response Format:
Return a JSON object with:
- "primary_intent": Main intent category
- "confidence": Confidence score (0.0-1.0)
- "secondary_intents": List of other possible intents with scores
- "reasoning": Brief explanation of the classification

Classify this query:
"""
        
        self.entity_extraction_prompt = """
You are an expert at extracting Splunk-specific entities from natural language queries. Identify and extract relevant entities that would be useful for constructing SPL searches.

## Entity Types:
1. TIME_RANGE: Time specifications (last hour, yesterday, etc.)
2. INDEX: Splunk index names
3. SOURCETYPE: Data source types
4. HOST: Server or host names
5. FIELD_NAME: Specific field names
6. FIELD_VALUE: Values to search for
7. USER_NAME: User identifiers
8. IP_ADDRESS: IP addresses or networks
9. APPLICATION: Application names
10. LOG_LEVEL: Error levels (error, warning, info, etc.)
11. EVENT_TYPE: Types of events or activities
12. THRESHOLD: Numeric thresholds or limits

## Response Format:
Return a JSON object with:
- "entities": Dictionary of entity_type -> [list of values]
- "entity_types": Dictionary of entity -> entity_type
- "confidence_scores": Dictionary of entity -> confidence score

Extract entities from this query:
"""
    
    def _load_entity_patterns(self):
        """Load regex patterns for entity extraction"""
        self.entity_patterns = {
            "TIME_RANGE": [
                r"\b(last|past)\s+(\d+)\s+(minute|hour|day|week|month)s?\b",
                r"\b(today|yesterday|this\s+week|last\s+week)\b",
                r"\b(\d{1,2}\/\d{1,2}\/\d{4})\b",
                r"\bfrom\s+(.+?)\s+to\s+(.+?)\b"
            ],
            "IP_ADDRESS": [
                r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
                r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"
            ],
            "LOG_LEVEL": [
                r"\b(error|warn|warning|info|debug|trace|fatal|critical)\b"
            ],
            "USER_NAME": [
                r"\buser[:\s]+([a-zA-Z0-9_.-]+)\b",
                r"\busername[:\s]+([a-zA-Z0-9_.-]+)\b"
            ],
            "THRESHOLD": [
                r"\b(more|less|greater|above|below|over|under)\s+than\s+(\d+)\b",
                r"\b(\d+)\s+(or\s+)?(more|less|greater|above|below|over|under)\b"
            ]
        }
    
    def _load_intent_patterns(self):
        """Load keyword patterns for intent classification"""
        self.intent_keywords = {
            "SEARCH_EVENTS": ["find", "search", "show", "list", "get", "events", "logs"],
            "AGGREGATE_DATA": ["count", "sum", "average", "total", "statistics", "stats", "calculate"],
            "FILTER_DATA": ["filter", "where", "only", "exclude", "include", "contains"],
            "VISUALIZE_DATA": ["chart", "graph", "plot", "visualize", "dashboard", "report"],
            "CORRELATE_EVENTS": ["correlate", "relationship", "connection", "related", "linked"],
            "MONITOR_ALERTS": ["alert", "monitor", "watch", "notify", "threshold", "trigger"],
            "INVESTIGATE_ISSUE": ["investigate", "troubleshoot", "debug", "problem", "issue", "error"],
            "EXTRACT_FIELDS": ["extract", "parse", "field", "column", "attribute"],
            "COMPARE_METRICS": ["compare", "versus", "vs", "difference", "trend", "change"],
            "EXPORT_DATA": ["export", "download", "save", "extract", "output"]
        }
    
    async def translate_to_spl(self, request: SPLTranslationRequest) -> SPLTranslationResponse:
        """Translate natural language query to SPL"""
        start_time = time.time()
        
        try:
            # Prepare context for AI
            context_info = ""
            if request.context:
                context_info = f"\nContext: {json.dumps(request.context, indent=2)}"
            
            conversation_context = ""
            if request.conversation_history:
                conversation_context = "\nConversation History:\n"
                for msg in request.conversation_history[-5:]:  # Last 5 messages
                    conversation_context += f"- {msg.get('role', 'user')}: {msg.get('content', '')}\n"
            
            # Build AI request
            ai_request = AIRequest(
                system_prompt=self.spl_translation_prompt,
                messages=[{
                    "role": "user",
                    "content": f"{request.natural_query}{context_info}{conversation_context}"
                }],
                temperature=0.1,  # Low temperature for consistent results
                metadata={"task": "spl_translation"}
            )
            
            # Get AI response
            ai_response = await ai_manager.generate_response(ai_request)
            
            # Parse response
            try:
                response_data = json.loads(ai_response.content)
                spl_query = response_data.get("spl_query", "")
                confidence = response_data.get("confidence", 0.0)
                explanation = response_data.get("explanation", "")
                suggestions = response_data.get("suggestions", [])
            except json.JSONDecodeError:
                # Fallback: treat entire response as SPL query
                spl_query = ai_response.content.strip()
                confidence = 0.8
                explanation = "Generated SPL query"
                suggestions = []
            
            processing_time = time.time() - start_time
            
            # Log metrics
            self.metrics.log_spl_translation(
                natural_query=request.natural_query,
                generated_spl=spl_query,
                confidence_score=confidence,
                processing_time=processing_time,
                success=True
            )
            
            return SPLTranslationResponse(
                spl_query=spl_query,
                confidence_score=confidence,
                explanation=explanation,
                suggested_improvements=suggestions,
                processing_time=processing_time,
                metadata={
                    "ai_provider": ai_response.provider,
                    "ai_model": ai_response.model,
                    "input_tokens": ai_response.input_tokens,
                    "output_tokens": ai_response.output_tokens
                }
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.metrics.log_spl_translation(
                natural_query=request.natural_query,
                processing_time=processing_time,
                success=False,
                error=str(e)
            )
            self.logger.error(f"SPL translation failed: {e}")
            raise
    
    async def classify_intent(self, query: str) -> IntentClassificationResult:
        """Classify the intent of a natural language query"""
        try:
            # Quick keyword-based classification
            keyword_scores = {}
            query_lower = query.lower()
            
            for intent, keywords in self.intent_keywords.items():
                score = sum(1 for keyword in keywords if keyword in query_lower)
                if score > 0:
                    keyword_scores[intent] = score / len(keywords)
            
            # AI-based classification for better accuracy
            ai_request = AIRequest(
                system_prompt=self.intent_classification_prompt,
                messages=[{"role": "user", "content": query}],
                temperature=0.1,
                metadata={"task": "intent_classification"}
            )
            
            ai_response = await ai_manager.generate_response(ai_request)
            
            try:
                response_data = json.loads(ai_response.content)
                primary_intent = response_data.get("primary_intent", "SEARCH_EVENTS")
                confidence = response_data.get("confidence", 0.5)
                secondary_intents = response_data.get("secondary_intents", [])
            except json.JSONDecodeError:
                # Fallback to keyword-based classification
                if keyword_scores:
                    primary_intent = max(keyword_scores, key=keyword_scores.get)
                    confidence = keyword_scores[primary_intent]
                    secondary_intents = [(k, v) for k, v in keyword_scores.items() if k != primary_intent]
                else:
                    primary_intent = "SEARCH_EVENTS"
                    confidence = 0.3
                    secondary_intents = []
            
            return IntentClassificationResult(
                primary_intent=primary_intent,
                confidence_score=confidence,
                secondary_intents=secondary_intents
            )
            
        except Exception as e:
            self.logger.error(f"Intent classification failed: {e}")
            return IntentClassificationResult(
                primary_intent="SEARCH_EVENTS",
                confidence_score=0.1
            )
    
    async def extract_entities(self, query: str) -> EntityExtractionResult:
        """Extract entities from natural language query"""
        try:
            # Pattern-based extraction
            pattern_entities = {}
            entity_types = {}
            confidence_scores = {}
            
            for entity_type, patterns in self.entity_patterns.items():
                for pattern in patterns:
                    matches = re.findall(pattern, query, re.IGNORECASE)
                    if matches:
                        if entity_type not in pattern_entities:
                            pattern_entities[entity_type] = []
                        
                        for match in matches:
                            if isinstance(match, tuple):
                                for item in match:
                                    if item.strip():
                                        pattern_entities[entity_type].append(item.strip())
                                        entity_types[item.strip()] = entity_type
                                        confidence_scores[item.strip()] = 0.8
                            else:
                                pattern_entities[entity_type].append(match.strip())
                                entity_types[match.strip()] = entity_type
                                confidence_scores[match.strip()] = 0.8
            
            # AI-based extraction for additional entities
            ai_request = AIRequest(
                system_prompt=self.entity_extraction_prompt,
                messages=[{"role": "user", "content": query}],
                temperature=0.1,
                metadata={"task": "entity_extraction"}
            )
            
            ai_response = await ai_manager.generate_response(ai_request)
            
            try:
                response_data = json.loads(ai_response.content)
                ai_entities = response_data.get("entities", {})
                ai_entity_types = response_data.get("entity_types", {})
                ai_confidence_scores = response_data.get("confidence_scores", {})
                
                # Merge AI results with pattern results
                for entity_type, values in ai_entities.items():
                    if entity_type not in pattern_entities:
                        pattern_entities[entity_type] = []
                    for value in values:
                        if value not in pattern_entities[entity_type]:
                            pattern_entities[entity_type].append(value)
                
                entity_types.update(ai_entity_types)
                confidence_scores.update(ai_confidence_scores)
                
            except json.JSONDecodeError:
                self.logger.warning("Failed to parse AI entity extraction response")
            
            return EntityExtractionResult(
                entities=pattern_entities,
                entity_types=entity_types,
                confidence_scores=confidence_scores
            )
            
        except Exception as e:
            self.logger.error(f"Entity extraction failed: {e}")
            return EntityExtractionResult(
                entities={},
                entity_types={},
                confidence_scores={}
            )
    
    async def enhance_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Enhance query with intent classification and entity extraction"""
        try:
            # Run classification and extraction in parallel
            intent_result = await self.classify_intent(query)
            entity_result = await self.extract_entities(query)
            
            return {
                "original_query": query,
                "intent": {
                    "primary": intent_result.primary_intent,
                    "confidence": intent_result.confidence_score,
                    "secondary": intent_result.secondary_intents
                },
                "entities": {
                    "extracted": entity_result.entities,
                    "types": entity_result.entity_types,
                    "confidence": entity_result.confidence_scores
                },
                "context": context or {}
            }
            
        except Exception as e:
            self.logger.error(f"Query enhancement failed: {e}")
            return {
                "original_query": query,
                "intent": {"primary": "SEARCH_EVENTS", "confidence": 0.1},
                "entities": {"extracted": {}, "types": {}, "confidence": {}},
                "context": context or {}
            }


# Global NLP service instance
nlp_service = NLPService()