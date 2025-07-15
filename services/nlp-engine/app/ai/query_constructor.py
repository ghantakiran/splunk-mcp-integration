"""
Complex Query Construction System

This module provides advanced SPL query construction capabilities, building upon
the comprehensive SPL mapping system to create sophisticated, multi-step queries
with complex logical structures and optimizations.
"""

import re
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime, timedelta

from .spl_mapping import spl_mapper, SPLCommand, SPLCommandType, FieldMapping
from ..core.logging import get_logger

logger = get_logger(__name__)


class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"          # Single command
    MODERATE = "moderate"      # 2-3 commands with pipes
    COMPLEX = "complex"        # 4-6 commands with multiple pipes
    ADVANCED = "advanced"      # 7+ commands with subqueries/joins


class LogicalOperator(Enum):
    """Logical operators for query construction"""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    XOR = "XOR"


class JoinType(Enum):
    """Join types for complex queries"""
    INNER = "inner"
    LEFT = "left"
    RIGHT = "right"
    OUTER = "outer"


@dataclass
class QueryCondition:
    """Represents a single query condition"""
    field: str
    operator: str
    value: Any
    field_type: Optional[str] = None
    negated: bool = False
    
    def to_spl(self) -> str:
        """Convert condition to SPL syntax"""
        # Handle different field types and operators
        if self.field_type == "string" and self.operator in ["=", "equals"]:
            condition = f'{self.field}="{self.value}"'
        elif self.field_type == "number" and self.operator in [">", "<", ">=", "<=", "=", "!="]:
            condition = f"{self.field}{self.operator}{self.value}"
        elif self.operator in ["like", "contains"]:
            condition = f'{self.field}="*{self.value}*"'
        elif self.operator == "matches":
            condition = f'{self.field} | regex "{self.value}"'
        else:
            condition = f'{self.field}{self.operator}"{self.value}"'
        
        return f"NOT ({condition})" if self.negated else condition


@dataclass
class QueryBlock:
    """Represents a logical block of query conditions"""
    conditions: List[QueryCondition] = field(default_factory=list)
    logical_operator: LogicalOperator = LogicalOperator.AND
    time_range: Optional[Tuple[str, str]] = None
    index: Optional[str] = None
    sourcetype: Optional[str] = None
    
    def to_spl(self) -> str:
        """Convert query block to SPL syntax"""
        parts = []
        
        # Add index if specified
        if self.index:
            parts.append(f"index={self.index}")
        
        # Add sourcetype if specified
        if self.sourcetype:
            parts.append(f"sourcetype={self.sourcetype}")
        
        # Add time range if specified
        if self.time_range:
            parts.append(f"earliest={self.time_range[0]} latest={self.time_range[1]}")
        
        # Add conditions
        if self.conditions:
            condition_strs = [cond.to_spl() for cond in self.conditions]
            if len(condition_strs) == 1:
                parts.append(condition_strs[0])
            else:
                operator_str = f" {self.logical_operator.value} "
                combined_conditions = operator_str.join(condition_strs)
                parts.append(f"({combined_conditions})")
        
        return " ".join(parts) if parts else "*"


