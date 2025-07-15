#!/usr/bin/env python3
"""
Test script for regex pattern matching system in SPL translation
"""

import re
from typing import Dict, List, Any
import json


def test_regex_pattern_detection():
    """Test regex pattern detection from natural language"""
    print("=" * 60)
    print("TESTING REGEX PATTERN DETECTION")
    print("=" * 60)
    
    # Test queries with various pattern matching requirements
    test_queries = [
        # Extraction patterns
        "Extract email addresses from log messages",
        "Get IP addresses from network logs",
        "Find phone numbers in customer data",
        "Extract URLs from web logs",
        "Parse timestamps from application logs",
        
        # Filtering patterns
        "Filter events containing error messages",
        "Show only successful login attempts",
        "Find events matching warning patterns",
        "Filter by IP address patterns",
        
        # Replacement patterns
        "Replace sensitive data with masked values in logs",
        "Change error codes to descriptions in messages",
        "Substitute IP addresses with hostnames",
        
        # Validation patterns
        "Validate email format in user data",
        "Check if phone numbers are valid",
        "Verify IP address format",
        
        # Complex combinations
        "Extract email addresses and IP addresses from security logs",
        "Find and replace credit card numbers with masked values"
    ]
    
    # Pattern detection functions (simplified for testing)
    def detect_extraction_patterns(query: str) -> List[Dict[str, str]]:
        """Detect extraction patterns"""
        patterns = []
        query_lower = query.lower()
        
        if "email" in query_lower:
            patterns.append({
                "type": "extraction",
                "target": "email",
                "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "spl": "rex field=_raw \"(?<email>\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b)\""
            })
        
        if "ip" in query_lower or "address" in query_lower:
            patterns.append({
                "type": "extraction",
                "target": "ip_address",
                "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
                "spl": "rex field=_raw \"(?<ip_address>\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b)\""
            })
        
        if "phone" in query_lower:
            patterns.append({
                "type": "extraction",
                "target": "phone",
                "pattern": r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
                "spl": "rex field=_raw \"(?<phone>\\b(?:\\+?1[-\\.\\s]?)?\\(?[0-9]{3}\\)?[-\\.\\s]?[0-9]{3}[-\\.\\s]?[0-9]{4}\\b)\""
            })
        
        if "url" in query_lower or "link" in query_lower:
            patterns.append({
                "type": "extraction",
                "target": "url",
                "pattern": r"https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*)?",
                "spl": "rex field=_raw \"(?<url>https?://(?:[-\\w.])+(?:\\:[0-9]+)?(?:/(?:[\\w/_.])*)?)\""
            })
        
        if "timestamp" in query_lower or "time" in query_lower:
            patterns.append({
                "type": "extraction",
                "target": "timestamp",
                "pattern": r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}",
                "spl": "rex field=_raw \"(?<timestamp>\\d{4}-\\d{2}-\\d{2}\\s+\\d{2}:\\d{2}:\\d{2})\""
            })
        
        return patterns
    
    def detect_filtering_patterns(query: str) -> List[Dict[str, str]]:
        """Detect filtering patterns"""
        patterns = []
        query_lower = query.lower()
        
        if "error" in query_lower:
            patterns.append({
                "type": "filtering",
                "target": "error_messages",
                "pattern": r"(?i)error|fail|exception",
                "spl": "regex _raw=\"(?i)error|fail|exception\""
            })
        
        if "success" in query_lower:
            patterns.append({
                "type": "filtering",
                "target": "successful_events",
                "pattern": r"(?i)success|ok|complete",
                "spl": "regex _raw=\"(?i)success|ok|complete\""
            })
        
        if "warning" in query_lower:
            patterns.append({
                "type": "filtering",
                "target": "warning_events",
                "pattern": r"(?i)warn|warning|caution",
                "spl": "regex _raw=\"(?i)warn|warning|caution\""
            })
        
        return patterns
    
    def detect_validation_patterns(query: str) -> List[Dict[str, str]]:
        """Detect validation patterns"""
        patterns = []
        query_lower = query.lower()
        
        if "validate" in query_lower and "email" in query_lower:
            patterns.append({
                "type": "validation",
                "target": "email_validation",
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                "spl": "regex email=\"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$\""
            })
        
        if "validate" in query_lower and ("phone" in query_lower or "number" in query_lower):
            patterns.append({
                "type": "validation",
                "target": "phone_validation",
                "pattern": r"^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$",
                "spl": "regex phone=\"^\\+?1?[-\\.\\s]?\\(?[0-9]{3}\\)?[-\\.\\s]?[0-9]{3}[-\\.\\s]?[0-9]{4}$\""
            })
        
        return patterns
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        detected_patterns = []
        detected_patterns.extend(detect_extraction_patterns(query))
        detected_patterns.extend(detect_filtering_patterns(query))
        detected_patterns.extend(detect_validation_patterns(query))
        
        if detected_patterns:
            for pattern in detected_patterns:
                print(f"  Type: {pattern['type']}")
                print(f"  Target: {pattern['target']}")
                print(f"  Pattern: {pattern['pattern']}")
                print(f"  SPL: {pattern['spl']}")
                print()
        else:
            print("  No regex patterns detected")


