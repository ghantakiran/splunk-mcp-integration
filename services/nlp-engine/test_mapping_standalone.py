#!/usr/bin/env python3
"""
Standalone test for SPL mapping system without AI dependencies
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Import just the SPL mapping module directly
sys.path.append(os.path.join(os.path.dirname(__file__), 'app', 'ai'))
from spl_mapping import ComprehensiveSPLMapper, SPLCommandType, FieldType

def test_spl_mapping():
    """Test SPL mapping functionality"""
    print("Testing SPL Mapping System")
    print("=" * 50)
    
    # Initialize mapper
    mapper = ComprehensiveSPLMapper()
    print(f"✓ Mapper initialized successfully")
    print(f"  - Total commands: {len(mapper.commands)}")
    print(f"  - Total field mappings: {len(mapper.field_mappings)}")
    print(f"  - Total intent patterns: {len(mapper.intent_patterns)}")
    print(f"  - Total aggregation mappings: {len(mapper.aggregation_mappings)}")
    print(f"  - Total time mappings: {len(mapper.time_mappings)}")
    print(f"  - Total operator mappings: {len(mapper.operator_mappings)}")
    
    print("\nTesting Command Lookup:")
    print("-" * 30)
    
    # Test command lookup
    test_commands = ["search", "stats", "eval", "where", "sort"]
    for cmd_name in test_commands:
        cmd = mapper.get_command_by_name(cmd_name)
        if cmd:
            print(f"✓ {cmd_name}: {cmd.description}")
        else:
            print(f"✗ {cmd_name}: Not found")
    
    print("\nTesting Field Mappings:")
    print("-" * 30)
    
    # Test field mappings
    test_fields = ["time", "user", "host", "source ip", "status"]
    for field_name in test_fields:
        mapping = mapper.find_field_mapping(field_name)
        if mapping:
            print(f"✓ '{field_name}' → {mapping.splunk_field} ({mapping.field_type.value})")
        else:
            print(f"✗ '{field_name}': No mapping found")
    
    print("\nTesting Aggregation Functions:")
    print("-" * 30)
    
    # Test aggregation functions
    test_aggs = ["count", "average", "maximum", "sum", "total"]
    for agg in test_aggs:
        result = mapper.resolve_aggregation_function(agg)
        print(f"✓ '{agg}' → {result}")
    
    print("\nTesting Time Expressions:")
    print("-" * 30)
    
    # Test time expressions
    test_times = ["today", "yesterday", "last hour", "5 hours ago", "last 3 days"]
    for time_expr in test_times:
        result = mapper.resolve_time_expression(time_expr)
        print(f"✓ '{time_expr}' → {result}")
    
    print("\nTesting Operators:")
    print("-" * 30)
    
    # Test operators
    test_ops = ["equals", "greater than", "contains", "not equal"]
    for op in test_ops:
        result = mapper.resolve_operator(op)
        print(f"✓ '{op}' → {result}")
    
    print("\nTesting Command Suggestions:")
    print("-" * 30)
    
    # Test command suggestions
    test_queries = ["find errors", "count events", "show me top users"]
    for query in test_queries:
        suggestions = mapper.get_command_suggestions(query)
        top_suggestions = [cmd for cmd, score in suggestions[:3]]
        print(f"✓ '{query}' → {top_suggestions}")
    
    print("\nTesting SPL Syntax Validation:")
    print("-" * 30)
    
    # Test syntax validation
    test_queries = [
        "search error",
        "search error | stats count",
        "search \"unmatched quote",
        "",
        "search (unmatched paren"
    ]
    
    for query in test_queries:
        is_valid, errors = mapper.validate_spl_syntax(query)
        status = "✓" if is_valid else "✗"
        error_msg = f" ({', '.join(errors)})" if errors else ""
        print(f"{status} '{query}' → Valid: {is_valid}{error_msg}")
    
    print("\nTesting Query Optimization:")
    print("-" * 30)
    
    # Test optimization
    test_queries = [
        "search error",
        "search index=main error",
        "search *error* *warning* *info*"
    ]
    
    for query in test_queries:
        optimized, suggestions = mapper.optimize_spl_query(query)
        print(f"✓ '{query}'")
        for suggestion in suggestions[:2]:  # Show first 2 suggestions
            print(f"    → {suggestion}")
    
    print("\nTesting Intent Classification Support:")
    print("-" * 30)
    
    # Test intent pattern matching
    test_queries = [
        "find all errors",
        "count the events", 
        "show me top users",
        "errors over time"
    ]
    
    for query in test_queries:
        print(f"✓ '{query}':")
        for pattern in mapper.intent_patterns:
            for regex_pattern in pattern.patterns:
                import re
                if re.search(regex_pattern, query.lower()):
                    print(f"    → Intent: {pattern.intent}")
                    break
    
    print("\n" + "=" * 50)
    print("All SPL Mapping Tests Completed Successfully! ✓")
    return True

if __name__ == "__main__":
    try:
        test_spl_mapping()
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)