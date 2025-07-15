#!/usr/bin/env python3
"""
Test script for query performance analysis system in SPL optimization
"""

import json
from typing import Dict, List, Any


def test_query_complexity_analysis():
    """Test query complexity analysis"""
    print("=" * 60)
    print("TESTING QUERY COMPLEXITY ANALYSIS")
    print("=" * 60)
    
    # Test queries with different complexity levels
    test_queries = [
        # Simple queries
        {
            "name": "Simple search",
            "spl": "search index=main error",
            "expected_complexity": "excellent",
            "expected_factors": []
        },
        {
            "name": "Basic stats",
            "spl": "search index=main | stats count by host",
            "expected_complexity": "good",
            "expected_factors": ["stats operations"]
        },
        
        # Moderate complexity
        {
            "name": "Multiple commands",
            "spl": "search index=main error | rex field=message \\\"(?<error_type>\\\\w+)\\\" | stats count by error_type | sort -count | head 10",
            "expected_complexity": "moderate",
            "expected_factors": ["regex operations", "aggregation operations"]
        },
        {
            "name": "Time chart with filtering",
            "spl": "search index=web status>=400 | eval error_category=if(status<500, \"client\", \"server\") | timechart span=1h count by error_category",
            "expected_complexity": "moderate",
            "expected_factors": ["aggregation operations"]
        },
        
        # Complex queries
        {
            "name": "Join operation",
            "spl": "search index=main error | join host [search index=infrastructure | stats latest(cpu_usage) as cpu by host] | stats count by host, cpu",
            "expected_complexity": "poor",
            "expected_factors": ["join operations", "aggregation operations"]
        },
        {
            "name": "Multiple subsearches",
            "spl": "search index=main [search index=security failed | return 100 user] | stats count by action | append [search index=audit | stats count by action]",
            "expected_complexity": "poor",
            "expected_factors": ["subsearches", "aggregation operations"]
        },
        
        # Very complex queries
        {
            "name": "Heavy aggregation with joins",
            "spl": "search index=main | join type=outer host [search index=infrastructure | stats avg(cpu) as avg_cpu, avg(memory) as avg_mem by host] | join type=left user [search index=user_data | stats latest(department) as dept by user] | stats count, avg(avg_cpu), avg(avg_mem) by dept, host | sort -count",
            "expected_complexity": "critical",
            "expected_factors": ["high command count", "join operations", "aggregation operations"]
        }
    ]
    
    def analyze_query_complexity(spl_query: str) -> Dict[str, Any]:
        """Simplified complexity analysis for testing"""
        import re
        
        # Count different elements
        command_count = len(re.findall(r'\|\s*\w+', spl_query)) + 1
        join_count = len(re.findall(r'\|\s*join', spl_query, re.IGNORECASE))
        subsearch_count = len(re.findall(r'\[.*search.*\]', spl_query))
        regex_count = len(re.findall(r'rex|regex|replace', spl_query, re.IGNORECASE))
        aggregation_count = len(re.findall(r'stats|chart|timechart|eventstats', spl_query, re.IGNORECASE))
        field_extraction_count = len(re.findall(r'rex|extract|spath', spl_query, re.IGNORECASE))
        
        # Calculate complexity score
        complexity_score = (command_count * 3) + (join_count * 15) + (subsearch_count * 12) + (regex_count * 8) + (aggregation_count * 6) + (field_extraction_count * 4)
        
        # Determine complexity level
        if complexity_score <= 20:
            complexity_level = "excellent"
        elif complexity_score <= 40:
            complexity_level = "good"
        elif complexity_score <= 60:
            complexity_level = "moderate"
        elif complexity_score <= 80:
            complexity_level = "poor"
        else:
            complexity_level = "critical"
        
        # Identify complexity factors
        factors = []
        if command_count > 5:
            factors.append(f"high command count ({command_count})")
        if join_count > 0:
            factors.append(f"join operations ({join_count})")
        if subsearch_count > 0:
            factors.append(f"subsearches ({subsearch_count})")
        if regex_count > 0:
            factors.append(f"regex operations ({regex_count})")
        if aggregation_count > 0:
            factors.append(f"aggregation operations ({aggregation_count})")
        if field_extraction_count > 0:
            factors.append(f"field extraction operations ({field_extraction_count})")
        
        return {
            "complexity_score": complexity_score,
            "complexity_level": complexity_level,
            "command_count": command_count,
            "join_count": join_count,
            "subsearch_count": subsearch_count,
            "regex_count": regex_count,
            "aggregation_count": aggregation_count,
            "field_extraction_count": field_extraction_count,
            "factors": factors
        }
    
    for query in test_queries:
        print(f"\nQuery: {query['name']}")
        print(f"SPL: {query['spl']}")
        print("-" * 50)
        
        analysis = analyze_query_complexity(query['spl'])
        
        print(f"Complexity Score: {analysis['complexity_score']}")
        print(f"Complexity Level: {analysis['complexity_level']}")
        print(f"Command Count: {analysis['command_count']}")
        print(f"Join Count: {analysis['join_count']}")
        print(f"Subsearch Count: {analysis['subsearch_count']}")
        print(f"Regex Count: {analysis['regex_count']}")
        print(f"Aggregation Count: {analysis['aggregation_count']}")
        
        if analysis['factors']:
            print(f"Complexity Factors: {', '.join(analysis['factors'])}")
        else:
            print("Complexity Factors: None")
        
        # Check if matches expected
        level_match = analysis['complexity_level'] == query['expected_complexity']
        print(f"Expected Level: {query['expected_complexity']} | Match: {'✓' if level_match else '✗'}")


