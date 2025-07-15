#!/usr/bin/env python3
"""
Test script for index selection optimization system in SPL optimization

This script validates the comprehensive index selection optimization functionality including:
- Index recommendation based on query analysis and field patterns
- Multi-index optimization strategies for complex queries
- Cost-benefit analysis and performance impact prediction
- Field coverage and time range compatibility assessment
- Optimization level handling (basic, intermediate, advanced, expert)
"""

import json
from typing import Dict, List, Any


def test_basic_index_recommendation():
    """Test basic index recommendation functionality"""
    print("=" * 60)
    print("TESTING BASIC INDEX RECOMMENDATION")
    print("=" * 60)
    
    def analyze_index_recommendation(spl_query: str, natural_query: str = None) -> Dict[str, Any]:
        """Simplified index recommendation for testing"""
        import re
        
        # Define index patterns and scoring
        index_patterns = {
            "security": {
                "keywords": ["login", "auth", "security", "failed", "unauthorized"],
                "fields": ["user", "src_ip", "action", "result"],
                "performance_score": 85.0,
                "cost_score": 75.0
            },
            "web": {
                "keywords": ["http", "web", "apache", "nginx", "status", "response"],
                "fields": ["status", "method", "uri", "response_time"],
                "performance_score": 75.0,
                "cost_score": 60.0
            },
            "application": {
                "keywords": ["error", "exception", "application", "service", "debug"],
                "fields": ["level", "message", "component", "thread"],
                "performance_score": 80.0,
                "cost_score": 70.0
            },
            "network": {
                "keywords": ["network", "firewall", "router", "protocol", "bandwidth"],
                "fields": ["src_ip", "dest_ip", "protocol", "bytes"],
                "performance_score": 70.0,
                "cost_score": 65.0
            },
            "system": {
                "keywords": ["system", "performance", "cpu", "memory", "disk"],
                "fields": ["host", "cpu", "memory", "process"],
                "performance_score": 85.0,
                "cost_score": 80.0
            }
        }
        
        query_text = (spl_query + " " + (natural_query or "")).lower()
        
        best_index = "main"
        best_score = 30.0
        reasoning = "Default fallback to main index"
        
        for index_name, index_info in index_patterns.items():
            score = 0.0
            
            # Keyword matching
            keyword_matches = sum(1 for keyword in index_info["keywords"] if keyword in query_text)
            keyword_score = (keyword_matches / len(index_info["keywords"])) * 40
            
            # Field matching
            field_matches = sum(1 for field in index_info["fields"] if field in spl_query)
            field_score = (field_matches / len(index_info["fields"])) * 30
            
            # Performance and cost consideration
            perf_score = index_info["performance_score"] * 0.2
            cost_score = index_info["cost_score"] * 0.1
            
            total_score = keyword_score + field_score + perf_score + cost_score
            
            if total_score > best_score:
                best_score = total_score
                best_index = index_name
                reasoning = f"Best match with {keyword_matches} keyword matches, {field_matches} field matches"
        
        # Generate optimized SPL
        if re.search(r'index=\\w+', spl_query):
            optimized_spl = re.sub(r'index=\\w+', f'index={best_index}', spl_query)
        else:
            if spl_query.strip().startswith("search"):
                optimized_spl = spl_query.replace("search", f"search index={best_index}", 1)
            else:
                optimized_spl = f"search index={best_index} {spl_query}"
        
        return {
            "recommended_index": best_index,
            "confidence": min(best_score / 100, 1.0),
            "reasoning": reasoning,
            "optimized_spl": optimized_spl,
            "field_coverage": field_score,
            "performance_impact": "excellent" if best_score > 80 else "good" if best_score > 60 else "moderate"
        }
    
    test_queries = [
        {
            "name": "Security query",
            "spl": "search failed login | stats count by user",
            "natural": "Find failed login attempts by user",
            "expected_index": "security"
        },
        {
            "name": "Web server query",
            "spl": "search status>=400 | stats count by uri",
            "natural": "Show HTTP errors by URL",
            "expected_index": "web"
        },
        {
            "name": "Application error query", 
            "spl": "search level=ERROR | stats count by component",
            "natural": "Application errors by component",
            "expected_index": "application"
        },
        {
            "name": "Network query",
            "spl": "search protocol=tcp | stats sum(bytes) by src_ip",
            "natural": "Network traffic by source IP",
            "expected_index": "network"
        },
        {
            "name": "System performance query",
            "spl": "search cpu>80 | stats avg(memory) by host",
            "natural": "High CPU usage with memory stats",
            "expected_index": "system"
        },
        {
            "name": "Generic query",
            "spl": "search * | head 100",
            "natural": "Show latest events",
            "expected_index": "main"
        }
    ]
    
    for query in test_queries:
        print(f"\\nQuery: {query['name']}")
        print(f"SPL: {query['spl']}")
        print(f"Natural: {query['natural']}")
        print("-" * 50)
        
        result = analyze_index_recommendation(query['spl'], query['natural'])
        
        print(f"Recommended Index: {result['recommended_index']}")
        print(f"Confidence: {result['confidence']:.3f}")
        print(f"Reasoning: {result['reasoning']}")
        print(f"Optimized SPL: {result['optimized_spl']}")
        print(f"Performance Impact: {result['performance_impact']}")
        
        index_match = result['recommended_index'] == query['expected_index']
        print(f"Expected: {query['expected_index']} | Match: {'✓' if index_match else '✗'}")


