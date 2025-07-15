"""
Eval and Calculated Fields System for SPL Translation

This module provides comprehensive support for eval expressions and calculated fields including:
- Natural language to eval expression conversion
- Mathematical and logical expression parsing
- String manipulation and formatting functions
- Date/time calculations and field transformations
- Conditional logic and case statements
- Advanced data type conversions and validations
"""

import re
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime

from ..core.logging import get_logger
from .spl_mapping import spl_mapper, FieldType

logger = get_logger(__name__)


class EvalFunctionType(Enum):
    """Types of eval functions"""
    MATHEMATICAL = "mathematical"           # Math operations (+, -, *, /, pow, sqrt, etc.)
    STRING = "string"                      # String functions (substr, len, upper, lower, etc.)
    DATETIME = "datetime"                  # Date/time functions (strftime, strptime, now, etc.)
    CONDITIONAL = "conditional"            # Conditional logic (if, case, coalesce, etc.)
    COMPARISON = "comparison"              # Comparison operations (=, !=, <, >, like, etc.)
    LOGICAL = "logical"                    # Logical operations (AND, OR, NOT, XOR)
    CONVERSION = "conversion"              # Type conversions (tonumber, tostring, etc.)
    VALIDATION = "validation"              # Data validation (isnull, isnotnull, etc.)
    AGGREGATION = "aggregation"            # Aggregation helpers (mvcount, mvindex, etc.)
    NETWORKING = "networking"              # Network functions (cidrmatch, etc.)


class ExpressionComplexity(Enum):
    """Complexity levels for eval expressions"""
    SIMPLE = "simple"                      # Single operation or function
    MODERATE = "moderate"                  # Multiple operations with basic logic
    COMPLEX = "complex"                    # Nested functions and conditional logic
    ADVANCED = "advanced"                  # Multiple nested conditions and complex calculations


@dataclass
class EvalFunction:
    """Eval function definition"""
    name: str
    function_type: EvalFunctionType
    syntax: str
    description: str
    parameters: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    return_type: FieldType = FieldType.STRING
    complexity: ExpressionComplexity = ExpressionComplexity.SIMPLE
    performance_notes: Optional[str] = None


@dataclass
class EvalExpression:
    """Eval expression specification"""
    field_name: str
    expression: str
    expression_type: EvalFunctionType
    complexity: ExpressionComplexity
    description: str
    dependencies: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    validation_rules: List[str] = field(default_factory=list)


@dataclass
class CalculatedField:
    """Calculated field definition"""
    name: str
    expression: str
    source_fields: List[str]
    field_type: FieldType
    description: str
    is_persistent: bool = False
    validation_expression: Optional[str] = None
    default_value: Optional[str] = None
    format_pattern: Optional[str] = None


@dataclass
class EvalTranslation:
    """Result of eval expression translation"""
    spl_command: str
    eval_expression: EvalExpression
    confidence: float
    explanation: str
    optimization_suggestions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    performance_notes: List[str] = field(default_factory=list)


