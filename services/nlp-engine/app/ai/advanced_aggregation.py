"""
Advanced Aggregation Handler for SPL Translation

This module provides sophisticated aggregation handling capabilities including:
- Complex multi-field aggregations
- Statistical functions with parameters
- Time-based aggregations with windowing
- Conditional aggregations
- Nested aggregations
- Performance optimization
"""

import re
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime, timedelta

from ..core.logging import get_logger
from .spl_mapping import spl_mapper, FieldType

logger = get_logger(__name__)


class AggregationFunction(Enum):
    """Supported aggregation functions"""
    # Basic functions
    COUNT = "count"
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    
    # Statistical functions
    STDEV = "stdev"
    VAR = "var"
    MEDIAN = "median"
    RANGE = "range"
    
    # Advanced functions
    PERCENTILE = "perc"
    FIRST = "first"
    LAST = "last"
    VALUES = "values"
    LIST = "list"
    
    # Time-based functions
    EARLIEST = "earliest"
    LATEST = "latest"
    RATE = "rate"
    
    # Conditional functions
    COUNT_IF = "count_if"
    SUM_IF = "sum_if"
    AVG_IF = "avg_if"


class AggregationType(Enum):
    """Types of aggregations"""
    SIMPLE = "simple"          # Single field, single function
    MULTI_FIELD = "multi_field"  # Multiple fields, single function
    MULTI_FUNCTION = "multi_function"  # Single field, multiple functions
    COMPLEX = "complex"        # Multiple fields, multiple functions
    CONDITIONAL = "conditional"  # Aggregations with conditions
    TEMPORAL = "temporal"      # Time-based aggregations
    STATISTICAL = "statistical"  # Advanced statistical functions
    NESTED = "nested"          # Nested aggregations with subqueries


@dataclass
class AggregationParameter:
    """Parameters for aggregation functions"""
    name: str
    value: Any
    parameter_type: str = "value"  # "value", "field", "expression"
    required: bool = False


@dataclass
class AggregationCondition:
    """Conditions for conditional aggregations"""
    field: str
    operator: str
    value: Any
    condition_type: str = "where"  # "where", "if", "case"