def test_performance_bottleneck_detection():
    """Test performance bottleneck detection"""
    print("\n" + "=" * 60)
    print("TESTING PERFORMANCE BOTTLENECK DETECTION")
    print("=" * 60)
    
    def detect_bottlenecks(spl_query: str) -> List[Dict[str, Any]]:
        """Simplified bottleneck detection for testing"""
        import re
        bottlenecks = []
        
        # Check for various bottleneck patterns
        patterns = {
            "missing_index": {
                "pattern": r'^search\s+(?!index=)',
                "type": "index_scanning",
                "severity": "critical",
                "description": "No index specified - full index scanning"
            },
            "broad_wildcards": {
                "pattern": r'index=\*|sourcetype=\*',
                "type": "disk_io",
                "severity": "high",
                "description": "Broad wildcard usage increases disk I/O"
            },
            "complex_regex": {
                "pattern": r'rex.*".*\.\*.*\.\*"',
                "type": "cpu_intensive",
                "severity": "medium",
                "description": "Complex regex patterns are CPU intensive"
            },
            "multiple_joins": {
                "pattern": r'join.*join',
                "type": "memory_usage",
                "severity": "high",
                "description": "Multiple joins consume significant memory"
            },
            "heavy_sort": {
                "pattern": r'sort.*\d{4,}',
                "type": "memory_usage",
                "severity": "medium",
                "description": "Sorting large datasets requires significant memory"
            },
            "inefficient_aggregation": {
                "pattern": r'stats.*by.*,.*,.*,',
                "type": "aggregation",
                "severity": "medium",
                "description": "High cardinality aggregation impacts performance"
            }
        }
        
        for pattern_name, pattern_info in patterns.items():
            if re.search(pattern_info["pattern"], spl_query, re.IGNORECASE):
                bottlenecks.append({
                    "name": pattern_name,
                    "type": pattern_info["type"],
                    "severity": pattern_info["severity"],
                    "description": pattern_info["description"]
                })
        
        return bottlenecks
    
    test_queries = [
        {
            "name": "Optimized query",
            "spl": "search index=main earliest=-1h error | stats count by host | head 10",
            "expected_bottlenecks": 0
        },
        {
            "name": "Missing index",
            "spl": "search error | stats count",
            "expected_bottlenecks": ["missing_index"]
        },
        {
            "name": "Broad wildcards",
            "spl": "search index=* sourcetype=* | stats count",
            "expected_bottlenecks": ["broad_wildcards"]
        },
        {
            "name": "Complex regex",
            "spl": "search index=main | rex field=message \\\"(?<data>.*error.*exception.*)\\\"",
            "expected_bottlenecks": ["complex_regex"]
        },
        {
            "name": "Multiple joins",
            "spl": "search index=main | join host [search index=infra] | join user [search index=auth]",
            "expected_bottlenecks": ["multiple_joins"]
        },
        {
            "name": "Multiple issues",
            "spl": "search * | rex field=message \\\"(?<data>.*error.*warning.*debug.*)\\\" | join host [search index=*] | stats count by host, user, action, status",
            "expected_bottlenecks": ["missing_index", "broad_wildcards", "complex_regex", "inefficient_aggregation"]
        }
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query['name']}")
        print(f"SPL: {query['spl']}")
        print("-" * 50)
        
        bottlenecks = detect_bottlenecks(query['spl'])
        
        print(f"Detected Bottlenecks: {len(bottlenecks)}")
        
        if bottlenecks:
            for bottleneck in bottlenecks:
                print(f"  - {bottleneck['name']} ({bottleneck['type']}, {bottleneck['severity']})")
                print(f"    Description: {bottleneck['description']}")
        else:
            print("  No bottlenecks detected")
        
        # Check expected count
        expected_count = query['expected_bottlenecks'] if isinstance(query['expected_bottlenecks'], int) else len(query['expected_bottlenecks'])
        count_match = len(bottlenecks) == expected_count
        print(f"Expected Count: {expected_count} | Actual: {len(bottlenecks)} | Match: {'✓' if count_match else '✗'}")