@dataclass
class QueryPipeline:
    """Represents a complete SPL query pipeline"""
    search_block: QueryBlock
    transformations: List[Dict[str, Any]] = field(default_factory=list)
    aggregations: List[Dict[str, Any]] = field(default_factory=list)
    sorting: Optional[Dict[str, Any]] = None
    limiting: Optional[int] = None
    complexity: QueryComplexity = QueryComplexity.SIMPLE
    
    def to_spl(self) -> str:
        """Convert entire pipeline to SPL syntax"""
        pipeline_parts = []
        
        # Start with search block
        search_spl = self.search_block.to_spl()
        if not search_spl.startswith("search "):
            search_spl = f"search {search_spl}"
        pipeline_parts.append(search_spl)
        
        # Add transformations
        for transform in self.transformations:
            cmd = transform.get("command")
            params = transform.get("parameters", {})
            
            if cmd == "eval":
                field_name = params.get("field")
                expression = params.get("expression")
                pipeline_parts.append(f"eval {field_name}={expression}")
            elif cmd == "rex":
                field = params.get("field", "_raw")
                pattern = params.get("pattern")
                pipeline_parts.append(f'rex field={field} "{pattern}"')
            elif cmd == "where":
                condition = params.get("condition")
                pipeline_parts.append(f"where {condition}")
            elif cmd == "dedup":
                fields = params.get("fields", [])
                pipeline_parts.append(f"dedup {' '.join(fields)}")
        
        # Add aggregations
        for agg in self.aggregations:
            cmd = agg.get("command", "stats")
            functions = agg.get("functions", [])
            by_fields = agg.get("by_fields", [])
            
            if cmd == "stats":
                func_strs = []
                for func in functions:
                    func_name = func.get("function")
                    field = func.get("field")
                    alias = func.get("alias")
                    
                    if field:
                        func_str = f"{func_name}({field})"
                    else:
                        func_str = func_name
                    
                    if alias:
                        func_str += f" as {alias}"
                    
                    func_strs.append(func_str)
                
                stats_cmd = f"stats {', '.join(func_strs)}"
                if by_fields:
                    stats_cmd += f" by {', '.join(by_fields)}"
                pipeline_parts.append(stats_cmd)
            
            elif cmd == "timechart":
                span = agg.get("span", "auto")
                functions = agg.get("functions", [])
                by_field = agg.get("by_field")
                
                func_strs = []
                for func in functions:
                    func_name = func.get("function")
                    field = func.get("field")
                    if field:
                        func_strs.append(f"{func_name}({field})")
                    else:
                        func_strs.append(func_name)
                
                timechart_cmd = f"timechart span={span} {', '.join(func_strs)}"
                if by_field:
                    timechart_cmd += f" by {by_field}"
                pipeline_parts.append(timechart_cmd)
        
        # Add sorting
        if self.sorting:
            sort_fields = self.sorting.get("fields", [])
            order = self.sorting.get("order", "asc")
            limit = self.sorting.get("limit")
            
            sort_cmd = "sort "
            if limit:
                sort_cmd += f"{limit} "
            
            sort_field_strs = []
            for field in sort_fields:
                if order == "desc":
                    sort_field_strs.append(f"-{field}")
                else:
                    sort_field_strs.append(f"+{field}")
            
            sort_cmd += ", ".join(sort_field_strs)
            pipeline_parts.append(sort_cmd)
        
        # Add limiting
        if self.limiting:
            pipeline_parts.append(f"head {self.limiting}")
        
        return " | ".join(pipeline_parts)


@dataclass
class ComplexQuery:
    """Represents a complex query with multiple pipelines and joins"""
    main_pipeline: QueryPipeline
    subqueries: List[QueryPipeline] = field(default_factory=list)
    joins: List[Dict[str, Any]] = field(default_factory=list)
    unions: List[QueryPipeline] = field(default_factory=list)
    complexity: QueryComplexity = QueryComplexity.COMPLEX
    
    def to_spl(self) -> str:
        """Convert complex query to SPL syntax"""
        if not self.subqueries and not self.joins and not self.unions:
            return self.main_pipeline.to_spl()
        
        query_parts = []
        main_spl = self.main_pipeline.to_spl()
        
        # Handle joins
        if self.joins:
            for join_info in self.joins:
                join_type = join_info.get("type", "inner")
                join_pipeline = join_info.get("pipeline")
                join_fields = join_info.get("fields", [])
                
                if join_pipeline:
                    join_spl = join_pipeline.to_spl()
                    # Create join command
                    join_cmd = f"join type={join_type} {' '.join(join_fields)} [search {join_spl}]"
                    main_spl += f" | {join_cmd}"
        
        # Handle unions
        if self.unions:
            union_queries = [main_spl]
            for union_pipeline in self.unions:
                union_spl = union_pipeline.to_spl()
                union_queries.append(union_spl)
            
            # Create multisearch command for union
            multisearch_parts = []
            for i, query in enumerate(union_queries):
                multisearch_parts.append(f"[search {query}]")
            
            return f"multisearch {' '.join(multisearch_parts)}"
        
        return main_spl


