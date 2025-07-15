"""
Comprehensive SPL Command Mapping System

This module provides a complete mapping system from natural language concepts
to Splunk SPL commands, supporting advanced query construction and optimization.
"""

import re
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime, timedelta

from ..core.logging import get_logger

logger = get_logger(__name__)


class SPLCommandType(Enum):
    """SPL command categories"""
    SEARCH = "search"
    FILTERING = "filtering"
    TRANSFORMATION = "transformation"
    AGGREGATION = "aggregation"
    STATISTICAL = "statistical"
    TEMPORAL = "temporal"
    FORMATTING = "formatting"
    VISUALIZATION = "visualization"
    UTILITY = "utility"


class FieldType(Enum):
    """Common Splunk field types"""
    STRING = "string"
    NUMBER = "number"
    TIMESTAMP = "timestamp"
    IP_ADDRESS = "ip"
    URL = "url"
    EMAIL = "email"
    BOOLEAN = "boolean"
    JSON = "json"


@dataclass
class SPLCommand:
    """SPL command definition"""
    name: str
    command_type: SPLCommandType
    syntax: str
    description: str
    parameters: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    common_patterns: List[str] = field(default_factory=list)
    performance_notes: Optional[str] = None
    limitations: List[str] = field(default_factory=list)


@dataclass
class FieldMapping:
    """Mapping for common field names"""
    natural_names: List[str]
    splunk_field: str
    field_type: FieldType
    common_values: List[str] = field(default_factory=list)
    extraction_patterns: List[str] = field(default_factory=list)
    validation_regex: Optional[str] = None


@dataclass
class IntentPattern:
    """Pattern for intent recognition"""
    intent: str
    patterns: List[str]
    required_entities: List[str] = field(default_factory=list)
    optional_entities: List[str] = field(default_factory=list)
    spl_template: str = ""
    confidence_boost: float = 0.0