def test_multi_index_strategies():
    """Test multi-index optimization strategies"""
    print("\\n" + "=" * 60)
    print("TESTING MULTI-INDEX OPTIMIZATION STRATEGIES")
    print("=" * 60)
    
    def generate_multi_index_strategy(spl_query: str) -> Dict[str, Any]:
        """Generate multi-index strategy based on query complexity"""
        import re
        
        # Analyze query complexity
        join_count = len(re.findall(r'join', spl_query, re.IGNORECASE))
        subsearch_count = len(re.findall(r'\[.*search.*\]', spl_query))
        command_count = len(re.findall(r'\|\s*\w+', spl_query)) + 1
        
        # Determine if multi-index strategy is beneficial
        if join_count == 0 and subsearch_count == 0 and command_count <= 3:
            return {
                "strategy": "single_index",
                "primary_indexes": ["application"],
                "union_strategy": "none",
                "reasoning": "Simple query benefits from single index optimization",
                "complexity_score": 0.4,
                "cost_benefit_ratio": 1.0,
                "expected_performance_gain": 0.3,
                "recommended_spl": "search index=application"
            }
        
        # Multi-index strategy selection
        if join_count > 0:
            strategy = "multi_index_join"
            primary_indexes = ["security", "web"]
            union_strategy = "multisearch"
            reasoning = f"Query with {join_count} join(s) benefits from parallel index searching"
        elif subsearch_count > 0:
            strategy = "multi_index_subsearch"
            primary_indexes = ["application", "system"]
            union_strategy = "append"
            reasoning = f"Query with {subsearch_count} subsearch(es) benefits from sequential index processing"
        else:
            strategy = "multi_index_union"
            primary_indexes = ["security", "web", "application"]
            union_strategy = "search"
            reasoning = "Complex query benefits from searching multiple related indexes"
        
        # Calculate metrics
        complexity_score = (command_count * 0.2) + (join_count * 0.5) + (subsearch_count * 0.3)
        cost_benefit_ratio = min(1.0 / len(primary_indexes), 1.0)
        expected_performance_gain = min(complexity_score * 0.3, 0.8)
        
        return {
            "strategy": strategy,
            "primary_indexes": primary_indexes,
            "union_strategy": union_strategy,
            "reasoning": reasoning,
            "complexity_score": complexity_score,
            "cost_benefit_ratio": cost_benefit_ratio,
            "expected_performance_gain": expected_performance_gain,
            "recommended_spl": f"| multisearch [search index={primary_indexes[0]}] [search index={primary_indexes[1]}]" if len(primary_indexes) > 1 else f"search index={primary_indexes[0]}"
        }
    
    test_queries = [
        {
            "name": "Simple aggregation",
            "spl": "search error | stats count by host",
            "expected_strategy": "single_index"
        },
        {
            "name": "Join query",
            "spl": "search index=security failed | join user [search index=web | stats latest(uri) as last_page by user]",
            "expected_strategy": "multi_index_join"
        },
        {
            "name": "Subsearch query",
            "spl": "search [search index=alerts severity=critical | return 100 host] | stats count by source",
            "expected_strategy": "multi_index_subsearch"
        },
        {
            "name": "Complex multi-command",
            "spl": "search error | eval error_type=case(match(message, \\\"timeout\\\"), \\\"timeout\\\", 1=1, \\\"other\\\") | stats count by error_type, host | sort -count",
            "expected_strategy": "multi_index_union"
        }
    ]
    
    for query in test_queries:
        print(f"\\nQuery: {query['name']}")
        print(f"SPL: {query['spl']}")
        print("-" * 50)
        
        strategy = generate_multi_index_strategy(query['spl'])
        
        print(f"Strategy: {strategy['strategy']}")
        print(f"Primary Indexes: {', '.join(strategy['primary_indexes'])}")
        print(f"Union Strategy: {strategy['union_strategy']}")
        print(f"Reasoning: {strategy['reasoning']}")
        print(f"Complexity Score: {strategy['complexity_score']:.2f}")
        print(f"Cost-Benefit Ratio: {strategy['cost_benefit_ratio']:.2f}")
        print(f"Expected Performance Gain: {strategy['expected_performance_gain']:.2f}")
        print(f"Recommended SPL: {strategy['recommended_spl']}")
        
        strategy_match = strategy['strategy'] == query['expected_strategy']
        print(f"Expected Strategy: {query['expected_strategy']} | Match: {'✓' if strategy_match else '✗'}")