class ComplexQueryConstructor:
    """Advanced query constructor for complex SPL queries"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Query construction patterns
        self.construction_patterns = self._initialize_construction_patterns()
        self.complexity_rules = self._initialize_complexity_rules()
        self.optimization_rules = self._initialize_optimization_rules()
    
    def _initialize_construction_patterns(self) -> Dict[str, Any]:
        """Initialize query construction patterns"""
        return {
            "temporal_analysis": {
                "pattern": r"(.+)\s+(?:over time|by time|timeline|trend)",
                "template": {
                    "command": "timechart",
                    "span": "auto",
                    "functions": [{"function": "count"}]
                }
            },
            "aggregation_with_grouping": {
                "pattern": r"(.+)\s+(?:by|group by|grouped by)\s+(.+)",
                "template": {
                    "command": "stats",
                    "functions": [{"function": "count"}],
                    "by_fields": []
                }
            },
            "comparison_query": {
                "pattern": r"compare\s+(.+)\s+(?:to|with|vs|versus)\s+(.+)",
                "template": {
                    "type": "comparison",
                    "main_condition": "",
                    "comparison_condition": ""
                }
            },
            "top_analysis": {
                "pattern": r"(?:top|most|highest|maximum)\s+(\d+)?\s*(.+)",
                "template": {
                    "command": "top",
                    "limit": 10,
                    "field": ""
                }
            },
            "statistical_analysis": {
                "pattern": r"(?:average|mean|sum|total|min|minimum|max|maximum|count)\s+(.+)",
                "template": {
                    "command": "stats",
                    "functions": []
                }
            }
        }
    
    def _initialize_complexity_rules(self) -> Dict[str, Any]:
        """Initialize rules for determining query complexity"""
        return {
            "simple": {
                "max_commands": 1,
                "has_subqueries": False,
                "has_joins": False,
                "max_conditions": 3
            },
            "moderate": {
                "max_commands": 3,
                "has_subqueries": False,
                "has_joins": False,
                "max_conditions": 5
            },
            "complex": {
                "max_commands": 6,
                "has_subqueries": True,
                "has_joins": False,
                "max_conditions": 10
            },
            "advanced": {
                "max_commands": float('inf'),
                "has_subqueries": True,
                "has_joins": True,
                "max_conditions": float('inf')
            }
        }
    
    def _initialize_optimization_rules(self) -> List[Dict[str, Any]]:
        """Initialize query optimization rules"""
        return [
            {
                "name": "index_first",
                "description": "Place index specification at the beginning",
                "priority": 1
            },
            {
                "name": "time_range_early",
                "description": "Apply time range filters early",
                "priority": 2
            },
            {
                "name": "field_filters_before_stats",
                "description": "Apply field filters before aggregations",
                "priority": 3
            },
            {
                "name": "limit_results",
                "description": "Limit results when possible",
                "priority": 4
            }
        ]
    
    def construct_complex_query(
        self, 
        natural_query: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> ComplexQuery:
        """Construct a complex SPL query from natural language"""
        
        try:
            self.logger.info("Constructing complex query", query=natural_query[:100])
            
            # Analyze query structure
            query_analysis = self._analyze_query_structure(natural_query)
            
            # Determine complexity
            complexity = self._determine_complexity(query_analysis)
            
            # Extract components
            components = self._extract_query_components(natural_query, context)
            
            # Build main pipeline
            main_pipeline = self._build_main_pipeline(components, complexity)
            
            # Handle complex features
            subqueries = self._identify_subqueries(components)
            joins = self._identify_joins(components)
            unions = self._identify_unions(components)
            
            # Create complex query
            complex_query = ComplexQuery(
                main_pipeline=main_pipeline,
                subqueries=subqueries,
                joins=joins,
                unions=unions,
                complexity=complexity
            )
            
            # Optimize query
            optimized_query = self._optimize_complex_query(complex_query)
            
            self.logger.info(
                "Complex query constructed",
                complexity=complexity.value,
                has_subqueries=len(subqueries) > 0,
                has_joins=len(joins) > 0
            )
            
            return optimized_query
            
        except Exception as e:
            self.logger.error(f"Complex query construction failed: {e}")
            # Fallback to simple query
            return self._create_fallback_query(natural_query, context)
    
    def _analyze_query_structure(self, query: str) -> Dict[str, Any]:
        """Analyze the structure of a natural language query"""
        analysis = {
            "has_temporal_aspect": False,
            "has_aggregation": False,
            "has_grouping": False,
            "has_comparison": False,
            "has_subquery_indicators": False,
            "has_join_indicators": False,
            "condition_count": 0,
            "command_indicators": []
        }
        
        query_lower = query.lower()
        
        # Check for temporal aspects
        temporal_keywords = ["over time", "by time", "timeline", "trend", "hourly", "daily", "weekly"]
        analysis["has_temporal_aspect"] = any(keyword in query_lower for keyword in temporal_keywords)
        
        # Check for aggregation
        agg_keywords = ["count", "sum", "average", "total", "max", "min", "mean"]
        analysis["has_aggregation"] = any(keyword in query_lower for keyword in agg_keywords)
        
        # Check for grouping
        group_keywords = ["by", "group by", "grouped by", "per", "for each"]
        analysis["has_grouping"] = any(keyword in query_lower for keyword in group_keywords)
        
        # Check for comparison
        comp_keywords = ["compare", "vs", "versus", "to", "with", "against"]
        analysis["has_comparison"] = any(keyword in query_lower for keyword in comp_keywords)
        
        # Check for subquery indicators
        subquery_keywords = ["where", "that have", "which contain", "with"]
        analysis["has_subquery_indicators"] = any(keyword in query_lower for keyword in subquery_keywords)
        
        # Check for join indicators
        join_keywords = ["and", "also", "combined with", "together with"]
        analysis["has_join_indicators"] = any(keyword in query_lower for keyword in join_keywords)
        
        # Count conditions (rough estimate)
        condition_indicators = ["=", ">", "<", "contains", "matches", "equals", "not", "and", "or"]
        analysis["condition_count"] = sum(1 for indicator in condition_indicators if indicator in query_lower)
        
        # Identify command indicators
        for cmd_name, cmd in spl_mapper.commands.items():
            if any(pattern in query_lower for pattern in cmd.common_patterns):
                analysis["command_indicators"].append(cmd_name)
        
        return analysis
    
    def _determine_complexity(self, analysis: Dict[str, Any]) -> QueryComplexity:
        """Determine query complexity based on analysis"""
        
        complexity_score = 0
        
        # Add scores based on features
        if analysis["has_temporal_aspect"]:
            complexity_score += 2
        if analysis["has_aggregation"]:
            complexity_score += 1
        if analysis["has_grouping"]:
            complexity_score += 1
        if analysis["has_comparison"]:
            complexity_score += 2
        if analysis["has_subquery_indicators"]:
            complexity_score += 3
        if analysis["has_join_indicators"]:
            complexity_score += 4
        
        complexity_score += min(analysis["condition_count"], 5)
        complexity_score += min(len(analysis["command_indicators"]), 3)
        
        # Determine complexity level
        if complexity_score <= 2:
            return QueryComplexity.SIMPLE
        elif complexity_score <= 5:
            return QueryComplexity.MODERATE
        elif complexity_score <= 10:
            return QueryComplexity.COMPLEX
        else:
            return QueryComplexity.ADVANCED
    
    def _extract_query_components(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract components from natural language query"""
        
        components = {
            "conditions": [],
            "aggregations": [],
            "transformations": [],
            "time_range": None,
            "index": None,
            "sourcetype": None,
            "fields": [],
            "sorting": None,
            "limiting": None
        }
        
        # Extract context information
        if context:
            components["index"] = context.get("index")
            components["sourcetype"] = context.get("sourcetype")
            components["time_range"] = context.get("time_range")
        
        # Extract conditions using patterns
        conditions = self._extract_conditions(query)
        components["conditions"] = conditions
        
        # Extract aggregations
        aggregations = self._extract_aggregations(query)
        components["aggregations"] = aggregations
        
        # Extract transformations
        transformations = self._extract_transformations(query)
        components["transformations"] = transformations
        
        # Extract time range from query
        time_range = self._extract_time_range(query)
        if time_range:
            components["time_range"] = time_range
        
        # Extract sorting and limiting
        sorting = self._extract_sorting(query)
        if sorting:
            components["sorting"] = sorting
        
        limiting = self._extract_limiting(query)
        if limiting:
            components["limiting"] = limiting
        
        return components
    
    def _extract_conditions(self, query: str) -> List[QueryCondition]:
        """Extract query conditions from natural language"""
        conditions = []
        
        # Pattern for field = value
        field_value_patterns = [
            r"(\w+)\s+(?:equals|is|=)\s+([^\s]+)",
            r"(\w+)\s+(?:contains|has)\s+([^\s]+)",
            r"(\w+)\s+(?:greater than|>)\s+([^\s]+)",
            r"(\w+)\s+(?:less than|<)\s+([^\s]+)",
            r"(\w+)\s+(?:not equal|!=)\s+([^\s]+)"
        ]
        
        for pattern in field_value_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                field = match.group(1)
                value = match.group(2).strip('"\'')
                
                # Determine operator
                operator_text = query[match.start():match.end()].lower()
                if "equals" in operator_text or " is " in operator_text or "=" in operator_text:
                    operator = "="
                elif "contains" in operator_text or "has" in operator_text:
                    operator = "like"
                elif "greater than" in operator_text or ">" in operator_text:
                    operator = ">"
                elif "less than" in operator_text or "<" in operator_text:
                    operator = "<"
                elif "not equal" in operator_text or "!=" in operator_text:
                    operator = "!="
                else:
                    operator = "="
                
                # Check for field mapping
                field_mapping = spl_mapper.find_field_mapping(field)
                if field_mapping:
                    field = field_mapping.splunk_field
                    field_type = field_mapping.field_type.value
                else:
                    field_type = "string"
                
                condition = QueryCondition(
                    field=field,
                    operator=operator,
                    value=value,
                    field_type=field_type
                )
                conditions.append(condition)
        
        return conditions
    
    def _extract_aggregations(self, query: str) -> List[Dict[str, Any]]:
        """Extract aggregation functions from query"""
        aggregations = []
        
        # Check for temporal analysis
        temporal_pattern = r"(.+)\s+(?:over time|by time|timeline|trend)"
        temporal_match = re.search(temporal_pattern, query, re.IGNORECASE)
        if temporal_match:
            aggregations.append({
                "command": "timechart",
                "span": "auto",
                "functions": [{"function": "count"}]
            })
        
        # Check for grouping
        group_pattern = r"(.+)\s+(?:by|group by)\s+(\w+)"
        group_match = re.search(group_pattern, query, re.IGNORECASE)
        if group_match:
            by_field = group_match.group(2)
            # Map field if needed
            field_mapping = spl_mapper.find_field_mapping(by_field)
            if field_mapping:
                by_field = field_mapping.splunk_field
            
            aggregations.append({
                "command": "stats",
                "functions": [{"function": "count"}],
                "by_fields": [by_field]
            })
        
        # Check for statistical functions
        stat_patterns = {
            r"count\s+(?:of\s+)?(\w+)?": "count",
            r"(?:sum|total)\s+(?:of\s+)?(\w+)": "sum",
            r"(?:average|mean)\s+(?:of\s+)?(\w+)": "avg",
            r"(?:max|maximum)\s+(?:of\s+)?(\w+)": "max",
            r"(?:min|minimum)\s+(?:of\s+)?(\w+)": "min"
        }
        
        for pattern, func_name in stat_patterns.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                field = match.group(1) if match.group(1) else None
                
                # Map field if needed
                if field:
                    field_mapping = spl_mapper.find_field_mapping(field)
                    if field_mapping:
                        field = field_mapping.splunk_field
                
                function_def = {"function": func_name}
                if field:
                    function_def["field"] = field
                
                # Check if we already have a stats aggregation
                stats_agg = next((agg for agg in aggregations if agg["command"] == "stats"), None)
                if stats_agg:
                    stats_agg["functions"].append(function_def)
                else:
                    aggregations.append({
                        "command": "stats",
                        "functions": [function_def]
                    })
        
        return aggregations
    
    def _extract_transformations(self, query: str) -> List[Dict[str, Any]]:
        """Extract transformation operations from query"""
        transformations = []
        
        # Check for where conditions
        where_pattern = r"where\s+(.+?)(?:\s+(?:and|or|$))"
        where_matches = re.finditer(where_pattern, query, re.IGNORECASE)
        for match in where_matches:
            condition = match.group(1).strip()
            transformations.append({
                "command": "where",
                "parameters": {"condition": condition}
            })
        
        # Check for field extraction patterns
        extract_pattern = r"extract\s+(\w+)\s+from\s+(\w+)"
        extract_match = re.search(extract_pattern, query, re.IGNORECASE)
        if extract_match:
            field_name = extract_match.group(1)
            source_field = extract_match.group(2)
            transformations.append({
                "command": "rex",
                "parameters": {
                    "field": source_field,
                    "pattern": f"(?<{field_name}>\\w+)"
                }
            })
        
        return transformations
    
    def _extract_time_range(self, query: str) -> Optional[Tuple[str, str]]:
        """Extract time range from query"""
        # Common time expressions
        time_patterns = {
            r"(?:in the\s+)?last\s+(\d+)\s+(hour|day|week|month)s?": lambda m: (f"-{m.group(1)}{m.group(2)[0]}", "now"),
            r"(?:in the\s+)?past\s+(\d+)\s+(hour|day|week|month)s?": lambda m: (f"-{m.group(1)}{m.group(2)[0]}", "now"),
            r"today": lambda m: ("-0d@d", "now"),
            r"yesterday": lambda m: ("-1d@d", "-0d@d"),
            r"this\s+week": lambda m: ("-0w@w", "now"),
            r"last\s+24\s+hours": lambda m: ("-24h", "now")
        }
        
        for pattern, time_func in time_patterns.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return time_func(match)
        
        return None
    
    def _extract_sorting(self, query: str) -> Optional[Dict[str, Any]]:
        """Extract sorting information from query"""
        sort_patterns = [
            r"(?:sort|order)\s+by\s+(\w+)(?:\s+(asc|desc|ascending|descending))?",
            r"(?:top|highest|maximum)\s+(\d+)?\s*(\w+)",
            r"(?:bottom|lowest|minimum)\s+(\d+)?\s*(\w+)"
        ]
        
        for pattern in sort_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                if "top" in pattern or "highest" in pattern or "maximum" in pattern:
                    return {
                        "fields": [match.group(2) if len(match.groups()) >= 2 else match.group(1)],
                        "order": "desc",
                        "limit": int(match.group(1)) if match.group(1) and match.group(1).isdigit() else 10
                    }
                elif "bottom" in pattern or "lowest" in pattern or "minimum" in pattern:
                    return {
                        "fields": [match.group(2) if len(match.groups()) >= 2 else match.group(1)],
                        "order": "asc",
                        "limit": int(match.group(1)) if match.group(1) and match.group(1).isdigit() else 10
                    }
                else:
                    order = "desc" if match.group(2) and "desc" in match.group(2).lower() else "asc"
                    return {
                        "fields": [match.group(1)],
                        "order": order
                    }
        
        return None
    
    def _extract_limiting(self, query: str) -> Optional[int]:
        """Extract result limiting from query"""
        limit_patterns = [
            r"(?:limit|first|top)\s+(\d+)",
            r"show\s+(?:me\s+)?(?:only\s+)?(\d+)"
        ]
        
        for pattern in limit_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def _build_main_pipeline(
        self, 
        components: Dict[str, Any], 
        complexity: QueryComplexity
    ) -> QueryPipeline:
        """Build the main query pipeline from components"""
        
        # Create search block
        search_block = QueryBlock(
            conditions=[],
            index=components.get("index"),
            sourcetype=components.get("sourcetype"),
            time_range=components.get("time_range")
        )
        
        # Add conditions to search block
        for condition in components.get("conditions", []):
            search_block.conditions.append(condition)
        
        # Create pipeline
        pipeline = QueryPipeline(
            search_block=search_block,
            transformations=components.get("transformations", []),
            aggregations=components.get("aggregations", []),
            sorting=components.get("sorting"),
            limiting=components.get("limiting"),
            complexity=complexity
        )
        
        return pipeline
    
    def _identify_subqueries(self, components: Dict[str, Any]) -> List[QueryPipeline]:
        """Identify and create subqueries"""
        # For now, return empty list - subquery identification is complex
        # and would require more sophisticated natural language analysis
        return []
    
    def _identify_joins(self, components: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify join requirements"""
        # For now, return empty list - join identification requires
        # complex analysis of relationships between data sources
        return []
    
    def _identify_unions(self, components: Dict[str, Any]) -> List[QueryPipeline]:
        """Identify union requirements"""
        # For now, return empty list - union identification requires
        # analysis of multiple data sources or conditions
        return []
    
    def _optimize_complex_query(self, query: ComplexQuery) -> ComplexQuery:
        """Optimize a complex query for performance"""
        
        # Apply optimization rules
        for rule in self.optimization_rules:
            if rule["name"] == "index_first":
                # Ensure index is specified in search block
                if not query.main_pipeline.search_block.index:
                    # Could suggest adding index specification
                    pass
            
            elif rule["name"] == "time_range_early":
                # Ensure time range is in search block, not as a separate filter
                if query.main_pipeline.search_block.time_range is None:
                    # Look for time filters in transformations and move them
                    pass
            
            elif rule["name"] == "field_filters_before_stats":
                # Ensure field filters come before aggregations
                pass
            
            elif rule["name"] == "limit_results":
                # Add reasonable limits if not specified
                if query.main_pipeline.limiting is None and query.complexity in [QueryComplexity.COMPLEX, QueryComplexity.ADVANCED]:
                    query.main_pipeline.limiting = 10000
        
        return query
    
    def _create_fallback_query(
        self, 
        natural_query: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> ComplexQuery:
        """Create a simple fallback query"""
        
        # Create basic search block
        search_block = QueryBlock(
            conditions=[QueryCondition(field="_raw", operator="like", value=natural_query[:50])],
            index=context.get("index") if context else None,
            sourcetype=context.get("sourcetype") if context else None
        )
        
        # Create simple pipeline
        pipeline = QueryPipeline(
            search_block=search_block,
            complexity=QueryComplexity.SIMPLE
        )
        
        return ComplexQuery(main_pipeline=pipeline, complexity=QueryComplexity.SIMPLE)
    
    def analyze_query_performance(self, query: ComplexQuery) -> Dict[str, Any]:
        """Analyze query performance characteristics"""
        
        performance_analysis = {
            "complexity_score": 0,
            "estimated_cost": "low",
            "optimization_suggestions": [],
            "performance_warnings": []
        }
        
        # Calculate complexity score
        score = 0
        score += len(query.main_pipeline.transformations) * 2
        score += len(query.main_pipeline.aggregations) * 3
        score += len(query.subqueries) * 5
        score += len(query.joins) * 10
        
        performance_analysis["complexity_score"] = score
        
        # Determine estimated cost
        if score <= 5:
            performance_analysis["estimated_cost"] = "low"
        elif score <= 15:
            performance_analysis["estimated_cost"] = "medium"
        else:
            performance_analysis["estimated_cost"] = "high"
        
        # Generate optimization suggestions
        if not query.main_pipeline.search_block.index:
            performance_analysis["optimization_suggestions"].append(
                "Specify an index to improve search performance"
            )
        
        if not query.main_pipeline.search_block.time_range:
            performance_analysis["optimization_suggestions"].append(
                "Specify a time range to reduce data volume"
            )
        
        if len(query.main_pipeline.aggregations) > 0 and not query.main_pipeline.limiting:
            performance_analysis["optimization_suggestions"].append(
                "Consider adding a limit to reduce result set size"
            )
        
        # Generate performance warnings
        if len(query.joins) > 2:
            performance_analysis["performance_warnings"].append(
                "Multiple joins may impact performance significantly"
            )
        
        if query.complexity == QueryComplexity.ADVANCED:
            performance_analysis["performance_warnings"].append(
                "Advanced complexity query may require significant resources"
            )
        
        return performance_analysis


# Global instance
query_constructor = ComplexQueryConstructor()