@dataclass
class AdvancedAggregation:
    """Advanced aggregation specification"""
    function: AggregationFunction
    fields: List[str]
    alias: Optional[str] = None
    parameters: List[AggregationParameter] = field(default_factory=list)
    conditions: List[AggregationCondition] = field(default_factory=list)
    aggregation_type: AggregationType = AggregationType.SIMPLE
    by_fields: List[str] = field(default_factory=list)
    time_window: Optional[str] = None
    nested_aggregations: List['AdvancedAggregation'] = field(default_factory=list)
    
    def to_spl(self) -> str:
        """Convert aggregation to SPL syntax"""
        if self.aggregation_type == AggregationType.CONDITIONAL:
            return self._generate_conditional_spl()
        elif self.aggregation_type == AggregationType.STATISTICAL:
            return self._generate_statistical_spl()
        elif self.aggregation_type == AggregationType.TEMPORAL:
            return self._generate_temporal_spl()
        elif self.aggregation_type == AggregationType.NESTED:
            return self._generate_nested_spl()
        else:
            return self._generate_basic_spl()
    
    def _generate_basic_spl(self) -> str:
        """Generate basic aggregation SPL"""
        func_name = self.function.value
        
        # Handle field specification
        if self.fields:
            if len(self.fields) == 1:
                field_spec = self.fields[0]
            else:
                field_spec = f"({', '.join(self.fields)})"
        else:
            field_spec = ""
        
        # Handle parameters
        param_str = ""
        if self.parameters:
            param_parts = []
            for param in self.parameters:
                if param.parameter_type == "field":
                    param_parts.append(f"{param.name}={param.value}")
                else:
                    param_parts.append(f"{param.name}={param.value}")
            if param_parts:
                param_str = f"({', '.join(param_parts)})"
        
        # Construct function call
        if field_spec:
            func_call = f"{func_name}({field_spec})"
        else:
            func_call = func_name
        
        if param_str:
            func_call = f"{func_name}{param_str}"
        
        # Add alias
        if self.alias:
            func_call = f"{func_call} as {self.alias}"
        
        return func_call
    
    def _generate_conditional_spl(self) -> str:
        """Generate conditional aggregation SPL"""
        if self.function in [AggregationFunction.COUNT_IF, AggregationFunction.SUM_IF, AggregationFunction.AVG_IF]:
            base_func = self.function.value.replace("_if", "")
            
            # Build condition expression
            condition_parts = []
            for condition in self.conditions:
                if condition.operator == "=":
                    condition_parts.append(f"{condition.field}=\"{condition.value}\"")
                elif condition.operator == ">":
                    condition_parts.append(f"{condition.field}>{condition.value}")
                elif condition.operator == "<":
                    condition_parts.append(f"{condition.field}<{condition.value}")
                elif condition.operator == "contains":
                    condition_parts.append(f"like({condition.field}, \"%{condition.value}%\")")
                else:
                    condition_parts.append(f"{condition.field}{condition.operator}{condition.value}")
            
            condition_expr = " AND ".join(condition_parts)
            
            # Generate conditional expression
            if self.fields:
                field_spec = self.fields[0]
                if base_func == "count":
                    func_call = f"count(eval(if({condition_expr}, {field_spec}, null())))"
                else:
                    func_call = f"{base_func}(eval(if({condition_expr}, {field_spec}, null())))"
            else:
                func_call = f"count(eval(if({condition_expr}, 1, null())))"
            
            if self.alias:
                func_call = f"{func_call} as {self.alias}"
            
            return func_call
        
        return self._generate_basic_spl()
    
    def _generate_statistical_spl(self) -> str:
        """Generate statistical aggregation SPL"""
        func_name = self.function.value
        
        if self.function == AggregationFunction.PERCENTILE:
            # Handle percentile function
            percentile_value = 50  # default
            for param in self.parameters:
                if param.name == "percentile":
                    percentile_value = param.value
            
            if self.fields:
                func_call = f"perc{percentile_value}({self.fields[0]})"
            else:
                func_call = f"perc{percentile_value}(_time)"
        elif self.function == AggregationFunction.RANGE:
            # Handle range function (max - min)
            if self.fields:
                field = self.fields[0]
                func_call = f"range({field})"
            else:
                func_call = "range(_time)"
        else:
            func_call = self._generate_basic_spl()
        
        if self.alias:
            func_call = f"{func_call} as {self.alias}"
        
        return func_call
    
    def _generate_temporal_spl(self) -> str:
        """Generate temporal aggregation SPL"""
        if self.function == AggregationFunction.RATE:
            # Handle rate calculation
            if self.fields:
                field = self.fields[0]
                func_call = f"rate({field})"
            else:
                func_call = "rate(count)"
        elif self.function in [AggregationFunction.EARLIEST, AggregationFunction.LATEST]:
            # Handle earliest/latest functions
            if self.fields:
                field = self.fields[0]
                func_call = f"{self.function.value}({field})"
            else:
                func_call = f"{self.function.value}(_time)"
        else:
            func_call = self._generate_basic_spl()
        
        if self.alias:
            func_call = f"{func_call} as {self.alias}"
        
        return func_call
    
    def _generate_nested_spl(self) -> str:
        """Generate nested aggregation SPL"""
        # For nested aggregations, we need to create multiple stats commands
        main_func = self._generate_basic_spl()
        
        if self.nested_aggregations:
            nested_parts = []
            for nested_agg in self.nested_aggregations:
                nested_parts.append(nested_agg.to_spl())
            
            if nested_parts:
                return f"{main_func}, {', '.join(nested_parts)}"
        
        return main_func


