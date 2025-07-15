#!/usr/bin/env python3
"""
Test script for statistical functions mapping in SPL translation
"""

import re
from typing import Dict, List, Any
import json


def test_statistical_function_detection():
    """Test statistical function detection patterns"""
    print("=" * 60)
    print("TESTING STATISTICAL FUNCTION DETECTION")
    print("=" * 60)
    
    # Test queries with various statistical functions
    test_queries = [
        # Descriptive statistics
        "Calculate the mean of response time",
        "Find the median cpu usage",
        "Get the standard deviation of temperatures",
        "What's the variance of scores",
        "Show me the range of latencies",
        "Find the mode of status codes",
        
        # Percentiles and quartiles
        "Calculate the 95th percentile of response time",
        "Find the first quartile of scores",
        "Get the interquartile range of measurements",
        "Show me the 99th percentile of latency",
        
        # Distribution analysis
        "Calculate the skewness of response times",
        "Find the kurtosis of error rates",
        "Test for normality of cpu usage",
        "Analyze the distribution of temperatures",
        
        # Correlation and relationships
        "Calculate the correlation between cpu usage and memory usage",
        "Find the covariance between response time and error rate",
        "Correlate temperature with humidity",
        
        # Time series analysis
        "Calculate the 5-day moving average of stock prices",
        "Find the trend in cpu usage over time",
        "Detect seasonality in sales data",
        "Apply exponential smoothing to temperature data",
        
        # Outlier detection
        "Detect outliers in response times",
        "Find anomalies in cpu usage",
        "Calculate the z-score of measurements",
        
        # Regression analysis
        "Perform linear regression of sales on advertising",
        "Fit a regression model for temperature and humidity",
        "Predict response time based on load",
        
        # Statistical inference
        "Calculate the 95% confidence interval for mean response time",
        "Test the hypothesis that mean > 100",
        "Calculate the required sample size for 95% confidence",
        
        # Complex combinations
        "Calculate the 95th percentile of response time and correlation between cpu and memory",
        "Find the mean, median, and standard deviation of scores by department"
    ]
    
    # Statistical function patterns
    descriptive_patterns = [
        r"(?:calculate|compute|find|get)\s+(?:the\s+)?(?:mean|average)\s+(?:of\s+)?(.+)",
        r"(?:calculate|compute|find|get)\s+(?:the\s+)?median\s+(?:of\s+)?(.+)",
        r"(?:calculate|compute|find|get)\s+(?:the\s+)?(?:standard deviation|stdev)\s+(?:of\s+)?(.+)",
        r"(?:calculate|compute|find|get)\s+(?:the\s+)?variance\s+(?:of\s+)?(.+)",
        r"(?:calculate|compute|find|get)\s+(?:the\s+)?range\s+(?:of\s+)?(.+)",
        r"(?:calculate|compute|find|get)\s+(?:the\s+)?mode\s+(?:of\s+)?(.+)"
    ]
    
    percentile_patterns = [
        r"(?:calculate|compute|find|get)\s+(?:the\s+)?(\d+)(?:th|st|nd|rd)?\s+percentile\s+(?:of\s+)?(.+)",
        r"(?:calculate|compute|find|get)\s+(?:the\s+)?(?:first|1st)\s+quartile\s+(?:of\s+)?(.+)",
        r"(?:calculate|compute|find|get)\s+(?:the\s+)?(?:interquartile range|iqr)\s+(?:of\s+)?(.+)"
    ]
    
    correlation_patterns = [
        r"(?:calculate|compute|find|get)\s+(?:the\s+)?correlation\s+(?:between\s+)?(.+?)\s+(?:and|with)\s+(.+)",
        r"(?:calculate|compute|find|get)\s+(?:the\s+)?covariance\s+(?:between\s+)?(.+?)\s+(?:and|with)\s+(.+)",
        r"(?:correlate|relate)\s+(.+?)\s+(?:with|to)\s+(.+)"
    ]
    
    time_series_patterns = [
        r"(?:calculate|compute|find|get)\s+(?:the\s+)?(?:(\d+)(?:-day|day)?\s+)?(?:moving average|rolling average)\s+(?:of\s+)?(.+)",
        r"(?:calculate|compute|find|get)\s+(?:the\s+)?trend\s+(?:in\s+)?(.+?)(?:\s+over\s+time)?",
        r"(?:detect|find|identify)\s+(?:the\s+)?seasonality\s+(?:in\s+)?(.+)",
        r"(?:apply\s+)?(?:exponential\s+)?smoothing\s+(?:to\s+)?(.+)"
    ]
    
    outlier_patterns = [
        r"(?:detect|find|identify)\s+(?:the\s+)?outliers\s+(?:in\s+)?(.+)",
        r"(?:detect|find|identify)\s+(?:the\s+)?anomalies\s+(?:in\s+)?(.+)",
        r"(?:calculate|compute|find|get)\s+(?:the\s+)?(?:z-score|z score)\s+(?:of\s+)?(.+)"
    ]
    
    regression_patterns = [
        r"(?:perform|run|calculate)\s+(?:linear\s+)?regression\s+(?:of\s+)?(.+?)\s+(?:on|against)\s+(.+)",
        r"(?:fit|create)\s+(?:a\s+)?(?:regression\s+)?model\s+(?:for\s+)?(.+?)\s+(?:and|with)\s+(.+)",
        r"(?:predict|forecast)\s+(.+?)\s+(?:using|based on)\s+(.+)"
    ]
    
    inference_patterns = [
        r"(?:calculate|compute|find|get)\s+(?:the\s+)?(?:(\d+)%\s+)?(?:confidence interval|ci)\s+(?:for\s+)?(.+)",
        r"(?:test|perform)\s+(?:the\s+)?hypothesis\s+(?:that\s+)?(.+)",
        r"(?:calculate|compute|find|get)\s+(?:the\s+)?(?:required\s+)?sample\s+size\s+(?:for\s+)?(.+)"
    ]
    
    all_patterns = {
        "descriptive": descriptive_patterns,
        "percentile": percentile_patterns,
        "correlation": correlation_patterns,
        "time_series": time_series_patterns,
        "outlier": outlier_patterns,
        "regression": regression_patterns,
        "inference": inference_patterns
    }
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        query_lower = query.lower()
        detected_patterns = []
        
        # Test each pattern category
        for category, patterns in all_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, query_lower)
                for match in matches:
                    detected_patterns.append((category, match.groups()))
        
        if detected_patterns:
            for pattern_type, groups in detected_patterns:
                print(f"  {pattern_type}: {groups}")
        else:
            print("  No statistical patterns detected")