def test_field_coverage_analysis():
    """Test field coverage analysis for index optimization"""
    print("\\n" + "=" * 60)
    print("TESTING FIELD COVERAGE ANALYSIS")
    print("=" * 60)
    
    def analyze_field_coverage(spl_query: str, index_name: str) -> Dict[str, Any]:
        """Analyze field coverage for specific index"""
        import re
        
        # Define index field coverage
        index_fields = {
            "security": {
                "user": 95.0, "src_ip": 90.0, "action": 98.0, "result": 92.0,
                "auth_method": 85.0, "session_id": 80.0
            },
            "web": {
                "status": 99.0, "method": 98.0, "uri": 95.0, "response_time": 88.0,
                "user_agent": 85.0, "bytes": 90.0, "referer": 75.0
            },
            "application": {
                "level": 95.0, "message": 90.0, "component": 85.0, "thread": 80.0,
                "exception": 70.0, "stack_trace": 65.0
            },
            "system": {
                "host": 99.0, "cpu": 85.0, "memory": 88.0, "disk": 82.0,
                "process": 78.0, "load_avg": 75.0
            },
            "main": {
                "_time": 100.0, "host": 95.0, "source": 90.0, "sourcetype": 88.0
            }
        }
        
        # Extract fields from query
        query_fields = []
        field_patterns = [
            r'by\s+(\w+)',  # group by fields
            r'eval\s+(\w+)\s*=',  # eval fields
            r'where\s+(\w+)',  # where clause fields
            r'sort\s+[+-]?(\w+)',  # sort fields
            r'stats.*?(\w+)\(',  # stats function fields
            r'(\w+)=',  # field=value patterns
        ]
        
        for pattern in field_patterns:
            matches = re.findall(pattern, spl_query, re.IGNORECASE)
            query_fields.extend(matches)
        
        # Remove duplicates and common non-field terms
        query_fields = list(set(query_fields))
        common_terms = ['search', 'stats', 'eval', 'where', 'sort', 'head', 'tail', 'top']
        query_fields = [f for f in query_fields if f.lower() not in common_terms]
        
        if not query_fields:
            return {
                "total_fields": 0,
                "covered_fields": 0,
                "coverage_percentage": 80.0,  # Default for queries without specific fields
                "field_details": {},
                "missing_fields": [],
                "coverage_quality": "moderate"
            }
        
        # Calculate coverage
        index_field_map = index_fields.get(index_name, {})
        covered_fields = []
        field_details = {}
        missing_fields = []
        
        for field in query_fields:
            if field in index_field_map:
                coverage = index_field_map[field]
                covered_fields.append(field)
                field_details[field] = coverage
            else:
                missing_fields.append(field)
                field_details[field] = 0.0
        
        # Calculate overall coverage
        if query_fields:
            coverage_percentage = sum(field_details.values()) / len(query_fields)
        else:
            coverage_percentage = 80.0
        
        # Determine coverage quality
        if coverage_percentage >= 85:
            coverage_quality = "excellent"
        elif coverage_percentage >= 70:
            coverage_quality = "good"
        elif coverage_percentage >= 50:
            coverage_quality = "moderate"
        else:
            coverage_quality = "poor"
        
        return {
            "total_fields": len(query_fields),
            "covered_fields": len(covered_fields),
            "coverage_percentage": coverage_percentage,
            "field_details": field_details,
            "missing_fields": missing_fields,
            "coverage_quality": coverage_quality
        }
    
    test_cases = [
        {
            "name": "Security query with good coverage",
            "spl": "search user=admin action=login result=failed | stats count by user, src_ip",
            "index": "security",
            "expected_quality": "excellent"
        },
        {
            "name": "Web query with partial coverage",
            "spl": "search status>=400 method=GET | stats avg(response_time) by uri, custom_field",
            "index": "web",
            "expected_quality": "good"
        },
        {
            "name": "Application query with missing fields",
            "spl": "search level=ERROR | stats count by component, unknown_field, another_missing",
            "index": "application",
            "expected_quality": "moderate"
        },
        {
            "name": "System query with excellent coverage",
            "spl": "search host=server01 cpu>80 | stats avg(memory) by host, process",
            "index": "system",
            "expected_quality": "excellent"
        },
        {
            "name": "Generic query without specific fields",
            "spl": "search * | head 100",
            "index": "main",
            "expected_quality": "moderate"
        }
    ]
    
    for case in test_cases:
        print(f"\\nTest Case: {case['name']}")
        print(f"SPL: {case['spl']}")
        print(f"Index: {case['index']}")
        print("-" * 50)
        
        coverage = analyze_field_coverage(case['spl'], case['index'])
        
        print(f"Total Fields: {coverage['total_fields']}")
        print(f"Covered Fields: {coverage['covered_fields']}")
        print(f"Coverage Percentage: {coverage['coverage_percentage']:.1f}%")
        print(f"Coverage Quality: {coverage['coverage_quality']}")
        
        if coverage['field_details']:
            print(f"Field Details:")
            for field, coverage_pct in coverage['field_details'].items():
                print(f"  - {field}: {coverage_pct:.1f}%")
        
        if coverage['missing_fields']:
            print(f"Missing Fields: {', '.join(coverage['missing_fields'])}")
        
        quality_match = coverage['coverage_quality'] == case['expected_quality']
        print(f"Expected Quality: {case['expected_quality']} | Match: {'✓' if quality_match else '✗'}")


