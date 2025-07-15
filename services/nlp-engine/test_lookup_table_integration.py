#!/usr/bin/env python3
"""
Test script for lookup table integration system in SPL translation
"""

import re
from typing import Dict, List, Any
import json


def test_lookup_table_detection():
    """Test lookup table operation detection from natural language"""
    print("=" * 60)
    print("TESTING LOOKUP TABLE OPERATION DETECTION")
    print("=" * 60)
    
    # Test queries with various lookup requirements
    test_queries = [
        # User enrichment
        "Enrich user data with department information",
        "Add employee details from user lookup table",
        "Get full names for all usernames",
        "Lookup user department and manager information",
        
        # Host enrichment
        "Enrich host information with OS and environment data",
        "Add server details for all hostnames",
        "Get datacenter location for each host",
        "Lookup host criticality and owner information",
        
        # Geographic enrichment
        "Get geographic data for IP addresses",
        "Add country and city information for all IPs",
        "Enrich events with location data from IP addresses",
        "Lookup timezone information for IP addresses",
        
        # Status code enrichment
        "Add HTTP status descriptions to response codes",
        "Enrich status codes with error categorization",
        "Get meaningful descriptions for HTTP status codes",
        
        # Application enrichment
        "Lookup application owner and criticality",
        "Enrich app names with support team information",
        "Add application metadata for service names",
        
        # Threat intelligence
        "Check IP addresses against threat intelligence",
        "Lookup threat level for suspicious indicators",
        "Enrich events with malware family information",
        
        # Complex combinations
        "Enrich user data and add geographic information for IP addresses",
        "Lookup host details and threat intelligence for all events"
    ]
    
    # Simplified lookup detection functions for testing
    def detect_user_lookup(query: str) -> bool:
        """Detect user lookup patterns"""
        user_terms = ["user", "username", "employee", "login", "account"]
        enrich_terms = ["enrich", "add", "lookup", "get", "department", "full name", "manager"]
        return any(term in query.lower() for term in user_terms) and any(term in query.lower() for term in enrich_terms)
    
    def detect_host_lookup(query: str) -> bool:
        """Detect host lookup patterns"""
        host_terms = ["host", "hostname", "server", "machine"]
        enrich_terms = ["enrich", "add", "lookup", "get", "os", "environment", "datacenter", "owner"]
        return any(term in query.lower() for term in host_terms) and any(term in query.lower() for term in enrich_terms)
    
    def detect_geo_lookup(query: str) -> bool:
        """Detect geographic lookup patterns"""
        geo_terms = ["geographic", "geo", "location", "country", "city", "timezone"]
        ip_terms = ["ip", "address", "addresses"]
        return any(term in query.lower() for term in geo_terms) and any(term in query.lower() for term in ip_terms)
    
    def detect_status_lookup(query: str) -> bool:
        """Detect status code lookup patterns"""
        status_terms = ["status", "http", "response", "code", "codes"]
        lookup_terms = ["description", "meaning", "error", "categorization"]
        return any(term in query.lower() for term in status_terms) and any(term in query.lower() for term in lookup_terms)
    
    def detect_threat_lookup(query: str) -> bool:
        """Detect threat intelligence lookup patterns"""
        threat_terms = ["threat", "intelligence", "malware", "suspicious", "indicators"]
        lookup_terms = ["check", "lookup", "level", "family"]
        return any(term in query.lower() for term in threat_terms) and any(term in query.lower() for term in lookup_terms)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        detected_lookups = []
        
        if detect_user_lookup(query):
            detected_lookups.append({
                "type": "user_enrichment",
                "lookup_table": "users",
                "description": "Enrich user information with department, manager, and contact details"
            })
        
        if detect_host_lookup(query):
            detected_lookups.append({
                "type": "host_enrichment", 
                "lookup_table": "hosts",
                "description": "Enrich host information with OS, environment, and ownership data"
            })
        
        if detect_geo_lookup(query):
            detected_lookups.append({
                "type": "geo_enrichment",
                "lookup_table": "geoip", 
                "description": "Add geographic information for IP addresses"
            })
        
        if detect_status_lookup(query):
            detected_lookups.append({
                "type": "status_enrichment",
                "lookup_table": "http_status",
                "description": "Enrich HTTP status codes with descriptions and categories"
            })
        
        if detect_threat_lookup(query):
            detected_lookups.append({
                "type": "threat_enrichment",
                "lookup_table": "threat_intel",
                "description": "Check indicators against threat intelligence feeds"
            })
        
        if detected_lookups:
            for lookup in detected_lookups:
                print(f"  Type: {lookup['type']}")
                print(f"  Table: {lookup['lookup_table']}")
                print(f"  Description: {lookup['description']}")
                print()
        else:
            print("  No lookup operations detected")


