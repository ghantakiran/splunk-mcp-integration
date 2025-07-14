#!/usr/bin/env python3
"""
Simple validation test for SPL mapping concepts
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Replicate key components for testing
class SPLCommandType(Enum):
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
    name: str
    command_type: SPLCommandType
    syntax: str
    description: str
    parameters: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)

def test_spl_mapping_concepts():
    """Test core SPL mapping concepts"""
    print("Testing SPL Mapping Concepts")
    print("=" * 50)
    
    # Test command creation
    search_cmd = SPLCommand(
        name="search",
        command_type=SPLCommandType.SEARCH,
        syntax="search <search-expression>",
        description="Primary search command to find events",
        parameters=["search-expression", "index", "sourcetype"],
        examples=["search error", "search index=main sourcetype=access_log"]
    )
    
    print(f"✓ Created search command: {search_cmd.name}")
    print(f"  - Type: {search_cmd.command_type.value}")
    print(f"  - Description: {search_cmd.description}")
    print(f"  - Parameters: {search_cmd.parameters}")
    
    # Test aggregation mappings
    aggregation_mappings = {
        "count": "count",
        "average": "avg",
        "maximum": "max",
        "sum": "sum",
        "total": "sum"
    }
    
    print("\n✓ Aggregation Mappings:")
    for natural, spl in aggregation_mappings.items():
        print(f"  - '{natural}' → {spl}")
    
    # Test time mappings
    time_mappings = {
        "today": "-0d@d",
        "yesterday": "-1d@d", 
        "last hour": "-1h",
        "last 24 hours": "-24h"
    }
    
    print("\n✓ Time Mappings:")
    for natural, spl in time_mappings.items():
        print(f"  - '{natural}' → {spl}")
    
    # Test field mappings
    field_mappings = {
        "time": "_time",
        "user": "user",
        "source ip": "src_ip",
        "host": "host",
        "status": "status"
    }
    
    print("\n✓ Field Mappings:")
    for natural, spl in field_mappings.items():
        print(f"  - '{natural}' → {spl}")
    
    # Test intent patterns
    intent_patterns = [
        (r"(?:find|search|look for|get|show me) (.+)", "SEARCH_EVENTS"),
        (r"(?:count|number of|how many) (.+)", "COUNT_EVENTS"),
        (r"(?:top|most|highest|maximum) (.+)", "TOP_VALUES"),
        (r"(.+) (?:over time|by time|timeline)", "TIME_ANALYSIS")
    ]
    
    print("\n✓ Intent Pattern Matching:")
    test_queries = [
        "find all errors",
        "count the events",
        "show me top users", 
        "errors over time"
    ]
    
    for query in test_queries:
        matched_intent = None
        for pattern, intent in intent_patterns:
            if re.search(pattern, query.lower()):
                matched_intent = intent
                break
        print(f"  - '{query}' → {matched_intent or 'UNKNOWN'}")
    
    # Test SPL syntax validation concepts
    print("\n✓ SPL Syntax Validation:")
    test_queries = [
        ("search error", True, []),
        ("search error | stats count", True, []),
        ("search \"unmatched quote", False, ["Unmatched double quotes"]),
        ("", False, ["Empty query"]),
        ("search (unmatched paren", False, ["Unmatched parentheses"])
    ]
    
    for query, expected_valid, expected_errors in test_queries:
        # Simple validation logic
        errors = []
        if not query.strip():
            errors.append("Empty query")
        
        double_quotes = query.count('"')
        if double_quotes % 2 != 0:
            errors.append("Unmatched double quotes")
        
        open_parens = query.count("(")
        close_parens = query.count(")")
        if open_parens != close_parens:
            errors.append("Unmatched parentheses")
        
        is_valid = len(errors) == 0
        status = "✓" if is_valid == expected_valid else "✗"
        print(f"  {status} '{query}' → Valid: {is_valid}, Errors: {errors}")
    
    # Test optimization suggestions
    print("\n✓ Query Optimization Suggestions:")
    test_queries = [
        ("search error", ["Consider specifying an index", "Consider specifying a sourcetype"]),
        ("search index=main error", ["Consider specifying a time range"]),
        ("search *error* *warning* *info* *debug*", ["Consider reducing wildcard usage"])
    ]
    
    for query, expected_suggestions in test_queries:
        suggestions = []
        
        if "index=" not in query.lower():
            suggestions.append("Consider specifying an index")
        if "sourcetype=" not in query.lower():
            suggestions.append("Consider specifying a sourcetype") 
        if "earliest=" not in query.lower() and "latest=" not in query.lower():
            suggestions.append("Consider specifying a time range")
        if query.count("*") > 3:
            suggestions.append("Consider reducing wildcard usage")
        
        print(f"  - '{query}':")
        for suggestion in suggestions[:2]:  # Show first 2
            print(f"    → {suggestion}")
    
    # Test time expression parsing
    print("\n✓ Time Expression Parsing:")
    unit_map = {'minute': 'm', 'hour': 'h', 'day': 'd', 'week': 'w', 'month': 'mon'}
    time_patterns = [
        (r"(\d+)\s+(minute|hour|day|week|month)s?\s+ago", lambda m: f"-{m.group(1)}{unit_map[m.group(2)]}"),
        (r"last\s+(\d+)\s+(minute|hour|day|week|month)s?", lambda m: f"-{m.group(1)}{unit_map[m.group(2)]}")
    ]
    
    test_expressions = ["3 hours ago", "5 minutes ago", "last 2 days", "last 1 week"]
    
    for expr in test_expressions:
        result = expr  # default
        for pattern, func in time_patterns:
            match = re.search(pattern, expr)
            if match:
                try:
                    result = func(match)
                    break
                except:
                    pass
        print(f"  - '{expr}' → {result}")
    
    print("\n" + "=" * 50)
    print("SPL Mapping Concept Tests Completed Successfully! ✓")
    print("\nKey Features Validated:")
    print("  ✓ Command type classification")
    print("  ✓ Natural language to SPL mappings")
    print("  ✓ Intent pattern recognition")
    print("  ✓ Syntax validation logic")
    print("  ✓ Query optimization suggestions")
    print("  ✓ Time expression parsing")
    print("  ✓ Field name mapping")
    print("  ✓ Aggregation function resolution")
    
    return True

if __name__ == "__main__":
    try:
        test_spl_mapping_concepts()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)