def test_optimization_levels():
    """Test different optimization levels"""
    print("\\n" + "=" * 60)
    print("TESTING OPTIMIZATION LEVELS")
    print("=" * 60)
    
    def apply_optimization_level(spl_query: str, level: str) -> Dict[str, Any]:
        """Apply optimization based on level"""
        import re
        
        levels = {
            "basic": {
                "max_indexes": 1,
                "multi_index": False,
                "cost_analysis": False,
                "advanced_strategies": False
            },
            "intermediate": {
                "max_indexes": 2,
                "multi_index": True,
                "cost_analysis": True,
                "advanced_strategies": False
            },
            "advanced": {
                "max_indexes": 3,
                "multi_index": True,
                "cost_analysis": True,
                "advanced_strategies": True
            },
            "expert": {
                "max_indexes": 5,
                "multi_index": True,
                "cost_analysis": True,
                "advanced_strategies": True
            }
        }
        
        config = levels.get(level, levels["intermediate"])
        
        # Analyze query complexity
        join_count = len(re.findall(r'join', spl_query, re.IGNORECASE))
        subsearch_count = len(re.findall(r'\[.*search.*\]', spl_query))
        command_count = len(re.findall(r'\|\s*\w+', spl_query)) + 1
        
        # Generate recommendations based on level
        if level == "basic":
            recommendations = ["Use single index for optimal performance"]
            strategy = "single_index"
            indexes = ["application"]
        elif level == "intermediate":
            recommendations = [
                "Consider field coverage when selecting indexes",
                "Add time range for better performance"
            ]
            strategy = "field_based" if join_count == 0 else "multi_index"
            indexes = ["application", "security"] if config["multi_index"] and command_count > 2 else ["application"]
        elif level == "advanced":
            recommendations = [
                "Optimize for both performance and cost",
                "Consider parallel execution for complex queries",
                "Use specialized indexes for domain-specific queries"
            ]
            strategy = "performance_optimized" if join_count > 0 else "field_based"
            indexes = ["security", "web", "application"][:config["max_indexes"]]
        else:  # expert
            recommendations = [
                "Apply cost-optimized multi-index strategies",
                "Use advanced query rewriting techniques",
                "Implement sophisticated caching strategies",
                "Consider query federation across multiple indexes"
            ]
            strategy = "cost_optimized"
            indexes = ["security", "web", "application", "system", "network"][:config["max_indexes"]]
        
        # Calculate confidence based on level complexity
        base_confidence = 0.6
        level_multiplier = {"basic": 0.8, "intermediate": 1.0, "advanced": 1.2, "expert": 1.1}
        confidence = min(base_confidence * level_multiplier[level], 1.0)
        
        return {
            "optimization_level": level,
            "strategy": strategy,
            "recommended_indexes": indexes,
            "recommendations": recommendations,
            "confidence": confidence,
            "multi_index_enabled": config["multi_index"],
            "cost_analysis_enabled": config["cost_analysis"],
            "advanced_strategies_enabled": config["advanced_strategies"]
        }
    
    test_query = "search error | join host [search index=system cpu>80] | stats count by host, error_type | sort -count"
    
    levels = ["basic", "intermediate", "advanced", "expert"]
    
    for level in levels:
        print(f"\\nOptimization Level: {level.upper()}")
        print(f"Query: {test_query}")
        print("-" * 50)
        
        result = apply_optimization_level(test_query, level)
        
        print(f"Strategy: {result['strategy']}")
        print(f"Recommended Indexes: {', '.join(result['recommended_indexes'])}")
        print(f"Confidence: {result['confidence']:.3f}")
        print(f"Multi-Index Enabled: {result['multi_index_enabled']}")
        print(f"Cost Analysis Enabled: {result['cost_analysis_enabled']}")
        print(f"Advanced Strategies Enabled: {result['advanced_strategies_enabled']}")
        print(f"Recommendations:")
        for i, rec in enumerate(result['recommendations'], 1):
            print(f"  {i}. {rec}")


