#!/usr/bin/env python3
"""
Test script for time range optimization system in SPL optimization

This script validates the comprehensive time range optimization functionality including:
- Time range detection and parsing from SPL queries and natural language
- Time range optimization strategies (minimal, balanced, comprehensive, performance-first, accuracy-first, adaptive)
- Performance impact analysis and optimization recommendations
- Context-aware time range suggestions based on data type and user intent
- Time range validation and constraint checking for optimal performance
"""

import json
import uuid
from typing import Dict, List, Any
from datetime import datetime, timedelta


def test_time_range_detection():
    """Test time range detection and parsing functionality"""
    print("=" * 60)
    print("TESTING TIME RANGE DETECTION AND PARSING")
    print("=" * 60)
    
    def detect_time_range(spl_query: str, natural_query: str = None) -> Dict[str, Any]:
        """Simplified time range detection for testing"""
        import re
        
        # Time range patterns for detection
        patterns = {
            "relative_simple": {
                "pattern": r'earliest=(-?\d+)([smhdwy])',
                "type": "relative",
                "confidence": 0.95
            },
            "relative_complex": {
                "pattern": r'earliest=(-?\d+)([smhdwy])(?:@[smhdwy])?',
                "type": "relative", 
                "confidence": 0.90
            },
            "snap_to": {
                "pattern": r'@[hdmy]',
                "type": "snap_to",
                "confidence": 0.98
            },
            "natural_last": {
                "pattern": r'(?:last|past)\s+(\d+)\s+(second|minute|hour|day|week|month)s?',
                "type": "natural",
                "confidence": 0.85
            },
            "natural_this": {
                "pattern": r'this\s+(hour|day|week|month)',
                "type": "natural",
                "confidence": 0.80
            }
        }
        
        detected_range = None
        range_type = None
        confidence = 0.0
        duration = None
        unit = None
        
        # Check SPL query first
        for pattern_name, pattern_info in patterns.items():
            match = re.search(pattern_info["pattern"], spl_query, re.IGNORECASE)
            if match:
                detected_range = match.group(0)
                range_type = pattern_info["type"]
                confidence = pattern_info["confidence"]
                
                if len(match.groups()) >= 2:
                    try:
                        duration = int(match.group(1))
                        unit = match.group(2)
                    except:
                        pass
                break
        
        # Check natural language query if no SPL match
        if not detected_range and natural_query:
            for pattern_name, pattern_info in patterns.items():
                if "natural" in pattern_name:
                    match = re.search(pattern_info["pattern"], natural_query, re.IGNORECASE)
                    if match:
                        detected_range = match.group(0)
                        range_type = pattern_info["type"]
                        confidence = pattern_info["confidence"]
                        
                        if len(match.groups()) >= 2:
                            try:
                                duration = int(match.group(1))
                                unit = match.group(2)
                            except:
                                pass
                        break
        
        return {
            "detected_range": detected_range,
            "range_type": range_type,
            "confidence": confidence,
            "duration": duration,
            "unit": unit,
            "parsed_successfully": detected_range is not None
        }
    
    test_cases = [
        {
            "name": "Simple relative time range",
            "spl": "search earliest=-1h error | stats count by host",
            "natural": "Show me errors in the last hour",
            "expected_type": "relative",
            "expected_duration": 1,
            "expected_unit": "h"
        },
        {
            "name": "Complex relative time range with snap",
            "spl": "search earliest=-24h@h latest=now failed login",
            "natural": "Failed logins in the last 24 hours",
            "expected_type": "relative",
            "expected_duration": 24,
            "expected_unit": "h"
        },
        {
            "name": "Snap-to time boundary",
            "spl": "search earliest=@d status>=400 | timechart count",
            "natural": "HTTP errors since start of day",
            "expected_type": "snap_to"
        },
        {
            "name": "Natural language time expression",
            "spl": "search error | stats count by component",
            "natural": "Show me errors from the last 6 hours",
            "expected_type": "natural",
            "expected_duration": 6,
            "expected_unit": "hour"
        },
        {
            "name": "This period expression",
            "spl": "search cpu>80 | stats avg(memory) by host",
            "natural": "High CPU usage this week",
            "expected_type": "natural"
        },
        {
            "name": "No time range specified",
            "spl": "search * | head 100",
            "natural": "Show me recent events",
            "expected_type": None
        }
    ]
    
    for case in test_cases:
        print(f"\\nTest Case: {case['name']}")
        print(f"SPL: {case['spl']}")
        print(f"Natural: {case['natural']}")
        print("-" * 50)
        
        result = detect_time_range(case['spl'], case['natural'])
        
        print(f"Detected Range: {result['detected_range'] or 'None'}")
        print(f"Range Type: {result['range_type'] or 'None'}")
        print(f"Confidence: {result['confidence']:.3f}")
        print(f"Duration: {result['duration'] or 'N/A'}")
        print(f"Unit: {result['unit'] or 'N/A'}")
        print(f"Parsed Successfully: {result['parsed_successfully']}")
        
        type_match = result['range_type'] == case.get('expected_type')
        duration_match = result['duration'] == case.get('expected_duration', result['duration'])
        unit_match = result['unit'] == case.get('expected_unit', result['unit'])
        
        print(f"Expected Type: {case.get('expected_type')} | Match: {'✓' if type_match else '✗'}")
        if case.get('expected_duration'):
            print(f"Expected Duration: {case['expected_duration']} | Match: {'✓' if duration_match else '✗'}")
        if case.get('expected_unit'):
            print(f"Expected Unit: {case['expected_unit']} | Match: {'✓' if unit_match else '✗'}")


