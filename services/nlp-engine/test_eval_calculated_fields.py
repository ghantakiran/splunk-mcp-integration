#!/usr/bin/env python3
"""
Test script for eval and calculated fields system in SPL translation
"""

import re
from typing import Dict, List, Any
import json


def test_eval_function_detection():
    """Test eval function detection from natural language"""
    print("=" * 60)
    print("TESTING EVAL FUNCTION DETECTION")
    print("=" * 60)
    
    # Test queries with various eval function requirements
    test_queries = [
        # Mathematical functions
        "Calculate the sum of response_time and processing_time",
        "Compute the average of cpu_usage",
        "Find the absolute value of temperature_difference",
        "Round the price to 2 decimal places",
        "Get the square root of variance",
        "Calculate percentage of successful requests",
        
        # String functions
        "Convert username to uppercase",
        "Get the length of error_message",
        "Extract first 10 characters from description",
        "Replace spaces with underscores in file_name",
        "Trim whitespace from user_input",
        "Split user_roles by comma",
        
        # DateTime functions
        "Get the current timestamp",
        "Format timestamp as YYYY-MM-DD",
        "Extract year from event_time",
        "Calculate time difference between start and end",
        "Parse date_string as timestamp",
        
        # Conditional functions
        "If status is 200 then OK else ERROR",
        "Set priority to high when severity is critical",
        "Use default value unknown if username is null",
        "Choose first non-null value from user_name and user_id",
        
        # Validation functions
        "Check if response_time is numeric",
        "Verify that email is not null",
        "Test if message contains error",
        "Validate that port is a number",
        
        # Conversion functions
        "Convert response_code to string",
        "Parse user_id as number",
        "Cast price as numeric value"
    ]
    
    # Simplified detection functions for testing
    def detect_mathematical_functions(query: str) -> List[Dict[str, Any]]:
        """Detect mathematical function patterns"""
        detected = []
        query_lower = query.lower()
        
        math_patterns = {
            "sum": ["sum", "add", "total", "plus"],
            "avg": ["average", "mean"],
            "abs": ["absolute", "abs"],
            "round": ["round"],
            "sqrt": ["square root", "sqrt"],
            "percentage": ["percentage", "percent"]
        }
        
        for func_name, keywords in math_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                detected.append({
                    "function": func_name,
                    "type": "mathematical",
                    "description": f"Mathematical operation: {func_name}"
                })
        
        return detected
    
    def detect_string_functions(query: str) -> List[Dict[str, Any]]:
        """Detect string function patterns"""
        detected = []
        query_lower = query.lower()
        
        string_patterns = {
            "upper": ["uppercase", "upper"],
            "lower": ["lowercase", "lower"],
            "len": ["length", "len"],
            "substr": ["extract", "substring", "first", "characters"],
            "replace": ["replace"],
            "trim": ["trim", "whitespace"],
            "split": ["split"]
        }
        
        for func_name, keywords in string_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                detected.append({
                    "function": func_name,
                    "type": "string",
                    "description": f"String manipulation: {func_name}"
                })
        
        return detected
    
    def detect_datetime_functions(query: str) -> List[Dict[str, Any]]:
        """Detect datetime function patterns"""
        detected = []
        query_lower = query.lower()
        
        datetime_patterns = {
            "now": ["current", "now", "timestamp"],
            "strftime": ["format", "yyyy-mm-dd"],
            "strptime": ["parse", "date_string"],
            "time_extract": ["extract", "year", "month", "day", "hour"],
            "time_diff": ["difference", "between"]
        }
        
        for func_name, keywords in datetime_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                detected.append({
                    "function": func_name,
                    "type": "datetime",
                    "description": f"Date/time operation: {func_name}"
                })
        
        return detected
    
    def detect_conditional_functions(query: str) -> List[Dict[str, Any]]:
        """Detect conditional function patterns"""
        detected = []
        query_lower = query.lower()
        
        conditional_patterns = {
            "if": ["if", "then", "else"],
            "case": ["when", "choose", "select"],
            "coalesce": ["default", "first non-null", "null"],
            "nullif": ["set null", "nullif"]
        }
        
        for func_name, keywords in conditional_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                detected.append({
                    "function": func_name,
                    "type": "conditional",
                    "description": f"Conditional logic: {func_name}"
                })
        
        return detected
    
    def detect_validation_functions(query: str) -> List[Dict[str, Any]]:
        """Detect validation function patterns"""
        detected = []
        query_lower = query.lower()
        
        validation_patterns = {
            "isnum": ["numeric", "number"],
            "isnull": ["null", "empty"],
            "isnotnull": ["not null", "verify"],
            "match": ["contains", "test"]
        }
        
        for func_name, keywords in validation_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                detected.append({
                    "function": func_name,
                    "type": "validation",
                    "description": f"Data validation: {func_name}"
                })
        
        return detected
    
    def detect_conversion_functions(query: str) -> List[Dict[str, Any]]:
        """Detect conversion function patterns"""
        detected = []
        query_lower = query.lower()
        
        conversion_patterns = {
            "tostring": ["to string", "as string", "convert.*string"],
            "tonumber": ["to number", "as number", "parse.*number", "cast.*numeric"]
        }
        
        for func_name, keywords in conversion_patterns.items():
            if any(re.search(keyword, query_lower) for keyword in keywords):
                detected.append({
                    "function": func_name,
                    "type": "conversion",
                    "description": f"Type conversion: {func_name}"
                })
        
        return detected
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        all_detected = []
        all_detected.extend(detect_mathematical_functions(query))
        all_detected.extend(detect_string_functions(query))
        all_detected.extend(detect_datetime_functions(query))
        all_detected.extend(detect_conditional_functions(query))
        all_detected.extend(detect_validation_functions(query))
        all_detected.extend(detect_conversion_functions(query))
        
        if all_detected:
            for func in all_detected:
                print(f"  Function: {func['function']}")
                print(f"  Type: {func['type']}")
                print(f"  Description: {func['description']}")
                print()
        else:
            print("  No eval functions detected")