def test_optimization_suggestions():
    """Test optimization suggestion generation"""
    print("\n" + "=" * 60)
    print("TESTING OPTIMIZATION SUGGESTIONS")
    print("=" * 60)
    
    def generate_optimization_suggestions(spl_query: str) -> List[Dict[str, Any]]:
        """Generate optimization suggestions"""
        import re
        suggestions = []
        
        # Index specification optimization
        if not re.search(r'index=\w+', spl_query):
            suggestions.append({
                "type": "index_selection",
                "priority": 10,
                "impact": "high",
                "description": "Add specific index specification to limit search scope",
                "before": spl_query.split('|')[0].strip(),
                "after": f"search index=main {spl_query.split('|')[0].strip().replace('search ', '')}",
                "expected_improvement": "50-80% faster execution"
            })
        
        # Time range optimization
        if not re.search(r'earliest=|latest=', spl_query):
            suggestions.append({
                "type": "time_range",
                "priority": 9,
                "impact": "high",
                "description": "Add specific time range to reduce data volume",
                "before": spl_query.split('|')[0].strip(),
                "after": f"{spl_query.split('|')[0].strip()} earliest=-24h@h",
                "expected_improvement": "30-60% faster execution"
            })
        
        # Sort + head optimization
        if re.search(r'sort.*\|\s*head', spl_query, re.IGNORECASE):
            suggestions.append({
                "type": "command_order",
                "priority": 7,
                "impact": "medium",
                "description": "Replace sort | head with top command for better performance",
                "before": "sort field | head 10",
                "after": "top 10 field",
                "expected_improvement": "20-40% faster execution"
            })
        
        # Join optimization
        if re.search(r'\|\s*join', spl_query, re.IGNORECASE):
            suggestions.append({
                "type": "join_optimization",
                "priority": 8,
                "impact": "high",
                "description": "Consider using lookup tables instead of joins for static data",
                "before": "join field [subsearch]",
                "after": "lookup lookup_table field OUTPUT other_fields",
                "expected_improvement": "40-70% faster execution"
            })
        
        # Aggregation optimization
        aggregation_count = len(re.findall(r'stats|chart|timechart', spl_query, re.IGNORECASE))
        if aggregation_count > 2:
            suggestions.append({
                "type": "aggregation",
                "priority": 6,
                "impact": "medium",
                "description": "Combine multiple aggregation operations",
                "before": "| stats count | stats sum(count)",
                "after": "| stats count sum(count)",
                "expected_improvement": "15-30% faster execution"
            })
        
        # Sort suggestions by priority
        suggestions.sort(key=lambda x: x["priority"], reverse=True)
        return suggestions
    
    test_queries = [
        {
            "name": "Well optimized query",
            "spl": "search index=main earliest=-1h error | stats count by host | head 10",
            "expected_suggestions": 0
        },
        {
            "name": "Missing index and time",
            "spl": "search error | stats count by host",
            "expected_suggestions": ["index_selection", "time_range"]
        },
        {
            "name": "Inefficient sort",
            "spl": "search index=main error | stats count by host | sort -count | head 10",
            "expected_suggestions": ["time_range", "command_order"]
        },
        {
            "name": "Join operation",
            "spl": "search index=main | join host [search index=infra] | stats count",
            "expected_suggestions": ["time_range", "join_optimization"]
        },
        {
            "name": "Multiple issues",
            "spl": "search * | join host [search other] | stats count | stats sum(count) | sort -sum | head 5",
            "expected_suggestions": ["index_selection", "time_range", "join_optimization", "aggregation", "command_order"]
        }
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query['name']}")
        print(f"SPL: {query['spl']}")
        print("-" * 50)
        
        suggestions = generate_optimization_suggestions(query['spl'])
        
        print(f"Generated Suggestions: {len(suggestions)}")
        
        if suggestions:
            for i, suggestion in enumerate(suggestions[:5], 1):  # Show top 5
                print(f"\n  {i}. {suggestion['type']} (Priority: {suggestion['priority']}, Impact: {suggestion['impact']})")
                print(f"     Description: {suggestion['description']}")
                print(f"     Before: {suggestion['before']}")
                print(f"     After: {suggestion['after']}")
                print(f"     Expected Improvement: {suggestion['expected_improvement']}")
        else:
            print("  No optimization suggestions generated")
        
        # Check expected count
        expected_count = query['expected_suggestions'] if isinstance(query['expected_suggestions'], int) else len(query['expected_suggestions'])
        count_match = len(suggestions) == expected_count
        print(f"\nExpected Count: {expected_count} | Actual: {len(suggestions)} | Match: {'✓' if count_match else '✗'}")