def test_predefined_lookup_tables():
    """Test predefined lookup table definitions"""
    print("\n" + "=" * 60)
    print("TESTING PREDEFINED LOOKUP TABLES")
    print("=" * 60)
    
    predefined_lookups = {
        "users": {
            "type": "csv_lookup",
            "key_fields": ["username"],
            "output_fields": ["full_name", "department", "title", "manager", "email", "phone", "location"],
            "description": "User information lookup table",
            "sample_spl": "lookup users username OUTPUT full_name, department, manager, email"
        },
        "hosts": {
            "type": "csv_lookup", 
            "key_fields": ["hostname", "ip_address"],
            "output_fields": ["os", "environment", "datacenter", "owner", "criticality", "patch_group"],
            "description": "Host and server information lookup",
            "sample_spl": "lookup hosts hostname OUTPUT os, environment, datacenter, owner"
        },
        "geoip": {
            "type": "geospatial_lookup",
            "key_fields": ["ip"],
            "output_fields": ["country", "region", "city", "latitude", "longitude", "organization", "timezone"],
            "description": "Geographic IP address lookup",
            "sample_spl": "lookup geoip ip OUTPUT country, region, city, latitude, longitude"
        },
        "http_status": {
            "type": "csv_lookup",
            "key_fields": ["status_code"],
            "output_fields": ["status_description", "status_category", "is_error", "is_client_error", "is_server_error"],
            "description": "HTTP status code descriptions and categorization", 
            "sample_spl": "lookup http_status status_code OUTPUT status_description, status_category, is_error"
        },
        "applications": {
            "type": "kv_store",
            "key_fields": ["app_name", "app_id"],
            "output_fields": ["owner", "criticality", "environment", "support_team", "sla", "monitoring_url"],
            "description": "Application metadata and ownership information",
            "sample_spl": "lookup applications app_name OUTPUT owner, criticality, support_team"
        },
        "threat_intel": {
            "type": "external_lookup",
            "key_fields": ["indicator"],
            "output_fields": ["indicator_type", "threat_level", "malware_family", "first_seen", "last_seen", "confidence", "source"],
            "description": "Threat intelligence enrichment",
            "sample_spl": "lookup threat_intel indicator OUTPUT threat_level, malware_family, confidence"
        }
    }
    
    for lookup_name, lookup_info in predefined_lookups.items():
        print(f"\nLookup Table: {lookup_name.upper()}")
        print(f"Type: {lookup_info['type']}")
        print(f"Description: {lookup_info['description']}")
        print("-" * 40)
        
        print(f"Key Fields: {', '.join(lookup_info['key_fields'])}")
        print(f"Output Fields: {', '.join(lookup_info['output_fields'][:5])}{'...' if len(lookup_info['output_fields']) > 5 else ''}")
        print(f"Sample SPL: {lookup_info['sample_spl']}")


