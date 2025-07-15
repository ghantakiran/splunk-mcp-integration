"""
NLP Service for natural language processing and SPL translation
"""

import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import re
import json

from .providers import AIRequest, AIResponse, ai_manager
from .spl_mapping import spl_mapper, SPLCommand, FieldMapping, IntentPattern
from .query_constructor import query_constructor, ComplexQuery, QueryComplexity
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
    optimization_suggestions: Optional[List[str]] = None
    syntax_valid: bool = True
    syntax_errors: Optional[List[str]] = None
    command_suggestions: Optional[List[Tuple[str, float]]] = None
    complex_query: Optional[ComplexQuery] = None
    query_complexity: Optional[QueryComplexity] = None
    performance_analysis: Optional[Dict[str, Any]] = None


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
        """Translate natural language query to SPL using comprehensive mapping and complex query construction"""
        start_time = time.time()
        
        try:
            # Pre-process with SPL mapping system
            command_suggestions = spl_mapper.get_command_suggestions(request.natural_query)
            
            # Extract entities and intents using mapping
            entities = self._extract_entities_with_mapping(request.natural_query)
            intent_result = await self.classify_intent(request.natural_query)
            
            # Use complex query constructor for advanced queries
            complex_query = query_constructor.construct_complex_query(
                natural_query=request.natural_query,
                context=request.context
            )
            
            # Get performance analysis
            performance_analysis = query_constructor.analyze_query_performance(complex_query)
            
            # Generate SPL template if intent matches
            spl_template = ""
            if intent_result.primary_intent:
                spl_template = spl_mapper.generate_spl_template(
                    intent_result.primary_intent, 
                    entities
                )
            
            # Prepare enhanced context for AI with mapping information
            context_info = ""
            if request.context:
                context_info = f"\nContext: {json.dumps(request.context, indent=2)}"
            
            conversation_context = ""
            if request.conversation_history:
                conversation_context = "\nConversation History:\n"
                for msg in request.conversation_history[-5:]:  # Last 5 messages
                    conversation_context += f"- {msg.get('role', 'user')}: {msg.get('content', '')}\n"
            
            # Add SPL mapping context with complex query analysis
            mapping_context = f"""
SPL Mapping Analysis:
- Detected Intent: {intent_result.primary_intent} (confidence: {intent_result.confidence_score:.2f})
- Extracted Entities: {json.dumps(entities, indent=2)}
- Suggested Commands: {[cmd for cmd, score in command_suggestions[:3]]}
- Template Suggestion: {spl_template}

Complex Query Analysis:
- Query Complexity: {complex_query.complexity.value}
- Performance Score: {performance_analysis['complexity_score']}
- Estimated Cost: {performance_analysis['estimated_cost']}
- Generated SPL: {complex_query.to_spl()}
- Optimization Suggestions: {performance_analysis['optimization_suggestions'][:3]}
"""
            
            # Enhanced prompt with mapping knowledge
            enhanced_prompt = self.spl_translation_prompt + f"""

## SPL Command Mapping Knowledge:
{self._get_command_reference_text()}

## Field Mapping Knowledge:
{self._get_field_mapping_text()}

## Current Analysis:
{mapping_context}

Please use this mapping knowledge to generate accurate, optimized SPL queries."""
            
            # Build AI request
            ai_request = AIRequest(
                system_prompt=enhanced_prompt,
                messages=[{
                    "role": "user",
                    "content": f"{request.natural_query}{context_info}{conversation_context}"
                }],
                temperature=0.1,  # Low temperature for consistent results
                metadata={"task": "spl_translation_enhanced"}
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
                
                # Use complex query SPL if AI response is insufficient
                if not spl_query or confidence < 0.5:
                    spl_query = complex_query.to_spl()
                    confidence = max(confidence, 0.7)  # Boost confidence for complex constructor
                    explanation = f"Generated using complex query constructor. {explanation}"
                    
            except json.JSONDecodeError:
                # Fallback to complex query constructor
                spl_query = complex_query.to_spl()
                confidence = 0.8
                explanation = "Generated SPL query using complex query constructor and comprehensive mapping"
                suggestions = []
            
            # Validate and optimize SPL using mapping system
            syntax_valid, syntax_errors = spl_mapper.validate_spl_syntax(spl_query)
            optimized_query, optimization_suggestions = spl_mapper.optimize_spl_query(spl_query)
            
            # Update confidence based on validation
            if not syntax_valid:
                confidence *= 0.7  # Reduce confidence for invalid syntax
            
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
                optimization_suggestions=optimization_suggestions,
                syntax_valid=syntax_valid,
                syntax_errors=syntax_errors if not syntax_valid else None,
                command_suggestions=command_suggestions,
                complex_query=complex_query,
                query_complexity=complex_query.complexity,
                performance_analysis=performance_analysis,
                metadata={
                    "ai_provider": ai_response.provider,
                    "ai_model": ai_response.model,
                    "input_tokens": ai_response.input_tokens,
                    "output_tokens": ai_response.output_tokens,
                    "detected_intent": intent_result.primary_intent,
                    "extracted_entities": entities,
                    "template_used": spl_template if spl_template else None,
                    "complex_query_used": True,
                    "query_complexity": complex_query.complexity.value,
                    "performance_score": performance_analysis['complexity_score']
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
            self.logger.error(f"Enhanced SPL translation failed: {e}")
            raise
    
    def _extract_entities_with_mapping(self, query: str) -> Dict[str, Any]:
        """Extract entities using SPL mapping system"""
        entities = {}
        query_lower = query.lower()
        
        # Extract time references
        time_entities = []
        for time_expr, spl_time in spl_mapper.time_mappings.items():
            if time_expr in query_lower:
                time_entities.append({
                    "natural": time_expr,
                    "spl": spl_time
                })
        if time_entities:
            entities["time_range"] = time_entities
        
        # Extract field references
        field_entities = {}
        for field_key, field_mapping in spl_mapper.field_mappings.items():
            for natural_name in field_mapping.natural_names:
                if natural_name in query_lower:
                    field_entities[natural_name] = {
                        "splunk_field": field_mapping.splunk_field,
                        "field_type": field_mapping.field_type.value
                    }
        if field_entities:
            entities["fields"] = field_entities
        
        # Extract aggregation functions
        aggregations = []
        for natural_func, spl_func in spl_mapper.aggregation_mappings.items():
            if natural_func in query_lower:
                aggregations.append({
                    "natural": natural_func,
                    "spl": spl_func
                })
        if aggregations:
            entities["aggregations"] = aggregations
        
        # Extract operators
        operators = []
        for natural_op, spl_op in spl_mapper.operator_mappings.items():
            if natural_op in query_lower:
                operators.append({
                    "natural": natural_op,
                    "spl": spl_op
                })
        if operators:
            entities["operators"] = operators
        
        return entities
    
    def _get_command_reference_text(self) -> str:
        """Generate command reference text for AI prompt"""
        reference_text = "## Available SPL Commands:\n"
        
        for cmd_name, cmd in spl_mapper.commands.items():
            reference_text += f"- **{cmd_name}**: {cmd.description}\n"
            reference_text += f"  Syntax: {cmd.syntax}\n"
            if cmd.common_patterns:
                reference_text += f"  Common patterns: {', '.join(cmd.common_patterns[:3])}\n"
            reference_text += "\n"
        
        return reference_text
    
    def _get_field_mapping_text(self) -> str:
        """Generate field mapping text for AI prompt"""
        mapping_text = "## Common Field Mappings:\n"
        
        for field_key, mapping in spl_mapper.field_mappings.items():
            mapping_text += f"- **{mapping.splunk_field}**: {', '.join(mapping.natural_names)}\n"
            mapping_text += f"  Type: {mapping.field_type.value}\n"
            if mapping.common_values:
                mapping_text += f"  Common values: {', '.join(mapping.common_values[:5])}\n"
            mapping_text += "\n"
        
        return mapping_text
    
    async def classify_intent(self, query: str) -> IntentClassificationResult:
        """Classify the intent of a natural language query using enhanced mapping"""
        try:
            # Use SPL mapping intent patterns for enhanced classification
            pattern_scores = {}
            query_lower = query.lower()
            
            # Check SPL mapping patterns first
            for pattern in spl_mapper.intent_patterns:
                for regex_pattern in pattern.patterns:
                    if re.search(regex_pattern, query_lower):
                        if pattern.intent not in pattern_scores:
                            pattern_scores[pattern.intent] = 0
                        pattern_scores[pattern.intent] += 1 + pattern.confidence_boost
            
            # Quick keyword-based classification as fallback
            keyword_scores = {}
            for intent, keywords in self.intent_keywords.items():
                score = sum(1 for keyword in keywords if keyword in query_lower)
                if score > 0:
                    keyword_scores[intent] = score / len(keywords)
            
            # Combine pattern and keyword scores
            combined_scores = {}
            for intent, score in pattern_scores.items():
                combined_scores[intent] = score * 1.5  # Boost pattern matches
            
            for intent, score in keyword_scores.items():
                if intent in combined_scores:
                    combined_scores[intent] += score
                else:
                    combined_scores[intent] = score
            
            # AI-based classification for better accuracy
            ai_request = AIRequest(
                system_prompt=self.intent_classification_prompt + f"""
                
## Enhanced Intent Analysis:
Pattern matches found: {list(pattern_scores.keys())}
Keyword matches found: {list(keyword_scores.keys())}
Combined scores: {combined_scores}

Use this information to improve intent classification accuracy.""",
                messages=[{"role": "user", "content": query}],
                temperature=0.1,
                metadata={"task": "intent_classification_enhanced"}
            )
            
            ai_response = await ai_manager.generate_response(ai_request)
            
            try:
                response_data = json.loads(ai_response.content)
                primary_intent = response_data.get("primary_intent", "SEARCH_EVENTS")
                confidence = response_data.get("confidence", 0.5)
                secondary_intents = response_data.get("secondary_intents", [])
                
                # Boost confidence if patterns matched
                if primary_intent in pattern_scores:
                    confidence = min(1.0, confidence + 0.2)
                
            except json.JSONDecodeError:
                # Fallback to pattern/keyword-based classification
                if combined_scores:
                    primary_intent = max(combined_scores, key=combined_scores.get)
                    confidence = min(1.0, combined_scores[primary_intent] / 3.0)  # Normalize
                    secondary_intents = [(k, v/3.0) for k, v in combined_scores.items() if k != primary_intent]
                elif keyword_scores:
                    primary_intent = max(keyword_scores, key=keyword_scores.get)
                    confidence = keyword_scores[primary_intent]
                    secondary_intents = [(k, v) for k, v in keyword_scores.items() if k != primary_intent]
                else:
                    primary_intent = "SEARCH_EVENTS"
                    confidence = 0.3
                    secondary_intents = []
            
            # Extract entities for the detected intent
            entities = {}
            if primary_intent in pattern_scores:
                # Find the matching pattern and extract entities
                for pattern in spl_mapper.intent_patterns:
                    if pattern.intent == primary_intent:
                        for regex_pattern in pattern.patterns:
                            match = re.search(regex_pattern, query_lower)
                            if match:
                                if pattern.required_entities:
                                    for i, entity in enumerate(pattern.required_entities):
                                        if i < len(match.groups()):
                                            entities[entity] = match.group(i + 1)
                                break
            
            return IntentClassificationResult(
                primary_intent=primary_intent,
                confidence_score=confidence,
                secondary_intents=secondary_intents[:5],  # Limit to top 5
                entities=entities if entities else None
            )
            
        except Exception as e:
            self.logger.error(f"Enhanced intent classification failed: {e}")
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
    
    async def construct_complex_query(self, request: SPLTranslationRequest) -> Dict[str, Any]:
        """Construct complex SPL query using advanced query constructor"""
        try:
            start_time = time.time()
            
            # Build complex query
            complex_query = query_constructor.construct_complex_query(
                natural_query=request.natural_query,
                context=request.context
            )
            
            # Get performance analysis
            performance_analysis = query_constructor.analyze_query_performance(complex_query)
            
            # Generate SPL
            spl_query = complex_query.to_spl()
            
            # Validate syntax
            syntax_valid, syntax_errors = spl_mapper.validate_spl_syntax(spl_query)
            
            processing_time = time.time() - start_time
            
            return {
                "spl_query": spl_query,
                "complex_query": complex_query,
                "query_complexity": complex_query.complexity.value,
                "performance_analysis": performance_analysis,
                "syntax_valid": syntax_valid,
                "syntax_errors": syntax_errors if not syntax_valid else None,
                "processing_time": processing_time,
                "metadata": {
                    "pipeline_components": len(complex_query.main_pipeline.transformations) + len(complex_query.main_pipeline.aggregations),
                    "has_subqueries": len(complex_query.subqueries) > 0,
                    "has_joins": len(complex_query.joins) > 0,
                    "has_unions": len(complex_query.unions) > 0,
                    "estimated_cost": performance_analysis['estimated_cost'],
                    "optimization_suggestions": performance_analysis['optimization_suggestions'],
                    "performance_warnings": performance_analysis['performance_warnings']
                }
            }
            
        except Exception as e:
            self.logger.error(f"Complex query construction failed: {e}")
            return {
                "spl_query": f"search {request.natural_query[:50]}",
                "error": str(e),
                "processing_time": time.time() - start_time
            }

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