def test_resource_estimation():
    """Test resource usage estimation"""
    print("\n" + "=" * 60)
    print("TESTING RESOURCE USAGE ESTIMATION")
    print("=" * 60)
    
    def estimate_resource_usage(spl_query: str) -> Dict[str, Any]:
        """Estimate resource usage for query"""
        import re
        
        # Calculate complexity factors
        join_count = len(re.findall(r'\|\s*join', spl_query, re.IGNORECASE))
        subsearch_count = len(re.findall(r'\[.*search.*\]', spl_query))
        regex_count = len(re.findall(r'rex|regex|replace', spl_query, re.IGNORECASE))
        aggregation_count = len(re.findall(r'stats|chart|timechart', spl_query, re.IGNORECASE))
        has_index = bool(re.search(r'index=\w+', spl_query))
        has_time_range = bool(re.search(r'earliest=|latest=', spl_query))
        
        # CPU usage estimation
        cpu_usage = "low"
        if regex_count > 2:
            cpu_usage = "high"
        elif regex_count > 0 or aggregation_count > 2:
            cpu_usage = "medium"
        
        # Memory usage estimation
        memory_usage = "low"
        if join_count > 1 or aggregation_count > 3:
            memory_usage = "high"
        elif join_count > 0 or aggregation_count > 1:
            memory_usage = "medium"
        
        # Disk I/O estimation
        disk_io = "low" if has_index else "high"
        if subsearch_count > 0:
            disk_io = "high"
        
        # Network I/O estimation
        network_io = "low"
        if re.search(r'lookup.*external|dbconnect', spl_query, re.IGNORECASE):
            network_io = "high"
        elif re.search(r'lookup', spl_query, re.IGNORECASE):
            network_io = "medium"
        
        # Execution time estimation
        complexity_factor = (join_count * 3 + subsearch_count * 2 + regex_count + aggregation_count * 2) / 10
        base_time = 5  # seconds
        execution_time = base_time * (1 + complexity_factor)
        
        if execution_time < 10:
            time_estimate = f"{execution_time:.1f} seconds"
        elif execution_time < 300:
            time_estimate = f"{execution_time/60:.1f} minutes"
        else:
            time_estimate = f"{execution_time/3600:.1f} hours"
        
        # Data volume estimation
        if has_index and has_time_range:
            data_volume = "Small to Medium (optimized)"
        elif has_index or has_time_range:
            data_volume = "Medium to Large"
        else:
            data_volume = "Very Large (unoptimized)"
        
        # Concurrent capacity
        if complexity_factor < 0.3:
            concurrent_capacity = 50
        elif complexity_factor < 0.6:
            concurrent_capacity = 20
        else:
            concurrent_capacity = 5
        
        return {
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "disk_io": disk_io,
            "network_io": network_io,
            "estimated_execution_time": time_estimate,
            "estimated_data_volume": data_volume,
            "concurrent_capacity": concurrent_capacity
        }
    
    test_queries = [
        {
            "name": "Lightweight query",
            "spl": "search index=main earliest=-1h error | head 100",
            "expected_resources": {"cpu": "low", "memory": "low", "disk_io": "low"}
        },
        {
            "name": "Medium complexity",
            "spl": "search index=main earliest=-4h | rex field=message \\\"(?<error_type>\\\\w+)\\\" | stats count by error_type",
            "expected_resources": {"cpu": "medium", "memory": "medium", "disk_io": "low"}
        },
        {
            "name": "Heavy query with joins",
            "spl": "search index=main | join host [search index=infra] | join user [search index=auth] | stats count by host, user",
            "expected_resources": {"cpu": "low", "memory": "high", "disk_io": "high"}
        },
        {
            "name": "Regex intensive",
            "spl": "search index=main | rex field=msg \\\"(?<data>.*)\\\" | rex field=data \\\"(?<error>.*)\\\" | rex field=error \\\"(?<type>.*)\\\"",
            "expected_resources": {"cpu": "high", "memory": "low", "disk_io": "low"}
        },
        {
            "name": "Unoptimized broad search",
            "spl": "search * | stats count by host, user, action, status, method",
            "expected_resources": {"cpu": "low", "memory": "medium", "disk_io": "high"}
        }
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query['name']}")
        print(f"SPL: {query['spl']}")
        print("-" * 50)
        
        resources = estimate_resource_usage(query['spl'])
        
        print(f"CPU Usage: {resources['cpu_usage']}")
        print(f"Memory Usage: {resources['memory_usage']}")
        print(f"Disk I/O: {resources['disk_io']}")
        print(f"Network I/O: {resources['network_io']}")
        print(f"Estimated Execution Time: {resources['estimated_execution_time']}")
        print(f"Estimated Data Volume: {resources['estimated_data_volume']}")
        print(f"Concurrent Capacity: {resources['concurrent_capacity']} queries")
        
        # Check expected resource levels
        expected = query['expected_resources']
        cpu_match = resources['cpu_usage'] == expected.get('cpu', 'unknown')
        memory_match = resources['memory_usage'] == expected.get('memory', 'unknown')
        disk_match = resources['disk_io'] == expected.get('disk_io', 'unknown')
        
        print(f"CPU Match: {'✓' if cpu_match else '✗'} | Memory Match: {'✓' if memory_match else '✗'} | Disk I/O Match: {'✓' if disk_match else '✗'}")