def test_spl_generation_for_eval():
    """Test SPL generation for eval expressions"""
    print("\n" + "=" * 60)
    print("TESTING SPL GENERATION FOR EVAL EXPRESSIONS")
    print("=" * 60)
    
    def generate_eval_spl(expression_type: str, field_name: str, expression: str) -> str:
        """Generate eval SPL command"""
        return f"eval {field_name}={expression}"
    
    test_cases = [
        # Mathematical expressions
        {
            "type": "mathematical",
            "description": "Sum of two fields",
            "field_name": "total_time",
            "expression": "response_time + processing_time",
            "expected_pattern": "eval total_time=response_time + processing_time"
        },
        {
            "type": "mathematical",
            "description": "Percentage calculation",
            "field_name": "success_rate",
            "expression": "round((successful_requests / total_requests) * 100, 2)",
            "expected_pattern": "eval success_rate=round((successful_requests / total_requests) * 100, 2)"
        },
        
        # String expressions
        {
            "type": "string",
            "description": "Convert to uppercase",
            "field_name": "status_upper",
            "expression": "upper(status)",
            "expected_pattern": "eval status_upper=upper(status)"
        },
        {
            "type": "string",
            "description": "Extract substring",
            "field_name": "short_message",
            "expression": "substr(message, 1, 50)",
            "expected_pattern": "eval short_message=substr(message, 1, 50)"
        },
        
        # DateTime expressions
        {
            "type": "datetime",
            "description": "Format timestamp",
            "field_name": "formatted_date",
            "expression": "strftime(_time, \"%Y-%m-%d\")",
            "expected_pattern": "eval formatted_date=strftime(_time, \"%Y-%m-%d\")"
        },
        {
            "type": "datetime",
            "description": "Extract hour",
            "field_name": "hour",
            "expression": "tonumber(strftime(_time, \"%H\"))",
            "expected_pattern": "eval hour=tonumber(strftime(_time, \"%H\"))"
        },
        
        # Conditional expressions
        {
            "type": "conditional",
            "description": "Simple if condition",
            "field_name": "status_category",
            "expression": "if(status<400, \"Success\", \"Error\")",
            "expected_pattern": "eval status_category=if(status<400, \"Success\", \"Error\")"
        },
        {
            "type": "conditional",
            "description": "Case statement",
            "field_name": "priority_level",
            "expression": "case(severity=\"critical\", 1, severity=\"high\", 2, severity=\"medium\", 3, 4)",
            "expected_pattern": "eval priority_level=case(severity=\"critical\", 1, severity=\"high\", 2, severity=\"medium\", 3, 4)"
        },
        
        # Validation expressions
        {
            "type": "validation",
            "description": "Check if numeric",
            "field_name": "is_numeric_port",
            "expression": "isnum(port)",
            "expected_pattern": "eval is_numeric_port=isnum(port)"
        },
        {
            "type": "validation",
            "description": "Check if not null",
            "field_name": "has_user",
            "expression": "isnotnull(username)",
            "expected_pattern": "eval has_user=isnotnull(username)"
        },
        
        # Conversion expressions
        {
            "type": "conversion",
            "description": "Convert to number",
            "field_name": "numeric_code",
            "expression": "tonumber(response_code)",
            "expected_pattern": "eval numeric_code=tonumber(response_code)"
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTest Case {i+1}: {test_case['type'].upper()}")
        print(f"Description: {test_case['description']}")
        print("-" * 40)
        
        generated = generate_eval_spl(
            test_case["type"],
            test_case["field_name"], 
            test_case["expression"]
        )
        
        expected = test_case["expected_pattern"]
        print(f"Generated: {generated}")
        print(f"Expected:  {expected}")
        print(f"Match: {'✓' if expected == generated else '✗'}")


def test_eval_expression_validation():
    """Test eval expression validation"""
    print("\n" + "=" * 60)
    print("TESTING EVAL EXPRESSION VALIDATION")
    print("=" * 60)
    
    def validate_eval_expression(field_name: str, expression: str) -> Dict[str, Any]:
        """Validate eval expression"""
        validation = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # Check basic requirements
        if not field_name or not field_name.strip():
            validation["errors"].append("Field name is required")
            validation["valid"] = False
        
        if not expression or not expression.strip():
            validation["errors"].append("Expression is required")
            validation["valid"] = False
            return validation
        
        # Check for unmatched parentheses
        if expression.count("(") != expression.count(")"):
            validation["errors"].append("Unmatched parentheses")
            validation["valid"] = False
        
        # Check for unmatched quotes
        single_quotes = expression.count("'")
        double_quotes = expression.count('"')
        
        if single_quotes % 2 != 0:
            validation["warnings"].append("Unmatched single quotes")
        
        if double_quotes % 2 != 0:
            validation["warnings"].append("Unmatched double quotes")
        
        # Check expression length
        if len(expression) > 200:
            validation["warnings"].append("Very long expression may impact performance")
        
        # Check for complex case statements
        if expression.count("case(") > 3:
            validation["warnings"].append("Multiple case statements may impact performance")
            validation["suggestions"].append("Consider breaking down complex expressions")
        
        # Check for field name conventions
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', field_name):
            validation["warnings"].append("Field name should follow naming conventions")
        
        return validation
    
    test_cases = [
        # Valid expressions
        {
            "name": "Valid mathematical expression",
            "field_name": "total_time",
            "expression": "response_time + processing_time"
        },
        {
            "name": "Valid conditional expression",
            "field_name": "status_category",
            "expression": "if(status<400, \"Success\", \"Error\")"
        },
        
        # Invalid expressions
        {
            "name": "Missing field name",
            "field_name": "",
            "expression": "upper(status)"
        },
        {
            "name": "Missing expression",
            "field_name": "result",
            "expression": ""
        },
        {
            "name": "Unmatched parentheses",
            "field_name": "result",
            "expression": "if(status<400, \"Success\", \"Error\""
        },
        {
            "name": "Unmatched quotes",
            "field_name": "result",
            "expression": "if(status<400, \"Success, \"Error\")"
        },
        
        # Performance issues
        {
            "name": "Very long expression",
            "field_name": "complex_result",
            "expression": "if(field1>100, \"high\", if(field2>50, \"medium\", if(field3>25, \"low\", if(field4>10, \"very_low\", if(field5>5, \"minimal\", \"none\")))))" * 2
        },
        {
            "name": "Multiple case statements",
            "field_name": "category",
            "expression": "case(type=\"A\", \"Alpha\", type=\"B\", \"Beta\") + case(status=\"OK\", \"Good\", \"Bad\") + case(level>5, \"High\", \"Low\") + case(score>90, \"Excellent\", \"Average\")"
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTest: {test_case['name']}")
        print("-" * 40)
        
        validation = validate_eval_expression(
            test_case["field_name"],
            test_case["expression"]
        )
        
        print(f"Valid: {'✓' if validation['valid'] else '✗'}")
        print(f"Field Name: '{test_case['field_name']}'")
        print(f"Expression: '{test_case['expression'][:80]}{'...' if len(test_case['expression']) > 80 else ''}'")
        
        if validation["errors"]:
            print("Errors:")
            for error in validation["errors"]:
                print(f"  ❌ {error}")
        
        if validation["warnings"]:
            print("Warnings:")
            for warning in validation["warnings"]:
                print(f"  ⚠️  {warning}")
        
        if validation["suggestions"]:
            print("Suggestions:")
            for suggestion in validation["suggestions"]:
                print(f"  💡 {suggestion}")
        
        if validation["valid"] and not validation["warnings"]:
            print("✓ No issues found")


def test_common_eval_expressions():
    """Test common eval expression templates"""
    print("\n" + "=" * 60)
    print("TESTING COMMON EVAL EXPRESSIONS")
    print("=" * 60)
    
    common_expressions = {
        "url_domain": {
            "expression": "replace(replace(url, \"^https?://([^/]+).*\", \"\\1\"), \"^www\\.\", \"\")",
            "description": "Extract domain from URL",
            "example_input": "https://www.example.com/path",
            "expected_output": "example.com"
        },
        "file_extension": {
            "expression": "if(match(file_path, \"\\.[^.]+$\"), replace(file_path, \".*\\.(\\w+)$\", \"\\1\"), \"none\")",
            "description": "Extract file extension from path",
            "example_input": "/path/to/document.pdf",
            "expected_output": "pdf"
        },
        "http_status_category": {
            "expression": "case(status<300, \"Success\", status<400, \"Redirect\", status<500, \"Client Error\", \"Server Error\")",
            "description": "Categorize HTTP status codes",
            "example_input": "404",
            "expected_output": "Client Error"
        },
        "email_domain": {
            "expression": "if(match(email, \"@\"), replace(email, \".*@(.*)\", \"\\1\"), null())",
            "description": "Extract domain from email address",
            "example_input": "user@example.com",
            "expected_output": "example.com"
        },
        "business_hours": {
            "expression": "if(tonumber(strftime(_time, \"%H\"))>=9 AND tonumber(strftime(_time, \"%H\"))<17 AND tonumber(strftime(_time, \"%w\"))>=1 AND tonumber(strftime(_time, \"%w\"))<=5, \"Business Hours\", \"Off Hours\")",
            "description": "Classify events as business hours or off hours",
            "example_input": "Timestamp during weekday 2PM",
            "expected_output": "Business Hours"
        },
        "response_time_category": {
            "expression": "case(response_time<100, \"Fast\", response_time<500, \"Normal\", response_time<2000, \"Slow\", \"Very Slow\")",
            "description": "Categorize response times by performance",
            "example_input": "250ms",
            "expected_output": "Normal"
        }
    }
    
    for expr_name, expr_info in common_expressions.items():
        print(f"\nExpression: {expr_name.upper()}")
        print(f"Description: {expr_info['description']}")
        print("-" * 40)
        
        print(f"Expression: {expr_info['expression']}")
        print(f"Example Input: {expr_info['example_input']}")
        print(f"Expected Output: {expr_info['expected_output']}")
        
        # Generate SPL command
        spl_command = f"eval {expr_name}={expr_info['expression']}"
        print(f"SPL Command: {spl_command}")
        
        # Simple complexity analysis
        complexity = "Simple"
        if expr_info['expression'].count("case(") > 0:
            complexity = "Complex"
        elif expr_info['expression'].count("if(") > 1:
            complexity = "Moderate"
        elif len(expr_info['expression']) > 100:
            complexity = "Moderate"
        
        print(f"Complexity: {complexity}")


def test_eval_function_suggestions():
    """Test eval function suggestions based on query"""
    print("\n" + "=" * 60)
    print("TESTING EVAL FUNCTION SUGGESTIONS")
    print("=" * 60)
    
    def suggest_eval_functions(query: str, available_fields: List[str] = None) -> List[Dict[str, Any]]:
        """Suggest eval functions based on query"""
        query_lower = query.lower()
        available_fields = available_fields or []
        suggestions = []
        
        # Function categories and their keywords
        function_suggestions = {
            "mathematical": {
                "functions": ["sum", "avg", "abs", "round", "pow", "sqrt"],
                "keywords": ["calculate", "compute", "math", "sum", "average", "total", "round"],
                "score_base": 8
            },
            "string": {
                "functions": ["upper", "lower", "len", "substr", "replace", "trim", "split"],
                "keywords": ["text", "string", "upper", "lower", "length", "extract", "replace"],
                "score_base": 7
            },
            "datetime": {
                "functions": ["now", "strftime", "strptime", "relative_time"],
                "keywords": ["time", "date", "format", "parse", "now", "current"],
                "score_base": 9
            },
            "conditional": {
                "functions": ["if", "case", "coalesce", "nullif"],
                "keywords": ["if", "when", "case", "condition", "choose", "default"],
                "score_base": 8
            },
            "validation": {
                "functions": ["isnull", "isnotnull", "isnum", "match"],
                "keywords": ["check", "verify", "validate", "null", "empty", "numeric"],
                "score_base": 6
            },
            "conversion": {
                "functions": ["tonumber", "tostring"],
                "keywords": ["convert", "parse", "cast", "number", "string"],
                "score_base": 5
            }
        }
        
        for category, info in function_suggestions.items():
            score = 0
            reasons = []
            
            # Check for category keywords
            for keyword in info["keywords"]:
                if keyword in query_lower:
                    score += 2
                    reasons.append(f"Keyword '{keyword}' found")
            
            # Check for function names
            for func_name in info["functions"]:
                if func_name in query_lower:
                    score += 5
                    reasons.append(f"Function '{func_name}' mentioned")
            
            # Check for field relevance
            for field in available_fields:
                if field in query_lower:
                    score += 1
                    reasons.append(f"Field '{field}' available")
            
            if score > 0:
                suggestions.append({
                    "category": category,
                    "functions": info["functions"][:3],  # Top 3 functions
                    "score": score + info["score_base"],
                    "reasons": reasons
                })
        
        # Sort by score
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return suggestions[:5]  # Top 5 suggestions
    
    test_queries = [
        {
            "query": "Calculate the total response time for each user",
            "available_fields": ["user", "response_time", "request_count"]
        },
        {
            "query": "Convert all usernames to uppercase",
            "available_fields": ["username", "user_id", "email"]
        },
        {
            "query": "Check if the error message is not null",
            "available_fields": ["error_message", "error_code", "status"]
        },
        {
            "query": "Format the timestamp as YYYY-MM-DD",
            "available_fields": ["timestamp", "_time", "event_time"]
        },
        {
            "query": "If status is 200 then success else error",
            "available_fields": ["status", "response_code", "method"]
        },
        {
            "query": "Parse the port number as integer",
            "available_fields": ["port", "host", "service"]
        }
    ]
    
    for test_query in test_queries:
        print(f"\nQuery: '{test_query['query']}'")
        print(f"Available Fields: {', '.join(test_query['available_fields'])}")
        print("-" * 50)
        
        suggestions = suggest_eval_functions(
            test_query["query"], 
            test_query["available_fields"]
        )
        
        if suggestions:
            for suggestion in suggestions:
                print(f"  Category: {suggestion['category']}")
                print(f"  Functions: {', '.join(suggestion['functions'])}")
                print(f"  Score: {suggestion['score']}")
                print(f"  Reasons: {', '.join(suggestion['reasons'])}")
                print()
        else:
            print("  No function suggestions found")


if __name__ == "__main__":
    print("Testing Eval and Calculated Fields System")
    print("=" * 60)
    
    # Run all tests
    test_eval_function_detection()
    test_spl_generation_for_eval()
    test_eval_expression_validation()
    test_common_eval_expressions()
    test_eval_function_suggestions()
    
    print("\n" + "=" * 60)
    print("EVAL AND CALCULATED FIELDS TESTING COMPLETE")
    print("=" * 60)