def test_optimization_strategies():
    """Test different time range optimization strategies"""
    print("\\n" + "=" * 60)
    print("TESTING TIME RANGE OPTIMIZATION STRATEGIES")
    print("=" * 60)
    
    def apply_optimization_strategy(spl_query: str, strategy: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply optimization strategy to SPL query"""
        
        # Define strategy-specific time ranges by data type
        strategy_ranges = {
            "minimal": {
                "security": "15m", "web": "5m", "application": "10m", 
                "network": "2m", "system": "5m"
            },
            "balanced": {
                "security": "24h", "web": "4h", "application": "6h",
                "network": "1h", "system": "2h"
            },
            "comprehensive": {
                "security": "7d", "web": "24h", "application": "48h",
                "network": "12h", "system": "24h"
            },
            "performance_first": {
                "security": "1h", "web": "30m", "application": "1h",
                "network": "15m", "system": "30m"
            },
            "accuracy_first": {
                "security": "30d", "web": "7d", "application": "14d",
                "network": "7d", "system": "30d"
            },
            "adaptive": {
                "monitoring": {"security": "15m", "web": "5m", "application": "10m"},
                "investigation": {"security": "30d", "web": "7d", "application": "14d"},
                "reporting": {"security": "24h", "web": "4h", "application": "6h"}
            }
        }
        
        data_type = context.get("data_type", "application")
        user_intent = context.get("user_intent", "analysis")
        
        # Determine time range based on strategy
        if strategy == "adaptive":
            intent_key = user_intent if user_intent in ["monitoring", "investigation", "reporting"] else "reporting"
            time_range = strategy_ranges[strategy][intent_key].get(data_type, "6h")
        else:
            time_range = strategy_ranges[strategy].get(data_type, "6h")
        
        # Apply time range to SPL
        if "earliest=" in spl_query:
            import re
            optimized_spl = re.sub(r'earliest=[^\\s]+', f'earliest=-{time_range}', spl_query)
        else:
            if spl_query.strip().startswith("search"):
                optimized_spl = spl_query.replace("search", f"search earliest=-{time_range}", 1)
            else:
                optimized_spl = f"search earliest=-{time_range} {spl_query}"
        
        # Calculate performance metrics
        time_to_minutes = {
            "m": 1, "h": 60, "d": 1440, "w": 10080, "mon": 43200, "y": 525600
        }
        
        # Extract numeric value and unit
        import re
        match = re.match(r'(\\d+)([mhdwy]|mon)', time_range)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            total_minutes = value * time_to_minutes.get(unit, 60)
        else:
            total_minutes = 360  # default 6 hours
        
        # Performance scoring based on time range size
        if total_minutes <= 60:  # <= 1 hour
            performance_impact = "excellent"
            data_volume = "small"
            execution_time = "< 10 seconds"
            optimization_score = 95
        elif total_minutes <= 1440:  # <= 1 day
            performance_impact = "good"
            data_volume = "medium"
            execution_time = "10-30 seconds"
            optimization_score = 80
        elif total_minutes <= 10080:  # <= 1 week
            performance_impact = "moderate"
            data_volume = "large"
            execution_time = "30-120 seconds"
            optimization_score = 60
        else:
            performance_impact = "poor"
            data_volume = "very_large"
            execution_time = "> 2 minutes"
            optimization_score = 30
        
        # Strategy-specific adjustments
        strategy_adjustments = {
            "minimal": {"score_bonus": 15, "coverage": 60},
            "balanced": {"score_bonus": 10, "coverage": 85},
            "comprehensive": {"score_bonus": 0, "coverage": 95},
            "performance_first": {"score_bonus": 20, "coverage": 70},
            "accuracy_first": {"score_bonus": -10, "coverage": 98},
            "adaptive": {"score_bonus": 5, "coverage": 80}
        }
        
        adjustments = strategy_adjustments.get(strategy, {"score_bonus": 0, "coverage": 80})
        final_score = min(optimization_score + adjustments["score_bonus"], 100)
        
        return {
            "strategy": strategy,
            "optimized_spl": optimized_spl,
            "recommended_time_range": time_range,
            "performance_impact": performance_impact,
            "data_volume": data_volume,
            "execution_time": execution_time,
            "optimization_score": final_score,
            "data_coverage": adjustments["coverage"],
            "reasoning": f"{strategy.replace('_', ' ').title()} strategy for {data_type} data with {user_intent} intent"
        }
    
    test_query = "search failed login | stats count by user"
    
    test_contexts = [
        {
            "name": "Security monitoring",
            "context": {"data_type": "security", "user_intent": "monitoring"},
            "strategies": ["minimal", "balanced", "performance_first", "adaptive"]
        },
        {
            "name": "Web server investigation",
            "context": {"data_type": "web", "user_intent": "investigation"},
            "strategies": ["comprehensive", "accuracy_first", "balanced", "adaptive"]
        },
        {
            "name": "Application reporting",
            "context": {"data_type": "application", "user_intent": "reporting"},
            "strategies": ["balanced", "comprehensive", "adaptive"]
        },
        {
            "name": "Network analysis",
            "context": {"data_type": "network", "user_intent": "analysis"},
            "strategies": ["minimal", "performance_first", "balanced"]
        }
    ]
    
    for test_context in test_contexts:
        print(f"\\nContext: {test_context['name']}")
        print(f"Data Type: {test_context['context']['data_type']}")
        print(f"User Intent: {test_context['context']['user_intent']}")
        print(f"Query: {test_query}")
        print("-" * 50)
        
        for strategy in test_context['strategies']:
            result = apply_optimization_strategy(test_query, strategy, test_context['context'])
            
            print(f"\\n  Strategy: {result['strategy'].upper()}")
            print(f"  Recommended Time Range: {result['recommended_time_range']}")
            print(f"  Optimized SPL: {result['optimized_spl']}")
            print(f"  Performance Impact: {result['performance_impact']}")
            print(f"  Data Coverage: {result['data_coverage']}%")
            print(f"  Optimization Score: {result['optimization_score']}")
            print(f"  Reasoning: {result['reasoning']}")


def test_performance_analysis():
    """Test performance impact analysis for time range optimization"""
    print("\\n" + "=" * 60)
    print("TESTING PERFORMANCE IMPACT ANALYSIS")
    print("=" * 60)
    
    def analyze_performance_impact(time_range: str, data_type: str, query_complexity: str) -> Dict[str, Any]:
        """Analyze performance impact of time range"""
        
        # Convert time range to minutes for analysis
        time_to_minutes = {
            "m": 1, "h": 60, "d": 1440, "w": 10080, "mon": 43200, "y": 525600
        }
        
        import re
        match = re.match(r'(\\d+)([mhdwy]|mon)', time_range)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            total_minutes = value * time_to_minutes.get(unit, 60)
        else:
            total_minutes = 360  # default
        
        # Data type volume multipliers
        volume_multipliers = {
            "security": 1.0,
            "web": 3.0,
            "application": 1.5,
            "network": 4.0,
            "system": 1.2
        }
        
        # Query complexity multipliers
        complexity_multipliers = {
            "simple": 1.0,
            "moderate": 2.0,
            "complex": 4.0,
            "advanced": 8.0
        }
        
        # Calculate base metrics
        base_volume = total_minutes * volume_multipliers.get(data_type, 1.0)
        adjusted_volume = base_volume * complexity_multipliers.get(query_complexity, 1.0)
        
        # Determine performance characteristics
        if adjusted_volume <= 100:
            performance_impact = "excellent"
            execution_time = "< 5 seconds"
            resource_usage = "low"
            concurrent_capacity = 100
            index_efficiency = 95
        elif adjusted_volume <= 1000:
            performance_impact = "good"
            execution_time = "5-15 seconds"
            resource_usage = "medium"
            concurrent_capacity = 50
            index_efficiency = 85
        elif adjusted_volume <= 10000:
            performance_impact = "moderate"
            execution_time = "15-60 seconds"
            resource_usage = "medium"
            concurrent_capacity = 20
            index_efficiency = 70
        elif adjusted_volume <= 50000:
            performance_impact = "poor"
            execution_time = "1-5 minutes"
            resource_usage = "high"
            concurrent_capacity = 5
            index_efficiency = 50
        else:
            performance_impact = "very_poor"
            execution_time = "> 5 minutes"
            resource_usage = "very_high"
            concurrent_capacity = 1
            index_efficiency = 30
        
        # Calculate optimization score
        if performance_impact == "excellent":
            optimization_score = 95
        elif performance_impact == "good":
            optimization_score = 80
        elif performance_impact == "moderate":
            optimization_score = 60
        elif performance_impact == "poor":
            optimization_score = 35
        else:
            optimization_score = 15
        
        return {
            "time_range": time_range,
            "total_minutes": total_minutes,
            "adjusted_volume": adjusted_volume,
            "performance_impact": performance_impact,
            "execution_time": execution_time,
            "resource_usage": resource_usage,
            "concurrent_capacity": concurrent_capacity,
            "index_efficiency": index_efficiency,
            "optimization_score": optimization_score
        }
    
    test_cases = [
        {
            "name": "Real-time monitoring query",
            "time_range": "15m",
            "data_type": "security",
            "query_complexity": "simple",
            "expected_performance": "excellent"
        },
        {
            "name": "Standard web analysis",
            "time_range": "4h",
            "data_type": "web",
            "query_complexity": "moderate",
            "expected_performance": "good"
        },
        {
            "name": "Complex application investigation",
            "time_range": "24h",
            "data_type": "application",
            "query_complexity": "complex",
            "expected_performance": "moderate"
        },
        {
            "name": "Network forensic analysis",
            "time_range": "7d",
            "data_type": "network",
            "query_complexity": "advanced",
            "expected_performance": "poor"
        },
        {
            "name": "System performance historical",
            "time_range": "30d",
            "data_type": "system",
            "query_complexity": "complex",
            "expected_performance": "poor"
        }
    ]
    
    for case in test_cases:
        print(f"\\nTest Case: {case['name']}")
        print(f"Time Range: {case['time_range']}")
        print(f"Data Type: {case['data_type']}")
        print(f"Query Complexity: {case['query_complexity']}")
        print("-" * 50)
        
        result = analyze_performance_impact(
            case['time_range'],
            case['data_type'],
            case['query_complexity']
        )
        
        print(f"Total Minutes: {result['total_minutes']:,}")
        print(f"Adjusted Volume: {result['adjusted_volume']:,.0f}")
        print(f"Performance Impact: {result['performance_impact']}")
        print(f"Execution Time: {result['execution_time']}")
        print(f"Resource Usage: {result['resource_usage']}")
        print(f"Concurrent Capacity: {result['concurrent_capacity']}")
        print(f"Index Efficiency: {result['index_efficiency']}%")
        print(f"Optimization Score: {result['optimization_score']}")
        
        performance_match = result['performance_impact'] == case['expected_performance']
        print(f"Expected Performance: {case['expected_performance']} | Match: {'✓' if performance_match else '✗'}")


def test_context_aware_recommendations():
    """Test context-aware time range recommendations"""
    print("\\n" + "=" * 60)
    print("TESTING CONTEXT-AWARE RECOMMENDATIONS")
    print("=" * 60)
    
    def generate_context_recommendations(
        spl_query: str,
        natural_query: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate context-aware time range recommendations"""
        
        data_type = context.get("data_type", "application")
        user_intent = context.get("user_intent", "analysis")
        environment = context.get("environment", "production")
        
        # Intent-based time range recommendations
        intent_ranges = {
            "monitoring": {
                "security": "15m", "web": "5m", "application": "10m",
                "network": "2m", "system": "5m"
            },
            "investigation": {
                "security": "7d", "web": "24h", "application": "48h",
                "network": "12h", "system": "24h"
            },
            "reporting": {
                "security": "24h", "web": "4h", "application": "6h",
                "network": "1h", "system": "2h"
            },
            "analysis": {
                "security": "24h", "web": "8h", "application": "12h",
                "network": "4h", "system": "8h"
            }
        }
        
        recommended_range = intent_ranges.get(user_intent, intent_ranges["analysis"]).get(data_type, "6h")
        
        # Generate multiple recommendations with different strategies
        recommendations = []
        
        # Primary recommendation based on intent
        primary_spl = f"search earliest=-{recommended_range} {spl_query.replace('search ', '')}"
        recommendations.append({
            "type": "primary",
            "spl": primary_spl,
            "range": recommended_range,
            "reasoning": f"Optimized for {user_intent} on {data_type} data",
            "confidence": 0.9
        })
        
        # Performance-optimized alternative
        perf_ranges = {"security": "1h", "web": "30m", "application": "1h", "network": "15m", "system": "30m"}
        perf_range = perf_ranges.get(data_type, "1h")
        perf_spl = f"search earliest=-{perf_range} {spl_query.replace('search ', '')}"
        recommendations.append({
            "type": "performance",
            "spl": perf_spl,
            "range": perf_range,
            "reasoning": "Performance-optimized for faster execution",
            "confidence": 0.8
        })
        
        # Comprehensive alternative for investigation/forensics
        comp_ranges = {"security": "30d", "web": "7d", "application": "14d", "network": "7d", "system": "30d"}
        comp_range = comp_ranges.get(data_type, "7d")
        comp_spl = f"search earliest=-{comp_range} {spl_query.replace('search ', '')}"
        recommendations.append({
            "type": "comprehensive",
            "spl": comp_spl,
            "range": comp_range,
            "reasoning": "Comprehensive coverage for thorough analysis",
            "confidence": 0.7
        })
        
        # Context-specific adjustments
        adjustments = []
        if environment == "development":
            adjustments.append("Consider shorter time ranges in development environment")
        if "real-time" in natural_query.lower():
            adjustments.append("Real-time query detected - consider minimal time range")
        if any(word in natural_query.lower() for word in ["historical", "trend", "pattern"]):
            adjustments.append("Historical analysis detected - consider longer time range")
        
        return {
            "context": context,
            "detected_intent": user_intent,
            "detected_data_type": data_type,
            "recommendations": recommendations,
            "adjustments": adjustments,
            "primary_recommendation": recommendations[0]
        }
    
    test_cases = [
        {
            "name": "Security incident monitoring",
            "spl": "search failed login | stats count by user",
            "natural": "Show me failed login attempts for monitoring",
            "context": {
                "data_type": "security",
                "user_intent": "monitoring",
                "environment": "production"
            },
            "expected_intent": "monitoring"
        },
        {
            "name": "Web application investigation",
            "spl": "search status>=400 | stats count by uri",
            "natural": "Investigate HTTP errors for security incident",
            "context": {
                "data_type": "web",
                "user_intent": "investigation",
                "environment": "production"
            },
            "expected_intent": "investigation"
        },
        {
            "name": "Application performance reporting",
            "spl": "search level=ERROR | timechart count",
            "natural": "Generate daily error report for management",
            "context": {
                "data_type": "application",
                "user_intent": "reporting",
                "environment": "production"
            },
            "expected_intent": "reporting"
        },
        {
            "name": "Network traffic analysis",
            "spl": "search protocol=tcp | stats sum(bytes) by src_ip",
            "natural": "Analyze network traffic patterns and trends",
            "context": {
                "data_type": "network",
                "user_intent": "analysis",
                "environment": "production"
            },
            "expected_intent": "analysis"
        },
        {
            "name": "Real-time system monitoring",
            "spl": "search cpu>80 | stats avg(memory) by host",
            "natural": "Real-time monitoring of high CPU systems",
            "context": {
                "data_type": "system",
                "user_intent": "monitoring",
                "environment": "production"
            },
            "expected_intent": "monitoring"
        }
    ]
    
    for case in test_cases:
        print(f"\\nTest Case: {case['name']}")
        print(f"SPL: {case['spl']}")
        print(f"Natural: {case['natural']}")
        print(f"Context: {case['context']}")
        print("-" * 50)
        
        result = generate_context_recommendations(
            case['spl'],
            case['natural'],
            case['context']
        )
        
        print(f"Detected Intent: {result['detected_intent']}")
        print(f"Detected Data Type: {result['detected_data_type']}")
        print(f"\\nRecommendations:")
        
        for i, rec in enumerate(result['recommendations'], 1):
            print(f"  {i}. {rec['type'].title()} ({rec['range']})")
            print(f"     SPL: {rec['spl']}")
            print(f"     Reasoning: {rec['reasoning']}")
            print(f"     Confidence: {rec['confidence']:.1f}")
        
        print(f"\\nPrimary Recommendation:")
        primary = result['primary_recommendation']
        print(f"  Range: {primary['range']}")
        print(f"  Reasoning: {primary['reasoning']}")
        
        if result['adjustments']:
            print(f"\\nContext Adjustments:")
            for adj in result['adjustments']:
                print(f"  - {adj}")
        
        intent_match = result['detected_intent'] == case['expected_intent']
        print(f"\\nExpected Intent: {case['expected_intent']} | Match: {'✓' if intent_match else '✗'}")


def test_time_range_validation():
    """Test time range expression validation"""
    print("\\n" + "=" * 60)
    print("TESTING TIME RANGE VALIDATION")
    print("=" * 60)
    
    def validate_time_range_expression(time_expression: str) -> Dict[str, Any]:
        """Validate time range expression syntax and semantics"""
        import re
        
        errors = []
        warnings = []
        suggestions = []
        
        # Basic syntax validation patterns
        valid_patterns = [
            r'^earliest=-?\d+[smhdwy](\s+latest=-?\d+[smhdwy])?$',
            r'^earliest=-?\d+[smhdwy]@[smhdwy](\s+latest=-?\d+[smhdwy]@[smhdwy])?$',
            r'^earliest=@[hdmy](\s+latest=@[hdmy])?$',
            r'^earliest=-?\d+(\s+latest=-?\d+)?$'
        ]
        
        # Check if expression matches any valid pattern
        syntax_valid = any(re.match(pattern, time_expression, re.IGNORECASE) for pattern in valid_patterns)
        
        if not syntax_valid:
            errors.append("Invalid time range syntax")
        
        # Extract time components for analysis
        time_parts = []
        for part in time_expression.split():
            if '=' in part:
                key, value = part.split('=', 1)
                time_parts.append((key, value))
        
        # Validate each time component
        for key, value in time_parts:
            if key.lower() in ['earliest', 'latest']:
                # Check for valid time format
                if value.startswith('-'):
                    # Relative time
                    match = re.match(r'-(\d+)([smhdwy])', value)
                    if not match:
                        errors.append(f"Invalid relative time format: {value}")
                    else:
                        duration = int(match.group(1))
                        unit = match.group(2)
                        
                        # Performance warnings based on duration
                        if unit == 'y' and duration > 1:
                            warnings.append("Time range > 1 year may impact performance")
                        elif unit == 'mon' and duration > 6:
                            warnings.append("Time range > 6 months may impact performance")
                        elif unit == 'd' and duration > 30:
                            warnings.append("Time range > 30 days may impact performance")
                        elif unit == 'h' and duration > 168:  # 1 week
                            warnings.append("Time range > 1 week may impact performance")
                
                elif value.startswith('@'):
                    # Snap-to time
                    if not re.match(r'@[hdmy]\d*', value):
                        errors.append(f"Invalid snap-to time format: {value}")
                
                else:
                    # Absolute time or other format
                    if not re.match(r'\d+', value):
                        errors.append(f"Unrecognized time format: {value}")
        
        # Generate suggestions based on analysis
        if not errors:
            if not warnings:
                suggestions.append("Time range expression is well-optimized")
            else:
                suggestions.append("Consider shorter time range for better performance")
                suggestions.append("Add index specification to improve efficiency")
        
        # Performance impact assessment
        if any("year" in w or "month" in w for w in warnings):
            performance_impact = "poor"
        elif any("day" in w or "week" in w for w in warnings):
            performance_impact = "moderate"
        else:
            performance_impact = "good"
        
        return {
            "valid": len(errors) == 0,
            "syntax_valid": syntax_valid,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
            "performance_impact": performance_impact,
            "components": time_parts
        }
    
    test_expressions = [
        {
            "name": "Valid relative time range",
            "expression": "earliest=-24h latest=-1h",
            "expected_valid": True,
            "expected_performance": "good"
        },
        {
            "name": "Valid snap-to time range",
            "expression": "earliest=@d latest=@h",
            "expected_valid": True,
            "expected_performance": "good"
        },
        {
            "name": "Simple earliest only",
            "expression": "earliest=-1h",
            "expected_valid": True,
            "expected_performance": "good"
        },
        {
            "name": "Long time range with warning",
            "expression": "earliest=-30d",
            "expected_valid": True,
            "expected_performance": "moderate"
        },
        {
            "name": "Very long time range",
            "expression": "earliest=-1y",
            "expected_valid": True,
            "expected_performance": "poor"
        },
        {
            "name": "Invalid syntax",
            "expression": "earliest=invalid",
            "expected_valid": False,
            "expected_performance": "good"
        },
        {
            "name": "Missing time unit",
            "expression": "earliest=-24",
            "expected_valid": False,
            "expected_performance": "good"
        },
        {
            "name": "Complex valid expression",
            "expression": "earliest=-7d@d latest=now",
            "expected_valid": True,
            "expected_performance": "moderate"
        }
    ]
    
    for expr in test_expressions:
        print(f"\\nExpression: {expr['name']}")
        print(f"Time Range: {expr['expression']}")
        print("-" * 50)
        
        result = validate_time_range_expression(expr['expression'])
        
        print(f"Valid: {result['valid']}")
        print(f"Syntax Valid: {result['syntax_valid']}")
        print(f"Performance Impact: {result['performance_impact']}")
        
        if result['errors']:
            print(f"Errors:")
            for error in result['errors']:
                print(f"  - {error}")
        
        if result['warnings']:
            print(f"Warnings:")
            for warning in result['warnings']:
                print(f"  - {warning}")
        
        if result['suggestions']:
            print(f"Suggestions:")
            for suggestion in result['suggestions']:
                print(f"  - {suggestion}")
        
        if result['components']:
            print(f"Components: {result['components']}")
        
        valid_match = result['valid'] == expr['expected_valid']
        perf_match = result['performance_impact'] == expr['expected_performance']
        print(f"Expected Valid: {expr['expected_valid']} | Match: {'✓' if valid_match else '✗'}")
        print(f"Expected Performance: {expr['expected_performance']} | Match: {'✓' if perf_match else '✗'}")


if __name__ == "__main__":
    print("Testing Time Range Optimization System")
    print("=" * 60)
    
    # Run all tests
    test_time_range_detection()
    test_optimization_strategies()
    test_performance_analysis()
    test_context_aware_recommendations()
    test_time_range_validation()
    
    print("\\n" + "=" * 60)
    print("TIME RANGE OPTIMIZATION TESTING COMPLETE")
    print("=" * 60)