class AdvancedAggregationHandler:
    """Advanced aggregation handler for natural language processing"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Initialize advanced aggregation patterns
        self.aggregation_patterns = self._initialize_aggregation_patterns()
        self.statistical_patterns = self._initialize_statistical_patterns()
        self.temporal_patterns = self._initialize_temporal_patterns()
        self.conditional_patterns = self._initialize_conditional_patterns()
        
        # Initialize function mappings
        self.function_mappings = self._initialize_function_mappings()
        self.parameter_mappings = self._initialize_parameter_mappings()
    
    def _initialize_aggregation_patterns(self) -> Dict[str, Any]:
        """Initialize aggregation detection patterns"""
        return {
            # Multi-field aggregations
            "multi_field": {
                "patterns": [
                    r"(?:sum|total|add)\s+(?:of\s+)?(.+?)\s+(?:and|,)\s+(.+?)(?:\s+by|\s+group|$)",
                    r"(?:average|mean)\s+(?:of\s+)?(.+?)\s+(?:and|,)\s+(.+?)(?:\s+by|\s+group|$)",
                    r"(?:count|number)\s+(?:of\s+)?(.+?)\s+(?:and|,)\s+(.+?)(?:\s+by|\s+group|$)"
                ],
                "type": AggregationType.MULTI_FIELD
            },
            
            # Multi-function aggregations
            "multi_function": {
                "patterns": [
                    r"(?:sum|total)\s+(?:and|,)\s+(?:count|number)\s+(?:of\s+)?(.+)",
                    r"(?:average|mean)\s+(?:and|,)\s+(?:max|maximum)\s+(?:of\s+)?(.+)",
                    r"(?:min|minimum)\s+(?:and|,)\s+(?:max|maximum)\s+(?:of\s+)?(.+)"
                ],
                "type": AggregationType.MULTI_FUNCTION
            },
            
            # Complex aggregations
            "complex": {
                "patterns": [
                    r"(?:sum|total)\s+(?:of\s+)?(.+?)\s+(?:and|,)\s+(?:count|number)\s+(?:of\s+)?(.+?)\s+(?:by|group by)\s+(.+)",
                    r"(?:average|mean)\s+(?:of\s+)?(.+?)\s+(?:and|,)\s+(?:standard deviation|stdev)\s+(?:of\s+)?(.+?)\s+(?:by|group by)\s+(.+)"
                ],
                "type": AggregationType.COMPLEX
            }
        }
    
    def _initialize_statistical_patterns(self) -> Dict[str, Any]:
        """Initialize statistical function patterns"""
        return {
            # Percentile patterns
            "percentile": {
                "patterns": [
                    r"(\d+)(?:th|st|nd|rd)?\s+percentile\s+(?:of\s+)?(.+)",
                    r"percentile\s+(\d+)\s+(?:of\s+)?(.+)",
                    r"p(\d+)\s+(?:of\s+)?(.+)"
                ],
                "function": AggregationFunction.PERCENTILE,
                "extract_parameter": True
            },
            
            # Statistical measures
            "statistical": {
                "patterns": [
                    r"(?:standard deviation|stdev)\s+(?:of\s+)?(.+)",
                    r"(?:variance|var)\s+(?:of\s+)?(.+)",
                    r"(?:median)\s+(?:of\s+)?(.+)",
                    r"(?:range)\s+(?:of\s+)?(.+)"
                ],
                "functions": {
                    "standard deviation": AggregationFunction.STDEV,
                    "stdev": AggregationFunction.STDEV,
                    "variance": AggregationFunction.VAR,
                    "var": AggregationFunction.VAR,
                    "median": AggregationFunction.MEDIAN,
                    "range": AggregationFunction.RANGE
                }
            }
        }
    
    def _initialize_temporal_patterns(self) -> Dict[str, Any]:
        """Initialize temporal aggregation patterns"""
        return {
            # Time-based aggregations
            "temporal": {
                "patterns": [
                    r"(?:rate|per second|per minute|per hour)\s+(?:of\s+)?(.+)",
                    r"(?:earliest|first)\s+(?:value\s+)?(?:of\s+)?(.+)",
                    r"(?:latest|last)\s+(?:value\s+)?(?:of\s+)?(.+)",
                    r"(?:over time|timeline|trend)\s+(?:of\s+)?(.+)"
                ],
                "functions": {
                    "rate": AggregationFunction.RATE,
                    "per second": AggregationFunction.RATE,
                    "per minute": AggregationFunction.RATE,
                    "per hour": AggregationFunction.RATE,
                    "earliest": AggregationFunction.EARLIEST,
                    "first": AggregationFunction.FIRST,
                    "latest": AggregationFunction.LATEST,
                    "last": AggregationFunction.LAST
                }
            },
            
            # Windowed aggregations
            "windowed": {
                "patterns": [
                    r"(.+)\s+(?:in|over)\s+(?:last|past)\s+(\d+)\s+(minute|hour|day|week)s?",
                    r"(.+)\s+(?:every|per)\s+(\d+)\s+(minute|hour|day)s?",
                    r"(.+)\s+(?:with|using)\s+(\d+)\s+(minute|hour|day)\s+(?:window|span)"
                ],
                "type": AggregationType.TEMPORAL
            }
        }
    
    def _initialize_conditional_patterns(self) -> Dict[str, Any]:
        """Initialize conditional aggregation patterns"""
        return {
            # Conditional aggregations
            "conditional": {
                "patterns": [
                    r"(?:count|number)\s+(?:of\s+)?(.+?)\s+(?:where|if)\s+(.+)",
                    r"(?:sum|total)\s+(?:of\s+)?(.+?)\s+(?:where|if)\s+(.+)",
                    r"(?:average|mean)\s+(?:of\s+)?(.+?)\s+(?:where|if)\s+(.+)",
                    r"(?:count|number)\s+(?:of\s+)?(.+?)\s+(?:that|which)\s+(.+)"
                ],
                "functions": {
                    "count": AggregationFunction.COUNT_IF,
                    "number": AggregationFunction.COUNT_IF,
                    "sum": AggregationFunction.SUM_IF,
                    "total": AggregationFunction.SUM_IF,
                    "average": AggregationFunction.AVG_IF,
                    "mean": AggregationFunction.AVG_IF
                }
            },
            
            # Case-based aggregations
            "case_based": {
                "patterns": [
                    r"(?:sum|total)\s+(?:of\s+)?(.+?)\s+(?:when|case)\s+(.+)",
                    r"(?:count|number)\s+(?:of\s+)?(.+?)\s+(?:when|case)\s+(.+)"
                ],
                "type": AggregationType.CONDITIONAL
            }
        }
    
    def _initialize_function_mappings(self) -> Dict[str, AggregationFunction]:
        """Initialize function name mappings"""
        return {
            # Basic functions
            "count": AggregationFunction.COUNT,
            "number": AggregationFunction.COUNT,
            "how many": AggregationFunction.COUNT,
            "sum": AggregationFunction.SUM,
            "total": AggregationFunction.SUM,
            "add": AggregationFunction.SUM,
            "average": AggregationFunction.AVG,
            "mean": AggregationFunction.AVG,
            "avg": AggregationFunction.AVG,
            "maximum": AggregationFunction.MAX,
            "max": AggregationFunction.MAX,
            "highest": AggregationFunction.MAX,
            "minimum": AggregationFunction.MIN,
            "min": AggregationFunction.MIN,
            "lowest": AggregationFunction.MIN,
            
            # Statistical functions
            "standard deviation": AggregationFunction.STDEV,
            "stdev": AggregationFunction.STDEV,
            "variance": AggregationFunction.VAR,
            "var": AggregationFunction.VAR,
            "median": AggregationFunction.MEDIAN,
            "range": AggregationFunction.RANGE,
            "percentile": AggregationFunction.PERCENTILE,
            
            # Advanced functions
            "first": AggregationFunction.FIRST,
            "last": AggregationFunction.LAST,
            "earliest": AggregationFunction.EARLIEST,
            "latest": AggregationFunction.LATEST,
            "values": AggregationFunction.VALUES,
            "list": AggregationFunction.LIST,
            "rate": AggregationFunction.RATE
        }
    
    def _initialize_parameter_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Initialize parameter mappings for functions"""
        return {
            "percentile": {
                "parameters": ["percentile_value"],
                "defaults": {"percentile_value": 50},
                "patterns": [r"(\d+)(?:th|st|nd|rd)?\s+percentile"]
            },
            "rate": {
                "parameters": ["time_unit"],
                "defaults": {"time_unit": "second"},
                "patterns": [r"per\s+(second|minute|hour|day)"]
            },
            "values": {
                "parameters": ["delimiter"],
                "defaults": {"delimiter": ","},
                "patterns": [r"(?:delimited|separated)\s+by\s+[\"']([^\"']+)[\"']"]
            }
        }
    
    def detect_aggregations(self, query: str) -> List[AdvancedAggregation]:
        """Detect advanced aggregations from natural language query"""
        query_lower = query.lower()
        detected_aggregations = []
        
        try:
            # Check for statistical patterns
            statistical_aggs = self._detect_statistical_aggregations(query_lower)
            detected_aggregations.extend(statistical_aggs)
            
            # Check for temporal patterns
            temporal_aggs = self._detect_temporal_aggregations(query_lower)
            detected_aggregations.extend(temporal_aggs)
            
            # Check for conditional patterns
            conditional_aggs = self._detect_conditional_aggregations(query_lower)
            detected_aggregations.extend(conditional_aggs)
            
            # Check for multi-field/multi-function patterns
            complex_aggs = self._detect_complex_aggregations(query_lower)
            detected_aggregations.extend(complex_aggs)
            
            # If no advanced aggregations found, fall back to basic detection
            if not detected_aggregations:
                basic_aggs = self._detect_basic_aggregations(query_lower)
                detected_aggregations.extend(basic_aggs)
            
            self.logger.info(f"Detected {len(detected_aggregations)} aggregations", query=query[:100])
            
            return detected_aggregations
            
        except Exception as e:
            self.logger.error(f"Aggregation detection failed: {e}")
            return []
    
    def _detect_statistical_aggregations(self, query: str) -> List[AdvancedAggregation]:
        """Detect statistical aggregations"""
        aggregations = []
        
        # Check percentile patterns
        for pattern in self.statistical_patterns["percentile"]["patterns"]:
            matches = re.finditer(pattern, query)
            for match in matches:
                if len(match.groups()) >= 2:
                    percentile_value = int(match.group(1))
                    field = match.group(2).strip()
                    
                    # Map field if possible
                    field_mapping = spl_mapper.find_field_mapping(field)
                    if field_mapping:
                        field = field_mapping.splunk_field
                    
                    aggregations.append(AdvancedAggregation(
                        function=AggregationFunction.PERCENTILE,
                        fields=[field],
                        parameters=[AggregationParameter("percentile", percentile_value)],
                        aggregation_type=AggregationType.STATISTICAL,
                        alias=f"p{percentile_value}_{field}"
                    ))
        
        # Check other statistical functions
        for func_name, func_enum in self.statistical_patterns["statistical"]["functions"].items():
            for pattern in self.statistical_patterns["statistical"]["patterns"]:
                if func_name in pattern:
                    matches = re.finditer(pattern, query)
                    for match in matches:
                        field = match.group(1).strip()
                        
                        # Map field if possible
                        field_mapping = spl_mapper.find_field_mapping(field)
                        if field_mapping:
                            field = field_mapping.splunk_field
                        
                        aggregations.append(AdvancedAggregation(
                            function=func_enum,
                            fields=[field],
                            aggregation_type=AggregationType.STATISTICAL,
                            alias=f"{func_name}_{field}"
                        ))
        
        return aggregations
    
    def _detect_temporal_aggregations(self, query: str) -> List[AdvancedAggregation]:
        """Detect temporal aggregations"""
        aggregations = []
        
        # Check temporal function patterns
        for func_name, func_enum in self.temporal_patterns["temporal"]["functions"].items():
            for pattern in self.temporal_patterns["temporal"]["patterns"]:
                if func_name in pattern:
                    matches = re.finditer(pattern, query)
                    for match in matches:
                        field = match.group(1).strip()
                        
                        # Map field if possible
                        field_mapping = spl_mapper.find_field_mapping(field)
                        if field_mapping:
                            field = field_mapping.splunk_field
                        
                        aggregations.append(AdvancedAggregation(
                            function=func_enum,
                            fields=[field],
                            aggregation_type=AggregationType.TEMPORAL,
                            alias=f"{func_name}_{field}"
                        ))
        
        # Check windowed aggregations
        for pattern in self.temporal_patterns["windowed"]["patterns"]:
            matches = re.finditer(pattern, query)
            for match in matches:
                if len(match.groups()) >= 3:
                    aggregation_desc = match.group(1).strip()
                    window_size = match.group(2)
                    window_unit = match.group(3)
                    
                    # Extract function and field from description
                    function, field = self._extract_function_and_field(aggregation_desc)
                    
                    if function and field:
                        time_window = f"{window_size}{window_unit[0]}"  # e.g., "1h", "5m"
                        
                        aggregations.append(AdvancedAggregation(
                            function=function,
                            fields=[field],
                            aggregation_type=AggregationType.TEMPORAL,
                            time_window=time_window,
                            alias=f"{function.value}_{field}_{time_window}"
                        ))
        
        return aggregations
    
    def _detect_conditional_aggregations(self, query: str) -> List[AdvancedAggregation]:
        """Detect conditional aggregations"""
        aggregations = []
        
        # Check conditional patterns
        for func_name, func_enum in self.conditional_patterns["conditional"]["functions"].items():
            for pattern in self.conditional_patterns["conditional"]["patterns"]:
                if func_name in pattern:
                    matches = re.finditer(pattern, query)
                    for match in matches:
                        if len(match.groups()) >= 2:
                            field = match.group(1).strip()
                            condition_text = match.group(2).strip()
                            
                            # Map field if possible
                            field_mapping = spl_mapper.find_field_mapping(field)
                            if field_mapping:
                                field = field_mapping.splunk_field
                            
                            # Parse condition
                            conditions = self._parse_condition(condition_text)
                            
                            aggregations.append(AdvancedAggregation(
                                function=func_enum,
                                fields=[field],
                                conditions=conditions,
                                aggregation_type=AggregationType.CONDITIONAL,
                                alias=f"{func_name}_{field}_conditional"
                            ))
        
        return aggregations
    
    def _detect_complex_aggregations(self, query: str) -> List[AdvancedAggregation]:
        """Detect complex multi-field or multi-function aggregations"""
        aggregations = []
        
        # Check multi-field patterns
        for pattern in self.aggregation_patterns["multi_field"]["patterns"]:
            matches = re.finditer(pattern, query)
            for match in matches:
                if len(match.groups()) >= 2:
                    field1 = match.group(1).strip()
                    field2 = match.group(2).strip()
                    
                    # Map fields if possible
                    field1_mapping = spl_mapper.find_field_mapping(field1)
                    if field1_mapping:
                        field1 = field1_mapping.splunk_field
                    
                    field2_mapping = spl_mapper.find_field_mapping(field2)
                    if field2_mapping:
                        field2 = field2_mapping.splunk_field
                    
                    # Determine function from pattern
                    function = self._determine_function_from_pattern(pattern)
                    
                    if function:
                        aggregations.append(AdvancedAggregation(
                            function=function,
                            fields=[field1, field2],
                            aggregation_type=AggregationType.MULTI_FIELD,
                            alias=f"{function.value}_multi_field"
                        ))
        
        # Check multi-function patterns
        for pattern in self.aggregation_patterns["multi_function"]["patterns"]:
            matches = re.finditer(pattern, query)
            for match in matches:
                field = match.group(1).strip()
                
                # Map field if possible
                field_mapping = spl_mapper.find_field_mapping(field)
                if field_mapping:
                    field = field_mapping.splunk_field
                
                # Extract multiple functions from pattern
                functions = self._extract_multiple_functions(pattern)
                
                for function in functions:
                    aggregations.append(AdvancedAggregation(
                        function=function,
                        fields=[field],
                        aggregation_type=AggregationType.MULTI_FUNCTION,
                        alias=f"{function.value}_{field}"
                    ))
        
        return aggregations
    
    def _detect_basic_aggregations(self, query: str) -> List[AdvancedAggregation]:
        """Detect basic aggregations as fallback"""
        aggregations = []
        
        # Use existing SPL mapper for basic detection
        for natural_func, spl_func in spl_mapper.aggregation_mappings.items():
            if natural_func in query:
                # Try to extract field
                field_pattern = rf"{re.escape(natural_func)}\s+(?:of\s+)?(\w+)"
                match = re.search(field_pattern, query)
                
                if match:
                    field = match.group(1)
                    
                    # Map field if possible
                    field_mapping = spl_mapper.find_field_mapping(field)
                    if field_mapping:
                        field = field_mapping.splunk_field
                    
                    # Map function
                    function = self._map_spl_function_to_enum(spl_func)
                    
                    if function:
                        aggregations.append(AdvancedAggregation(
                            function=function,
                            fields=[field],
                            aggregation_type=AggregationType.SIMPLE,
                            alias=f"{spl_func}_{field}"
                        ))
        
        return aggregations
    
    def _extract_function_and_field(self, description: str) -> Tuple[Optional[AggregationFunction], Optional[str]]:
        """Extract function and field from description"""
        description = description.lower()
        
        # Check for function keywords
        for func_name, func_enum in self.function_mappings.items():
            if func_name in description:
                # Extract field after function
                field_pattern = rf"{re.escape(func_name)}\s+(?:of\s+)?(\w+)"
                match = re.search(field_pattern, description)
                
                if match:
                    field = match.group(1)
                    
                    # Map field if possible
                    field_mapping = spl_mapper.find_field_mapping(field)
                    if field_mapping:
                        field = field_mapping.splunk_field
                    
                    return func_enum, field
        
        return None, None
    
    def _parse_condition(self, condition_text: str) -> List[AggregationCondition]:
        """Parse condition text into structured conditions"""
        conditions = []
        
        # Simple condition parsing
        condition_patterns = [
            r"(\w+)\s*=\s*[\"']([^\"']+)[\"']",
            r"(\w+)\s*=\s*(\w+)",
            r"(\w+)\s*>\s*(\d+)",
            r"(\w+)\s*<\s*(\d+)",
            r"(\w+)\s+contains\s+[\"']([^\"']+)[\"']",
            r"(\w+)\s+like\s+[\"']([^\"']+)[\"']"
        ]
        
        for pattern in condition_patterns:
            matches = re.finditer(pattern, condition_text)
            for match in matches:
                field = match.group(1)
                value = match.group(2)
                
                # Determine operator
                if "=" in match.group(0):
                    operator = "="
                elif ">" in match.group(0):
                    operator = ">"
                elif "<" in match.group(0):
                    operator = "<"
                elif "contains" in match.group(0) or "like" in match.group(0):
                    operator = "contains"
                else:
                    operator = "="
                
                # Map field if possible
                field_mapping = spl_mapper.find_field_mapping(field)
                if field_mapping:
                    field = field_mapping.splunk_field
                
                conditions.append(AggregationCondition(
                    field=field,
                    operator=operator,
                    value=value
                ))
        
        return conditions
    
    def _determine_function_from_pattern(self, pattern: str) -> Optional[AggregationFunction]:
        """Determine function from pattern"""
        pattern_lower = pattern.lower()
        
        if "sum" in pattern_lower or "total" in pattern_lower:
            return AggregationFunction.SUM
        elif "count" in pattern_lower or "number" in pattern_lower:
            return AggregationFunction.COUNT
        elif "average" in pattern_lower or "mean" in pattern_lower:
            return AggregationFunction.AVG
        elif "max" in pattern_lower or "maximum" in pattern_lower:
            return AggregationFunction.MAX
        elif "min" in pattern_lower or "minimum" in pattern_lower:
            return AggregationFunction.MIN
        
        return None
    
    def _extract_multiple_functions(self, pattern: str) -> List[AggregationFunction]:
        """Extract multiple functions from pattern"""
        functions = []
        pattern_lower = pattern.lower()
        
        if "sum" in pattern_lower or "total" in pattern_lower:
            functions.append(AggregationFunction.SUM)
        if "count" in pattern_lower or "number" in pattern_lower:
            functions.append(AggregationFunction.COUNT)
        if "average" in pattern_lower or "mean" in pattern_lower:
            functions.append(AggregationFunction.AVG)
        if "max" in pattern_lower or "maximum" in pattern_lower:
            functions.append(AggregationFunction.MAX)
        if "min" in pattern_lower or "minimum" in pattern_lower:
            functions.append(AggregationFunction.MIN)
        
        return functions
    
    def _map_spl_function_to_enum(self, spl_func: str) -> Optional[AggregationFunction]:
        """Map SPL function string to enum"""
        mapping = {
            "count": AggregationFunction.COUNT,
            "sum": AggregationFunction.SUM,
            "avg": AggregationFunction.AVG,
            "max": AggregationFunction.MAX,
            "min": AggregationFunction.MIN,
            "stdev": AggregationFunction.STDEV,
            "var": AggregationFunction.VAR,
            "median": AggregationFunction.MEDIAN,
            "range": AggregationFunction.RANGE,
            "perc": AggregationFunction.PERCENTILE,
            "first": AggregationFunction.FIRST,
            "last": AggregationFunction.LAST,
            "earliest": AggregationFunction.EARLIEST,
            "latest": AggregationFunction.LATEST,
            "values": AggregationFunction.VALUES,
            "list": AggregationFunction.LIST,
            "rate": AggregationFunction.RATE
        }
        
        return mapping.get(spl_func)
    
    def generate_aggregation_spl(self, aggregations: List[AdvancedAggregation], by_fields: List[str] = None) -> str:
        """Generate complete SPL for aggregations"""
        if not aggregations:
            return ""
        
        # Generate individual aggregation expressions
        agg_expressions = []
        for agg in aggregations:
            agg_expr = agg.to_spl()
            if agg_expr:
                agg_expressions.append(agg_expr)
        
        if not agg_expressions:
            return ""
        
        # Combine into stats command
        stats_cmd = f"stats {', '.join(agg_expressions)}"
        
        # Add by clause if specified
        if by_fields:
            stats_cmd += f" by {', '.join(by_fields)}"
        
        return stats_cmd
    
    def optimize_aggregations(self, aggregations: List[AdvancedAggregation]) -> List[AdvancedAggregation]:
        """Optimize aggregations for better performance"""
        optimized = []
        
        for agg in aggregations:
            # Create optimized copy
            optimized_agg = AdvancedAggregation(
                function=agg.function,
                fields=agg.fields.copy(),
                alias=agg.alias,
                parameters=agg.parameters.copy(),
                conditions=agg.conditions.copy(),
                aggregation_type=agg.aggregation_type,
                by_fields=agg.by_fields.copy(),
                time_window=agg.time_window,
                nested_aggregations=agg.nested_aggregations.copy()
            )
            
            # Apply optimizations
            if agg.aggregation_type == AggregationType.CONDITIONAL:
                # Optimize conditional aggregations
                optimized_agg = self._optimize_conditional_aggregation(optimized_agg)
            elif agg.aggregation_type == AggregationType.STATISTICAL:
                # Optimize statistical aggregations
                optimized_agg = self._optimize_statistical_aggregation(optimized_agg)
            elif agg.aggregation_type == AggregationType.TEMPORAL:
                # Optimize temporal aggregations
                optimized_agg = self._optimize_temporal_aggregation(optimized_agg)
            
            optimized.append(optimized_agg)
        
        return optimized
    
    def _optimize_conditional_aggregation(self, agg: AdvancedAggregation) -> AdvancedAggregation:
        """Optimize conditional aggregation"""
        # Simplify conditions if possible
        if len(agg.conditions) == 1:
            condition = agg.conditions[0]
            if condition.operator == "=" and condition.value in ["true", "1", "yes"]:
                # Simplify boolean conditions
                agg.conditions = []
                if agg.fields:
                    agg.fields = [condition.field]
        
        return agg
    
    def _optimize_statistical_aggregation(self, agg: AdvancedAggregation) -> AdvancedAggregation:
        """Optimize statistical aggregation"""
        # Add appropriate aliases for statistical functions
        if agg.function == AggregationFunction.PERCENTILE and not agg.alias:
            percentile_value = 50
            for param in agg.parameters:
                if param.name == "percentile":
                    percentile_value = param.value
            agg.alias = f"p{percentile_value}"
        elif agg.function == AggregationFunction.STDEV and not agg.alias:
            agg.alias = "stdev"
        elif agg.function == AggregationFunction.VAR and not agg.alias:
            agg.alias = "variance"
        
        return agg
    
    def _optimize_temporal_aggregation(self, agg: AdvancedAggregation) -> AdvancedAggregation:
        """Optimize temporal aggregation"""
        # Add time window to alias if present
        if agg.time_window and agg.alias:
            agg.alias = f"{agg.alias}_{agg.time_window}"
        
        return agg


# Global instance
advanced_aggregation_handler = AdvancedAggregationHandler()