def test_spl_generation():
    """Test SPL generation for statistical functions"""
    print("\n" + "=" * 60)
    print("TESTING SPL GENERATION FOR STATISTICAL FUNCTIONS")
    print("=" * 60)
    
    def generate_descriptive_spl(function: str, field: str) -> str:
        """Generate SPL for descriptive statistics"""
        if function == "mean":
            return f"stats avg({field})"
        elif function == "median":
            return f"stats median({field})"
        elif function == "standard deviation":
            return f"stats stdev({field})"
        elif function == "variance":
            return f"stats var({field})"
        elif function == "range":
            return f"stats range({field})"
        elif function == "mode":
            return f"stats mode({field})"
        else:
            return f"stats {function}({field})"
    
    def generate_percentile_spl(percentile: int, field: str) -> str:
        """Generate SPL for percentile calculations"""
        return f"stats perc{percentile}({field})"
    
    def generate_correlation_spl(field1: str, field2: str) -> str:
        """Generate SPL for correlation analysis"""
        return f"""eventstats avg({field1}) as x_mean, avg({field2}) as y_mean |
                  eval xy_dev = ({field1} - x_mean) * ({field2} - y_mean) |
                  eval x_dev_sq = ({field1} - x_mean) * ({field1} - x_mean) |
                  eval y_dev_sq = ({field2} - y_mean) * ({field2} - y_mean) |
                  eventstats sum(xy_dev) as sum_xy_dev, sum(x_dev_sq) as sum_x_dev_sq, sum(y_dev_sq) as sum_y_dev_sq |
                  eval correlation = sum_xy_dev / sqrt(sum_x_dev_sq * sum_y_dev_sq)"""
    
    def generate_moving_average_spl(field: str, window: int = 5) -> str:
        """Generate SPL for moving average"""
        return f"streamstats avg({field}) as moving_avg window={window}"
    
    def generate_outlier_spl(field: str, threshold: float = 2.0) -> str:
        """Generate SPL for outlier detection"""
        return f"""eventstats avg({field}) as field_mean, stdev({field}) as field_stdev |
                  eval zscore = abs(({field} - field_mean) / field_stdev) |
                  eval is_outlier = if(zscore > {threshold}, 1, 0)"""
    
    def generate_trend_spl(field: str) -> str:
        """Generate SPL for trend analysis"""
        return f"""sort _time |
                  streamstats count as x |
                  eventstats avg(x) as x_mean, avg({field}) as y_mean |
                  eval xy_dev = (x - x_mean) * ({field} - y_mean) |
                  eval x_dev_sq = (x - x_mean) * (x - x_mean) |
                  eventstats sum(xy_dev) as sum_xy_dev, sum(x_dev_sq) as sum_x_dev_sq |
                  eval trend_slope = sum_xy_dev / sum_x_dev_sq"""
    
    def generate_confidence_interval_spl(field: str, confidence: float = 0.95) -> str:
        """Generate SPL for confidence interval"""
        z_score = 1.96 if confidence == 0.95 else 2.576 if confidence == 0.99 else 1.645
        return f"""eventstats avg({field}) as field_mean, stdev({field}) as field_stdev, count as n |
                  eval margin_error = {z_score} * field_stdev / sqrt(n) |
                  eval ci_lower = field_mean - margin_error |
                  eval ci_upper = field_mean + margin_error"""
    
    # Test cases
    test_cases = [
        # Descriptive statistics
        {
            "type": "descriptive",
            "function": "mean",
            "field": "response_time",
            "expected": "stats avg(response_time)"
        },
        {
            "type": "descriptive",
            "function": "median",
            "field": "cpu_usage",
            "expected": "stats median(cpu_usage)"
        },
        {
            "type": "descriptive",
            "function": "standard deviation",
            "field": "latency",
            "expected": "stats stdev(latency)"
        },
        
        # Percentiles
        {
            "type": "percentile",
            "percentile": 95,
            "field": "response_time",
            "expected": "stats perc95(response_time)"
        },
        {
            "type": "percentile",
            "percentile": 99,
            "field": "error_rate",
            "expected": "stats perc99(error_rate)"
        },
        
        # Time series
        {
            "type": "moving_average",
            "field": "stock_price",
            "window": 5,
            "expected": "streamstats avg(stock_price) as moving_avg window=5"
        },
        {
            "type": "moving_average",
            "field": "temperature",
            "window": 10,
            "expected": "streamstats avg(temperature) as moving_avg window=10"
        },
        
        # Outlier detection
        {
            "type": "outlier",
            "field": "response_time",
            "threshold": 2.0,
            "expected": "eventstats avg(response_time) as field_mean, stdev(response_time) as field_stdev"
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTest Case {i+1}: {test_case['type'].upper()}")
        print("-" * 40)
        
        if test_case["type"] == "descriptive":
            generated = generate_descriptive_spl(test_case["function"], test_case["field"])
        elif test_case["type"] == "percentile":
            generated = generate_percentile_spl(test_case["percentile"], test_case["field"])
        elif test_case["type"] == "moving_average":
            generated = generate_moving_average_spl(test_case["field"], test_case["window"])
        elif test_case["type"] == "outlier":
            generated = generate_outlier_spl(test_case["field"], test_case.get("threshold", 2.0))
        
        expected = test_case["expected"]
        print(f"Generated: {generated}")
        print(f"Expected:  {expected}")
        print(f"Match: {'✓' if expected in generated else '✗'}")


def test_statistical_complexity_analysis():
    """Test statistical function complexity analysis"""
    print("\n" + "=" * 60)
    print("TESTING STATISTICAL FUNCTION COMPLEXITY ANALYSIS")
    print("=" * 60)
    
    def analyze_statistical_complexity(query: str) -> Dict[str, Any]:
        """Analyze statistical function complexity"""
        query_lower = query.lower()
        
        analysis = {
            "descriptive_functions": 0,
            "advanced_functions": 0,
            "time_series_functions": 0,
            "multivariate_functions": 0,
            "inference_functions": 0,
            "complexity_score": 0
        }
        
        # Count descriptive functions
        descriptive_funcs = ["mean", "median", "mode", "stdev", "variance", "range"]
        for func in descriptive_funcs:
            if func in query_lower:
                analysis["descriptive_functions"] += 1
        
        # Count advanced functions
        advanced_funcs = ["skewness", "kurtosis", "percentile", "quartile", "outliers", "anomalies"]
        for func in advanced_funcs:
            if func in query_lower:
                analysis["advanced_functions"] += 1
        
        # Count time series functions
        time_series_funcs = ["moving average", "trend", "seasonality", "smoothing"]
        for func in time_series_funcs:
            if func in query_lower:
                analysis["time_series_functions"] += 1
        
        # Count multivariate functions
        multivariate_funcs = ["correlation", "covariance", "regression"]
        for func in multivariate_funcs:
            if func in query_lower:
                analysis["multivariate_functions"] += 1
        
        # Count inference functions
        inference_funcs = ["confidence interval", "hypothesis test", "sample size"]
        for func in inference_funcs:
            if func in query_lower:
                analysis["inference_functions"] += 1
        
        # Calculate complexity score
        score = 0
        score += analysis["descriptive_functions"] * 1
        score += analysis["advanced_functions"] * 2
        score += analysis["time_series_functions"] * 3
        score += analysis["multivariate_functions"] * 3
        score += analysis["inference_functions"] * 4
        
        analysis["complexity_score"] = score
        
        # Determine complexity level
        if score <= 2:
            analysis["complexity_level"] = "simple"
        elif score <= 5:
            analysis["complexity_level"] = "intermediate"
        elif score <= 10:
            analysis["complexity_level"] = "advanced"
        else:
            analysis["complexity_level"] = "expert"
        
        return analysis
    
    test_queries = [
        "Calculate the mean of response time",
        "Find the 95th percentile of cpu usage",
        "Calculate the correlation between temperature and humidity",
        "Detect outliers in response times using z-score analysis",
        "Calculate the 5-day moving average and trend of stock prices",
        "Perform regression analysis and calculate confidence intervals",
        "Find the mean, median, standard deviation, skewness, and kurtosis of measurements"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        analysis = analyze_statistical_complexity(query)
        
        print(f"Descriptive functions: {analysis['descriptive_functions']}")
        print(f"Advanced functions: {analysis['advanced_functions']}")
        print(f"Time series functions: {analysis['time_series_functions']}")
        print(f"Multivariate functions: {analysis['multivariate_functions']}")
        print(f"Inference functions: {analysis['inference_functions']}")
        print(f"Complexity score: {analysis['complexity_score']}")
        print(f"Complexity level: {analysis['complexity_level']}")


def test_statistical_validation():
    """Test statistical function validation"""
    print("\n" + "=" * 60)
    print("TESTING STATISTICAL FUNCTION VALIDATION")
    print("=" * 60)
    
    def validate_statistical_query(query: str) -> Dict[str, Any]:
        """Validate statistical query"""
        query_lower = query.lower()
        
        validation = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "suggestions": []
        }
        
        # Check for field requirements
        if "correlation" in query_lower and " and " not in query_lower and " with " not in query_lower:
            validation["errors"].append("Correlation requires two fields")
            validation["valid"] = False
        
        if "regression" in query_lower and " on " not in query_lower and " against " not in query_lower:
            validation["errors"].append("Regression requires dependent and independent variables")
            validation["valid"] = False
        
        # Check for parameter requirements
        if "percentile" in query_lower:
            if not re.search(r"\d+(?:th|st|nd|rd)?\s+percentile", query_lower):
                validation["warnings"].append("Percentile value not specified, using default 50th percentile")
        
        if "moving average" in query_lower:
            if not re.search(r"\d+(?:-day|day)?\s+moving", query_lower):
                validation["warnings"].append("Moving average window not specified, using default 5 periods")
        
        if "confidence interval" in query_lower:
            if not re.search(r"\d+%\s+confidence", query_lower):
                validation["warnings"].append("Confidence level not specified, using default 95%")
        
        # Provide suggestions
        if "outlier" in query_lower:
            validation["suggestions"].append("Consider specifying outlier detection method (z-score, IQR, etc.)")
        
        if "trend" in query_lower:
            validation["suggestions"].append("Consider specifying trend analysis method (linear, polynomial, etc.)")
        
        if len([f for f in ["mean", "median", "mode", "stdev", "variance"] if f in query_lower]) > 3:
            validation["suggestions"].append("Consider using descriptive statistics summary instead of individual functions")
        
        return validation
    
    test_queries = [
        "Calculate the mean of response time",
        "Find the correlation between cpu and memory",
        "Get the 95th percentile of latency",
        "Calculate the moving average of stock prices",
        "Perform regression of sales on advertising",
        "Find the 95% confidence interval for response time",
        "Calculate the mean, median, mode, stdev, and variance of scores"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        validation = validate_statistical_query(query)
        
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


def test_statistical_categories():
    """Test statistical function categorization"""
    print("\n" + "=" * 60)
    print("TESTING STATISTICAL FUNCTION CATEGORIZATION")
    print("=" * 60)
    
    statistical_categories = {
        "descriptive": {
            "functions": ["mean", "median", "mode", "stdev", "variance", "range", "percentile", "quartile"],
            "description": "Functions that describe basic properties of data"
        },
        "inferential": {
            "functions": ["confidence interval", "hypothesis test", "sample size", "bootstrap"],
            "description": "Functions for statistical inference and hypothesis testing"
        },
        "time_series": {
            "functions": ["moving average", "trend", "seasonality", "exponential smoothing"],
            "description": "Functions for analyzing time-based data patterns"
        },
        "multivariate": {
            "functions": ["correlation", "covariance", "regression", "principal components"],
            "description": "Functions for analyzing relationships between multiple variables"
        },
        "diagnostic": {
            "functions": ["outliers", "anomalies", "z-score", "normality test"],
            "description": "Functions for identifying unusual patterns or validating assumptions"
        },
        "distribution": {
            "functions": ["skewness", "kurtosis", "normal distribution", "poisson distribution"],
            "description": "Functions for analyzing distribution properties"
        }
    }
    
    test_queries = [
        "Calculate the mean and standard deviation of response times",
        "Find the 95% confidence interval for cpu usage",
        "Calculate the 5-day moving average of stock prices",
        "Find the correlation between temperature and humidity",
        "Detect outliers in response times",
        "Calculate the skewness of error rates"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        query_lower = query.lower()
        detected_categories = []
        
        for category, info in statistical_categories.items():
            for function in info["functions"]:
                if function in query_lower:
                    detected_categories.append({
                        "category": category,
                        "function": function,
                        "description": info["description"]
                    })
        
        if detected_categories:
            for detection in detected_categories:
                print(f"  {detection['category']}: {detection['function']}")
                print(f"    Description: {detection['description']}")
        else:
            print("  No statistical categories detected")


if __name__ == "__main__":
    print("Testing Statistical Functions Mapping System")
    print("=" * 60)
    
    # Run all tests
    test_statistical_function_detection()
    test_spl_generation()
    test_statistical_complexity_analysis()
    test_statistical_validation()
    test_statistical_categories()
    
    print("\n" + "=" * 60)
    print("STATISTICAL FUNCTIONS TESTING COMPLETE")
    print("=" * 60)