class ComprehensiveSPLMapper:
    """Comprehensive SPL command mapping system"""
    
    def __init__(self):
        self.commands = self._initialize_commands()
        self.field_mappings = self._initialize_field_mappings()
        self.intent_patterns = self._initialize_intent_patterns()
        self.aggregation_mappings = self._initialize_aggregation_mappings()
        self.time_mappings = self._initialize_time_mappings()
        self.operator_mappings = self._initialize_operator_mappings()
        
    def _initialize_commands(self) -> Dict[str, SPLCommand]:
        """Initialize comprehensive SPL command mappings"""
        commands = {}
        
        # Search Commands
        commands["search"] = SPLCommand(
            name="search",
            command_type=SPLCommandType.SEARCH,
            syntax="search <search-expression>",
            description="Primary search command to find events",
            parameters=["search-expression", "index", "sourcetype", "host", "source"],
            examples=[
                "search error",
                "search index=main sourcetype=access_log",
                "search host=web01 AND status=500"
            ],
            aliases=[""],
            common_patterns=[
                "find {term}",
                "show me {term}",
                "get {term}",
                "look for {term}"
            ]
        )
        
        # Filtering Commands
        commands["where"] = SPLCommand(
            name="where",
            command_type=SPLCommandType.FILTERING,
            syntax="where <predicate-expression>",
            description="Filter results based on field values",
            parameters=["field", "operator", "value"],
            examples=[
                "where status_code>400",
                "where user=\"admin\"",
                "where like(url, \"%login%\")"
            ],
            common_patterns=[
                "where {field} {operator} {value}",
                "filter by {field}",
                "only show {condition}"
            ]
        )
        
        commands["regex"] = SPLCommand(
            name="regex",
            command_type=SPLCommandType.FILTERING,
            syntax="regex [field=]<field> \"<regex-expression>\"",
            description="Filter events using regular expressions",
            parameters=["field", "regex"],
            examples=[
                "regex _raw=\"(?i)error\"",
                "regex user_agent=\".*bot.*\"",
                "regex ip=\"^192\\.168\\.\""
            ],
            common_patterns=[
                "match {pattern}",
                "contains pattern {pattern}",
                "matches {regex}"
            ]
        )
        
        # Transformation Commands
        commands["eval"] = SPLCommand(
            name="eval",
            command_type=SPLCommandType.TRANSFORMATION,
            syntax="eval <field>=<expression>",
            description="Create or modify fields using expressions",
            parameters=["field", "expression"],
            examples=[
                "eval total=price*quantity",
                "eval status_category=if(status<400,\"success\",\"error\")",
                "eval hour=strftime(_time, \"%H\")"
            ],
            common_patterns=[
                "calculate {field}",
                "compute {expression}",
                "create field {field}"
            ]
        )
        
        commands["rex"] = SPLCommand(
            name="rex",
            command_type=SPLCommandType.TRANSFORMATION,
            syntax="rex [field=<field>] \"<regex-with-groups>\"",
            description="Extract fields using regular expressions",
            parameters=["field", "regex", "named_groups"],
            examples=[
                "rex \"(?<method>\\w+) (?<url>\\S+) HTTP\"",
                "rex field=message \"Error: (?<error_code>\\d+)\"",
                "rex max_match=0 \"user=(?<user>\\w+)\""
            ],
            common_patterns=[
                "extract {field} from {source}",
                "parse {field}",
                "get {field} from text"
            ]
        )
        
        # Aggregation Commands
        commands["stats"] = SPLCommand(
            name="stats",
            command_type=SPLCommandType.AGGREGATION,
            syntax="stats <stats-function>(<field>) [by <field-list>]",
            description="Calculate aggregate statistics",
            parameters=["function", "field", "by_fields"],
            examples=[
                "stats count by sourcetype",
                "stats avg(response_time) by host",
                "stats sum(bytes) as total_bytes, max(_time) as latest by user"
            ],
            common_patterns=[
                "count {field}",
                "sum of {field}",
                "average {field}",
                "group by {field}"
            ]
        )
        
        commands["chart"] = SPLCommand(
            name="chart",
            command_type=SPLCommandType.AGGREGATION,
            syntax="chart <stats-function>(<field>) [by <split-by> <over>]",
            description="Create statistical charts",
            parameters=["function", "field", "split_by", "over"],
            examples=[
                "chart count by status_code",
                "chart avg(response_time) over _time span=1h",
                "chart sum(bytes) by user over host"
            ],
            common_patterns=[
                "chart {function} by {field}",
                "show {function} over time",
                "plot {field} by {grouping}"
            ]
        )
        
        commands["timechart"] = SPLCommand(
            name="timechart",
            command_type=SPLCommandType.TEMPORAL,
            syntax="timechart [span=<time-span>] <stats-function>(<field>) [by <field>]",
            description="Create time-based charts",
            parameters=["span", "function", "field", "by_field"],
            examples=[
                "timechart count",
                "timechart span=1h avg(cpu_usage) by host",
                "timechart span=5m sum(errors) by service"
            ],
            common_patterns=[
                "over time",
                "time series",
                "trend of {field}",
                "hourly {function}"
            ]
        )
        
        # Statistical Commands
        commands["eventstats"] = SPLCommand(
            name="eventstats",
            command_type=SPLCommandType.STATISTICAL,
            syntax="eventstats <stats-function>(<field>) [by <field-list>]",
            description="Add aggregate statistics to each event",
            parameters=["function", "field", "by_fields"],
            examples=[
                "eventstats avg(response_time) as avg_rt by service",
                "eventstats count as total_events",
                "eventstats max(_time) as latest_time by user"
            ]
        )
        
        commands["streamstats"] = SPLCommand(
            name="streamstats",
            command_type=SPLCommandType.STATISTICAL,
            syntax="streamstats <stats-function>(<field>) [window=<int>] [by <field-list>]",
            description="Calculate streaming statistics",
            parameters=["function", "field", "window", "by_fields"],
            examples=[
                "streamstats avg(value) window=10",
                "streamstats count as running_count by user",
                "streamstats range(cpu) window=5 by host"
            ]
        )
        
        # Formatting Commands
        commands["table"] = SPLCommand(
            name="table",
            command_type=SPLCommandType.FORMATTING,
            syntax="table <field-list>",
            description="Display specified fields in tabular format",
            parameters=["fields"],
            examples=[
                "table _time, host, source, message",
                "table user, action, result",
                "table src_ip, dest_ip, bytes"
            ],
            common_patterns=[
                "show {fields}",
                "display {fields}",
                "table of {fields}"
            ]
        )
        
        commands["sort"] = SPLCommand(
            name="sort",
            command_type=SPLCommandType.FORMATTING,
            syntax="sort [<count>] [<sort-order>] <field-list>",
            description="Sort search results",
            parameters=["count", "order", "fields"],
            examples=[
                "sort _time",
                "sort -count, +_time",
                "sort 10 -response_time"
            ],
            common_patterns=[
                "sort by {field}",
                "order by {field}",
                "arrange by {field}"
            ]
        )
        
        # Utility Commands
        commands["dedup"] = SPLCommand(
            name="dedup",
            command_type=SPLCommandType.UTILITY,
            syntax="dedup [<count>] <field-list> [keepevents=<bool>]",
            description="Remove duplicate events",
            parameters=["count", "fields", "keepevents"],
            examples=[
                "dedup user",
                "dedup src_ip, dest_ip",
                "dedup 5 host keepevents=true"
            ],
            common_patterns=[
                "remove duplicates",
                "unique {field}",
                "distinct {field}"
            ]
        )
        
        commands["head"] = SPLCommand(
            name="head",
            command_type=SPLCommandType.UTILITY,
            syntax="head [<count>]",
            description="Return first N results",
            parameters=["count"],
            examples=[
                "head 10",
                "head 100"
            ],
            common_patterns=[
                "first {count}",
                "top {count}",
                "limit {count}"
            ]
        )
        
        commands["tail"] = SPLCommand(
            name="tail",
            command_type=SPLCommandType.UTILITY,
            syntax="tail [<count>]",
            description="Return last N results",
            parameters=["count"],
            examples=[
                "tail 10",
                "tail 50"
            ],
            common_patterns=[
                "last {count}",
                "recent {count}",
                "latest {count}"
            ]
        )
        
        return commands
    
    def _initialize_field_mappings(self) -> Dict[str, FieldMapping]:
        """Initialize common field name mappings"""
        mappings = {}
        
        # Time fields
        mappings["time"] = FieldMapping(
            natural_names=["time", "timestamp", "when", "date", "datetime"],
            splunk_field="_time",
            field_type=FieldType.TIMESTAMP,
            common_values=["now", "today", "yesterday", "last hour", "last 24 hours"]
        )
        
        # User fields
        mappings["user"] = FieldMapping(
            natural_names=["user", "username", "userid", "account", "login"],
            splunk_field="user",
            field_type=FieldType.STRING,
            extraction_patterns=["user=(?<user>\\w+)", "username[=:](?<user>\\S+)"]
        )
        
        # IP address fields
        mappings["source_ip"] = FieldMapping(
            natural_names=["source ip", "src ip", "client ip", "remote ip", "origin"],
            splunk_field="src_ip",
            field_type=FieldType.IP_ADDRESS,
            validation_regex=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        )
        
        mappings["destination_ip"] = FieldMapping(
            natural_names=["destination ip", "dest ip", "target ip", "server ip"],
            splunk_field="dest_ip",
            field_type=FieldType.IP_ADDRESS,
            validation_regex=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        )
        
        # Status fields
        mappings["status"] = FieldMapping(
            natural_names=["status", "status code", "response code", "http status"],
            splunk_field="status",
            field_type=FieldType.NUMBER,
            common_values=["200", "404", "500", "401", "403", "503"]
        )
        
        # Host fields
        mappings["host"] = FieldMapping(
            natural_names=["host", "hostname", "server", "machine", "node"],
            splunk_field="host",
            field_type=FieldType.STRING
        )
        
        # Message fields
        mappings["message"] = FieldMapping(
            natural_names=["message", "msg", "log message", "event", "description"],
            splunk_field="message",
            field_type=FieldType.STRING
        )
        
        return mappings
    
    def _initialize_intent_patterns(self) -> List[IntentPattern]:
        """Initialize intent recognition patterns"""
        patterns = []
        
        # Search intents
        patterns.append(IntentPattern(
            intent="SEARCH_EVENTS",
            patterns=[
                r"(?:find|search|look for|get|show me) (.+)",
                r"(?:what|which) (.+)",
                r"(.+) events",
                r"events (?:with|containing|about) (.+)"
            ],
            required_entities=["search_term"],
            spl_template="search {search_term}"
        ))
        
        # Count intents
        patterns.append(IntentPattern(
            intent="COUNT_EVENTS",
            patterns=[
                r"(?:count|number of|how many) (.+)",
                r"total (.+)",
                r"(.+) count"
            ],
            required_entities=["field"],
            spl_template="search {filter} | stats count"
        ))
        
        # Top/Bottom intents
        patterns.append(IntentPattern(
            intent="TOP_VALUES",
            patterns=[
                r"(?:top|most|highest|maximum) (.+)",
                r"(.+) (?:with most|with highest)",
                r"(?:best|leading) (.+)"
            ],
            required_entities=["field"],
            spl_template="search {filter} | top {field}"
        ))
        
        # Time-based intents
        patterns.append(IntentPattern(
            intent="TIME_ANALYSIS",
            patterns=[
                r"(.+) (?:over time|by time|timeline)",
                r"(?:trend|pattern) (?:of|for) (.+)",
                r"(?:hourly|daily|weekly) (.+)",
                r"time series (?:of|for) (.+)"
            ],
            required_entities=["field"],
            spl_template="search {filter} | timechart {function}({field})"
        ))
        
        # Error analysis intents
        patterns.append(IntentPattern(
            intent="ERROR_ANALYSIS",
            patterns=[
                r"(?:error|errors|failures|failed) (.+)",
                r"(?:problems|issues) (?:with|in) (.+)",
                r"(.+) (?:not working|failing)"
            ],
            required_entities=["context"],
            spl_template="search error OR failed OR failure {context}"
        ))
        
        return patterns
    
    def _initialize_aggregation_mappings(self) -> Dict[str, str]:
        """Initialize aggregation function mappings"""
        return {
            # Count variations
            "count": "count",
            "number": "count",
            "total": "count",
            "how many": "count",
            
            # Sum variations
            "sum": "sum",
            "total": "sum",
            "add up": "sum",
            "cumulative": "sum",
            
            # Average variations
            "average": "avg",
            "mean": "avg",
            "avg": "avg",
            
            # Maximum variations
            "maximum": "max",
            "max": "max",
            "highest": "max",
            "largest": "max",
            "peak": "max",
            
            # Minimum variations
            "minimum": "min",
            "min": "min",
            "lowest": "min",
            "smallest": "min",
            
            # Statistical functions
            "standard deviation": "stdev",
            "variance": "var",
            "median": "median",
            "percentile": "perc",
            "range": "range"
        }
    
    def _initialize_time_mappings(self) -> Dict[str, str]:
        """Initialize time expression mappings"""
        return {
            # Relative times
            "now": "now",
            "today": "-0d@d",
            "yesterday": "-1d@d",
            "this week": "-0w@w",
            "last week": "-1w@w",
            "this month": "-0mon@mon",
            "last month": "-1mon@mon",
            
            # Hour-based
            "last hour": "-1h",
            "last 2 hours": "-2h",
            "last 24 hours": "-24h",
            "past hour": "-1h",
            
            # Day-based
            "last day": "-1d",
            "last 7 days": "-7d",
            "past week": "-7d",
            "last 30 days": "-30d",
            
            # Minute-based
            "last 15 minutes": "-15m",
            "last 30 minutes": "-30m",
            "past 10 minutes": "-10m",
            
            # Real-time
            "real time": "rt-15m",
            "live": "rt-1m"
        }
    
    def _initialize_operator_mappings(self) -> Dict[str, str]:
        """Initialize operator mappings"""
        return {
            # Equality
            "equals": "=",
            "is": "=",
            "is equal to": "=",
            "exactly": "=",
            
            # Inequality
            "not equal": "!=",
            "not": "!=",
            "is not": "!=",
            "different from": "!=",
            
            # Comparison
            "greater than": ">",
            "more than": ">",
            "above": ">",
            "higher than": ">",
            
            "less than": "<",
            "below": "<",
            "under": "<",
            "lower than": "<",
            
            "greater than or equal": ">=",
            "at least": ">=",
            "minimum": ">=",
            
            "less than or equal": "<=",
            "at most": "<=",
            "maximum": "<=",
            
            # Pattern matching
            "contains": "like",
            "includes": "like",
            "has": "like",
            "matches": "match",
            "starts with": "like",
            "ends with": "like"
        }
    
    def get_command_by_name(self, name: str) -> Optional[SPLCommand]:
        """Get SPL command by name"""
        return self.commands.get(name.lower())
    
    def get_commands_by_type(self, command_type: SPLCommandType) -> List[SPLCommand]:
        """Get all commands of a specific type"""
        return [cmd for cmd in self.commands.values() if cmd.command_type == command_type]
    
    def find_field_mapping(self, natural_name: str) -> Optional[FieldMapping]:
        """Find field mapping for natural language field name"""
        natural_name = natural_name.lower().strip()
        
        for mapping in self.field_mappings.values():
            if natural_name in [name.lower() for name in mapping.natural_names]:
                return mapping
        
        return None
    
    def resolve_aggregation_function(self, natural_function: str) -> str:
        """Resolve natural language aggregation to SPL function"""
        natural_function = natural_function.lower().strip()
        return self.aggregation_mappings.get(natural_function, natural_function)
    
    def resolve_time_expression(self, natural_time: str) -> str:
        """Resolve natural language time expression to SPL time"""
        natural_time = natural_time.lower().strip()
        
        # Check direct mappings first
        if natural_time in self.time_mappings:
            return self.time_mappings[natural_time]
        
        # Pattern matching for complex time expressions
        # Handle "N hours/days/minutes ago"
        pattern = r"(\d+)\s+(minute|hour|day|week|month)s?\s+ago"
        match = re.search(pattern, natural_time)
        if match:
            num, unit = match.groups()
            unit_map = {"minute": "m", "hour": "h", "day": "d", "week": "w", "month": "mon"}
            return f"-{num}{unit_map.get(unit, unit)}"
        
        # Handle "last N hours/days/minutes"
        pattern = r"last\s+(\d+)\s+(minute|hour|day|week|month)s?"
        match = re.search(pattern, natural_time)
        if match:
            num, unit = match.groups()
            unit_map = {"minute": "m", "hour": "h", "day": "d", "week": "w", "month": "mon"}
            return f"-{num}{unit_map.get(unit, unit)}"
        
        return natural_time
    
    def resolve_operator(self, natural_operator: str) -> str:
        """Resolve natural language operator to SPL operator"""
        natural_operator = natural_operator.lower().strip()
        return self.operator_mappings.get(natural_operator, natural_operator)
    
    def suggest_commands_for_intent(self, intent: str) -> List[str]:
        """Suggest SPL commands for a given intent"""
        intent_map = {
            "SEARCH_EVENTS": ["search", "regex", "where"],
            "COUNT_EVENTS": ["stats", "chart", "timechart"],
            "TOP_VALUES": ["top", "rare", "stats"],
            "TIME_ANALYSIS": ["timechart", "bin", "streamstats"],
            "ERROR_ANALYSIS": ["search", "stats", "chart"],
            "AGGREGATION": ["stats", "chart", "eventstats"],
            "FILTERING": ["where", "search", "regex"],
            "TRANSFORMATION": ["eval", "rex", "replace"]
        }
        
        return intent_map.get(intent, [])
    
    def generate_spl_template(self, intent: str, entities: Dict[str, Any]) -> str:
        """Generate SPL template for intent and entities"""
        for pattern in self.intent_patterns:
            if pattern.intent == intent:
                template = pattern.spl_template
                
                # Replace placeholders with actual entities
                for entity_type, entity_value in entities.items():
                    placeholder = "{" + entity_type + "}"
                    if placeholder in template:
                        template = template.replace(placeholder, str(entity_value))
                
                return template
        
        return ""
    
    def get_command_suggestions(self, partial_query: str) -> List[Tuple[str, float]]:
        """Get command suggestions based on partial query"""
        partial_query = partial_query.lower().strip()
        suggestions = []
        
        for command_name, command in self.commands.items():
            score = 0.0
            
            # Check if command name is in query
            if command_name in partial_query:
                score += 1.0
            
            # Check aliases
            for alias in command.aliases:
                if alias in partial_query:
                    score += 0.8
            
            # Check common patterns
            for pattern in command.common_patterns:
                pattern_words = pattern.lower().split()
                query_words = partial_query.split()
                
                # Calculate word overlap
                overlap = len(set(pattern_words) & set(query_words))
                if overlap > 0:
                    score += overlap / len(pattern_words) * 0.6
            
            if score > 0:
                suggestions.append((command_name, score))
        
        # Sort by score descending
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:5]  # Return top 5 suggestions
    
    def validate_spl_syntax(self, spl_query: str) -> Tuple[bool, List[str]]:
        """Basic SPL syntax validation"""
        errors = []
        
        # Check for basic syntax issues
        if not spl_query.strip():
            errors.append("Empty query")
            return False, errors
        
        # Check for unmatched quotes
        single_quotes = spl_query.count("'")
        double_quotes = spl_query.count('"')
        
        if single_quotes % 2 != 0:
            errors.append("Unmatched single quotes")
        
        if double_quotes % 2 != 0:
            errors.append("Unmatched double quotes")
        
        # Check for unmatched parentheses
        open_parens = spl_query.count("(")
        close_parens = spl_query.count(")")
        
        if open_parens != close_parens:
            errors.append("Unmatched parentheses")
        
        # Check for valid command usage
        commands = spl_query.split("|")
        for i, cmd in enumerate(commands):
            cmd = cmd.strip()
            if not cmd:
                continue
                
            # First command should be search or a command that generates events
            if i == 0 and not any(cmd.startswith(start) for start in ["search", "inputlookup", "rest", "metadata"]):
                # If it doesn't start with a generating command, assume it's an implicit search
                pass
            
            # Check for known commands
            cmd_name = cmd.split()[0] if cmd.split() else ""
            if cmd_name and cmd_name not in self.commands and cmd_name not in ["search", "inputlookup", "rest", "metadata"]:
                # Don't mark as error, might be a valid SPL command not in our mapping
                pass
        
        return len(errors) == 0, errors
    
    def optimize_spl_query(self, spl_query: str) -> Tuple[str, List[str]]:
        """Provide SPL query optimization suggestions"""
        suggestions = []
        optimized_query = spl_query
        
        # Suggest index specification if missing
        if "index=" not in spl_query.lower():
            suggestions.append("Consider specifying an index (e.g., index=main) to improve performance")
        
        # Suggest sourcetype specification if missing
        if "sourcetype=" not in spl_query.lower():
            suggestions.append("Consider specifying a sourcetype to improve performance")
        
        # Check for inefficient wildcard usage
        if spl_query.count("*") > 3:
            suggestions.append("Consider reducing wildcard usage for better performance")
        
        # Suggest time range specification
        if "earliest=" not in spl_query.lower() and "latest=" not in spl_query.lower():
            suggestions.append("Consider specifying a time range (earliest/latest) to improve performance")
        
        # Check for head/tail usage after expensive operations
        if "| stats" in spl_query and "| head" not in spl_query:
            suggestions.append("Consider adding '| head N' after stats to limit results")
        
        return optimized_query, suggestions


# Global instance
spl_mapper = ComprehensiveSPLMapper()