def test_spl_generation_for_lookups():
    """Test SPL generation for different lookup types"""
    print("\n" + "=" * 60)
    print("TESTING SPL GENERATION FOR LOOKUP OPERATIONS")
    print("=" * 60)
    
    def generate_csv_lookup_spl(table_name: str, key_fields: List[str], output_fields: List[str], case_sensitive: bool = False) -> str:
        """Generate CSV lookup SPL"""
        output_clause = f" OUTPUT {' '.join(output_fields)}" if output_fields else ""
        case_clause = "" if case_sensitive else " case(ignore)"
        return f"lookup {table_name} {' '.join(key_fields)}{output_clause}{case_clause}"
    
    def generate_kv_lookup_spl(collection_name: str, key_fields: List[str]) -> str:
        """Generate KV store lookup SPL"""
        return f"join {' '.join(key_fields)} [| inputlookup {collection_name}]"
    
    def generate_external_lookup_spl(table_name: str, key_fields: List[str], output_fields: List[str]) -> str:
        """Generate external lookup SPL"""
        output_clause = f" OUTPUT {' '.join(output_fields)}" if output_fields else ""
        return f"lookup {table_name} {' '.join(key_fields)}{output_clause}"
    
    test_cases = [
        # CSV Lookup examples
        {
            "type": "csv_lookup",
            "description": "User information lookup",
            "table_name": "users",
            "key_fields": ["username"],
            "output_fields": ["full_name", "department", "manager"],
            "expected_pattern": "lookup users username OUTPUT full_name department manager"
        },
        {
            "type": "csv_lookup", 
            "description": "Host information lookup",
            "table_name": "hosts",
            "key_fields": ["hostname"],
            "output_fields": ["os", "environment", "datacenter"],
            "expected_pattern": "lookup hosts hostname OUTPUT os environment datacenter"
        },
        
        # KV Store examples
        {
            "type": "kv_store",
            "description": "Application metadata lookup",
            "collection_name": "applications",
            "key_fields": ["app_name"],
            "expected_pattern": "join app_name [| inputlookup applications]"
        },
        
        # External lookup examples
        {
            "type": "external_lookup",
            "description": "Threat intelligence lookup",
            "table_name": "threat_intel",
            "key_fields": ["indicator"],
            "output_fields": ["threat_level", "malware_family", "confidence"],
            "expected_pattern": "lookup threat_intel indicator OUTPUT threat_level malware_family confidence"
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTest Case {i+1}: {test_case['type'].upper()}")
        print(f"Description: {test_case['description']}")
        print("-" * 40)
        
        if test_case["type"] == "csv_lookup":
            generated = generate_csv_lookup_spl(
                test_case["table_name"],
                test_case["key_fields"], 
                test_case["output_fields"]
            )
        elif test_case["type"] == "kv_store":
            generated = generate_kv_lookup_spl(
                test_case["collection_name"],
                test_case["key_fields"]
            )
        elif test_case["type"] == "external_lookup":
            generated = generate_external_lookup_spl(
                test_case["table_name"],
                test_case["key_fields"],
                test_case["output_fields"]
            )
        
        expected = test_case["expected_pattern"]
        print(f"Generated: {generated}")
        print(f"Expected:  {expected}")
        print(f"Match: {'✓' if expected in generated else '✗'}")


def test_lookup_optimization():
    """Test lookup optimization suggestions"""
    print("\n" + "=" * 60)
    print("TESTING LOOKUP OPTIMIZATION")
    print("=" * 60)
    
    def analyze_lookup_performance(lookup_type: str, output_fields: List[str], max_matches: int) -> Dict[str, Any]:
        """Analyze lookup performance characteristics"""
        analysis = {
            "performance_level": "good",
            "warnings": [],
            "suggestions": [],
            "estimated_impact": "low"
        }
        
        # Check output field count
        if len(output_fields) > 10:
            analysis["warnings"].append("Large number of output fields may impact performance")
            analysis["suggestions"].append("Consider limiting output fields to essential data only")
            analysis["performance_level"] = "moderate"
        
        # Check max matches
        if max_matches > 100:
            analysis["warnings"].append("High max_matches value may cause performance issues")
            analysis["suggestions"].append("Consider reducing max_matches or using more specific key fields")
            analysis["performance_level"] = "poor"
        
        # Check lookup type performance
        if lookup_type == "external_lookup":
            analysis["warnings"].append("External lookups may have network latency")
            analysis["suggestions"].append("Consider caching external lookup results")
            analysis["estimated_impact"] = "medium"
        
        if lookup_type == "kv_store" and len(output_fields) > 5:
            analysis["suggestions"].append("KV store lookups with many fields - consider indexing")
        
        return analysis
    
    test_scenarios = [
        {
            "name": "Optimized user lookup",
            "lookup_type": "csv_lookup",
            "output_fields": ["full_name", "department", "email"],
            "max_matches": 1
        },
        {
            "name": "Heavy host lookup",
            "lookup_type": "csv_lookup", 
            "output_fields": ["os", "environment", "datacenter", "owner", "criticality", "patch_group", "last_patched", "vulnerability_scan", "compliance_status", "backup_status", "monitoring_enabled"],
            "max_matches": 1
        },
        {
            "name": "High-volume threat lookup",
            "lookup_type": "external_lookup",
            "output_fields": ["threat_level", "malware_family", "confidence", "source"],
            "max_matches": 50
        },
        {
            "name": "Excessive matching",
            "lookup_type": "kv_store",
            "output_fields": ["app_name", "owner", "environment"],
            "max_matches": 500
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\nScenario: {scenario['name']}")
        print("-" * 40)
        
        analysis = analyze_lookup_performance(
            scenario["lookup_type"],
            scenario["output_fields"], 
            scenario["max_matches"]
        )
        
        print(f"Performance Level: {analysis['performance_level']}")
        print(f"Estimated Impact: {analysis['estimated_impact']}")
        print(f"Output Fields: {len(scenario['output_fields'])} fields")
        print(f"Max Matches: {scenario['max_matches']}")
        
        if analysis["warnings"]:
            print("Warnings:")
            for warning in analysis["warnings"]:
                print(f"  ⚠️  {warning}")
        
        if analysis["suggestions"]:
            print("Suggestions:")
            for suggestion in analysis["suggestions"]:
                print(f"  💡 {suggestion}")
        
        if not analysis["warnings"] and not analysis["suggestions"]:
            print("✓ No performance issues detected")


def test_field_enrichment_mappings():
    """Test field enrichment mapping functionality"""
    print("\n" + "=" * 60)
    print("TESTING FIELD ENRICHMENT MAPPINGS")
    print("=" * 60)
    
    enrichment_mappings = {
        "user_enrichment": {
            "source_fields": ["user", "username", "userid", "login"],
            "lookup_table": "users",
            "common_outputs": ["full_name", "department", "manager", "email"],
            "sample_queries": [
                "Show failed logins with user department info",
                "Get full names for all login events",
                "Add manager information to user activities"
            ]
        },
        "host_enrichment": {
            "source_fields": ["host", "hostname", "server", "ip", "dest_ip", "src_ip"],
            "lookup_table": "hosts",
            "common_outputs": ["os", "environment", "datacenter", "owner"],
            "sample_queries": [
                "Enrich server logs with environment data",
                "Add datacenter info to host events",
                "Show OS information for all servers"
            ]
        },
        "geo_enrichment": {
            "source_fields": ["ip", "src_ip", "dest_ip", "client_ip"],
            "lookup_table": "geoip",
            "common_outputs": ["country", "region", "city", "latitude", "longitude"],
            "sample_queries": [
                "Add geographic data for login IP addresses",
                "Show country information for web traffic",
                "Get city data for suspicious IP addresses"
            ]
        }
    }
    
    def detect_enrichment_opportunity(query: str) -> List[Dict[str, Any]]:
        """Detect enrichment opportunities in query"""
        opportunities = []
        query_lower = query.lower()
        
        for enrichment_name, enrichment_info in enrichment_mappings.items():
            score = 0
            detected_fields = []
            
            # Check for source fields
            for source_field in enrichment_info["source_fields"]:
                if source_field in query_lower:
                    score += 1
                    detected_fields.append(source_field)
            
            # Check for output field requests
            for output_field in enrichment_info["common_outputs"]:
                if output_field.replace("_", " ") in query_lower or output_field in query_lower:
                    score += 2
            
            # Check for enrichment keywords
            if any(keyword in query_lower for keyword in ["enrich", "add", "get", "show", "with"]):
                score += 1
            
            if score >= 2:  # Minimum threshold for recommendation
                opportunities.append({
                    "enrichment_type": enrichment_name,
                    "lookup_table": enrichment_info["lookup_table"],
                    "detected_fields": detected_fields,
                    "suggested_outputs": enrichment_info["common_outputs"][:3],  # Top 3
                    "confidence": min(score / 5.0, 1.0)  # Normalize to 0-1
                })
        
        return opportunities
    
    test_queries = [
        "Show failed login attempts with user department information",
        "Get geographic data for suspicious IP addresses",
        "Add server environment info to error logs",
        "Display user full names and manager details for admin activities",
        "Enrich web traffic with country and city data",
        "Show host criticality for all security events"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 50)
        
        opportunities = detect_enrichment_opportunity(query)
        
        if opportunities:
            for opp in opportunities:
                print(f"  Enrichment: {opp['enrichment_type']}")
                print(f"  Lookup Table: {opp['lookup_table']}")
                print(f"  Detected Fields: {', '.join(opp['detected_fields'])}")
                print(f"  Suggested Outputs: {', '.join(opp['suggested_outputs'])}")
                print(f"  Confidence: {opp['confidence']:.2f}")
                print()
        else:
            print("  No enrichment opportunities detected")


def test_lookup_validation():
    """Test lookup operation validation"""
    print("\n" + "=" * 60)
    print("TESTING LOOKUP OPERATION VALIDATION")
    print("=" * 60)
    
    def validate_lookup_operation(lookup_table: str, source_fields: List[str], target_fields: List[str], max_matches: int = 1) -> Dict[str, Any]:
        """Validate lookup operation configuration"""
        validation = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # Define available lookup tables and their fields
        available_tables = {
            "users": {
                "key_fields": ["username"],
                "output_fields": ["full_name", "department", "title", "manager", "email", "phone", "location"]
            },
            "hosts": {
                "key_fields": ["hostname", "ip_address"],
                "output_fields": ["os", "environment", "datacenter", "owner", "criticality", "patch_group"]
            },
            "geoip": {
                "key_fields": ["ip"],
                "output_fields": ["country", "region", "city", "latitude", "longitude", "organization", "timezone"]
            }
        }
        
        # Check if lookup table exists
        if lookup_table not in available_tables:
            validation["errors"].append(f"Lookup table '{lookup_table}' not found")
            validation["valid"] = False
            return validation
        
        table_info = available_tables[lookup_table]
        
        # Check source fields
        if not source_fields:
            validation["errors"].append("No source fields specified")
            validation["valid"] = False
        else:
            for source_field in source_fields:
                if source_field not in table_info["key_fields"]:
                    validation["warnings"].append(f"Source field '{source_field}' may not match key fields: {', '.join(table_info['key_fields'])}")
        
        # Check target fields
        for target_field in target_fields:
            if target_field not in table_info["output_fields"]:
                validation["warnings"].append(f"Target field '{target_field}' not available. Available: {', '.join(table_info['output_fields'])}")
        
        # Performance suggestions
        if len(target_fields) > 5:
            validation["suggestions"].append("Consider limiting output fields for better performance")
        
        if max_matches > 10:
            validation["warnings"].append("High max_matches value may impact performance")
        
        if not target_fields:
            validation["suggestions"].append("Specify output fields to control what data is enriched")
        
        return validation
    
    test_cases = [
        # Valid operations
        {
            "name": "Valid user lookup",
            "lookup_table": "users",
            "source_fields": ["username"],
            "target_fields": ["full_name", "department"],
            "max_matches": 1
        },
        {
            "name": "Valid geographic lookup",
            "lookup_table": "geoip", 
            "source_fields": ["ip"],
            "target_fields": ["country", "city"],
            "max_matches": 1
        },
        
        # Invalid operations
        {
            "name": "Invalid lookup table",
            "lookup_table": "nonexistent_table",
            "source_fields": ["username"],
            "target_fields": ["full_name"],
            "max_matches": 1
        },
        {
            "name": "Missing source fields",
            "lookup_table": "users",
            "source_fields": [],
            "target_fields": ["full_name"],
            "max_matches": 1
        },
        
        # Performance issues
        {
            "name": "Too many output fields",
            "lookup_table": "hosts",
            "source_fields": ["hostname"],
            "target_fields": ["os", "environment", "datacenter", "owner", "criticality", "patch_group", "extra1", "extra2"],
            "max_matches": 1
        },
        {
            "name": "High max matches",
            "lookup_table": "users",
            "source_fields": ["username"],
            "target_fields": ["full_name"],
            "max_matches": 100
        }
    ]
    
    for test_case in test_cases:
        print(f"\nTest: {test_case['name']}")
        print("-" * 40)
        
        validation = validate_lookup_operation(
            test_case["lookup_table"],
            test_case["source_fields"],
            test_case["target_fields"],
            test_case["max_matches"]
        )
        
        print(f"Valid: {'✓' if validation['valid'] else '✗'}")
        
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
        
        if validation["valid"] and not validation["warnings"] and not validation["suggestions"]:
            print("✓ No issues found")


if __name__ == "__main__":
    print("Testing Lookup Table Integration System")
    print("=" * 60)
    
    # Run all tests
    test_lookup_table_detection()
    test_predefined_lookup_tables()
    test_spl_generation_for_lookups()
    test_lookup_optimization()
    test_field_enrichment_mappings()
    test_lookup_validation()
    
    print("\n" + "=" * 60)
    print("LOOKUP TABLE INTEGRATION TESTING COMPLETE")
    print("=" * 60)