def test_index_optimization_suggestions():
    """Test index optimization suggestions"""
    print("\n" + "=" * 60)
    print("TESTING INDEX OPTIMIZATION SUGGESTIONS")
    print("=" * 60)
    
    def suggest_index_optimization(natural_query: str) -> Dict[str, Any]:
        """Suggest optimal indexes based on natural language query"""
        query_lower = natural_query.lower()
        
        index_patterns = {
            "security_logs": {
                "patterns": ["failed login", "authentication", "security", "auth", "login"],
                "recommended_indexes": ["security", "auth", "windows", "linux"],
                "time_range_suggestion": "last 24 hours for real-time, last 7 days for analysis"
            },
            "web_logs": {
                "patterns": ["http", "web", "apache", "nginx", "status", "response"],
                "recommended_indexes": ["web", "apache", "nginx", "access"],
                "time_range_suggestion": "last 1 hour for monitoring, last 24 hours for analysis"
            },
            "application_logs": {
                "patterns": ["application", "app", "error", "exception", "debug"],
                "recommended_indexes": ["application", "app", "java", "python"],
                "time_range_suggestion": "last 4 hours for troubleshooting"
            },
            "network_logs": {
                "patterns": ["network", "firewall", "router", "switch", "bandwidth"],
                "recommended_indexes": ["network", "firewall", "cisco", "juniper"],
                "time_range_suggestion": "last 15 minutes for real-time monitoring"
            },
            "system_logs": {
                "patterns": ["system", "cpu", "memory", "disk", "performance"],
                "recommended_indexes": ["system", "os", "perfmon", "vmware"],
                "time_range_suggestion": "last 1 hour for monitoring, last 24 hours for capacity planning"
            }
        }
        
        for category, info in index_patterns.items():
            for pattern in info["patterns"]:
                if pattern in query_lower:
                    return {
                        "category": category,
                        "recommended_indexes": info["recommended_indexes"],
                        "time_range_suggestion": info["time_range_suggestion"],
                        "confidence": 0.8,
                        "reasoning": f"Query contains '{pattern}' indicating {category} analysis"
                    }
        
        # Default suggestion
        return {
            "category": "general",
            "recommended_indexes": ["main", "_internal"],
            "time_range_suggestion": "last 24 hours",
            "confidence": 0.3,
            "reasoning": "Generic recommendation for unspecified query type"
        }
    
    test_queries = [
        {
            "natural_query": "Find failed login attempts and authentication errors",
            "expected_category": "security_logs",
            "expected_indexes": ["security", "auth", "windows", "linux"]
        },
        {
            "natural_query": "Show HTTP response codes and web server errors",
            "expected_category": "web_logs", 
            "expected_indexes": ["web", "apache", "nginx", "access"]
        },
        {
            "natural_query": "Application exceptions and debug information",
            "expected_category": "application_logs",
            "expected_indexes": ["application", "app", "java", "python"]
        },
        {
            "natural_query": "Network bandwidth usage and firewall logs",
            "expected_category": "network_logs",
            "expected_indexes": ["network", "firewall", "cisco", "juniper"]
        },
        {
            "natural_query": "System performance metrics and CPU usage",
            "expected_category": "system_logs",
            "expected_indexes": ["system", "os", "perfmon", "vmware"]
        },
        {
            "natural_query": "Generic data analysis request",
            "expected_category": "general",
            "expected_indexes": ["main", "_internal"]
        }
    ]
    
    for query_info in test_queries:
        print(f"\nNatural Query: '{query_info['natural_query']}'")
        print("-" * 50)
        
        suggestion = suggest_index_optimization(query_info['natural_query'])
        
        print(f"Detected Category: {suggestion['category']}")
        print(f"Recommended Indexes: {', '.join(suggestion['recommended_indexes'])}")
        print(f"Time Range Suggestion: {suggestion['time_range_suggestion']}")
        print(f"Confidence: {suggestion['confidence']:.1f}")
        print(f"Reasoning: {suggestion['reasoning']}")
        
        # Check matches
        category_match = suggestion['category'] == query_info['expected_category']
        indexes_match = set(suggestion['recommended_indexes']) == set(query_info['expected_indexes'])
        
        print(f"Category Match: {'✓' if category_match else '✗'} | Indexes Match: {'✓' if indexes_match else '✗'}")