class EvalCalculatedFieldsMapper:
    """Comprehensive eval and calculated fields system"""
    
    def __init__(self):
        self.eval_functions = self._initialize_eval_functions()
        self.expression_patterns = self._initialize_expression_patterns()
        self.calculation_mappings = self._initialize_calculation_mappings()
        self.field_transformations = self._initialize_field_transformations()
        self.common_expressions = self._initialize_common_expressions()
        
    def _initialize_eval_functions(self) -> Dict[str, EvalFunction]:
        """Initialize comprehensive eval function mappings"""
        functions = {}
        
        # Mathematical Functions
        functions["abs"] = EvalFunction(
            name="abs",
            function_type=EvalFunctionType.MATHEMATICAL,
            syntax="abs(X)",
            description="Return absolute value of X",
            parameters=["X"],
            examples=["abs(-5)", "abs(temperature - 32)"],
            return_type=FieldType.NUMBER
        )
        
        functions["ceil"] = EvalFunction(
            name="ceil",
            function_type=EvalFunctionType.MATHEMATICAL,
            syntax="ceil(X)",
            description="Return ceiling (round up) of X",
            parameters=["X"],
            examples=["ceil(3.2)", "ceil(response_time)"],
            return_type=FieldType.NUMBER
        )
        
        functions["floor"] = EvalFunction(
            name="floor",
            function_type=EvalFunctionType.MATHEMATICAL,
            syntax="floor(X)",
            description="Return floor (round down) of X",
            parameters=["X"],
            examples=["floor(3.8)", "floor(price)"],
            return_type=FieldType.NUMBER
        )
        
        functions["round"] = EvalFunction(
            name="round",
            function_type=EvalFunctionType.MATHEMATICAL,
            syntax="round(X, Y)",
            description="Round X to Y decimal places",
            parameters=["X", "Y"],
            examples=["round(3.14159, 2)", "round(avg_response, 1)"],
            return_type=FieldType.NUMBER
        )
        
        functions["pow"] = EvalFunction(
            name="pow",
            function_type=EvalFunctionType.MATHEMATICAL,
            syntax="pow(X, Y)",
            description="Return X raised to power Y",
            parameters=["X", "Y"],
            examples=["pow(2, 3)", "pow(base, exponent)"],
            aliases=["power"],
            return_type=FieldType.NUMBER
        )
        
        functions["sqrt"] = EvalFunction(
            name="sqrt",
            function_type=EvalFunctionType.MATHEMATICAL,
            syntax="sqrt(X)",
            description="Return square root of X",
            parameters=["X"],
            examples=["sqrt(16)", "sqrt(variance)"],
            return_type=FieldType.NUMBER
        )
        
        # String Functions
        functions["len"] = EvalFunction(
            name="len",
            function_type=EvalFunctionType.STRING,
            syntax="len(str)",
            description="Return length of string",
            parameters=["str"],
            examples=["len(message)", "len(user_name)"],
            aliases=["length"],
            return_type=FieldType.NUMBER
        )
        
        functions["upper"] = EvalFunction(
            name="upper",
            function_type=EvalFunctionType.STRING,
            syntax="upper(str)",
            description="Convert string to uppercase",
            parameters=["str"],
            examples=["upper(status)", "upper(user_name)"],
            aliases=["ucase"],
            return_type=FieldType.STRING
        )
        
        functions["lower"] = EvalFunction(
            name="lower",
            function_type=EvalFunctionType.STRING,
            syntax="lower(str)",
            description="Convert string to lowercase",
            parameters=["str"],
            examples=["lower(METHOD)", "lower(hostname)"],
            aliases=["lcase"],
            return_type=FieldType.STRING
        )
        
        functions["substr"] = EvalFunction(
            name="substr",
            function_type=EvalFunctionType.STRING,
            syntax="substr(str, start, length)",
            description="Extract substring from string",
            parameters=["str", "start", "length"],
            examples=["substr(message, 1, 10)", "substr(user_id, 4, 8)"],
            aliases=["substring"],
            return_type=FieldType.STRING
        )
        
        functions["replace"] = EvalFunction(
            name="replace",
            function_type=EvalFunctionType.STRING,
            syntax="replace(str, old, new)",
            description="Replace occurrences of old with new in string",
            parameters=["str", "old", "new"],
            examples=["replace(message, \"error\", \"ERROR\")", "replace(path, \"/\", \"_\")"],
            return_type=FieldType.STRING
        )
        
        functions["trim"] = EvalFunction(
            name="trim",
            function_type=EvalFunctionType.STRING,
            syntax="trim(str, chars)",
            description="Remove leading and trailing characters",
            parameters=["str", "chars"],
            examples=["trim(message)", "trim(field, \" \\t\")"],
            return_type=FieldType.STRING
        )
        
        functions["split"] = EvalFunction(
            name="split",
            function_type=EvalFunctionType.STRING,
            syntax="split(str, delim)",
            description="Split string by delimiter",
            parameters=["str", "delim"],
            examples=["split(user_roles, \",\")", "split(path, \"/\")"],
            return_type=FieldType.JSON,
            complexity=ExpressionComplexity.MODERATE
        )
        
        # DateTime Functions
        functions["now"] = EvalFunction(
            name="now",
            function_type=EvalFunctionType.DATETIME,
            syntax="now()",
            description="Return current timestamp",
            parameters=[],
            examples=["now()", "now() - _time"],
            return_type=FieldType.TIMESTAMP
        )
        
        functions["strftime"] = EvalFunction(
            name="strftime",
            function_type=EvalFunctionType.DATETIME,
            syntax="strftime(time, format)",
            description="Format timestamp as string",
            parameters=["time", "format"],
            examples=["strftime(_time, \"%Y-%m-%d\")", "strftime(timestamp, \"%H:%M:%S\")"],
            return_type=FieldType.STRING
        )
        
        functions["strptime"] = EvalFunction(
            name="strptime",
            function_type=EvalFunctionType.DATETIME,
            syntax="strptime(timestr, format)",
            description="Parse string as timestamp",
            parameters=["timestr", "format"],
            examples=["strptime(date_string, \"%Y-%m-%d\")", "strptime(log_time, \"%H:%M:%S\")"],
            return_type=FieldType.TIMESTAMP
        )
        
        functions["relative_time"] = EvalFunction(
            name="relative_time",
            function_type=EvalFunctionType.DATETIME,
            syntax="relative_time(time, spec)",
            description="Calculate relative time",
            parameters=["time", "spec"],
            examples=["relative_time(now(), \"-1d@d\")", "relative_time(_time, \"+1h\")"],
            return_type=FieldType.TIMESTAMP,
            complexity=ExpressionComplexity.MODERATE
        )
        
        # Conditional Functions
        functions["if"] = EvalFunction(
            name="if",
            function_type=EvalFunctionType.CONDITIONAL,
            syntax="if(condition, true_value, false_value)",
            description="Return value based on condition",
            parameters=["condition", "true_value", "false_value"],
            examples=["if(status=200, \"OK\", \"ERROR\")", "if(price>100, \"expensive\", \"cheap\")"],
            return_type=FieldType.STRING,
            complexity=ExpressionComplexity.MODERATE
        )
        
        functions["case"] = EvalFunction(
            name="case",
            function_type=EvalFunctionType.CONDITIONAL,
            syntax="case(condition1, value1, condition2, value2, ..., default)",
            description="Multi-condition case statement",
            parameters=["condition", "value", "default"],
            examples=["case(status<300, \"OK\", status<400, \"REDIRECT\", status<500, \"CLIENT_ERROR\", \"SERVER_ERROR\")"],
            return_type=FieldType.STRING,
            complexity=ExpressionComplexity.COMPLEX
        )
        
        functions["coalesce"] = EvalFunction(
            name="coalesce",
            function_type=EvalFunctionType.CONDITIONAL,
            syntax="coalesce(field1, field2, ..., default)",
            description="Return first non-null value",
            parameters=["field1", "field2", "default"],
            examples=["coalesce(user_name, user_id, \"unknown\")", "coalesce(primary_ip, secondary_ip, \"0.0.0.0\")"],
            return_type=FieldType.STRING,
            complexity=ExpressionComplexity.MODERATE
        )
        
        functions["nullif"] = EvalFunction(
            name="nullif",
            function_type=EvalFunctionType.CONDITIONAL,
            syntax="nullif(value1, value2)",
            description="Return null if values are equal",
            parameters=["value1", "value2"],
            examples=["nullif(response_time, 0)", "nullif(field, \"\")"],
            return_type=FieldType.STRING
        )
        
        # Conversion Functions
        functions["tonumber"] = EvalFunction(
            name="tonumber",
            function_type=EvalFunctionType.CONVERSION,
            syntax="tonumber(str, base)",
            description="Convert string to number",
            parameters=["str", "base"],
            examples=["tonumber(\"123\")", "tonumber(hex_value, 16)"],
            return_type=FieldType.NUMBER
        )
        
        functions["tostring"] = EvalFunction(
            name="tostring",
            function_type=EvalFunctionType.CONVERSION,
            syntax="tostring(value, format)",
            description="Convert value to string",
            parameters=["value", "format"],
            examples=["tostring(count)", "tostring(price, \"%.2f\")"],
            return_type=FieldType.STRING
        )
        
        # Validation Functions
        functions["isnull"] = EvalFunction(
            name="isnull",
            function_type=EvalFunctionType.VALIDATION,
            syntax="isnull(field)",
            description="Check if field is null",
            parameters=["field"],
            examples=["isnull(user_name)", "isnull(response_time)"],
            return_type=FieldType.BOOLEAN
        )
        
        functions["isnotnull"] = EvalFunction(
            name="isnotnull",
            function_type=EvalFunctionType.VALIDATION,
            syntax="isnotnull(field)",
            description="Check if field is not null",
            parameters=["field"],
            examples=["isnotnull(error_message)", "isnotnull(user_id)"],
            return_type=FieldType.BOOLEAN
        )
        
        functions["isnum"] = EvalFunction(
            name="isnum",
            function_type=EvalFunctionType.VALIDATION,
            syntax="isnum(field)",
            description="Check if field is numeric",
            parameters=["field"],
            examples=["isnum(response_time)", "isnum(port)"],
            return_type=FieldType.BOOLEAN
        )
        
        # Networking Functions
        functions["cidrmatch"] = EvalFunction(
            name="cidrmatch",
            function_type=EvalFunctionType.NETWORKING,
            syntax="cidrmatch(cidr, ip)",
            description="Check if IP matches CIDR block",
            parameters=["cidr", "ip"],
            examples=["cidrmatch(\"192.168.1.0/24\", src_ip)", "cidrmatch(subnet, client_ip)"],
            return_type=FieldType.BOOLEAN,
            complexity=ExpressionComplexity.MODERATE
        )
        
        # Multi-value Functions
        functions["mvcount"] = EvalFunction(
            name="mvcount",
            function_type=EvalFunctionType.AGGREGATION,
            syntax="mvcount(field)",
            description="Count values in multi-value field",
            parameters=["field"],
            examples=["mvcount(user_roles)", "mvcount(tags)"],
            return_type=FieldType.NUMBER
        )
        
        functions["mvindex"] = EvalFunction(
            name="mvindex",
            function_type=EvalFunctionType.AGGREGATION,
            syntax="mvindex(field, index)",
            description="Get value at index from multi-value field",
            parameters=["field", "index"],
            examples=["mvindex(user_roles, 0)", "mvindex(ip_list, -1)"],
            return_type=FieldType.STRING
        )
        
        return functions
    
    def _initialize_expression_patterns(self) -> Dict[str, List[str]]:
        """Initialize natural language patterns for eval expressions"""
        return {
            "mathematical": [
                r"calculate\s+(.+)",
                r"compute\s+(.+)",
                r"add\s+(.+?)\s+(?:and|to)\s+(.+)",
                r"subtract\s+(.+?)\s+from\s+(.+)",
                r"multiply\s+(.+?)\s+(?:by|with)\s+(.+)",
                r"divide\s+(.+?)\s+by\s+(.+)",
                r"(?:find|get)\s+(?:the\s+)?(?:sum|total)\s+of\s+(.+)",
                r"(?:find|get)\s+(?:the\s+)?(?:average|mean)\s+of\s+(.+)",
                r"(?:find|get)\s+(?:the\s+)?(?:difference|delta)\s+between\s+(.+?)\s+and\s+(.+)",
                r"(?:square|power)\s+(?:of\s+)?(.+)",
                r"(?:square\s+root|sqrt)\s+(?:of\s+)?(.+)",
                r"(?:absolute\s+value|abs)\s+(?:of\s+)?(.+)",
                r"round\s+(.+?)(?:\s+to\s+(\d+)\s+(?:decimal\s+)?places?)?"
            ],
            "string": [
                r"convert\s+(.+?)\s+to\s+(?:uppercase|upper)",
                r"convert\s+(.+?)\s+to\s+(?:lowercase|lower)",
                r"(?:get|find)\s+(?:the\s+)?length\s+of\s+(.+)",
                r"extract\s+(.+?)\s+from\s+(?:position\s+)?(\d+)(?:\s+for\s+(\d+)\s+characters?)?",
                r"replace\s+(.+?)\s+with\s+(.+?)\s+in\s+(.+)",
                r"trim\s+(.+)",
                r"split\s+(.+?)\s+by\s+(.+)",
                r"concatenate\s+(.+?)\s+(?:and|with)\s+(.+)",
                r"join\s+(.+?)\s+(?:and|with)\s+(.+)(?:\s+using\s+(.+))?"
            ],
            "datetime": [
                r"(?:current|now)\s+(?:time|timestamp|date)",
                r"format\s+(.+?)\s+as\s+(.+)",
                r"parse\s+(.+?)\s+as\s+(?:date|time|timestamp)",
                r"(?:get|extract)\s+(?:the\s+)?(?:year|month|day|hour|minute|second)\s+from\s+(.+)",
                r"add\s+(.+?)\s+(?:to|from)\s+(.+)",
                r"(?:time\s+)?difference\s+between\s+(.+?)\s+and\s+(.+)",
                r"convert\s+(.+?)\s+to\s+(?:date|time|timestamp)"
            ],
            "conditional": [
                r"if\s+(.+?)\s+then\s+(.+?)(?:\s+else\s+(.+))?",
                r"when\s+(.+?)\s+(?:is|equals?)\s+(.+?)\s+(?:then\s+)?(.+)",
                r"(?:set|assign)\s+(.+?)\s+(?:to\s+)?(.+?)\s+(?:if|when)\s+(.+)",
                r"use\s+(.+?)\s+if\s+(.+?)(?:\s+otherwise\s+(.+))?",
                r"(?:choose|select)\s+(.+?)\s+based\s+on\s+(.+)",
                r"default\s+(?:to\s+)?(.+?)\s+if\s+(.+?)\s+is\s+(?:null|empty|missing)",
                r"first\s+(?:non-)?(?:null|empty)\s+(?:value\s+)?(?:from\s+)?(.+)"
            ],
            "validation": [
                r"check\s+if\s+(.+?)\s+is\s+(?:null|empty|missing)",
                r"(?:verify|validate)\s+(?:that\s+)?(.+?)\s+is\s+(?:not\s+)?(?:null|empty|numeric|number)",
                r"(?:test|check)\s+(?:if\s+)?(.+?)\s+(?:contains|has)\s+(.+)",
                r"(?:is|check\s+if)\s+(.+?)\s+(?:a\s+)?(?:number|numeric|integer|decimal)"
            ],
            "conversion": [
                r"convert\s+(.+?)\s+to\s+(?:number|numeric|integer|string|text)",
                r"(?:parse|cast)\s+(.+?)\s+as\s+(?:number|numeric|integer|string|text)",
                r"make\s+(.+?)\s+(?:a\s+)?(?:number|numeric|string|text)"
            ]
        }
    
    def _initialize_calculation_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Initialize common calculation mappings"""
        return {
            "percentage": {
                "patterns": [
                    r"(?:calculate\s+)?(?:the\s+)?percentage\s+of\s+(.+?)\s+(?:out\s+of|from|over)\s+(.+)",
                    r"(?:what\s+)?(?:percent|%)\s+(?:of\s+)?(.+?)\s+(?:is|represents?)\s+(.+)",
                    r"(.+?)\s+as\s+(?:a\s+)?percentage\s+of\s+(.+)"
                ],
                "expression": "round(({numerator} / {denominator}) * 100, 2)",
                "description": "Calculate percentage"
            },
            "growth_rate": {
                "patterns": [
                    r"(?:growth\s+rate|change)\s+(?:of\s+)?(.+?)\s+(?:from\s+)?(.+?)\s+to\s+(.+)",
                    r"(?:percent|percentage)\s+(?:change|increase|decrease)\s+(?:in\s+)?(.+)",
                    r"(?:how\s+much\s+)?(?:did\s+)?(.+?)\s+(?:grow|change|increase|decrease)"
                ],
                "expression": "round((({new_value} - {old_value}) / {old_value}) * 100, 2)",
                "description": "Calculate growth rate percentage"
            },
            "ratio": {
                "patterns": [
                    r"ratio\s+(?:of\s+)?(.+?)\s+to\s+(.+)",
                    r"(.+?)\s+(?:divided\s+by|over)\s+(.+?)\s+ratio",
                    r"proportion\s+of\s+(.+?)\s+(?:to|vs|versus)\s+(.+)"
                ],
                "expression": "round({numerator} / {denominator}, 4)",
                "description": "Calculate ratio"
            },
            "age_calculation": {
                "patterns": [
                    r"age\s+(?:of\s+)?(.+?)(?:\s+(?:in\s+)?(?:days|hours|minutes|seconds))?",
                    r"(?:how\s+)?(?:old|long\s+ago)\s+(?:is\s+)?(.+)",
                    r"time\s+(?:since|elapsed\s+since)\s+(.+)"
                ],
                "expression": "round((now() - {timestamp}) / {time_unit}, 0)",
                "description": "Calculate time elapsed"
            },
            "score_calculation": {
                "patterns": [
                    r"(?:calculate\s+)?(?:a\s+)?score\s+(?:for\s+)?(.+?)(?:\s+based\s+on\s+(.+))?",
                    r"(?:weighted\s+)?(?:average|mean)\s+(?:of\s+)?(.+?)(?:\s+with\s+weights\s+(.+))?",
                    r"combine\s+(.+?)\s+(?:into\s+(?:a\s+)?(?:single\s+)?(?:score|value|metric))"
                ],
                "expression": "round(({field1} * {weight1} + {field2} * {weight2}) / ({weight1} + {weight2}), 2)",
                "description": "Calculate weighted score"
            }
        }
    
    def _initialize_field_transformations(self) -> Dict[str, Dict[str, Any]]:
        """Initialize field transformation mappings"""
        return {
            "status_code_category": {
                "patterns": [
                    r"categorize\s+(?:http\s+)?status\s+codes?",
                    r"(?:group|classify)\s+(?:status\s+)?(?:codes?\s+)?(?:by\s+)?(?:type|category)",
                    r"(?:http\s+)?status\s+(?:code\s+)?(?:category|type|class)"
                ],
                "expression": "case(status<300, \"Success\", status<400, \"Redirect\", status<500, \"Client Error\", \"Server Error\")",
                "description": "Categorize HTTP status codes"
            },
            "response_time_category": {
                "patterns": [
                    r"categorize\s+response\s+times?",
                    r"(?:classify|group)\s+response\s+times?\s+(?:by\s+)?(?:performance|speed)",
                    r"response\s+time\s+(?:category|performance|rating)"
                ],
                "expression": "case(response_time<100, \"Fast\", response_time<500, \"Normal\", response_time<2000, \"Slow\", \"Very Slow\")",
                "description": "Categorize response times by performance"
            },
            "severity_level": {
                "patterns": [
                    r"(?:assign\s+)?severity\s+levels?",
                    r"categorize\s+(?:by\s+)?severity",
                    r"(?:priority|criticality|severity)\s+(?:level|category|rating)"
                ],
                "expression": "case(priority=\"critical\", 1, priority=\"high\", 2, priority=\"medium\", 3, priority=\"low\", 4, 5)",
                "description": "Assign numeric severity levels"
            },
            "business_hours": {
                "patterns": [
                    r"(?:during\s+)?business\s+hours?",
                    r"(?:working|office)\s+hours?",
                    r"(?:is\s+)?(?:business|work)\s+time"
                ],
                "expression": "if(tonumber(strftime(_time, \"%H\"))>=9 AND tonumber(strftime(_time, \"%H\"))<17 AND tonumber(strftime(_time, \"%w\"))>=1 AND tonumber(strftime(_time, \"%w\"))<=5, \"Business Hours\", \"Off Hours\")",
                "description": "Classify events as business hours or off hours"
            },
            "ip_classification": {
                "patterns": [
                    r"classify\s+ip\s+addresses?",
                    r"(?:internal|external|private|public)\s+ip\s+(?:addresses?|classification)",
                    r"ip\s+(?:address\s+)?(?:type|category|class)"
                ],
                "expression": "case(cidrmatch(\"10.0.0.0/8\", ip) OR cidrmatch(\"172.16.0.0/12\", ip) OR cidrmatch(\"192.168.0.0/16\", ip), \"Internal\", \"External\")",
                "description": "Classify IP addresses as internal or external"
            }
        }
    
    def _initialize_common_expressions(self) -> Dict[str, Dict[str, Any]]:
        """Initialize common eval expressions"""
        return {
            "url_domain": {
                "expression": "replace(replace(url, \"^https?://([^/]+).*\", \"\\1\"), \"^www\\.\", \"\")",
                "description": "Extract domain from URL",
                "example": "eval domain=replace(replace(url, \"^https?://([^/]+).*\", \"\\1\"), \"^www\\.\", \"\")"
            },
            "file_extension": {
                "expression": "if(match(file_path, \"\\.[^.]+$\"), replace(file_path, \".*\\.(\\w+)$\", \"\\1\"), \"none\")",
                "description": "Extract file extension from path",
                "example": "eval extension=if(match(file_path, \"\\.[^.]+$\"), replace(file_path, \".*\\.(\\w+)$\", \"\\1\"), \"none\")"
            },
            "user_agent_browser": {
                "expression": "case(match(user_agent, \"Chrome\"), \"Chrome\", match(user_agent, \"Firefox\"), \"Firefox\", match(user_agent, \"Safari\"), \"Safari\", match(user_agent, \"Edge\"), \"Edge\", \"Other\")",
                "description": "Extract browser from user agent",
                "example": "eval browser=case(match(user_agent, \"Chrome\"), \"Chrome\", match(user_agent, \"Firefox\"), \"Firefox\", \"Other\")"
            },
            "log_level": {
                "expression": "case(match(message, \"(?i)error\"), \"ERROR\", match(message, \"(?i)warn\"), \"WARNING\", match(message, \"(?i)info\"), \"INFO\", match(message, \"(?i)debug\"), \"DEBUG\", \"UNKNOWN\")",
                "description": "Extract log level from message",
                "example": "eval log_level=case(match(message, \"(?i)error\"), \"ERROR\", match(message, \"(?i)warn\"), \"WARNING\", \"INFO\")"
            },
            "email_domain": {
                "expression": "if(match(email, \"@\"), replace(email, \".*@(.*)\", \"\\1\"), null())",
                "description": "Extract domain from email address",
                "example": "eval email_domain=if(match(email, \"@\"), replace(email, \".*@(.*)\", \"\\1\"), null())"
            }
        }
    
    def detect_eval_expressions(self, query: str) -> List[EvalExpression]:
        """Detect eval expressions from natural language"""
        query_lower = query.lower()
        detected_expressions = []
        
        # Check for mathematical expressions
        for pattern in self.expression_patterns["mathematical"]:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                expression = self._create_mathematical_expression(match, query)
                if expression:
                    detected_expressions.append(expression)
        
        # Check for string expressions
        for pattern in self.expression_patterns["string"]:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                expression = self._create_string_expression(match, query)
                if expression:
                    detected_expressions.append(expression)
        
        # Check for datetime expressions
        for pattern in self.expression_patterns["datetime"]:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                expression = self._create_datetime_expression(match, query)
                if expression:
                    detected_expressions.append(expression)
        
        # Check for conditional expressions
        for pattern in self.expression_patterns["conditional"]:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                expression = self._create_conditional_expression(match, query)
                if expression:
                    detected_expressions.append(expression)
        
        # Check for validation expressions
        for pattern in self.expression_patterns["validation"]:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                expression = self._create_validation_expression(match, query)
                if expression:
                    detected_expressions.append(expression)
        
        # Check for conversion expressions
        for pattern in self.expression_patterns["conversion"]:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                expression = self._create_conversion_expression(match, query)
                if expression:
                    detected_expressions.append(expression)
        
        # Check for common calculations
        for calc_name, calc_info in self.calculation_mappings.items():
            for pattern in calc_info["patterns"]:
                if re.search(pattern, query_lower):
                    expression = self._create_calculation_expression(calc_name, calc_info, query)
                    if expression:
                        detected_expressions.append(expression)
        
        # Check for field transformations
        for transform_name, transform_info in self.field_transformations.items():
            for pattern in transform_info["patterns"]:
                if re.search(pattern, query_lower):
                    expression = self._create_transformation_expression(transform_name, transform_info, query)
                    if expression:
                        detected_expressions.append(expression)
        
        return detected_expressions
    
    def _create_mathematical_expression(self, match: re.Match, query: str) -> Optional[EvalExpression]:
        """Create mathematical eval expression"""
        try:
            groups = match.groups()
            
            if "add" in match.group(0) or "sum" in match.group(0):
                if len(groups) >= 2:
                    field1, field2 = groups[0], groups[1]
                    expression = f"{field1} + {field2}"
                    field_name = f"sum_{field1}_{field2}".replace(" ", "_")
                else:
                    expression = f"sum({groups[0]})"
                    field_name = f"sum_{groups[0]}".replace(" ", "_")
                    
            elif "subtract" in match.group(0) or "difference" in match.group(0):
                if len(groups) >= 2:
                    field1, field2 = groups[0], groups[1]
                    expression = f"{field2} - {field1}"
                    field_name = f"diff_{field2}_{field1}".replace(" ", "_")
                else:
                    expression = groups[0]
                    field_name = "difference"
                    
            elif "multiply" in match.group(0):
                field1, field2 = groups[0], groups[1]
                expression = f"{field1} * {field2}"
                field_name = f"product_{field1}_{field2}".replace(" ", "_")
                
            elif "divide" in match.group(0):
                field1, field2 = groups[0], groups[1]
                expression = f"{field1} / {field2}"
                field_name = f"ratio_{field1}_{field2}".replace(" ", "_")
                
            elif "average" in match.group(0) or "mean" in match.group(0):
                expression = f"avg({groups[0]})"
                field_name = f"avg_{groups[0]}".replace(" ", "_")
                
            elif "square" in match.group(0) and "root" not in match.group(0):
                expression = f"pow({groups[0]}, 2)"
                field_name = f"square_{groups[0]}".replace(" ", "_")
                
            elif "sqrt" in match.group(0) or "square root" in match.group(0):
                expression = f"sqrt({groups[0]})"
                field_name = f"sqrt_{groups[0]}".replace(" ", "_")
                
            elif "abs" in match.group(0) or "absolute" in match.group(0):
                expression = f"abs({groups[0]})"
                field_name = f"abs_{groups[0]}".replace(" ", "_")
                
            elif "round" in match.group(0):
                if len(groups) >= 2 and groups[1]:
                    expression = f"round({groups[0]}, {groups[1]})"
                else:
                    expression = f"round({groups[0]})"
                field_name = f"rounded_{groups[0]}".replace(" ", "_")
                
            else:
                expression = groups[0]
                field_name = "calculated_value"
            
            return EvalExpression(
                field_name=field_name,
                expression=expression,
                expression_type=EvalFunctionType.MATHEMATICAL,
                complexity=ExpressionComplexity.SIMPLE,
                description=f"Mathematical calculation: {expression}",
                dependencies=[field for field in groups if field]
            )
            
        except Exception as e:
            logger.warning(f"Failed to create mathematical expression: {e}")
            return None
    
    def _create_string_expression(self, match: re.Match, query: str) -> Optional[EvalExpression]:
        """Create string manipulation eval expression"""
        try:
            groups = match.groups()
            
            if "uppercase" in match.group(0) or "upper" in match.group(0):
                expression = f"upper({groups[0]})"
                field_name = f"{groups[0]}_upper".replace(" ", "_")
                
            elif "lowercase" in match.group(0) or "lower" in match.group(0):
                expression = f"lower({groups[0]})"
                field_name = f"{groups[0]}_lower".replace(" ", "_")
                
            elif "length" in match.group(0):
                expression = f"len({groups[0]})"
                field_name = f"{groups[0]}_length".replace(" ", "_")
                
            elif "extract" in match.group(0) or "substr" in match.group(0):
                if len(groups) >= 3 and groups[2]:
                    expression = f"substr({groups[0]}, {groups[1]}, {groups[2]})"
                else:
                    expression = f"substr({groups[0]}, {groups[1]}, 10)"
                field_name = f"extracted_{groups[0]}".replace(" ", "_")
                
            elif "replace" in match.group(0):
                if len(groups) >= 3:
                    expression = f"replace({groups[2]}, \"{groups[0]}\", \"{groups[1]}\")"
                    field_name = f"replaced_{groups[2]}".replace(" ", "_")
                else:
                    expression = f"replace({groups[0]}, \"old\", \"new\")"
                    field_name = f"replaced_{groups[0]}".replace(" ", "_")
                    
            elif "trim" in match.group(0):
                expression = f"trim({groups[0]})"
                field_name = f"{groups[0]}_trimmed".replace(" ", "_")
                
            elif "split" in match.group(0):
                expression = f"split({groups[0]}, \"{groups[1]}\")"
                field_name = f"{groups[0]}_split".replace(" ", "_")
                
            elif "concatenate" in match.group(0) or "join" in match.group(0):
                if len(groups) >= 3 and groups[2]:
                    expression = f"{groups[0]} + \"{groups[2]}\" + {groups[1]}"
                else:
                    expression = f"{groups[0]} + {groups[1]}"
                field_name = f"combined_{groups[0]}_{groups[1]}".replace(" ", "_")
                
            else:
                expression = f"tostring({groups[0]})"
                field_name = f"string_{groups[0]}".replace(" ", "_")
            
            return EvalExpression(
                field_name=field_name,
                expression=expression,
                expression_type=EvalFunctionType.STRING,
                complexity=ExpressionComplexity.SIMPLE,
                description=f"String manipulation: {expression}",
                dependencies=[field for field in groups if field]
            )
            
        except Exception as e:
            logger.warning(f"Failed to create string expression: {e}")
            return None
    
    def _create_datetime_expression(self, match: re.Match, query: str) -> Optional[EvalExpression]:
        """Create datetime eval expression"""
        try:
            groups = match.groups()
            
            if "now" in match.group(0) or "current" in match.group(0):
                expression = "now()"
                field_name = "current_time"
                
            elif "format" in match.group(0):
                if len(groups) >= 2:
                    expression = f"strftime({groups[0]}, \"{groups[1]}\")"
                    field_name = f"formatted_{groups[0]}".replace(" ", "_")
                else:
                    expression = f"strftime({groups[0]}, \"%Y-%m-%d %H:%M:%S\")"
                    field_name = f"formatted_{groups[0]}".replace(" ", "_")
                    
            elif "parse" in match.group(0):
                expression = f"strptime({groups[0]}, \"%Y-%m-%d %H:%M:%S\")"
                field_name = f"parsed_{groups[0]}".replace(" ", "_")
                
            elif "year" in match.group(0):
                expression = f"strftime({groups[0]}, \"%Y\")"
                field_name = f"year_{groups[0]}".replace(" ", "_")
                
            elif "month" in match.group(0):
                expression = f"strftime({groups[0]}, \"%m\")"
                field_name = f"month_{groups[0]}".replace(" ", "_")
                
            elif "day" in match.group(0):
                expression = f"strftime({groups[0]}, \"%d\")"
                field_name = f"day_{groups[0]}".replace(" ", "_")
                
            elif "hour" in match.group(0):
                expression = f"strftime({groups[0]}, \"%H\")"
                field_name = f"hour_{groups[0]}".replace(" ", "_")
                
            elif "add" in match.group(0):
                if len(groups) >= 2:
                    expression = f"relative_time({groups[1]}, \"+{groups[0]}\")"
                    field_name = f"time_plus_{groups[0]}".replace(" ", "_")
                else:
                    expression = f"relative_time(now(), \"+1h\")"
                    field_name = "time_plus_hour"
                    
            elif "difference" in match.group(0):
                if len(groups) >= 2:
                    expression = f"{groups[1]} - {groups[0]}"
                    field_name = f"time_diff_{groups[0]}_{groups[1]}".replace(" ", "_")
                else:
                    expression = f"now() - {groups[0]}"
                    field_name = f"time_since_{groups[0]}".replace(" ", "_")
                    
            else:
                expression = f"strftime({groups[0]}, \"%Y-%m-%d\")"
                field_name = f"date_{groups[0]}".replace(" ", "_")
            
            return EvalExpression(
                field_name=field_name,
                expression=expression,
                expression_type=EvalFunctionType.DATETIME,
                complexity=ExpressionComplexity.SIMPLE,
                description=f"Date/time operation: {expression}",
                dependencies=[field for field in groups if field]
            )
            
        except Exception as e:
            logger.warning(f"Failed to create datetime expression: {e}")
            return None
    
    def _create_conditional_expression(self, match: re.Match, query: str) -> Optional[EvalExpression]:
        """Create conditional eval expression"""
        try:
            groups = match.groups()
            
            if "if" in match.group(0) and "then" in match.group(0):
                condition = groups[0]
                true_value = groups[1]
                false_value = groups[2] if len(groups) > 2 and groups[2] else "null()"
                expression = f"if({condition}, \"{true_value}\", \"{false_value}\")"
                field_name = "conditional_result"
                
            elif "when" in match.group(0):
                field = groups[0] if groups[0] else "field"
                value = groups[1]
                result = groups[2]
                expression = f"if({field}=\"{value}\", \"{result}\", null())"
                field_name = f"when_{field}_{value}".replace(" ", "_")
                
            elif "default" in match.group(0):
                default_value = groups[0]
                field = groups[1]
                expression = f"coalesce({field}, \"{default_value}\")"
                field_name = f"{field}_with_default".replace(" ", "_")
                
            elif "first" in match.group(0) and "null" in match.group(0):
                fields = groups[0].split(",") if groups[0] else ["field1", "field2"]
                expression = f"coalesce({', '.join(field.strip() for field in fields)})"
                field_name = "first_non_null"
                
            elif "choose" in match.group(0) or "select" in match.group(0):
                value = groups[0]
                condition = groups[1]
                expression = f"case({condition}, \"{value}\", \"other\")"
                field_name = "selected_value"
                
            else:
                expression = f"if({groups[0]}, \"true\", \"false\")"
                field_name = "condition_result"
            
            return EvalExpression(
                field_name=field_name,
                expression=expression,
                expression_type=EvalFunctionType.CONDITIONAL,
                complexity=ExpressionComplexity.MODERATE,
                description=f"Conditional logic: {expression}",
                dependencies=[field for field in groups if field]
            )
            
        except Exception as e:
            logger.warning(f"Failed to create conditional expression: {e}")
            return None
    
    def _create_validation_expression(self, match: re.Match, query: str) -> Optional[EvalExpression]:
        """Create validation eval expression"""
        try:
            groups = match.groups()
            
            if "null" in match.group(0) or "empty" in match.group(0) or "missing" in match.group(0):
                if "not" in match.group(0):
                    expression = f"isnotnull({groups[0]})"
                    field_name = f"is_not_null_{groups[0]}".replace(" ", "_")
                else:
                    expression = f"isnull({groups[0]})"
                    field_name = f"is_null_{groups[0]}".replace(" ", "_")
                    
            elif "numeric" in match.group(0) or "number" in match.group(0):
                expression = f"isnum({groups[0]})"
                field_name = f"is_numeric_{groups[0]}".replace(" ", "_")
                
            elif "contains" in match.group(0) or "has" in match.group(0):
                if len(groups) >= 2:
                    expression = f"match({groups[0]}, \"{groups[1]}\")"
                    field_name = f"contains_{groups[1]}".replace(" ", "_")
                else:
                    expression = f"len({groups[0]}) > 0"
                    field_name = f"has_value_{groups[0]}".replace(" ", "_")
                    
            else:
                expression = f"isnotnull({groups[0]})"
                field_name = f"is_valid_{groups[0]}".replace(" ", "_")
            
            return EvalExpression(
                field_name=field_name,
                expression=expression,
                expression_type=EvalFunctionType.VALIDATION,
                complexity=ExpressionComplexity.SIMPLE,
                description=f"Data validation: {expression}",
                dependencies=[field for field in groups if field]
            )
            
        except Exception as e:
            logger.warning(f"Failed to create validation expression: {e}")
            return None
    
    def _create_conversion_expression(self, match: re.Match, query: str) -> Optional[EvalExpression]:
        """Create conversion eval expression"""
        try:
            groups = match.groups()
            field = groups[0]
            
            if "number" in match.group(0) or "numeric" in match.group(0) or "integer" in match.group(0):
                expression = f"tonumber({field})"
                field_name = f"{field}_as_number".replace(" ", "_")
                
            elif "string" in match.group(0) or "text" in match.group(0):
                expression = f"tostring({field})"
                field_name = f"{field}_as_string".replace(" ", "_")
                
            else:
                expression = f"tostring({field})"
                field_name = f"converted_{field}".replace(" ", "_")
            
            return EvalExpression(
                field_name=field_name,
                expression=expression,
                expression_type=EvalFunctionType.CONVERSION,
                complexity=ExpressionComplexity.SIMPLE,
                description=f"Type conversion: {expression}",
                dependencies=[field]
            )
            
        except Exception as e:
            logger.warning(f"Failed to create conversion expression: {e}")
            return None
    
    def _create_calculation_expression(self, calc_name: str, calc_info: Dict[str, Any], query: str) -> Optional[EvalExpression]:
        """Create calculation eval expression"""
        try:
            expression_template = calc_info["expression"]
            description = calc_info["description"]
            
            # Extract field names from query for template substitution
            field_mappings = self._extract_calculation_fields(calc_name, query)
            
            # Substitute placeholders in expression template
            expression = expression_template
            for placeholder, value in field_mappings.items():
                expression = expression.replace(f"{{{placeholder}}}", value)
            
            field_name = f"{calc_name}_result"
            
            return EvalExpression(
                field_name=field_name,
                expression=expression,
                expression_type=EvalFunctionType.MATHEMATICAL,
                complexity=ExpressionComplexity.MODERATE,
                description=description,
                dependencies=list(field_mappings.values())
            )
            
        except Exception as e:
            logger.warning(f"Failed to create calculation expression: {e}")
            return None
    
    def _create_transformation_expression(self, transform_name: str, transform_info: Dict[str, Any], query: str) -> Optional[EvalExpression]:
        """Create transformation eval expression"""
        try:
            expression = transform_info["expression"]
            description = transform_info["description"]
            
            field_name = f"{transform_name}_category"
            
            return EvalExpression(
                field_name=field_name,
                expression=expression,
                expression_type=EvalFunctionType.CONDITIONAL,
                complexity=ExpressionComplexity.COMPLEX,
                description=description,
                dependencies=self._extract_field_dependencies(expression)
            )
            
        except Exception as e:
            logger.warning(f"Failed to create transformation expression: {e}")
            return None
    
    def _extract_calculation_fields(self, calc_name: str, query: str) -> Dict[str, str]:
        """Extract field mappings for calculation templates"""
        field_mappings = {}
        
        if calc_name == "percentage":
            # Try to extract numerator and denominator
            field_mappings = {"numerator": "value1", "denominator": "value2"}
        elif calc_name == "growth_rate":
            field_mappings = {"new_value": "current_value", "old_value": "previous_value"}
        elif calc_name == "ratio":
            field_mappings = {"numerator": "field1", "denominator": "field2"}
        elif calc_name == "age_calculation":
            field_mappings = {"timestamp": "_time", "time_unit": "86400"}  # seconds in a day
        elif calc_name == "score_calculation":
            field_mappings = {"field1": "metric1", "weight1": "1", "field2": "metric2", "weight2": "1"}
        
        return field_mappings
    
    def _extract_field_dependencies(self, expression: str) -> List[str]:
        """Extract field dependencies from expression"""
        # Simple regex to find field names (words that aren't functions)
        field_pattern = r'\b(?!case|if|and|or|not|null|true|false|tonumber|tostring|len|upper|lower|substr|replace|trim|split|strftime|strptime|now|abs|ceil|floor|round|pow|sqrt|cidrmatch|isnull|isnotnull|isnum|coalesce|nullif|mvcount|mvindex)\w+\b'
        fields = re.findall(field_pattern, expression, re.IGNORECASE)
        return list(set(fields))
    
    def generate_spl_for_eval(self, eval_expression: EvalExpression) -> str:
        """Generate SPL command for eval expression"""
        return f"eval {eval_expression.field_name}={eval_expression.expression}"
    
    def validate_eval_expression(self, eval_expression: EvalExpression) -> Dict[str, Any]:
        """Validate eval expression"""
        validation = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # Check expression syntax
        if not eval_expression.expression:
            validation["errors"].append("Empty expression")
            validation["valid"] = False
            return validation
        
        # Check for common syntax issues
        expression = eval_expression.expression
        
        # Check for unmatched parentheses
        if expression.count("(") != expression.count(")"):
            validation["errors"].append("Unmatched parentheses in expression")
            validation["valid"] = False
        
        # Check for unmatched quotes
        single_quotes = expression.count("'")
        double_quotes = expression.count('"')
        
        if single_quotes % 2 != 0:
            validation["warnings"].append("Unmatched single quotes")
        
        if double_quotes % 2 != 0:
            validation["warnings"].append("Unmatched double quotes")
        
        # Check for potential performance issues
        if len(expression) > 200:
            validation["warnings"].append("Very long expression may impact performance")
        
        if expression.count("case(") > 3:
            validation["warnings"].append("Multiple case statements may impact performance")
        
        # Check for field dependencies
        if not eval_expression.dependencies:
            validation["suggestions"].append("Consider specifying field dependencies for better validation")
        
        # Check complexity
        if eval_expression.complexity == ExpressionComplexity.ADVANCED:
            validation["suggestions"].append("Consider breaking down complex expression into multiple steps")
        
        return validation
    
    def optimize_eval_expression(self, eval_expression: EvalExpression) -> EvalExpression:
        """Optimize eval expression for performance"""
        optimized_expression = eval_expression.expression
        
        # Replace multiple string concatenations with single operation
        if optimized_expression.count("+") > 3 and '"' in optimized_expression:
            pass  # Would implement string concatenation optimization
        
        # Optimize nested case statements
        if optimized_expression.count("case(") > 2:
            pass  # Would implement case statement optimization
        
        # Create optimized copy
        return EvalExpression(
            field_name=eval_expression.field_name,
            expression=optimized_expression,
            expression_type=eval_expression.expression_type,
            complexity=eval_expression.complexity,
            description=eval_expression.description,
            dependencies=eval_expression.dependencies,
            conditions=eval_expression.conditions,
            validation_rules=eval_expression.validation_rules
        )
    
    def suggest_eval_functions(self, query: str, available_fields: List[str] = None) -> List[Dict[str, Any]]:
        """Suggest appropriate eval functions based on query and available fields"""
        suggestions = []
        query_lower = query.lower()
        available_fields = available_fields or []
        
        for func_name, func_info in self.eval_functions.items():
            suggestion_score = 0
            reasons = []
            
            # Check if function name is mentioned
            if func_name in query_lower:
                suggestion_score += 10
                reasons.append(f"Function '{func_name}' mentioned in query")
            
            # Check for aliases
            for alias in func_info.aliases:
                if alias in query_lower:
                    suggestion_score += 8
                    reasons.append(f"Function alias '{alias}' found")
            
            # Check for function type keywords
            function_keywords = {
                EvalFunctionType.MATHEMATICAL: ["calculate", "compute", "math", "number", "sum", "total", "average"],
                EvalFunctionType.STRING: ["text", "string", "upper", "lower", "length", "replace", "trim"],
                EvalFunctionType.DATETIME: ["time", "date", "format", "parse", "now", "current"],
                EvalFunctionType.CONDITIONAL: ["if", "when", "case", "condition", "choose", "select"],
                EvalFunctionType.VALIDATION: ["check", "verify", "validate", "test", "null", "empty"],
                EvalFunctionType.CONVERSION: ["convert", "parse", "cast", "transform"]
            }
            
            if func_info.function_type in function_keywords:
                for keyword in function_keywords[func_info.function_type]:
                    if keyword in query_lower:
                        suggestion_score += 3
                        reasons.append(f"Function type keyword '{keyword}' found")
            
            # Check for available fields that match function usage
            for field in available_fields:
                if field in func_info.description.lower():
                    suggestion_score += 2
                    reasons.append(f"Available field '{field}' matches function usage")
            
            if suggestion_score > 0:
                suggestions.append({
                    "function_name": func_name,
                    "score": suggestion_score,
                    "function_type": func_info.function_type.value,
                    "description": func_info.description,
                    "syntax": func_info.syntax,
                    "examples": func_info.examples[:2],  # Limit to first 2 examples
                    "reasons": reasons
                })
        
        # Sort by score
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return suggestions[:10]  # Return top 10 suggestions
    
    def get_function_info(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific eval function"""
        if function_name not in self.eval_functions:
            # Check aliases
            for func_name, func_info in self.eval_functions.items():
                if function_name in func_info.aliases:
                    function_name = func_name
                    break
            else:
                return None
        
        func_info = self.eval_functions[function_name]
        
        return {
            "name": func_info.name,
            "type": func_info.function_type.value,
            "syntax": func_info.syntax,
            "description": func_info.description,
            "parameters": func_info.parameters,
            "examples": func_info.examples,
            "aliases": func_info.aliases,
            "return_type": func_info.return_type.value,
            "complexity": func_info.complexity.value,
            "performance_notes": func_info.performance_notes
        }
    
    def get_all_functions(self) -> Dict[str, Any]:
        """Get information about all available eval functions"""
        return {
            "functions": list(self.eval_functions.keys()),
            "total_count": len(self.eval_functions),
            "by_type": {
                func_type.value: [
                    name for name, func in self.eval_functions.items()
                    if func.function_type == func_type
                ]
                for func_type in EvalFunctionType
            },
            "by_complexity": {
                complexity.value: [
                    name for name, func in self.eval_functions.items()
                    if func.complexity == complexity
                ]
                for complexity in ExpressionComplexity
            },
            "common_expressions": list(self.common_expressions.keys())
        }


# Global instance
eval_calculated_fields_mapper = EvalCalculatedFieldsMapper()