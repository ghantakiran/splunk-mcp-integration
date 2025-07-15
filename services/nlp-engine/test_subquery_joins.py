#!/usr/bin/env python3
"""
Test script for subquery and join support in SPL translation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.ai.query_constructor import query_constructor, QueryComplexity
from app.ai.spl_mapping import spl_mapper


def test_subquery_detection():
    """Test subquery detection and generation"""
    print("=" * 60)
    print("TESTING SUBQUERY DETECTION")
    print("=" * 60)
    
    test_queries = [
        "Show me users where status in failed login events",
        "Find hosts compared to baseline performance",
        "Get events enriched with user details from user_lookup",
        "Show errors relative to normal operation",
        "Find users where user exists in banned_users"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 50)
        
        try:
            complex_query = query_constructor.construct_complex_query(query)
            print(f"Complexity: {complex_query.complexity.value}")
            print(f"Subqueries: {len(complex_query.subqueries)}")
            
            for i, subquery in enumerate(complex_query.subqueries):
                print(f"  Subquery {i+1}: {subquery.purpose} - {subquery.name}")
                print(f"    Fields: {subquery.fields}")
                print(f"    SPL: {subquery.pipeline.to_spl()}")
            
            print(f"Generated SPL: {complex_query.to_spl()}")
            
        except Exception as e:
            print(f"Error: {e}")


def test_join_detection():
    """Test join detection and generation"""
    print("\n" + "=" * 60)
    print("TESTING JOIN DETECTION")
    print("=" * 60)
    
    test_queries = [
        "Show login events join user_details on user",
        "Find network traffic left join with asset_inventory using host",
        "Correlate failed logins with user_activity",
        "Match authentication events against user_profiles",
        "Merge security events with incident_data on src_ip"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 50)
        
        try:
            complex_query = query_constructor.construct_complex_query(query)
            print(f"Complexity: {complex_query.complexity.value}")
            print(f"Joins: {len(complex_query.joins)}")
            
            for i, join in enumerate(complex_query.joins):
                print(f"  Join {i+1}: {join.join_type}")
                print(f"    Fields: {join.join_fields}")
                print(f"    Subsearch SPL: {join.subsearch.to_spl()}")
            
            print(f"Generated SPL: {complex_query.to_spl()}")
            
        except Exception as e:
            print(f"Error: {e}")


def test_union_detection():
    """Test union detection and generation"""
    print("\n" + "=" * 60)
    print("TESTING UNION DETECTION")
    print("=" * 60)
    
    test_queries = [
        "Show errors from web logs or database logs",
        "Find events from security index and also from audit index",
        "Combine firewall events with IDS events"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 50)
        
        try:
            complex_query = query_constructor.construct_complex_query(query)
            print(f"Complexity: {complex_query.complexity.value}")
            print(f"Unions: {len(complex_query.unions)}")
            
            for i, union in enumerate(complex_query.unions):
                print(f"  Union {i+1}: {union.to_spl()}")
            
            print(f"Generated SPL: {complex_query.to_spl()}")
            
        except Exception as e:
            print(f"Error: {e}")


def test_complex_combinations():
    """Test complex queries with multiple features"""
    print("\n" + "=" * 60)
    print("TESTING COMPLEX COMBINATIONS")
    print("=" * 60)
    
    test_queries = [
        "Show failed logins join with user_details on user where user exists in suspicious_users over the last 24 hours",
        "Find top 10 users by login count left join with department_info using user_id relative to normal baseline",
        "Correlate network anomalies with security events and enrich with asset information from asset_db"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 50)
        
        try:
            complex_query = query_constructor.construct_complex_query(query)
            print(f"Complexity: {complex_query.complexity.value}")
            print(f"Subqueries: {len(complex_query.subqueries)}")
            print(f"Joins: {len(complex_query.joins)}")
            print(f"Unions: {len(complex_query.unions)}")
            
            # Show performance analysis
            performance = query_constructor.analyze_query_performance(complex_query)
            print(f"Performance Score: {performance['complexity_score']}")
            print(f"Estimated Cost: {performance['estimated_cost']}")
            print(f"Warnings: {performance['performance_warnings']}")
            
            print(f"Generated SPL: {complex_query.to_spl()}")
            
        except Exception as e:
            print(f"Error: {e}")


def test_spl_mapping_integration():
    """Test integration with SPL mapping system"""
    print("\n" + "=" * 60)
    print("TESTING SPL MAPPING INTEGRATION")
    print("=" * 60)
    
    test_query = "Show failed logins join with user details on user"
    
    print(f"Query: {test_query}")
    print("-" * 50)
    
    try:
        # Test command suggestions
        suggestions = spl_mapper.get_command_suggestions(test_query)
        print(f"Command suggestions: {[cmd for cmd, score in suggestions[:3]]}")
        
        # Test complex query construction
        complex_query = query_constructor.construct_complex_query(test_query)
        
        # Test SPL syntax validation
        spl_query = complex_query.to_spl()
        is_valid, errors = spl_mapper.validate_spl_syntax(spl_query)
        print(f"Generated SPL: {spl_query}")
        print(f"Syntax valid: {is_valid}")
        if errors:
            print(f"Syntax errors: {errors}")
        
        # Test optimization
        optimized_spl, suggestions = spl_mapper.optimize_spl_query(spl_query)
        print(f"Optimization suggestions: {suggestions}")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("Testing Subquery and Join Support in SPL Translation")
    print("=" * 60)
    
    # Run all tests
    test_subquery_detection()
    test_join_detection()
    test_union_detection()
    test_complex_combinations()
    test_spl_mapping_integration()
    
    print("\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)