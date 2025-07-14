"""
Context service for enhanced query processing with conversation awareness
"""

import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import re

from .conversation_manager import ConversationManager, ConversationContext, QueryContext, conversation_manager
from .memory_store import MemoryStore, memory_store
from ..ai import nlp_service, SPLTranslationRequest, SPLTranslationResponse
from ..core.logging import get_logger
from ..core.config import settings

logger = get_logger(__name__)


@dataclass
class ContextPreferences:
    """User preferences for context processing"""
    include_history: bool = True
    max_context_queries: int = 5
    prefer_recent_context: bool = True
    auto_resolve_references: bool = True
    context_sensitivity: str = "medium"  # low, medium, high
    
    # Response preferences
    include_explanations: bool = True
    show_context_used: bool = False
    suggest_follow_ups: bool = True


@dataclass
class ContextualResponse:
    """Enhanced response with context information"""
    spl_query: str
    confidence_score: float
    explanation: Optional[str] = None
    
    # Context information
    context_used: Dict[str, Any] = None
    resolved_references: Dict[str, str] = None
    assumptions_made: List[str] = None
    
    # Follow-up suggestions
    follow_up_suggestions: List[str] = None
    clarification_questions: List[str] = None
    
    # Metadata
    processing_time: Optional[float] = None
    context_confidence: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class ContextService:
    """Service for context-aware query processing"""
    
    def __init__(self, conversation_manager: ConversationManager, memory_store: MemoryStore):
        self.conversation_manager = conversation_manager
        self.memory_store = memory_store
        self.logger = get_logger(__name__)
        
        # Context processing configuration
        self.max_context_length = settings.max_context_length or 8192
        self.context_weight_decay = 0.8  # How much older context matters
        self.min_context_confidence = 0.3
        
        # Reference resolution patterns
        self._init_reference_patterns()
    
    def _init_reference_patterns(self):
        """Initialize patterns for resolving references"""
        self.reference_patterns = {
            # Demonstrative pronouns
            "this": r"\b(this|these)\s+(field|index|query|result|data|search)\b",
            "that": r"\b(that|those)\s+(field|index|query|result|data|search)\b",
            "it": r"\b(it|them)\b",
            
            # Temporal references
            "same": r"\bsame\s+(time|period|range|interval)\b",
            "previous": r"\b(previous|last|prior)\s+(query|search|result)\b",
            "similar": r"\bsimilar\s+(query|search|pattern)\b",
            
            # Field references
            "field_ref": r"\b(the|this|that)\s+field\b",
            "index_ref": r"\b(the|this|that)\s+index\b",
            
            # Continuation indicators
            "also": r"\b(also|additionally|furthermore|moreover)\b",
            "continue": r"\b(continue|keep|maintain)\s+(with|using|from)\b"
        }
    
    async def process_contextual_query(
        self,
        conversation_id: str,
        user_query: str,
        preferences: Optional[ContextPreferences] = None
    ) -> ContextualResponse:
        """Process a query with full context awareness"""
        start_time = datetime.utcnow()
        
        try:
            # Use default preferences if none provided
            if preferences is None:
                preferences = ContextPreferences()
            
            # Build query context
            query_context = await self.conversation_manager.build_query_context(
                conversation_id=conversation_id,
                user_query=user_query
            )
            
            # Enhance query with context
            enhanced_query, context_info = await self._enhance_query_with_context(
                query_context, preferences
            )
            
            # Detect and resolve references
            resolved_query, resolved_refs = await self._resolve_references(
                enhanced_query, query_context, preferences
            )
            
            # Create enhanced SPL translation request
            translation_request = SPLTranslationRequest(
                natural_query=resolved_query,
                context=context_info,
                conversation_history=await self._get_conversation_history(
                    conversation_id, preferences.max_context_queries
                )
            )
            
            # Get SPL translation
            translation_result = await nlp_service.translate_to_spl(translation_request)
            
            # Calculate context confidence
            context_confidence = self._calculate_context_confidence(
                query_context, context_info, resolved_refs
            )
            
            # Generate follow-up suggestions
            follow_ups = await self._generate_follow_up_suggestions(
                query_context, translation_result
            ) if preferences.suggest_follow_ups else []
            
            # Generate clarification questions if needed
            clarifications = await self._generate_clarification_questions(
                query_context, translation_result
            )
            
            # Store query result for future context
            await self.conversation_manager.store_query_result(
                query_context=query_context,
                spl_query=translation_result.spl_query,
                confidence=translation_result.confidence_score,
                execution_time=translation_result.processing_time,
                result_summary={
                    "enhanced_query": enhanced_query,
                    "resolved_references": resolved_refs,
                    "context_confidence": context_confidence
                }
            )
            
            # Build contextual response
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            response = ContextualResponse(
                spl_query=translation_result.spl_query,
                confidence_score=translation_result.confidence_score,
                explanation=translation_result.explanation,
                context_used=context_info if preferences.show_context_used else None,
                resolved_references=resolved_refs,
                assumptions_made=context_info.get("assumptions", []),
                follow_up_suggestions=follow_ups,
                clarification_questions=clarifications,
                processing_time=processing_time,
                context_confidence=context_confidence,
                metadata={
                    "original_query": user_query,
                    "enhanced_query": enhanced_query,
                    "resolved_query": resolved_query,
                    "context_sources": context_info.get("sources", [])
                }
            )
            
            self.logger.info(
                f"Processed contextual query with confidence {translation_result.confidence_score:.2f}, "
                f"context confidence {context_confidence:.2f}"
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to process contextual query: {e}")
            raise
    
    async def _enhance_query_with_context(
        self,
        query_context: QueryContext,
        preferences: ContextPreferences
    ) -> Tuple[str, Dict[str, Any]]:
        """Enhance query with relevant context information"""
        enhanced_query = query_context.original_query
        context_info = {
            "sources": [],
            "assumptions": [],
            "enhancements": []
        }
        
        try:
            # Add field context from previous queries
            if query_context.referenced_fields and preferences.include_history:
                common_fields = query_context.referenced_fields[:3]  # Top 3 fields
                if common_fields:
                    context_info["common_fields"] = common_fields
                    context_info["sources"].append("previous_queries")
                    
                    # Enhance query with field context if query seems incomplete
                    if self._query_needs_field_context(enhanced_query):
                        field_context = f" (considering fields: {', '.join(common_fields)})"
                        enhanced_query += field_context
                        context_info["enhancements"].append("added_field_context")
            
            # Add index context
            if query_context.referenced_indexes and preferences.include_history:
                common_indexes = query_context.referenced_indexes[:2]  # Top 2 indexes
                if common_indexes:
                    context_info["common_indexes"] = common_indexes
                    context_info["sources"].append("index_history")
                    
                    # Add index context if not specified
                    if not self._query_has_index_reference(enhanced_query):
                        index_context = f" from index {common_indexes[0]}"
                        enhanced_query += index_context
                        context_info["enhancements"].append("added_index_context")
            
            # Add temporal context
            if query_context.time_context:
                context_info["time_context"] = query_context.time_context
                context_info["sources"].append("temporal_context")
                
                # Resolve relative time references
                if query_context.relative_time_references:
                    enhanced_query = self._resolve_temporal_references(enhanced_query)
                    context_info["enhancements"].append("resolved_temporal_references")
            
            # Add conversation topic context
            if query_context.conversation_topic:
                context_info["topic"] = query_context.conversation_topic
                context_info["sources"].append("conversation_topic")
            
            # Add recent query patterns
            if query_context.previous_queries and preferences.include_history:
                patterns = self._extract_query_patterns(query_context.previous_queries)
                if patterns:
                    context_info["query_patterns"] = patterns
                    context_info["sources"].append("query_patterns")
            
            return enhanced_query, context_info
            
        except Exception as e:
            self.logger.error(f"Failed to enhance query with context: {e}")
            return query_context.original_query, context_info
    
    async def _resolve_references(
        self,
        query: str,
        query_context: QueryContext,
        preferences: ContextPreferences
    ) -> Tuple[str, Dict[str, str]]:
        """Resolve pronouns and references in the query"""
        if not preferences.auto_resolve_references:
            return query, {}
        
        resolved_query = query
        resolved_refs = {}
        
        try:
            # Resolve "this/that field" references
            if re.search(self.reference_patterns["field_ref"], query, re.IGNORECASE):
                if query_context.referenced_fields:
                    last_field = query_context.referenced_fields[0]
                    resolved_query = re.sub(
                        self.reference_patterns["field_ref"],
                        f"the {last_field} field",
                        resolved_query,
                        flags=re.IGNORECASE
                    )
                    resolved_refs["field_reference"] = last_field
            
            # Resolve "this/that index" references
            if re.search(self.reference_patterns["index_ref"], query, re.IGNORECASE):
                if query_context.referenced_indexes:
                    last_index = query_context.referenced_indexes[0]
                    resolved_query = re.sub(
                        self.reference_patterns["index_ref"],
                        f"the {last_index} index",
                        resolved_query,
                        flags=re.IGNORECASE
                    )
                    resolved_refs["index_reference"] = last_index
            
            # Resolve "same time" references
            if re.search(self.reference_patterns["same"], query, re.IGNORECASE):
                if query_context.time_context:
                    time_ref = query_context.time_context.get("conversation_time_range")
                    if time_ref:
                        resolved_query = re.sub(
                            self.reference_patterns["same"],
                            f"same time period (last used: {time_ref})",
                            resolved_query,
                            flags=re.IGNORECASE
                        )
                        resolved_refs["time_reference"] = str(time_ref)
            
            # Resolve "previous query" references
            if re.search(self.reference_patterns["previous"], query, re.IGNORECASE):
                if query_context.previous_queries:
                    last_query = query_context.previous_queries[0]
                    resolved_refs["previous_query"] = last_query
            
            return resolved_query, resolved_refs
            
        except Exception as e:
            self.logger.error(f"Failed to resolve references: {e}")
            return query, {}
    
    async def _get_conversation_history(
        self,
        conversation_id: str,
        max_queries: int
    ) -> List[Dict[str, str]]:
        """Get conversation history for context"""
        try:
            recent_queries = await self.memory_store.get_recent_queries(
                conversation_id=conversation_id,
                limit=max_queries
            )
            
            history = []
            for query in recent_queries:
                history.append({
                    "role": "user",
                    "content": query.original_query
                })
                history.append({
                    "role": "assistant", 
                    "content": f"Generated SPL: {query.spl_query}"
                })
            
            return history
            
        except Exception as e:
            self.logger.error(f"Failed to get conversation history: {e}")
            return []
    
    def _calculate_context_confidence(
        self,
        query_context: QueryContext,
        context_info: Dict[str, Any],
        resolved_refs: Dict[str, str]
    ) -> float:
        """Calculate confidence in the context enhancement"""
        confidence = 0.0
        
        # Base confidence from query clarity
        if query_context.confidence:
            confidence += query_context.confidence * 0.3
        
        # Boost for resolved references
        if resolved_refs:
            confidence += min(len(resolved_refs) * 0.2, 0.4)
        
        # Boost for context sources
        sources = context_info.get("sources", [])
        confidence += min(len(sources) * 0.1, 0.3)
        
        # Boost for previous queries context
        if query_context.previous_queries:
            confidence += min(len(query_context.previous_queries) * 0.05, 0.2)
        
        return min(confidence, 1.0)
    
    async def _generate_follow_up_suggestions(
        self,
        query_context: QueryContext,
        translation_result: SPLTranslationResponse
    ) -> List[str]:
        """Generate follow-up query suggestions"""
        suggestions = []
        
        try:
            # Based on intent
            if query_context.intent == "SEARCH_EVENTS":
                suggestions.append("Would you like to see the count of these events?")
                suggestions.append("Should I create a chart showing trends over time?")
            elif query_context.intent == "AGGREGATE_DATA":
                suggestions.append("Would you like to break this down by another field?")
                suggestions.append("Should I show this data in a different chart type?")
            elif query_context.intent == "FILTER_DATA":
                suggestions.append("Would you like to add more filters?")
                suggestions.append("Should I show the unfiltered data for comparison?")
            
            # Based on confidence
            if translation_result.confidence_score < 0.7:
                suggestions.append("Can you provide more specific details about what you're looking for?")
            
            # Based on entities found
            if query_context.entities:
                if "TIME_RANGE" in query_context.entities:
                    suggestions.append("Would you like to compare this with a different time period?")
                if "FIELD_NAME" in query_context.entities:
                    suggestions.append("Should I analyze other related fields?")
            
            return suggestions[:3]  # Limit to 3 suggestions
            
        except Exception as e:
            self.logger.error(f"Failed to generate follow-up suggestions: {e}")
            return []
    
    async def _generate_clarification_questions(
        self,
        query_context: QueryContext,
        translation_result: SPLTranslationResponse
    ) -> List[str]:
        """Generate clarification questions if needed"""
        questions = []
        
        try:
            # Low confidence indicates need for clarification
            if translation_result.confidence_score < 0.5:
                questions.append("Could you rephrase your question to be more specific?")
            
            # Missing time context
            if not query_context.time_context and not query_context.relative_time_references:
                questions.append("What time range should I search in?")
            
            # Ambiguous entities
            if query_context.entities:
                if len(query_context.entities.get("FIELD_NAME", [])) > 3:
                    questions.append("Which specific field are you most interested in?")
            
            # No previous context but references found
            if not query_context.previous_queries and self._has_references(query_context.original_query):
                questions.append("This seems to reference previous context. Could you provide more details?")
            
            return questions[:2]  # Limit to 2 questions
            
        except Exception as e:
            self.logger.error(f"Failed to generate clarification questions: {e}")
            return []
    
    # Helper methods
    
    def _query_needs_field_context(self, query: str) -> bool:
        """Check if query would benefit from field context"""
        # Simple heuristics
        has_general_terms = any(term in query.lower() for term in [
            "show", "find", "get", "list", "data", "information"
        ])
        lacks_specificity = not any(term in query.lower() for term in [
            "field", "column", "attribute", "where", "from"
        ])
        return has_general_terms and lacks_specificity
    
    def _query_has_index_reference(self, query: str) -> bool:
        """Check if query already references an index"""
        return any(term in query.lower() for term in [
            "index", "from", "sourcetype", "source"
        ])
    
    def _resolve_temporal_references(self, query: str) -> str:
        """Resolve relative temporal references to absolute ones"""
        # This is a simplified implementation
        # In production, you'd want more sophisticated temporal resolution
        
        temporal_replacements = {
            r"\blast hour\b": "earliest=-1h@h latest=now",
            r"\blast day\b": "earliest=-1d@d latest=now", 
            r"\btoday\b": "earliest=@d latest=now",
            r"\byesterday\b": "earliest=-1d@d latest=-0d@d",
            r"\blast week\b": "earliest=-7d@d latest=now"
        }
        
        resolved_query = query
        for pattern, replacement in temporal_replacements.items():
            resolved_query = re.sub(pattern, replacement, resolved_query, flags=re.IGNORECASE)
        
        return resolved_query
    
    def _extract_query_patterns(self, previous_queries: List[str]) -> List[str]:
        """Extract common patterns from previous queries"""
        patterns = []
        
        # Simple pattern extraction (could be enhanced with ML)
        query_words = []
        for query in previous_queries:
            query_words.extend(query.lower().split())
        
        # Find most common words (excluding stop words)
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        word_freq = {}
        for word in query_words:
            if word not in stop_words and len(word) > 2:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top patterns
        common_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        patterns = [word for word, freq in common_words if freq > 1]
        
        return patterns
    
    def _has_references(self, query: str) -> bool:
        """Check if query contains reference words"""
        reference_words = ["this", "that", "it", "them", "same", "previous", "last", "also"]
        return any(word in query.lower() for word in reference_words)


# Global context service instance
context_service = ContextService(conversation_manager, memory_store)