def test_overall_performance_scoring():
    """Test overall performance scoring"""
    print("\n" + "=" * 60)
    print("TESTING OVERALL PERFORMANCE SCORING")
    print("=" * 60)
    
    def calculate_performance_score(spl_query: str) -> Dict[str, Any]:
        """Calculate overall performance score"""
        import re
        
        # Start with base score
        score = 100.0
        
        # Calculate complexity factors
        command_count = len(re.findall(r'\|\s*\w+', spl_query)) + 1
        join_count = len(re.findall(r'\|\s*join', spl_query, re.IGNORECASE))
        subsearch_count = len(re.findall(r'\[.*search.*\]', spl_query))
        regex_count = len(re.findall(r'rex|regex|replace', spl_query, re.IGNORECASE))
        aggregation_count = len(re.findall(r'stats|chart|timechart', spl_query, re.IGNORECASE))
        
        # Penalize based on complexity
        complexity_score = (command_count * 3) + (join_count * 15) + (subsearch_count * 12) + (regex_count * 8) + (aggregation_count * 6)
        score -= min(complexity_score, 50)
        
        # Check optimizations
        has_index = bool(re.search(r'index=\w+', spl_query))
        has_time_range = bool(re.search(r'earliest=|latest=', spl_query))
        
        # Reward optimizations
        if has_index:
            score += 10
        if has_time_range:
            score += 5
        
        # Penalize anti-patterns
        if not has_index:
            score -= 30  # Major penalty for missing index
        if re.search(r'index=\*', spl_query):
            score -= 20  # Penalty for wildcard index
        if re.search(r'sort.*\|\s*head', spl_query, re.IGNORECASE):
            score -= 10  # Penalty for inefficient sort|head
        
        score = max(0.0, min(100.0, score))
        
        # Determine performance level
        if score >= 80:
            level = "excellent"
        elif score >= 65:
            level = "good"
        elif score >= 45:
            level = "moderate"
        elif score >= 25:
            level = "poor"
        else:
            level = "critical"
        
        return {
            "score": score,
            "level": level,
            "has_index": has_index,
            "has_time_range": has_time_range,
            "complexity_score": complexity_score
        }
    
    test_queries = [
        {
            "name": "Excellent performance",
            "spl": "search index=main earliest=-1h error | stats count by host | head 10",
            "expected_level": "excellent",
            "expected_score_range": (80, 100)
        },
        {
            "name": "Good performance",
            "spl": "search index=main error | rex field=message \\\"(?<type>\\\\w+)\\\" | stats count by type",
            "expected_level": "good",
            "expected_score_range": (65, 80)
        },
        {
            "name": "Moderate performance",
            "spl": "search index=main | stats count by host | sort -count | head 10",
            "expected_level": "moderate",
            "expected_score_range": (45, 65)
        },
        {
            "name": "Poor performance",
            "spl": "search * | join host [search other] | stats count by host",
            "expected_level": "poor",
            "expected_score_range": (25, 45)
        },
        {
            "name": "Critical performance",
            "spl": "search * | join host [search index=*] | join user [search *] | sort field | head 5",
            "expected_level": "critical",
            "expected_score_range": (0, 25)
        }
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query['name']}")
        print(f"SPL: {query['spl']}")
        print("-" * 50)
        
        result = calculate_performance_score(query['spl'])
        
        print(f"Performance Score: {result['score']:.1f}")
        print(f"Performance Level: {result['level']}")
        print(f"Has Index: {'✓' if result['has_index'] else '✗'}")
        print(f"Has Time Range: {'✓' if result['has_time_range'] else '✗'}")
        print(f"Complexity Score: {result['complexity_score']}")
        
        # Check expectations
        level_match = result['level'] == query['expected_level']
        score_in_range = query['expected_score_range'][0] <= result['score'] <= query['expected_score_range'][1]
        
        print(f"Expected Level: {query['expected_level']} | Match: {'✓' if level_match else '✗'}")
        print(f"Expected Score Range: {query['expected_score_range']} | In Range: {'✓' if score_in_range else '✗'}")


if __name__ == "__main__":
    print("Testing Query Performance Analysis System")
    print("=" * 60)
    
    # Run all tests
    test_query_complexity_analysis()
    test_performance_bottleneck_detection()
    test_optimization_suggestions()
    test_resource_estimation()
    test_index_optimization_suggestions()
    test_overall_performance_scoring()
    
    print("\n" + "=" * 60)
    print("QUERY PERFORMANCE ANALYSIS TESTING COMPLETE")
    print("=" * 60)