def test_common_regex_patterns():
    """Test common regex patterns"""
    print("\n" + "=" * 60)
    print("TESTING COMMON REGEX PATTERNS")
    print("=" * 60)
    
    common_patterns = {
        "ip_address": {
            "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "test_data": [
                "192.168.1.1",
                "10.0.0.1", 
                "172.16.0.1",
                "invalid.ip",
                "999.999.999.999"
            ],
            "expected_matches": [True, True, True, False, False]
        },
        "email": {
            "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "test_data": [
                "user@example.com",
                "test.email+tag@domain.org",
                "invalid-email",
                "user@",
                "@domain.com"
            ],
            "expected_matches": [True, True, False, False, False]
        },
        "url": {
            "pattern": r"https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*)?(?:\?(?:[\w&=%.])*)?",
            "test_data": [
                "https://example.com",
                "http://test.org/path?param=value",
                "ftp://invalid.protocol",
                "https://",
                "not-a-url"
            ],
            "expected_matches": [True, True, False, False, False]
        },
        "phone": {
            "pattern": r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
            "test_data": [
                "+1-555-123-4567",
                "(555) 123-4567",
                "555.123.4567",
                "5551234567",
                "invalid-phone"
            ],
            "expected_matches": [True, True, True, True, False]
        },
        "timestamp": {
            "pattern": r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}",
            "test_data": [
                "2023-01-15 14:30:45",
                "2023-12-31 23:59:59",
                "invalid-timestamp",
                "2023-01-15",
                "14:30:45"
            ],
            "expected_matches": [True, True, False, False, False]
        }
    }
    
    for pattern_name, pattern_info in common_patterns.items():
        print(f"\nTesting {pattern_name.upper()} pattern:")
        print(f"Pattern: {pattern_info['pattern']}")
        print("-" * 40)
        
        pattern = re.compile(pattern_info['pattern'])
        
        for i, test_string in enumerate(pattern_info['test_data']):
            match = bool(pattern.search(test_string))
            expected = pattern_info['expected_matches'][i]
            result = "✓" if match == expected else "✗"
            
            print(f"  {result} '{test_string}' -> {match} (expected: {expected})")


