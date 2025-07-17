"""
Intelligent Query Suggestions System for Splunk MCP Integration

This module provides intelligent query suggestions based on user behavior,
data patterns, and contextual analysis.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd
from collections import defaultdict, Counter
import re
import json
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class QuerySuggestion:
    """Data class for query suggestions."""
    query: str
    confidence: float
    category: str
    explanation: str
    spl_query: str
    estimated_results: int
    relevance_score: float
    context_tags: List[str]

class IntelligentSuggestionsEngine:
    """
    Intelligent query suggestions engine that provides contextual,
    personalized, and data-driven query recommendations.
    """
    
    def __init__(self):
        self.query_history = []
        self.user_patterns = {}
        self.common_queries = {}
        self.data_patterns = {}
        self.suggestion_templates = self._initialize_suggestion_templates()
        
    async def generate_suggestions(self, user_context: Dict[str, Any], 
                                 current_query: str = "",
                                 max_suggestions: int = 10) -> Dict[str, Any]:
        """
        Generate intelligent query suggestions based on context and history.
        
        Args:
            user_context: User context including history, preferences, and permissions
            current_query: Current partial query being typed
            max_suggestions: Maximum number of suggestions to return
            
        Returns:
            Dictionary containing suggested queries and metadata
        """
        try:
            suggestions = []
            
            # Generate different types of suggestions
            if current_query:
                # Auto-completion suggestions
                completion_suggestions = await self._generate_completion_suggestions(
                    current_query, user_context
                )
                suggestions.extend(completion_suggestions)
                
                # Related query suggestions
                related_suggestions = await self._generate_related_suggestions(
                    current_query, user_context
                )
                suggestions.extend(related_suggestions)
            
            # Historical suggestions
            history_suggestions = await self._generate_history_based_suggestions(
                user_context
            )
            suggestions.extend(history_suggestions)
            
            # Popular queries
            popular_suggestions = await self._generate_popular_suggestions(
                user_context
            )
            suggestions.extend(popular_suggestions)
            
            # Data-driven suggestions
            data_driven_suggestions = await self._generate_data_driven_suggestions(
                user_context
            )
            suggestions.extend(data_driven_suggestions)
            
            # Context-aware suggestions
            context_suggestions = await self._generate_context_aware_suggestions(
                user_context
            )
            suggestions.extend(context_suggestions)
            
            # Rank and filter suggestions
            ranked_suggestions = self._rank_suggestions(suggestions, user_context)
            
            # Apply diversity filter
            final_suggestions = self._apply_diversity_filter(
                ranked_suggestions, max_suggestions
            )
            
            return {
                "suggestions": [asdict(s) for s in final_suggestions],
                "total_suggestions": len(final_suggestions),
                "suggestion_categories": self._categorize_suggestions(final_suggestions),
                "confidence_distribution": self._calculate_confidence_distribution(final_suggestions),
                "generation_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            return {"error": f"Suggestion generation failed: {str(e)}"}
    
    async def learn_from_query(self, user_id: str, query: str, 
                             results_count: int, user_feedback: str = None) -> Dict[str, Any]:
        """
        Learn from user query patterns to improve future suggestions.
        
        Args:
            user_id: User identifier
            query: Executed query
            results_count: Number of results returned
            user_feedback: Optional user feedback on query usefulness
            
        Returns:
            Dictionary containing learning update status
        """
        try:
            # Update user patterns
            if user_id not in self.user_patterns:
                self.user_patterns[user_id] = {
                    "query_history": [],
                    "preferences": {},
                    "successful_patterns": [],
                    "failed_patterns": []
                }
            
            # Add to query history
            query_record = {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "results_count": results_count,
                "feedback": user_feedback
            }
            
            self.user_patterns[user_id]["query_history"].append(query_record)
            
            # Extract patterns
            patterns = self._extract_query_patterns(query)
            
            # Update successful/failed patterns based on results
            if results_count > 0 and user_feedback != "poor":
                self.user_patterns[user_id]["successful_patterns"].extend(patterns)
            elif results_count == 0 or user_feedback == "poor":
                self.user_patterns[user_id]["failed_patterns"].extend(patterns)
            
            # Update global query statistics
            self._update_global_query_stats(query, results_count)
            
            return {
                "learning_updated": True,
                "patterns_extracted": len(patterns),
                "user_query_count": len(self.user_patterns[user_id]["query_history"]),
                "update_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error learning from query: {str(e)}")
            return {"error": f"Learning update failed: {str(e)}"}
    
    async def suggest_improvements(self, query: str, 
                                 execution_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest improvements for existing queries based on performance.
        
        Args:
            query: Original query
            execution_stats: Query execution statistics
            
        Returns:
            Dictionary containing improvement suggestions
        """
        try:
            improvements = []
            
            # Performance-based improvements
            if execution_stats.get("execution_time", 0) > 30:  # Slow query
                perf_improvements = self._suggest_performance_improvements(query, execution_stats)
                improvements.extend(perf_improvements)
            
            # Accuracy improvements
            if execution_stats.get("results_count", 0) == 0:  # No results
                accuracy_improvements = self._suggest_accuracy_improvements(query)
                improvements.extend(accuracy_improvements)
            
            # Optimization suggestions
            optimization_suggestions = self._suggest_query_optimizations(query)
            improvements.extend(optimization_suggestions)
            
            # Alternative approaches
            alternative_suggestions = self._suggest_alternative_approaches(query)
            improvements.extend(alternative_suggestions)
            
            return {
                "improvements": improvements,
                "total_suggestions": len(improvements),
                "original_query": query,
                "improvement_categories": self._categorize_improvements(improvements),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error suggesting improvements: {str(e)}")
            return {"error": f"Improvement suggestion failed: {str(e)}"}
    
    async def get_contextual_help(self, query_fragment: str, 
                                cursor_position: int = 0) -> Dict[str, Any]:
        """
        Provide contextual help for query construction.
        
        Args:
            query_fragment: Partial query being constructed
            cursor_position: Position of cursor in query
            
        Returns:
            Dictionary containing contextual help information
        """
        try:
            help_info = {
                "syntax_help": [],
                "field_suggestions": [],
                "function_suggestions": [],
                "operator_suggestions": [],
                "example_queries": []
            }
            
            # Parse query fragment
            tokens = self._tokenize_query(query_fragment)
            current_context = self._determine_context(tokens, cursor_position)
            
            # Generate context-specific help
            if current_context == "field":
                help_info["field_suggestions"] = self._suggest_fields(query_fragment)
            elif current_context == "function":
                help_info["function_suggestions"] = self._suggest_functions(query_fragment)
            elif current_context == "operator":
                help_info["operator_suggestions"] = self._suggest_operators(query_fragment)
            
            # Add syntax help
            help_info["syntax_help"] = self._generate_syntax_help(current_context)
            
            # Add example queries
            help_info["example_queries"] = self._generate_example_queries(current_context)
            
            return {
                "help_info": help_info,
                "current_context": current_context,
                "cursor_position": cursor_position,
                "query_fragment": query_fragment,
                "help_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error providing contextual help: {str(e)}")
            return {"error": f"Contextual help failed: {str(e)}"}
    
    def _initialize_suggestion_templates(self) -> Dict[str, List[str]]:
        """Initialize suggestion templates for different categories."""
        return {
            "security": [
                "Show failed login attempts in the last hour",
                "Find unusual user activity patterns",
                "Identify suspicious IP addresses",
                "Detect privilege escalation attempts",
                "Monitor data exfiltration patterns"
            ],
            "performance": [
                "Show system performance metrics",
                "Find slow response times",
                "Identify CPU usage spikes",
                "Monitor memory utilization",
                "Track disk usage patterns"
            ],
            "network": [
                "Analyze network traffic patterns",
                "Find network connectivity issues",
                "Monitor bandwidth usage",
                "Detect network anomalies",
                "Track firewall blocks"
            ],
            "application": [
                "Show application error logs",
                "Find application performance issues",
                "Monitor user activity",
                "Track application usage patterns",
                "Identify application bottlenecks"
            ],
            "infrastructure": [
                "Monitor server health",
                "Track system availability",
                "Find infrastructure issues",
                "Monitor resource utilization",
                "Analyze system logs"
            ]
        }
    
    async def _generate_completion_suggestions(self, current_query: str, 
                                             user_context: Dict[str, Any]) -> List[QuerySuggestion]:
        """Generate auto-completion suggestions."""
        suggestions = []
        
        # Tokenize current query
        tokens = self._tokenize_query(current_query)
        
        if not tokens:
            return suggestions
        
        last_token = tokens[-1].lower()
        
        # Common SPL commands completion
        spl_commands = [
            "search", "stats", "eval", "where", "sort", "top", "rare", "head", "tail",
            "dedup", "join", "lookup", "rex", "replace", "rename", "fields", "table"
        ]
        
        matching_commands = [cmd for cmd in spl_commands if cmd.startswith(last_token)]
        
        for cmd in matching_commands:
            completion = current_query[:-len(last_token)] + cmd
            suggestions.append(QuerySuggestion(
                query=f"Complete with '{cmd}' command",
                confidence=0.8,
                category="completion",
                explanation=f"Auto-complete current query with '{cmd}' command",
                spl_query=completion,
                estimated_results=100,
                relevance_score=0.8,
                context_tags=["auto-complete", "spl-command"]
            ))
        
        return suggestions
    
    async def _generate_related_suggestions(self, current_query: str, 
                                          user_context: Dict[str, Any]) -> List[QuerySuggestion]:
        """Generate related query suggestions."""
        suggestions = []
        
        # Extract key terms from current query
        key_terms = self._extract_key_terms(current_query)
        
        # Generate related queries based on key terms
        for term in key_terms:
            related_templates = self._find_related_templates(term)
            
            for template in related_templates:
                suggestions.append(QuerySuggestion(
                    query=template["query"],
                    confidence=0.7,
                    category="related",
                    explanation=f"Related query focusing on {term}",
                    spl_query=template["spl"],
                    estimated_results=template.get("estimated_results", 50),
                    relevance_score=0.7,
                    context_tags=["related", term]
                ))
        
        return suggestions
    
    async def _generate_history_based_suggestions(self, user_context: Dict[str, Any]) -> List[QuerySuggestion]:
        """Generate suggestions based on user history."""
        suggestions = []
        
        user_id = user_context.get("user_id")
        if not user_id or user_id not in self.user_patterns:
            return suggestions
        
        # Get user's successful queries
        user_history = self.user_patterns[user_id]["query_history"]
        successful_queries = [
            q for q in user_history 
            if q.get("results_count", 0) > 0 and q.get("feedback") != "poor"
        ]
        
        # Sort by recency and success
        successful_queries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        for query_record in successful_queries[:5]:  # Top 5 recent successful queries
            suggestions.append(QuerySuggestion(
                query=query_record["query"],
                confidence=0.85,
                category="history",
                explanation="Previously successful query",
                spl_query=query_record["query"],
                estimated_results=query_record.get("results_count", 50),
                relevance_score=0.85,
                context_tags=["history", "successful"]
            ))
        
        return suggestions
    
    async def _generate_popular_suggestions(self, user_context: Dict[str, Any]) -> List[QuerySuggestion]:
        """Generate popular query suggestions."""
        suggestions = []
        
        # Get popular queries from global stats
        popular_queries = self._get_popular_queries()
        
        for query_data in popular_queries:
            suggestions.append(QuerySuggestion(
                query=query_data["query"],
                confidence=0.75,
                category="popular",
                explanation=f"Popular query used {query_data['usage_count']} times",
                spl_query=query_data["query"],
                estimated_results=query_data.get("avg_results", 100),
                relevance_score=0.75,
                context_tags=["popular", "community"]
            ))
        
        return suggestions
    
    async def _generate_data_driven_suggestions(self, user_context: Dict[str, Any]) -> List[QuerySuggestion]:
        """Generate suggestions based on data patterns."""
        suggestions = []
        
        # Get user's accessible indexes
        accessible_indexes = user_context.get("accessible_indexes", [])
        
        for index in accessible_indexes:
            # Generate suggestions for each index
            index_suggestions = self._get_index_specific_suggestions(index)
            
            for suggestion in index_suggestions:
                suggestions.append(QuerySuggestion(
                    query=suggestion["query"],
                    confidence=0.6,
                    category="data-driven",
                    explanation=f"Suggested based on {index} data patterns",
                    spl_query=suggestion["spl"],
                    estimated_results=suggestion.get("estimated_results", 75),
                    relevance_score=0.6,
                    context_tags=["data-driven", index]
                ))
        
        return suggestions
    
    async def _generate_context_aware_suggestions(self, user_context: Dict[str, Any]) -> List[QuerySuggestion]:
        """Generate context-aware suggestions."""
        suggestions = []
        
        # Get current time context
        current_hour = datetime.now().hour
        current_day = datetime.now().strftime("%A")
        
        # Time-based suggestions
        if 9 <= current_hour <= 17:  # Business hours
            business_suggestions = self._get_business_hour_suggestions()
            suggestions.extend(business_suggestions)
        else:  # After hours
            after_hours_suggestions = self._get_after_hours_suggestions()
            suggestions.extend(after_hours_suggestions)
        
        # Role-based suggestions
        user_roles = user_context.get("roles", [])
        for role in user_roles:
            role_suggestions = self._get_role_specific_suggestions(role)
            suggestions.extend(role_suggestions)
        
        return suggestions
    
    def _rank_suggestions(self, suggestions: List[QuerySuggestion], 
                         user_context: Dict[str, Any]) -> List[QuerySuggestion]:
        """Rank suggestions based on relevance and user context."""
        
        def calculate_score(suggestion: QuerySuggestion) -> float:
            score = suggestion.relevance_score
            
            # Boost based on confidence
            score *= suggestion.confidence
            
            # Boost based on user preferences
            user_preferences = user_context.get("preferences", {})
            if suggestion.category in user_preferences.get("preferred_categories", []):
                score *= 1.2
            
            # Boost recent successful patterns
            user_id = user_context.get("user_id")
            if user_id and user_id in self.user_patterns:
                successful_patterns = self.user_patterns[user_id]["successful_patterns"]
                query_patterns = self._extract_query_patterns(suggestion.query)
                
                pattern_overlap = len(set(query_patterns) & set(successful_patterns))
                if pattern_overlap > 0:
                    score *= (1 + pattern_overlap * 0.1)
            
            return score
        
        # Sort by calculated score
        return sorted(suggestions, key=calculate_score, reverse=True)
    
    def _apply_diversity_filter(self, suggestions: List[QuerySuggestion], 
                              max_suggestions: int) -> List[QuerySuggestion]:
        """Apply diversity filter to avoid similar suggestions."""
        filtered_suggestions = []
        seen_categories = set()
        seen_queries = set()
        
        for suggestion in suggestions:
            # Skip if too similar to existing suggestions
            if suggestion.query in seen_queries:
                continue
            
            # Limit suggestions per category
            category_count = sum(1 for s in filtered_suggestions if s.category == suggestion.category)
            if category_count >= max_suggestions // 3:  # Max 1/3 per category
                continue
            
            filtered_suggestions.append(suggestion)
            seen_categories.add(suggestion.category)
            seen_queries.add(suggestion.query)
            
            if len(filtered_suggestions) >= max_suggestions:
                break
        
        return filtered_suggestions
    
    def _categorize_suggestions(self, suggestions: List[QuerySuggestion]) -> Dict[str, int]:
        """Categorize suggestions by type."""
        categories = defaultdict(int)
        for suggestion in suggestions:
            categories[suggestion.category] += 1
        return dict(categories)
    
    def _calculate_confidence_distribution(self, suggestions: List[QuerySuggestion]) -> Dict[str, int]:
        """Calculate confidence distribution of suggestions."""
        distribution = {"high": 0, "medium": 0, "low": 0}
        
        for suggestion in suggestions:
            if suggestion.confidence >= 0.8:
                distribution["high"] += 1
            elif suggestion.confidence >= 0.6:
                distribution["medium"] += 1
            else:
                distribution["low"] += 1
        
        return distribution
    
    def _extract_query_patterns(self, query: str) -> List[str]:
        """Extract patterns from query for learning."""
        patterns = []
        
        # Extract SPL commands
        spl_commands = re.findall(r'\b(search|stats|eval|where|sort|top|rare|head|tail|dedup|join|lookup|rex|replace|rename|fields|table)\b', query.lower())
        patterns.extend(spl_commands)
        
        # Extract field names
        field_names = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=', query)
        patterns.extend(field_names)
        
        # Extract functions
        functions = re.findall(r'\b(count|sum|avg|min|max|values|list|dc|stats|eval)\s*\(', query.lower())
        patterns.extend(functions)
        
        return patterns
    
    def _update_global_query_stats(self, query: str, results_count: int):
        """Update global query statistics."""
        if query not in self.common_queries:
            self.common_queries[query] = {
                "usage_count": 0,
                "total_results": 0,
                "avg_results": 0
            }
        
        stats = self.common_queries[query]
        stats["usage_count"] += 1
        stats["total_results"] += results_count
        stats["avg_results"] = stats["total_results"] / stats["usage_count"]
    
    def _suggest_performance_improvements(self, query: str, 
                                        execution_stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest performance improvements for slow queries."""
        improvements = []
        
        # Check for common performance issues
        if "stats" in query.lower() and "by" not in query.lower():
            improvements.append({
                "type": "performance",
                "suggestion": "Add 'by' clause to stats command for better performance",
                "explanation": "Grouping data can improve aggregation performance",
                "confidence": 0.8
            })
        
        if query.lower().startswith("search *"):
            improvements.append({
                "type": "performance",
                "suggestion": "Add specific search terms instead of using wildcard",
                "explanation": "Specific search terms are more efficient than wildcards",
                "confidence": 0.9
            })
        
        # Check for time range optimization
        if "earliest" not in query.lower() and "latest" not in query.lower():
            improvements.append({
                "type": "performance",
                "suggestion": "Add time range constraints to improve query performance",
                "explanation": "Time range constraints significantly improve query speed",
                "confidence": 0.85
            })
        
        return improvements
    
    def _suggest_accuracy_improvements(self, query: str) -> List[Dict[str, Any]]:
        """Suggest accuracy improvements for queries with no results."""
        improvements = []
        
        # Check for common accuracy issues
        if "=" in query and "!" not in query:
            improvements.append({
                "type": "accuracy",
                "suggestion": "Try using wildcards or partial matches",
                "explanation": "Exact matches may be too restrictive",
                "confidence": 0.7
            })
        
        # Check for case sensitivity
        if any(c.isupper() for c in query):
            improvements.append({
                "type": "accuracy",
                "suggestion": "Check case sensitivity in search terms",
                "explanation": "Search terms may be case-sensitive",
                "confidence": 0.6
            })
        
        return improvements
    
    def _suggest_query_optimizations(self, query: str) -> List[Dict[str, Any]]:
        """Suggest general query optimizations."""
        optimizations = []
        
        # Check for field extraction optimization
        if "rex" in query.lower() and "extract" not in query.lower():
            optimizations.append({
                "type": "optimization",
                "suggestion": "Consider using extract command instead of rex for better performance",
                "explanation": "Extract command is optimized for field extraction",
                "confidence": 0.6
            })
        
        # Check for lookup optimization
        if "lookup" in query.lower():
            optimizations.append({
                "type": "optimization",
                "suggestion": "Ensure lookup tables are properly indexed",
                "explanation": "Indexed lookup tables improve join performance",
                "confidence": 0.7
            })
        
        return optimizations
    
    def _suggest_alternative_approaches(self, query: str) -> List[Dict[str, Any]]:
        """Suggest alternative approaches to the query."""
        alternatives = []
        
        # Suggest streaming vs non-streaming approaches
        if "stats" in query.lower() and "streamstats" not in query.lower():
            alternatives.append({
                "type": "alternative",
                "suggestion": "Consider using streamstats for real-time analysis",
                "explanation": "Streamstats provides continuous statistics calculation",
                "confidence": 0.5
            })
        
        # Suggest different aggregation methods
        if "count" in query.lower():
            alternatives.append({
                "type": "alternative",
                "suggestion": "Consider using 'dc' (distinct count) if you need unique values",
                "explanation": "Distinct count may be more appropriate for unique counting",
                "confidence": 0.6
            })
        
        return alternatives
    
    def _categorize_improvements(self, improvements: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize improvements by type."""
        categories = defaultdict(int)
        for improvement in improvements:
            categories[improvement["type"]] += 1
        return dict(categories)
    
    def _tokenize_query(self, query: str) -> List[str]:
        """Tokenize query into components."""
        # Simple tokenization - can be enhanced with proper SPL parser
        tokens = re.findall(r'\b\w+\b|[^\w\s]', query)
        return tokens
    
    def _determine_context(self, tokens: List[str], cursor_position: int) -> str:
        """Determine the current context based on tokens and cursor position."""
        # Simple context determination - can be enhanced
        if not tokens:
            return "start"
        
        last_token = tokens[-1].lower()
        
        if last_token in ["search", "stats", "eval", "where"]:
            return "command"
        elif last_token == "by":
            return "field"
        elif last_token in ["=", "!=", "<", ">", "<=", ">="]:
            return "value"
        else:
            return "general"
    
    def _suggest_fields(self, query_fragment: str) -> List[Dict[str, Any]]:
        """Suggest field names based on query fragment."""
        # Common Splunk fields
        common_fields = [
            "host", "source", "sourcetype", "index", "_time", "user", "src_ip",
            "dest_ip", "action", "status", "bytes", "duration", "method", "uri"
        ]
        
        return [
            {
                "field": field,
                "description": f"Common field: {field}",
                "confidence": 0.7
            }
            for field in common_fields
        ]
    
    def _suggest_functions(self, query_fragment: str) -> List[Dict[str, Any]]:
        """Suggest function names based on query fragment."""
        # Common Splunk functions
        common_functions = [
            "count", "sum", "avg", "min", "max", "values", "list", "dc",
            "stats", "eval", "if", "case", "match", "replace", "tonumber"
        ]
        
        return [
            {
                "function": func,
                "description": f"Function: {func}",
                "confidence": 0.8
            }
            for func in common_functions
        ]
    
    def _suggest_operators(self, query_fragment: str) -> List[Dict[str, Any]]:
        """Suggest operators based on query fragment."""
        # Common operators
        operators = [
            "=", "!=", "<", ">", "<=", ">=", "AND", "OR", "NOT",
            "LIKE", "IN", "BETWEEN"
        ]
        
        return [
            {
                "operator": op,
                "description": f"Operator: {op}",
                "confidence": 0.8
            }
            for op in operators
        ]
    
    def _generate_syntax_help(self, context: str) -> List[Dict[str, Any]]:
        """Generate syntax help based on context."""
        help_items = []
        
        if context == "command":
            help_items.append({
                "topic": "SPL Commands",
                "syntax": "search <terms> | stats <function> by <field>",
                "example": "search error | stats count by host"
            })
        
        elif context == "field":
            help_items.append({
                "topic": "Field Usage",
                "syntax": "fieldname=value",
                "example": "host=server1"
            })
        
        return help_items
    
    def _generate_example_queries(self, context: str) -> List[Dict[str, Any]]:
        """Generate example queries based on context."""
        examples = []
        
        if context == "command":
            examples.extend([
                {
                    "query": "search error | stats count by host",
                    "description": "Count errors by host"
                },
                {
                    "query": "search status=404 | top limit=10 uri",
                    "description": "Top 10 404 errors by URI"
                }
            ])
        
        return examples
    
    def _extract_key_terms(self, query: str) -> List[str]:
        """Extract key terms from query."""
        # Simple key term extraction
        terms = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', query)
        return [term for term in terms if len(term) > 2]
    
    def _find_related_templates(self, term: str) -> List[Dict[str, Any]]:
        """Find related query templates for a term."""
        templates = []
        
        # Security-related terms
        if term.lower() in ["error", "fail", "login", "auth"]:
            templates.append({
                "query": f"Find {term} patterns in security logs",
                "spl": f"search {term} | stats count by source",
                "estimated_results": 50
            })
        
        # Performance-related terms
        if term.lower() in ["slow", "timeout", "performance"]:
            templates.append({
                "query": f"Analyze {term} issues",
                "spl": f"search {term} | stats avg(duration) by host",
                "estimated_results": 30
            })
        
        return templates
    
    def _get_popular_queries(self) -> List[Dict[str, Any]]:
        """Get popular queries from global statistics."""
        # Sort by usage count
        popular = sorted(
            self.common_queries.items(),
            key=lambda x: x[1]["usage_count"],
            reverse=True
        )
        
        return [
            {
                "query": query,
                "usage_count": stats["usage_count"],
                "avg_results": stats["avg_results"]
            }
            for query, stats in popular[:5]
        ]
    
    def _get_index_specific_suggestions(self, index: str) -> List[Dict[str, Any]]:
        """Get suggestions specific to an index."""
        suggestions = []
        
        # Common patterns for different index types
        if "security" in index.lower():
            suggestions.append({
                "query": f"Recent security events in {index}",
                "spl": f"search index={index} | stats count by action",
                "estimated_results": 100
            })
        
        elif "performance" in index.lower():
            suggestions.append({
                "query": f"Performance metrics from {index}",
                "spl": f"search index={index} | stats avg(response_time) by host",
                "estimated_results": 75
            })
        
        return suggestions
    
    def _get_business_hour_suggestions(self) -> List[QuerySuggestion]:
        """Get suggestions appropriate for business hours."""
        suggestions = []
        
        # Business-focused queries
        business_queries = [
            "Show current system performance",
            "Monitor active user sessions",
            "Track business application metrics"
        ]
        
        for query in business_queries:
            suggestions.append(QuerySuggestion(
                query=query,
                confidence=0.6,
                category="business-hours",
                explanation="Relevant for business hours monitoring",
                spl_query=f"search {query.lower()}",
                estimated_results=50,
                relevance_score=0.6,
                context_tags=["business-hours", "monitoring"]
            ))
        
        return suggestions
    
    def _get_after_hours_suggestions(self) -> List[QuerySuggestion]:
        """Get suggestions appropriate for after hours."""
        suggestions = []
        
        # After-hours focused queries
        after_hours_queries = [
            "Check for security incidents",
            "Monitor batch job status",
            "Review system maintenance tasks"
        ]
        
        for query in after_hours_queries:
            suggestions.append(QuerySuggestion(
                query=query,
                confidence=0.6,
                category="after-hours",
                explanation="Relevant for after-hours monitoring",
                spl_query=f"search {query.lower()}",
                estimated_results=30,
                relevance_score=0.6,
                context_tags=["after-hours", "security"]
            ))
        
        return suggestions
    
    def _get_role_specific_suggestions(self, role: str) -> List[QuerySuggestion]:
        """Get suggestions specific to user role."""
        suggestions = []
        
        role_queries = {
            "security_admin": [
                "Monitor security events",
                "Check failed login attempts",
                "Review firewall logs"
            ],
            "system_admin": [
                "Check system health",
                "Monitor resource usage",
                "Review error logs"
            ],
            "developer": [
                "Monitor application logs",
                "Check API response times",
                "Review deployment logs"
            ]
        }
        
        if role in role_queries:
            for query in role_queries[role]:
                suggestions.append(QuerySuggestion(
                    query=query,
                    confidence=0.7,
                    category="role-specific",
                    explanation=f"Relevant for {role} role",
                    spl_query=f"search {query.lower()}",
                    estimated_results=60,
                    relevance_score=0.7,
                    context_tags=["role-specific", role]
                ))
        
        return suggestions

# Global instance
intelligent_suggestions = IntelligentSuggestionsEngine()