#!/usr/bin/env python3
"""
Test script for advanced aggregation handling in SPL translation
"""

import re
from typing import Dict, List, Any


def test_aggregation_patterns():
    """Test advanced aggregation pattern detection"""
    print("=" * 60)
    print("TESTING ADVANCED AGGREGATION PATTERNS")
    print("=" * 60)
    
    # Test queries with various aggregation types
    test_queries = [
        # Statistical aggregations
        "Show me the 95th percentile of response time",
        "What's the standard deviation of cpu usage",
        "Find the median response time by host",
        "Calculate the range of temperatures",
        
        # Conditional aggregations
        "Count users where status equals active",
        "Sum bytes if method equals POST",
        "Average response time where status > 200",
        "Count of errors that contain timeout",
        
        # Temporal aggregations
        "Show the rate of events per hour",
        "Find the earliest login time",
        "Get the latest temperature reading",
        "Calculate events per minute over last hour",
        
        # Multi-field aggregations
        "Sum of price and tax by category",
        "Count of users and sessions by region",
        "Average of cpu and memory usage",
        
        # Multi-function aggregations
        "Sum and average of bytes by host",
        "Min and max temperature by sensor",
        "Count and sum of transactions",
        
        # Complex combinations
        "Show 99th percentile of response time and count of errors by host where status > 400",
        "Calculate sum of bytes and average response time by user if method equals GET"
    ]
    
    # Pattern definitions for testing
    statistical_patterns = [
        r"(\d+)(?:th|st|nd|rd)?\s+percentile\s+(?:of\s+)?(.+)",
        r"(?:standard deviation|stdev)\s+(?:of\s+)?(.+)",
        r"(?:median)\s+(?:of\s+)?(.+)",
        r"(?:range)\s+(?:of\s+)?(.+)"
    ]
    
    conditional_patterns = [
        r"(?:count|number)\s+(?:of\s+)?(.+?)\s+(?:where|if)\s+(.+)",
        r"(?:sum|total)\s+(?:of\s+)?(.+?)\s+(?:where|if)\s+(.+)",
        r"(?:average|mean)\s+(?:of\s+)?(.+?)\s+(?:where|if)\s+(.+)"
    ]
    
    temporal_patterns = [
        r"(?:rate|per second|per minute|per hour)\s+(?:of\s+)?(.+)",
        r"(?:earliest|first)\s+(?:value\s+)?(?:of\s+)?(.+)",
        r"(?:latest|last)\s+(?:value\s+)?(?:of\s+)?(.+)"
    ]
    
    multi_field_patterns = [
        r"(?:sum|total|add)\s+(?:of\s+)?(.+?)\s+(?:and|,)\s+(.+?)(?:\s+by|\s+group|$)",
        r"(?:count|number)\s+(?:of\s+)?(.+?)\s+(?:and|,)\s+(.+?)(?:\s+by|\s+group|$)"
    ]
    
    multi_function_patterns = [
        r"(?:sum|total)\s+(?:and|,)\s+(?:average|mean)\s+(?:of\s+)?(.+)",
        r"(?:min|minimum)\s+(?:and|,)\s+(?:max|maximum)\s+(?:of\s+)?(.+)"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        query_lower = query.lower()
        detected_patterns = []
        
        # Test statistical patterns
        for pattern in statistical_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                detected_patterns.append(("statistical", match.groups()))
        
        # Test conditional patterns
        for pattern in conditional_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                detected_patterns.append(("conditional", match.groups()))
        
        # Test temporal patterns
        for pattern in temporal_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                detected_patterns.append(("temporal", match.groups()))
        
        # Test multi-field patterns
        for pattern in multi_field_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                detected_patterns.append(("multi_field", match.groups()))
        
        # Test multi-function patterns
        for pattern in multi_function_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                detected_patterns.append(("multi_function", match.groups()))
        
        if detected_patterns:
            for pattern_type, groups in detected_patterns:
                print(f"  {pattern_type}: {groups}")
        else:
            print("  No advanced patterns detected")


def test_spl_generation():
    """Test SPL generation for advanced aggregations"""
    print("\n" + "=" * 60)
    print("TESTING SPL GENERATION FOR ADVANCED AGGREGATIONS")
    print("=" * 60)
    
    def generate_statistical_spl(function: str, field: str, parameter: Any = None) -> str:
        """Generate SPL for statistical functions"""
        if function == "percentile":
            return f"perc{parameter}({field})"
        elif function == "stdev":
            return f"stdev({field})"
        elif function == "median":
            return f"median({field})"
        elif function == "range":
            return f"range({field})"
        else:
            return f"{function}({field})"
    
    def generate_conditional_spl(function: str, field: str, condition: str) -> str:
        """Generate SPL for conditional functions"""
        if function == "count":
            return f"count(eval(if({condition}, {field}, null())))"
        elif function == "sum":
            return f"sum(eval(if({condition}, {field}, null())))"
        elif function == "avg":
            return f"avg(eval(if({condition}, {field}, null())))"
        else:
            return f"{function}(eval(if({condition}, {field}, null())))"
    
    def generate_temporal_spl(function: str, field: str = None) -> str:
        """Generate SPL for temporal functions"""
        if function == "rate":
            return f"rate({field})" if field else "rate(count)"
        elif function == "earliest":
            return f"earliest({field})" if field else "earliest(_time)"
        elif function == "latest":
            return f"latest({field})" if field else "latest(_time)"
        else:
            return f"{function}({field})" if field else f"{function}(_time)"
    
    # Test cases
    test_cases = [
        # Statistical functions
        {
            "type": "statistical",
            "function": "percentile",
            "field": "response_time",
            "parameter": 95,
            "expected": "perc95(response_time)"
        },
        {
            "type": "statistical", 
            "function": "stdev",
            "field": "cpu_usage",
            "expected": "stdev(cpu_usage)"
        },
        
        # Conditional functions
        {
            "type": "conditional",
            "function": "count",
            "field": "user",
            "condition": "status=\"active\"",
            "expected": "count(eval(if(status=\"active\", user, null())))"
        },
        {
            "type": "conditional",
            "function": "sum",
            "field": "bytes",
            "condition": "method=\"POST\"",
            "expected": "sum(eval(if(method=\"POST\", bytes, null())))"
        },
        
        # Temporal functions
        {
            "type": "temporal",
            "function": "rate",
            "field": "events",
            "expected": "rate(events)"
        },
        {
            "type": "temporal",
            "function": "earliest",
            "field": "login_time",
            "expected": "earliest(login_time)"
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTest Case {i+1}: {test_case['type'].upper()} - {test_case['function']}")
        print("-" * 40)
        
        if test_case["type"] == "statistical":
            generated = generate_statistical_spl(
                test_case["function"],
                test_case["field"],
                test_case.get("parameter")
            )
        elif test_case["type"] == "conditional":
            generated = generate_conditional_spl(
                test_case["function"],
                test_case["field"],
                test_case["condition"]
            )
        elif test_case["type"] == "temporal":
            generated = generate_temporal_spl(
                test_case["function"],
                test_case.get("field")
            )
        
        expected = test_case["expected"]
        print(f"Generated: {generated}")
        print(f"Expected:  {expected}")
        print(f"Match: {'✓' if generated == expected else '✗'}")


def test_complexity_analysis():
    """Test aggregation complexity analysis"""
    print("\n" + "=" * 60)
    print("TESTING AGGREGATION COMPLEXITY ANALYSIS")
    print("=" * 60)
    
    def analyze_aggregation_complexity(query: str) -> Dict[str, Any]:
        """Analyze aggregation complexity"""
        query_lower = query.lower()
        
        analysis = {
            "aggregation_count": 0,
            "statistical_functions": 0,
            "conditional_aggregations": 0,
            "temporal_aggregations": 0,
            "multi_field": False,
            "multi_function": False,
            "complexity_score": 0
        }
        
        # Count basic aggregations
        basic_aggs = ["count", "sum", "avg", "max", "min"]
        for agg in basic_aggs:
            if agg in query_lower:
                analysis["aggregation_count"] += 1
        
        # Count statistical functions
        stat_funcs = ["percentile", "stdev", "median", "range", "variance"]
        for func in stat_funcs:
            if func in query_lower:
                analysis["statistical_functions"] += 1
        
        # Count conditional aggregations
        if re.search(r"(?:where|if)\s+", query_lower):
            analysis["conditional_aggregations"] += 1
        
        # Count temporal aggregations
        temporal_keywords = ["rate", "earliest", "latest", "first", "last", "per hour", "per minute"]
        for keyword in temporal_keywords:
            if keyword in query_lower:
                analysis["temporal_aggregations"] += 1
        
        # Check for multi-field
        if re.search(r"(?:and|,)\s+", query_lower) and "by" in query_lower:
            analysis["multi_field"] = True
        
        # Check for multi-function
        multi_func_patterns = [
            r"(?:sum|total)\s+(?:and|,)\s+(?:count|number)",
            r"(?:min|minimum)\s+(?:and|,)\s+(?:max|maximum)"
        ]
        for pattern in multi_func_patterns:
            if re.search(pattern, query_lower):
                analysis["multi_function"] = True
        
        # Calculate complexity score
        score = 0
        score += analysis["aggregation_count"] * 1
        score += analysis["statistical_functions"] * 3
        score += analysis["conditional_aggregations"] * 2
        score += analysis["temporal_aggregations"] * 2
        score += 2 if analysis["multi_field"] else 0
        score += 2 if analysis["multi_function"] else 0
        
        analysis["complexity_score"] = score
        
        # Determine complexity level
        if score <= 2:
            analysis["complexity_level"] = "simple"
        elif score <= 5:
            analysis["complexity_level"] = "moderate"
        elif score <= 10:
            analysis["complexity_level"] = "complex"
        else:
            analysis["complexity_level"] = "advanced"
        
        return analysis
    
    test_queries = [
        "Count of users",
        "Sum of bytes by host",
        "95th percentile of response time",
        "Count of errors where status > 400",
        "Rate of events per hour",
        "Sum and average of bytes by host",
        "95th percentile of response time and count of errors by host where status > 400"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        analysis = analyze_aggregation_complexity(query)
        
        print(f"Aggregation count: {analysis['aggregation_count']}")
        print(f"Statistical functions: {analysis['statistical_functions']}")
        print(f"Conditional aggregations: {analysis['conditional_aggregations']}")
        print(f"Temporal aggregations: {analysis['temporal_aggregations']}")
        print(f"Multi-field: {analysis['multi_field']}")
        print(f"Multi-function: {analysis['multi_function']}")
        print(f"Complexity score: {analysis['complexity_score']}")
        print(f"Complexity level: {analysis['complexity_level']}")


def test_optimization_suggestions():
    """Test aggregation optimization suggestions"""
    print("\n" + "=" * 60)
    print("TESTING AGGREGATION OPTIMIZATION SUGGESTIONS")
    print("=" * 60)
    
    def generate_optimization_suggestions(query: str) -> List[str]:
        """Generate optimization suggestions for aggregations"""
        suggestions = []
        query_lower = query.lower()
        
        # Check for too many aggregations
        agg_count = sum(1 for agg in ["count", "sum", "avg", "max", "min", "stdev", "median"] if agg in query_lower)
        if agg_count > 3:
            suggestions.append("Consider breaking down complex aggregations into multiple queries")
        
        # Check for conditional aggregations
        if re.search(r"(?:where|if)\s+", query_lower):
            suggestions.append("Use field filters before aggregation to improve performance")
        
        # Check for statistical functions
        if any(func in query_lower for func in ["percentile", "stdev", "median", "range"]):
            suggestions.append("Statistical functions may be resource-intensive on large datasets")
        
        # Check for missing grouping
        if agg_count > 1 and "by" not in query_lower:
            suggestions.append("Consider adding grouping fields to organize results")
        
        # Check for time-based aggregations
        if any(keyword in query_lower for keyword in ["rate", "per hour", "per minute"]):
            suggestions.append("Consider using appropriate time spans for temporal aggregations")
        
        # Check for complex conditions
        if query_lower.count("and") + query_lower.count("or") > 2:
            suggestions.append("Complex conditions may benefit from pre-filtering")
        
        return suggestions
    
    test_queries = [
        "Count of users",
        "Sum of bytes where method equals POST",
        "95th percentile of response time",
        "Count, sum, average, and max of bytes",
        "Count of errors and sum of bytes by host where status > 400 and method equals POST",
        "Rate of events per hour by service"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        suggestions = generate_optimization_suggestions(query)
        
        if suggestions:
            print("Optimization suggestions:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. {suggestion}")
        else:
            print("No optimization suggestions needed")


def test_full_aggregation_workflow():
    """Test complete aggregation workflow"""
    print("\n" + "=" * 60)
    print("TESTING COMPLETE AGGREGATION WORKFLOW")
    print("=" * 60)
    
    def process_aggregation_query(query: str) -> Dict[str, Any]:
        """Process a complete aggregation query"""
        result = {
            "original_query": query,
            "detected_aggregations": [],
            "combined_spl": "",
            "complexity_analysis": {},
            "optimization_suggestions": []
        }
        
        query_lower = query.lower()
        
        # Detect aggregations (simplified)
        aggregations = []
        
        # Statistical aggregations
        if "percentile" in query_lower:
            match = re.search(r"(\d+)(?:th|st|nd|rd)?\s+percentile\s+(?:of\s+)?(\w+)", query_lower)
            if match:
                aggregations.append({
                    "function": "percentile",
                    "field": match.group(2),
                    "parameter": int(match.group(1)),
                    "type": "statistical"
                })
        
        # Basic aggregations
        basic_functions = ["count", "sum", "avg", "max", "min"]
        for func in basic_functions:
            if func in query_lower:
                field_match = re.search(rf"{func}\s+(?:of\s+)?(\w+)", query_lower)
                field = field_match.group(1) if field_match else None
                aggregations.append({
                    "function": func,
                    "field": field,
                    "type": "basic"
                })
        
        result["detected_aggregations"] = aggregations
        
        # Generate combined SPL
        if aggregations:
            spl_parts = []
            for agg in aggregations:
                if agg["type"] == "statistical" and agg["function"] == "percentile":
                    spl_parts.append(f"perc{agg['parameter']}({agg['field']})")
                elif agg["field"]:
                    spl_parts.append(f"{agg['function']}({agg['field']})")
                else:
                    spl_parts.append(agg["function"])
            
            # Check for by clause
            by_match = re.search(r"(?:by|group by)\s+(\w+)", query_lower)
            by_field = by_match.group(1) if by_match else None
            
            if by_field:
                result["combined_spl"] = f"stats {', '.join(spl_parts)} by {by_field}"
            else:
                result["combined_spl"] = f"stats {', '.join(spl_parts)}"
        
        # Complexity analysis
        result["complexity_analysis"] = {
            "aggregation_count": len(aggregations),
            "has_statistical": any(agg["type"] == "statistical" for agg in aggregations),
            "has_grouping": "by" in query_lower,
            "complexity_level": "advanced" if any(agg["type"] == "statistical" for agg in aggregations) else "simple"
        }
        
        # Generate suggestions
        suggestions = []
        if len(aggregations) > 2:
            suggestions.append("Consider breaking down into multiple queries")
        if any(agg["type"] == "statistical" for agg in aggregations):
            suggestions.append("Statistical functions may require additional processing time")
        if not result["complexity_analysis"]["has_grouping"] and len(aggregations) > 1:
            suggestions.append("Consider adding grouping fields")
        
        result["optimization_suggestions"] = suggestions
        
        return result
    
    test_queries = [
        "Count of users by host",
        "95th percentile of response time by service",
        "Sum of bytes and count of requests by host",
        "Average response time where status > 400"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        result = process_aggregation_query(query)
        
        print(f"Detected aggregations: {len(result['detected_aggregations'])}")
        for agg in result["detected_aggregations"]:
            print(f"  - {agg['function']} of {agg.get('field', 'N/A')} ({agg['type']})")
        
        print(f"Generated SPL: {result['combined_spl']}")
        print(f"Complexity: {result['complexity_analysis']['complexity_level']}")
        
        if result["optimization_suggestions"]:
            print("Suggestions:")
            for suggestion in result["optimization_suggestions"]:
                print(f"  • {suggestion}")


if __name__ == "__main__":
    print("Testing Advanced Aggregation Handling")
    print("=" * 60)
    
    # Run all tests
    test_aggregation_patterns()
    test_spl_generation()
    test_complexity_analysis()
    test_optimization_suggestions()
    test_full_aggregation_workflow()
    
    print("\n" + "=" * 60)
    print("ADVANCED AGGREGATION TESTING COMPLETE")
    print("=" * 60)