def test_spl_generation():
    """Test SPL generation for regex patterns"""
    print("\n" + "=" * 60)
    print("TESTING SPL GENERATION FOR REGEX PATTERNS")
    print("=" * 60)
    
    def generate_rex_spl(field_name: str, pattern: str, source_field: str = "_raw") -> str:
        """Generate rex command SPL"""
        # Escape regex pattern for SPL
        escaped_pattern = pattern.replace("\\", "\\\\").replace("\"", "\\\"")
        return f"rex field={source_field} \"(?<{field_name}>{escaped_pattern})\""
    
    def generate_regex_spl(pattern: str, source_field: str = "_raw") -> str:
        """Generate regex command SPL"""
        escaped_pattern = pattern.replace("\\", "\\\\").replace("\"", "\\\"")
        return f"regex {source_field}=\"{escaped_pattern}\""
    
    def generate_replace_spl(source_field: str, find_pattern: str, replace_text: str, target_field: str) -> str:
        """Generate replace command SPL"""
        escaped_find = find_pattern.replace("\"", "\\\"")
        escaped_replace = replace_text.replace("\"", "\\\"")
        return f"eval {target_field}=replace({source_field}, \"{escaped_find}\", \"{escaped_replace}\")"
    
    test_cases = [
        # Extraction patterns
        {
            "type": "extraction",
            "description": "Extract email addresses",
            "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "field_name": "email",
            "expected_spl": "rex field=_raw \"(?<email>\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b)\""
        },
        {
            "type": "extraction",
            "description": "Extract IP addresses",
            "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "field_name": "ip_address",
            "expected_spl": "rex field=_raw \"(?<ip_address>\\b(?:\\d{1,3}\\.){3}\\d{1,3}\\b)\""
        },
        
        # Filtering patterns
        {
            "type": "filtering",
            "description": "Filter error messages",
            "pattern": r"(?i)error|fail|exception",
            "expected_spl": "regex _raw=\"(?i)error|fail|exception\""
        },
        {
            "type": "filtering",
            "description": "Filter by HTTP status codes",
            "pattern": r"\b[4-5]\d{2}\b",
            "expected_spl": "regex _raw=\"\\b[4-5]\\d{2}\\b\""
        },
        
        # Replacement patterns
        {
            "type": "replacement",
            "description": "Mask credit card numbers",
            "source_field": "message",
            "find_pattern": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
            "replace_text": "****-****-****-****",
            "target_field": "masked_message",
            "expected_spl": "eval masked_message=replace(message, \"\\b\\d{4}[-\\s]?\\d{4}[-\\s]?\\d{4}[-\\s]?\\d{4}\\b\", \"****-****-****-****\")"
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTest Case {i+1}: {test_case['type'].upper()}")
        print(f"Description: {test_case['description']}")
        print("-" * 40)
        
        if test_case["type"] == "extraction":
            generated = generate_rex_spl(test_case["field_name"], test_case["pattern"])
        elif test_case["type"] == "filtering":
            generated = generate_regex_spl(test_case["pattern"])
        elif test_case["type"] == "replacement":
            generated = generate_replace_spl(
                test_case["source_field"],
                test_case["find_pattern"],
                test_case["replace_text"],
                test_case["target_field"]
            )
        
        expected = test_case["expected_spl"]
        print(f"Generated: {generated}")
        print(f"Expected:  {expected}")
        print(f"Match: {'✓' if expected in generated else '✗'}")


def test_pattern_complexity_analysis():
    """Test pattern complexity analysis"""
    print("\n" + "=" * 60)
    print("TESTING PATTERN COMPLEXITY ANALYSIS")
    print("=" * 60)
    
    def analyze_pattern_complexity(pattern: str) -> Dict[str, Any]:
        """Analyze regex pattern complexity"""
        complexity_score = 0
        features = []
        
        # Basic patterns
        if re.search(r'[\.\*\+\?\[\]\\]', pattern):
            complexity_score += 1
            features.append("basic_metacharacters")
        
        # Character classes
        if re.search(r'\[.*?\]', pattern):
            complexity_score += 1
            features.append("character_classes")
        
        # Quantifiers
        if re.search(r'[\*\+\?]\??|\{.*?\}', pattern):
            complexity_score += 1
            features.append("quantifiers")
        
        # Groups
        if re.search(r'\(.*?\)', pattern):
            complexity_score += 2
            features.append("groups")
        
        # Lookaheads/lookbehinds
        if re.search(r'\(\?[=!<]', pattern):
            complexity_score += 3
            features.append("lookarounds")
        
        # Backreferences
        if re.search(r'\\[1-9]', pattern):
            complexity_score += 3
            features.append("backreferences")
        
        # Word boundaries
        if '\\b' in pattern:
            complexity_score += 1
            features.append("word_boundaries")
        
        # Case insensitive flag
        if '(?i)' in pattern:
            complexity_score += 1
            features.append("case_insensitive")
        
        # Determine complexity level
        if complexity_score <= 2:
            complexity_level = "simple"
        elif complexity_score <= 5:
            complexity_level = "intermediate"
        elif complexity_score <= 8:
            complexity_level = "advanced"
        else:
            complexity_level = "expert"
        
        return {
            "complexity_score": complexity_score,
            "complexity_level": complexity_level,
            "features": features,
            "pattern_length": len(pattern),
            "performance_warning": complexity_score > 6 or len(pattern) > 100
        }
    
    test_patterns = [
        # Simple patterns
        r"test",
        r"\d+",
        r"[a-z]+",
        
        # Intermediate patterns
        r"\b\w+@\w+\.\w+\b",
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",
        r"(?i)error|warning",
        
        # Advanced patterns
        r"(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})",
        r"\b(?:[A-Z0-9+/]{4})*(?:[A-Z0-9+/]{2}==|[A-Z0-9+/]{3}=)?\b",
        
        # Expert patterns
        r"(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}",
        r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    ]
    
    for pattern in test_patterns:
        print(f"\nPattern: '{pattern}'")
        print("-" * 50)
        
        analysis = analyze_pattern_complexity(pattern)
        
        print(f"Complexity Level: {analysis['complexity_level']}")
        print(f"Complexity Score: {analysis['complexity_score']}")
        print(f"Pattern Length: {analysis['pattern_length']}")
        print(f"Features: {', '.join(analysis['features'])}")
        
        if analysis['performance_warning']:
            print("⚠️  Performance Warning: Complex pattern may impact performance")
        else:
            print("✓ Performance: Pattern should perform well")


def test_pattern_validation():
    """Test pattern validation"""
    print("\n" + "=" * 60)
    print("TESTING PATTERN VALIDATION")
    print("=" * 60)
    
    def validate_pattern(pattern: str) -> Dict[str, Any]:
        """Validate regex pattern"""
        validation = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        try:
            re.compile(pattern)
        except re.error as e:
            validation["valid"] = False
            validation["errors"].append(f"Invalid regex: {str(e)}")
            return validation
        
        # Check for common issues
        if pattern.count('(') != pattern.count(')'):
            validation["warnings"].append("Unmatched parentheses")
        
        if pattern.count('[') != pattern.count(']'):
            validation["warnings"].append("Unmatched brackets")
        
        if '.*.*' in pattern:
            validation["warnings"].append("Multiple .* may cause performance issues")
        
        if len(pattern) > 100:
            validation["suggestions"].append("Consider breaking down very long patterns")
        
        if not any(char in pattern for char in r'.*+?[]{}()'):
            validation["suggestions"].append("Pattern appears to be literal text - consider using simple string search")
        
        return validation
    
    test_patterns = [
        # Valid patterns
        r"\d+",
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        
        # Invalid patterns
        r"[unclosed",
        r"(unclosed group",
        r"invalid\k<name>",
        
        # Performance issues
        r".*.*.*test.*.*",
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}" * 5,  # Very long pattern
        
        # Literal patterns
        r"exactly this text",
        r"simple test"
    ]
    
    for pattern in test_patterns:
        print(f"\nPattern: '{pattern[:50]}{'...' if len(pattern) > 50 else ''}'")
        print("-" * 50)
        
        validation = validate_pattern(pattern)
        
        print(f"Valid: {'✓' if validation['valid'] else '✗'}")
        
        if validation["errors"]:
            print("Errors:")
            for error in validation["errors"]:
                print(f"  • {error}")
        
        if validation["warnings"]:
            print("Warnings:")
            for warning in validation["warnings"]:
                print(f"  • {warning}")
        
        if validation["suggestions"]:
            print("Suggestions:")
            for suggestion in validation["suggestions"]:
                print(f"  • {suggestion}")
        
        if not validation["errors"] and not validation["warnings"] and not validation["suggestions"]:
            print("No issues found")


def test_log_parsing_patterns():
    """Test log parsing patterns"""
    print("\n" + "=" * 60)
    print("TESTING LOG PARSING PATTERNS")
    print("=" * 60)
    
    log_patterns = {
        "apache_access": {
            "pattern": r'(\S+) \S+ \S+ \[([^\]]+)\] "([^"]*)" (\d+) (\d+|-)',
            "spl": "rex field=_raw \"(?<client_ip>\\S+) \\S+ \\S+ \\[(?<timestamp>[^\\]]+)\\] \\\"(?<request>[^\\\"]*)\\\" (?<status>\\d+) (?<bytes>\\d+|-)\"",
            "sample_log": '192.168.1.1 - - [01/Jan/2023:12:00:00 +0000] "GET /index.html HTTP/1.1" 200 1234',
            "expected_fields": ["client_ip", "timestamp", "request", "status", "bytes"]
        },
        "nginx_access": {
            "pattern": r'(\S+) - \S+ \[([^\]]+)\] "([^"]*)" (\d+) (\d+) "([^"]*)" "([^"]*)"',
            "spl": "rex field=_raw \"(?<remote_addr>\\S+) - \\S+ \\[(?<time_local>[^\\]]+)\\] \\\"(?<request>[^\\\"]*)\\\" (?<status>\\d+) (?<body_bytes_sent>\\d+) \\\"(?<http_referer>[^\\\"]*)\\\" \\\"(?<http_user_agent>[^\\\"]*)\\\"\"",
            "sample_log": '192.168.1.1 - - [01/Jan/2023:12:00:00 +0000] "GET /index.html HTTP/1.1" 200 1234 "http://example.com" "Mozilla/5.0"',
            "expected_fields": ["remote_addr", "time_local", "request", "status", "body_bytes_sent", "http_referer", "http_user_agent"]
        },
        "syslog": {
            "pattern": r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(\S+)\s+(\S+):\s*(.*)',
            "spl": "rex field=_raw \"(?<timestamp>\\w{3}\\s+\\d{1,2}\\s+\\d{2}:\\d{2}:\\d{2})\\s+(?<hostname>\\S+)\\s+(?<process>\\S+):\\s*(?<message>.*)\"",
            "sample_log": 'Jan 15 14:30:45 server01 sshd: Failed password for user from 192.168.1.100',
            "expected_fields": ["timestamp", "hostname", "process", "message"]
        }
    }
    
    for log_type, log_info in log_patterns.items():
        print(f"\nTesting {log_type.upper()} log parsing:")
        print(f"Sample: {log_info['sample_log']}")
        print("-" * 40)
        
        pattern = re.compile(log_info['pattern'])
        match = pattern.search(log_info['sample_log'])
        
        if match:
            print("✓ Pattern matched successfully")
            print(f"Groups found: {len(match.groups())}")
            print(f"Expected fields: {', '.join(log_info['expected_fields'])}")
            print(f"SPL: {log_info['spl']}")
            
            # Show extracted values
            for i, field in enumerate(log_info['expected_fields']):
                if i < len(match.groups()):
                    print(f"  {field}: {match.group(i + 1)}")
        else:
            print("✗ Pattern did not match")


if __name__ == "__main__":
    print("Testing Regex Pattern Matching System")
    print("=" * 60)
    
    # Run all tests
    test_regex_pattern_detection()
    test_common_regex_patterns()
    test_spl_generation()
    test_pattern_complexity_analysis()
    test_pattern_validation()
    test_log_parsing_patterns()
    
    print("\n" + "=" * 60)
    print("REGEX PATTERN MATCHING TESTING COMPLETE")
    print("=" * 60)