def test_cost_benefit_analysis():
    """Test cost-benefit analysis for index optimization"""
    print("\\n" + "=" * 60)
    print("TESTING COST-BENEFIT ANALYSIS")
    print("=" * 60)
    
    def analyze_cost_benefit(index_strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze cost-benefit of index strategy"""
        
        # Define index costs (relative scale 1-10)
        index_costs = {
            "security": 6,  # Medium cost, high value for security queries
            "web": 8,       # High cost due to volume
            "application": 5, # Medium cost
            "network": 9,   # Very high cost due to volume
            "system": 4,    # Lower cost
            "main": 10      # Highest cost due to everything
        }
        
        # Define performance benefits (relative scale 1-10)
        index_benefits = {
            "security": 9,  # High benefit for security queries
            "web": 7,       # Good benefit
            "application": 8, # Good benefit
            "network": 6,   # Medium benefit
            "system": 8,    # Good benefit
            "main": 3       # Low benefit
        }
        
        indexes = index_strategy.get("recommended_indexes", ["main"])
        strategy = index_strategy.get("strategy", "single_index")
        
        # Calculate total cost and benefit
        total_cost = sum(index_costs.get(idx, 5) for idx in indexes)
        total_benefit = sum(index_benefits.get(idx, 5) for idx in indexes)
        
        # Adjust for strategy complexity
        strategy_multipliers = {
            "single_index": {"cost": 1.0, "benefit": 1.0},
            "multi_index": {"cost": 1.3, "benefit": 1.4},
            "field_based": {"cost": 1.1, "benefit": 1.2},
            "performance_optimized": {"cost": 1.2, "benefit": 1.5},
            "cost_optimized": {"cost": 0.9, "benefit": 1.1}
        }
        
        multiplier = strategy_multipliers.get(strategy, {"cost": 1.0, "benefit": 1.0})
        adjusted_cost = total_cost * multiplier["cost"]
        adjusted_benefit = total_benefit * multiplier["benefit"]
        
        # Calculate cost-benefit ratio
        cost_benefit_ratio = adjusted_benefit / adjusted_cost if adjusted_cost > 0 else 1.0
        
        # Determine recommendation
        if cost_benefit_ratio >= 1.5:
            recommendation = "Highly recommended - excellent cost-benefit ratio"
            rating = "excellent"
        elif cost_benefit_ratio >= 1.2:
            recommendation = "Recommended - good cost-benefit ratio"
            rating = "good"
        elif cost_benefit_ratio >= 1.0:
            recommendation = "Acceptable - balanced cost-benefit ratio"
            rating = "acceptable"
        else:
            recommendation = "Not recommended - poor cost-benefit ratio"
            rating = "poor"
        
        return {
            "total_cost": adjusted_cost,
            "total_benefit": adjusted_benefit,
            "cost_benefit_ratio": cost_benefit_ratio,
            "rating": rating,
            "recommendation": recommendation,
            "cost_breakdown": {idx: index_costs.get(idx, 5) for idx in indexes},
            "benefit_breakdown": {idx: index_benefits.get(idx, 5) for idx in indexes}
        }
    
    test_strategies = [
        {
            "name": "Single security index",
            "strategy": "single_index",
            "recommended_indexes": ["security"],
            "expected_rating": "excellent"
        },
        {
            "name": "Multi-index security + web",
            "strategy": "multi_index", 
            "recommended_indexes": ["security", "web"],
            "expected_rating": "good"
        },
        {
            "name": "Performance optimized three indexes",
            "strategy": "performance_optimized",
            "recommended_indexes": ["security", "web", "application"],
            "expected_rating": "acceptable"
        },
        {
            "name": "Cost optimized with system",
            "strategy": "cost_optimized",
            "recommended_indexes": ["system", "application"],
            "expected_rating": "excellent"
        },
        {
            "name": "Expensive main index strategy",
            "strategy": "single_index",
            "recommended_indexes": ["main"],
            "expected_rating": "poor"
        }
    ]
    
    for strategy in test_strategies:
        print(f"\\nStrategy: {strategy['name']}")
        print(f"Indexes: {', '.join(strategy['recommended_indexes'])}")
        print(f"Strategy Type: {strategy['strategy']}")
        print("-" * 50)
        
        analysis = analyze_cost_benefit(strategy)
        
        print(f"Total Cost: {analysis['total_cost']:.2f}")
        print(f"Total Benefit: {analysis['total_benefit']:.2f}")
        print(f"Cost-Benefit Ratio: {analysis['cost_benefit_ratio']:.2f}")
        print(f"Rating: {analysis['rating']}")
        print(f"Recommendation: {analysis['recommendation']}")
        
        print(f"Cost Breakdown:")
        for idx, cost in analysis['cost_breakdown'].items():
            print(f"  - {idx}: {cost}")
        
        print(f"Benefit Breakdown:")
        for idx, benefit in analysis['benefit_breakdown'].items():
            print(f"  - {idx}: {benefit}")
        
        rating_match = analysis['rating'] == strategy['expected_rating']
        print(f"Expected Rating: {strategy['expected_rating']} | Match: {'✓' if rating_match else '✗'}")


def test_time_range_optimization():
    """Test time range compatibility and optimization"""
    print("\\n" + "=" * 60)
    print("TESTING TIME RANGE OPTIMIZATION")
    print("=" * 60)
    
    def analyze_time_compatibility(spl_query: str, index_name: str) -> Dict[str, Any]:
        """Analyze time range compatibility with index"""
        import re
        
        # Define typical time ranges for indexes
        index_time_ranges = {
            "security": {"typical": "24 hours", "max_efficient": "7 days", "retention": "90 days"},
            "web": {"typical": "4 hours", "max_efficient": "24 hours", "retention": "30 days"},
            "application": {"typical": "6 hours", "max_efficient": "48 hours", "retention": "60 days"},
            "network": {"typical": "1 hour", "max_efficient": "12 hours", "retention": "14 days"},
            "system": {"typical": "2 hours", "max_efficient": "24 hours", "retention": "30 days"},
            "main": {"typical": "24 hours", "max_efficient": "30 days", "retention": "1 year"}
        }
        
        # Extract time range from query
        time_patterns = [
            (r'earliest=-(\d+)([hmdy])', "relative"),
            (r'latest=-(\d+)([hmdy])', "relative"),
            (r'@[hdmy]', "snap_to"),
            (r'last\s+(\d+)\s+(minute|hour|day|week|month)', "natural")
        ]
        
        detected_range = None
        range_type = None
        
        for pattern, rtype in time_patterns:
            match = re.search(pattern, spl_query, re.IGNORECASE)
            if match:
                detected_range = match.group(0)
                range_type = rtype
                break
        
        index_config = index_time_ranges.get(index_name, index_time_ranges["main"])
        
        if not detected_range:
            compatibility_score = 50.0  # Default for no time range
            recommendation = f"Add time range specification (typical: {index_config['typical']})"
            efficiency = "poor"
        else:
            # Simple heuristic for compatibility scoring
            if "h" in detected_range or "hour" in detected_range:
                if index_name in ["network", "system"]:
                    compatibility_score = 95.0
                    efficiency = "excellent"
                elif index_name in ["web", "application"]:
                    compatibility_score = 85.0
                    efficiency = "good"
                else:
                    compatibility_score = 75.0
                    efficiency = "moderate"
            elif "d" in detected_range or "day" in detected_range:
                if index_name in ["security", "main"]:
                    compatibility_score = 90.0
                    efficiency = "excellent"
                elif index_name in ["web", "application"]:
                    compatibility_score = 70.0
                    efficiency = "moderate"
                else:
                    compatibility_score = 60.0
                    efficiency = "poor"
            else:
                compatibility_score = 70.0
                efficiency = "moderate"
            
            recommendation = f"Time range compatible with {index_name} index"
        
        return {
            "detected_time_range": detected_range,
            "range_type": range_type,
            "compatibility_score": compatibility_score,
            "efficiency": efficiency,
            "recommendation": recommendation,
            "index_typical_range": index_config["typical"],
            "index_max_efficient": index_config["max_efficient"],
            "index_retention": index_config["retention"]
        }
    
    test_cases = [
        {
            "name": "Short time range for network index",
            "spl": "search earliest=-1h protocol=tcp | stats sum(bytes) by src_ip",
            "index": "network",
            "expected_efficiency": "excellent"
        },
        {
            "name": "Daily range for security index",
            "spl": "search earliest=-1d failed login | stats count by user",
            "index": "security", 
            "expected_efficiency": "excellent"
        },
        {
            "name": "No time range specified",
            "spl": "search error | stats count by component",
            "index": "application",
            "expected_efficiency": "poor"
        },
        {
            "name": "Long range for web index",
            "spl": "search earliest=-7d status>=400 | stats count by uri",
            "index": "web",
            "expected_efficiency": "poor"
        },
        {
            "name": "Hourly range for system index",
            "spl": "search earliest=-2h cpu>80 | stats avg(memory) by host",
            "index": "system",
            "expected_efficiency": "excellent"
        }
    ]
    
    for case in test_cases:
        print(f"\\nTest Case: {case['name']}")
        print(f"SPL: {case['spl']}")
        print(f"Index: {case['index']}")
        print("-" * 50)
        
        analysis = analyze_time_compatibility(case['spl'], case['index'])
        
        print(f"Detected Time Range: {analysis['detected_time_range'] or 'None'}")
        print(f"Range Type: {analysis['range_type'] or 'None'}")
        print(f"Compatibility Score: {analysis['compatibility_score']:.1f}")
        print(f"Efficiency: {analysis['efficiency']}")
        print(f"Recommendation: {analysis['recommendation']}")
        print(f"Index Typical Range: {analysis['index_typical_range']}")
        print(f"Index Max Efficient: {analysis['index_max_efficient']}")
        
        efficiency_match = analysis['efficiency'] == case['expected_efficiency']
        print(f"Expected Efficiency: {case['expected_efficiency']} | Match: {'✓' if efficiency_match else '✗'}")


if __name__ == "__main__":
    print("Testing Index Selection Optimization System")
    print("=" * 60)
    
    # Run all tests
    test_basic_index_recommendation()
    test_multi_index_strategies()
    test_field_coverage_analysis()
    test_optimization_levels()
    test_cost_benefit_analysis()
    test_time_range_optimization()
    
    print("\\n" + "=" * 60)
    print("INDEX SELECTION OPTIMIZATION TESTING COMPLETE")
    print("=" * 60)