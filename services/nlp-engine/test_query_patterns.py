#!/usr/bin/env python3
"""
Simple test script for testing query pattern detection without external dependencies
"""

import re
from typing import List, Dict, Any


def test_subquery_patterns():
    """Test subquery pattern detection"""
    print("=" * 60)
    print("TESTING SUBQUERY PATTERN DETECTION")
    print("=" * 60)
    
    subquery_patterns = [
        r"where\s+(\w+)\s+(?:in|exists in|is in)\s+(.+?)(?:\s+and|\s+or|$)",
        r"(?:compare|compared to|relative to|versus|vs)\s+(.+)",
        r"(?:enriched with|lookup from|join with|merge with)\s+(.+)"
    ]
    
    test_queries = [
        "Show me users where status in failed login events",
        "Find hosts compared to baseline performance", 
        "Get events enriched with user details from user_lookup",
        "Show errors relative to normal operation",
        "Find users where user exists in banned_users"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        found_patterns = []
        for i, pattern in enumerate(subquery_patterns):
            matches = list(re.finditer(pattern, query, re.IGNORECASE))
            if matches:
                found_patterns.append((i, matches))
                print(f"  Pattern {i+1} matched: {[m.groups() for m in matches]}")
        
        if not found_patterns:
            print("  No subquery patterns detected")


def test_join_patterns():
    """Test join pattern detection"""
    print("\n" + "=" * 60)
    print("TESTING JOIN PATTERN DETECTION") 
    print("=" * 60)
    
    join_patterns = [
        r"(?:inner\s+)?join\s+(.+?)\s+on\s+(.+)",
        r"(?:left\s+)?join\s+(.+?)\s+(?:using|on)\s+(.+)",
        r"(?:outer\s+)?join\s+(.+?)\s+(?:where|on)\s+(.+)",
        r"merge\s+with\s+(.+?)\s+(?:on|using)\s+(.+)",
        r"combine\s+with\s+(.+?)\s+(?:on|using|by)\s+(.+)",
        r"correlate\s+(.+?)\s+with\s+(.+)",
        r"match\s+(.+?)\s+against\s+(.+)",
        r"link\s+(.+?)\s+to\s+(.+)"
    ]
    
    test_queries = [
        "Show login events join user_details on user",
        "Find network traffic left join with asset_inventory using host",
        "Correlate failed logins with user_activity",
        "Match authentication events against user_profiles",
        "Merge security events with incident_data on src_ip"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        found_patterns = []
        for i, pattern in enumerate(join_patterns):
            matches = list(re.finditer(pattern, query, re.IGNORECASE))
            if matches:
                found_patterns.append((i, matches))
                print(f"  Pattern {i+1} matched: {[m.groups() for m in matches]}")
        
        if not found_patterns:
            print("  No join patterns detected")


def test_union_patterns():
    """Test union pattern detection"""
    print("\n" + "=" * 60)
    print("TESTING UNION PATTERN DETECTION")
    print("=" * 60)
    
    union_patterns = [
        r"(?:from\s+.+?\s+)?(?:or|and also)\s+(?:from\s+)?(.+)",
        r"(?:include|also include)\s+(.+)",
        r"(?:combine|merge)\s+(?:with\s+)?(.+)"
    ]
    
    test_queries = [
        "Show errors from web logs or database logs",
        "Find events from security index and also from audit index", 
        "Combine firewall events with IDS events"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        found_patterns = []
        for i, pattern in enumerate(union_patterns):
            matches = list(re.finditer(pattern, query, re.IGNORECASE))
            if matches:
                found_patterns.append((i, matches))
                print(f"  Pattern {i+1} matched: {[m.groups() for m in matches]}")
        
        if not found_patterns:
            print("  No union patterns detected")


def test_complexity_indicators():
    """Test complexity indicator detection"""
    print("\n" + "=" * 60)
    print("TESTING COMPLEXITY INDICATORS")
    print("=" * 60)
    
    subquery_keywords = [
        "where.*in", "exists in", "is in", "compare.*with", "relative to", 
        "versus", "vs", "enriched with", "lookup from", "baseline"
    ]
    
    join_keywords = [
        "join.*on", "merge.*with", "combine.*with", "correlate.*with", 
        "match.*against", "link.*to", "left join", "inner join", "outer join"
    ]
    
    test_queries = [
        "Show failed logins join with user_details on user where user exists in suspicious_users over the last 24 hours",
        "Find top 10 users by login count left join with department_info using user_id relative to normal baseline",
        "Correlate network anomalies with security events and enrich with asset information from asset_db"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        query_lower = query.lower()
        
        # Check subquery indicators
        subquery_found = []
        for keyword in subquery_keywords:
            if re.search(keyword, query_lower):
                subquery_found.append(keyword)
        
        # Check join indicators  
        join_found = []
        for keyword in join_keywords:
            if re.search(keyword, query_lower):
                join_found.append(keyword)
        
        print(f"  Subquery indicators: {subquery_found}")
        print(f"  Join indicators: {join_found}")
        
        # Estimate complexity
        complexity_score = 0
        complexity_score += len(subquery_found) * 3
        complexity_score += len(join_found) * 4
        
        if "over time" in query_lower or "timeline" in query_lower:
            complexity_score += 2
        if any(word in query_lower for word in ["count", "sum", "average", "max", "min"]):
            complexity_score += 1
        if any(word in query_lower for word in ["by", "group by", "per"]):
            complexity_score += 1
            
        if complexity_score <= 2:
            complexity = "SIMPLE"
        elif complexity_score <= 5:
            complexity = "MODERATE"
        elif complexity_score <= 10:
            complexity = "COMPLEX"
        else:
            complexity = "ADVANCED"
            
        print(f"  Complexity score: {complexity_score} ({complexity})")


def test_spl_generation_logic():
    """Test SPL generation logic for joins and subqueries"""
    print("\n" + "=" * 60)
    print("TESTING SPL GENERATION LOGIC")
    print("=" * 60)
    
    # Simulate join SPL generation
    def generate_join_spl(main_query: str, join_type: str, subsearch: str, join_fields: List[str]) -> str:
        if join_type == "inner":
            join_cmd = f"join {' '.join(join_fields)}"
        elif join_type == "left":
            join_cmd = f"join type=left {' '.join(join_fields)}"
        elif join_type == "outer":
            join_cmd = f"join type=outer {' '.join(join_fields)}"
        else:
            join_cmd = f"join {' '.join(join_fields)}"
        
        return f"{main_query} | {join_cmd} [ {subsearch} ]"
    
    # Simulate subquery SPL generation
    def generate_subquery_spl(main_query: str, purpose: str, subsearch: str, fields: List[str]) -> str:
        if purpose == "filter":
            return f"{main_query} | search [ {subsearch} | return {' '.join(fields)} ]"
        elif purpose == "lookup":
            return f"{main_query} | lookup [ {subsearch} | outputlookup temp_lookup ]"
        elif purpose == "comparison":
            return f"{main_query} | eval baseline=[ {subsearch} | return result ]"
        else:
            return main_query
    
    # Test cases
    test_cases = [
        {
            "type": "join",
            "main": "search failed login",
            "join_type": "left", 
            "subsearch": "search user_details",
            "fields": ["user"]
        },
        {
            "type": "subquery",
            "main": "search authentication",
            "purpose": "filter",
            "subsearch": "search banned_users | dedup user",
            "fields": ["user"]
        },
        {
            "type": "union",
            "queries": ["search index=web error", "search index=db error"]
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTest Case {i+1}: {test_case['type'].upper()}")
        print("-" * 30)
        
        if test_case["type"] == "join":
            spl = generate_join_spl(
                test_case["main"],
                test_case["join_type"], 
                test_case["subsearch"],
                test_case["fields"]
            )
            print(f"Generated SPL: {spl}")
            
        elif test_case["type"] == "subquery":
            spl = generate_subquery_spl(
                test_case["main"],
                test_case["purpose"],
                test_case["subsearch"], 
                test_case["fields"]
            )
            print(f"Generated SPL: {spl}")
            
        elif test_case["type"] == "union":
            union_parts = [f"[ {query} ]" for query in test_case["queries"]]
            spl = "| multisearch " + " ".join(union_parts)
            print(f"Generated SPL: {spl}")


if __name__ == "__main__":
    print("Testing Subquery and Join Pattern Detection")
    print("=" * 60)
    
    # Run all tests
    test_subquery_patterns()
    test_join_patterns()
    test_union_patterns()
    test_complexity_indicators()
    test_spl_generation_logic()
    
    print("\n" + "=" * 60)
    print("PATTERN TESTING COMPLETE")
    print("=" * 60)