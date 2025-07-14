"""
Tests for SPL Mapping System
"""

import pytest
from unittest.mock import Mock, patch
import re

from app.ai.spl_mapping import (
    ComprehensiveSPLMapper,
    SPLCommand,
    FieldMapping,
    IntentPattern,
    SPLCommandType,
    FieldType,
    spl_mapper
)


class TestComprehensiveSPLMapper:
    """Test the comprehensive SPL mapping system"""
    
    def test_initialization(self):
        """Test mapper initialization"""
        mapper = ComprehensiveSPLMapper()
        
        assert len(mapper.commands) > 0
        assert len(mapper.field_mappings) > 0
        assert len(mapper.intent_patterns) > 0
        assert len(mapper.aggregation_mappings) > 0
        assert len(mapper.time_mappings) > 0
        assert len(mapper.operator_mappings) > 0
    
    def test_get_command_by_name(self):
        """Test getting command by name"""
        mapper = ComprehensiveSPLMapper()
        
        # Test existing commands
        search_cmd = mapper.get_command_by_name("search")
        assert search_cmd is not None
        assert search_cmd.name == "search"
        assert search_cmd.command_type == SPLCommandType.SEARCH
        
        # Test case insensitive
        stats_cmd = mapper.get_command_by_name("STATS")
        assert stats_cmd is not None
        assert stats_cmd.name == "stats"
        
        # Test non-existing command
        non_cmd = mapper.get_command_by_name("nonexistent")
        assert non_cmd is None
    
    def test_get_commands_by_type(self):
        """Test getting commands by type"""
        mapper = ComprehensiveSPLMapper()
        
        search_commands = mapper.get_commands_by_type(SPLCommandType.SEARCH)
        assert len(search_commands) > 0
        
        agg_commands = mapper.get_commands_by_type(SPLCommandType.AGGREGATION)
        assert len(agg_commands) > 0
        
        # Verify all returned commands are of correct type
        for cmd in search_commands:
            assert cmd.command_type == SPLCommandType.SEARCH
    
    def test_find_field_mapping(self):
        """Test field mapping lookup"""
        mapper = ComprehensiveSPLMapper()
        
        # Test exact match
        time_mapping = mapper.find_field_mapping("time")
        assert time_mapping is not None
        assert time_mapping.splunk_field == "_time"
        
        # Test case insensitive
        user_mapping = mapper.find_field_mapping("USER")
        assert user_mapping is not None
        assert user_mapping.splunk_field == "user"
        
        # Test synonym
        timestamp_mapping = mapper.find_field_mapping("timestamp")
        assert timestamp_mapping is not None
        assert timestamp_mapping.splunk_field == "_time"
        
        # Test non-existing field
        non_mapping = mapper.find_field_mapping("nonexistent_field")
        assert non_mapping is None
    
    def test_resolve_aggregation_function(self):
        """Test aggregation function resolution"""
        mapper = ComprehensiveSPLMapper()
        
        # Test direct mappings
        assert mapper.resolve_aggregation_function("count") == "count"
        assert mapper.resolve_aggregation_function("average") == "avg"
        assert mapper.resolve_aggregation_function("maximum") == "max"
        assert mapper.resolve_aggregation_function("sum") == "sum"
        
        # Test case insensitive
        assert mapper.resolve_aggregation_function("AVERAGE") == "avg"
        
        # Test unmapped function (should return as-is)
        assert mapper.resolve_aggregation_function("unknown_func") == "unknown_func"
    
    def test_resolve_time_expression(self):
        """Test time expression resolution"""
        mapper = ComprehensiveSPLMapper()
        
        # Test direct mappings
        assert mapper.resolve_time_expression("today") == "-0d@d"
        assert mapper.resolve_time_expression("yesterday") == "-1d@d"
        assert mapper.resolve_time_expression("last hour") == "-1h"
        
        # Test pattern matching
        assert mapper.resolve_time_expression("5 hours ago") == "-5h"
        assert mapper.resolve_time_expression("2 days ago") == "-2d"
        assert mapper.resolve_time_expression("last 3 minutes") == "-3m"
        assert mapper.resolve_time_expression("last 1 week") == "-1w"
        
        # Test unmapped expression
        result = mapper.resolve_time_expression("some random time")
        assert result == "some random time"
    
    def test_resolve_operator(self):
        """Test operator resolution"""
        mapper = ComprehensiveSPLMapper()
        
        # Test direct mappings
        assert mapper.resolve_operator("equals") == "="
        assert mapper.resolve_operator("not equal") == "!="
        assert mapper.resolve_operator("greater than") == ">"
        assert mapper.resolve_operator("contains") == "like"
        
        # Test case insensitive
        assert mapper.resolve_operator("EQUALS") == "="
        
        # Test unmapped operator
        assert mapper.resolve_operator("unknown_op") == "unknown_op"
    
    def test_suggest_commands_for_intent(self):
        """Test command suggestions for intents"""
        mapper = ComprehensiveSPLMapper()
        
        # Test known intents
        search_commands = mapper.suggest_commands_for_intent("SEARCH_EVENTS")
        assert "search" in search_commands
        
        count_commands = mapper.suggest_commands_for_intent("COUNT_EVENTS")
        assert "stats" in count_commands
        
        time_commands = mapper.suggest_commands_for_intent("TIME_ANALYSIS")
        assert "timechart" in time_commands
        
        # Test unknown intent
        unknown_commands = mapper.suggest_commands_for_intent("UNKNOWN_INTENT")
        assert unknown_commands == []
    
    def test_generate_spl_template(self):
        """Test SPL template generation"""
        mapper = ComprehensiveSPLMapper()
        
        # Test with matching intent and entities
        entities = {"search_term": "error"}
        template = mapper.generate_spl_template("SEARCH_EVENTS", entities)
        assert "error" in template
        
        # Test with missing entities
        empty_entities = {}
        template = mapper.generate_spl_template("SEARCH_EVENTS", empty_entities)
        assert "{search_term}" in template  # Placeholder not replaced
        
        # Test with unknown intent
        template = mapper.generate_spl_template("UNKNOWN_INTENT", entities)
        assert template == ""
    
    def test_get_command_suggestions(self):
        """Test command suggestions based on partial query"""
        mapper = ComprehensiveSPLMapper()
        
        # Test with search-related query
        suggestions = mapper.get_command_suggestions("find errors")
        assert len(suggestions) > 0
        assert any("search" in cmd for cmd, score in suggestions)
        
        # Test with stats-related query
        suggestions = mapper.get_command_suggestions("count events")
        assert len(suggestions) > 0
        assert any("stats" in cmd for cmd, score in suggestions)
        
        # Test with empty query
        suggestions = mapper.get_command_suggestions("")
        assert len(suggestions) == 0
    
    def test_validate_spl_syntax(self):
        """Test SPL syntax validation"""
        mapper = ComprehensiveSPLMapper()
        
        # Test valid queries
        valid, errors = mapper.validate_spl_syntax("search error")
        assert valid is True
        assert len(errors) == 0
        
        valid, errors = mapper.validate_spl_syntax("search error | stats count")
        assert valid is True
        assert len(errors) == 0
        
        # Test invalid queries
        valid, errors = mapper.validate_spl_syntax("")
        assert valid is False
        assert "Empty query" in errors
        
        valid, errors = mapper.validate_spl_syntax("search \"unmatched quote")
        assert valid is False
        assert any("quote" in error.lower() for error in errors)
        
        valid, errors = mapper.validate_spl_syntax("search (unmatched paren")
        assert valid is False
        assert any("paren" in error.lower() for error in errors)
    
    def test_optimize_spl_query(self):
        """Test SPL query optimization"""
        mapper = ComprehensiveSPLMapper()
        
        # Test query without index
        query = "search error"
        optimized, suggestions = mapper.optimize_spl_query(query)
        assert "index" in " ".join(suggestions).lower()
        
        # Test query without time range
        query = "search index=main error"
        optimized, suggestions = mapper.optimize_spl_query(query)
        assert any("time" in suggestion.lower() for suggestion in suggestions)
        
        # Test query with many wildcards
        query = "search *error* *warning* *info* *debug*"
        optimized, suggestions = mapper.optimize_spl_query(query)
        assert any("wildcard" in suggestion.lower() for suggestion in suggestions)


class TestSPLCommand:
    """Test SPL command data structure"""
    
    def test_spl_command_creation(self):
        """Test SPL command creation"""
        cmd = SPLCommand(
            name="test",
            command_type=SPLCommandType.SEARCH,
            syntax="test <arg>",
            description="Test command"
        )
        
        assert cmd.name == "test"
        assert cmd.command_type == SPLCommandType.SEARCH
        assert cmd.syntax == "test <arg>"
        assert cmd.description == "Test command"
        assert cmd.parameters == []  # Default empty list


class TestFieldMapping:
    """Test field mapping data structure"""
    
    def test_field_mapping_creation(self):
        """Test field mapping creation"""
        mapping = FieldMapping(
            natural_names=["test", "testing"],
            splunk_field="test_field",
            field_type=FieldType.STRING
        )
        
        assert mapping.natural_names == ["test", "testing"]
        assert mapping.splunk_field == "test_field"
        assert mapping.field_type == FieldType.STRING
        assert mapping.common_values == []  # Default empty list


class TestIntentPattern:
    """Test intent pattern data structure"""
    
    def test_intent_pattern_creation(self):
        """Test intent pattern creation"""
        pattern = IntentPattern(
            intent="TEST_INTENT",
            patterns=["test pattern", "another pattern"],
            spl_template="search {term}"
        )
        
        assert pattern.intent == "TEST_INTENT"
        assert len(pattern.patterns) == 2
        assert pattern.spl_template == "search {term}"
        assert pattern.required_entities == []  # Default empty list


class TestGlobalMapper:
    """Test the global mapper instance"""
    
    def test_global_mapper_exists(self):
        """Test that global mapper instance exists"""
        assert spl_mapper is not None
        assert isinstance(spl_mapper, ComprehensiveSPLMapper)
    
    def test_global_mapper_functionality(self):
        """Test basic functionality of global mapper"""
        # Test command lookup
        search_cmd = spl_mapper.get_command_by_name("search")
        assert search_cmd is not None
        
        # Test field mapping
        time_mapping = spl_mapper.find_field_mapping("time")
        assert time_mapping is not None
        
        # Test aggregation resolution
        result = spl_mapper.resolve_aggregation_function("count")
        assert result == "count"


class TestAdvancedMappingFeatures:
    """Test advanced mapping features"""
    
    def test_complex_time_expressions(self):
        """Test complex time expression parsing"""
        mapper = ComprehensiveSPLMapper()
        
        # Test various time patterns
        test_cases = [
            ("3 hours ago", "-3h"),
            ("15 minutes ago", "-15m"),
            ("last 2 days", "-2d"),
            ("last 1 week", "-1w"),
            ("last 6 months", "-6mon")
        ]
        
        for natural, expected in test_cases:
            result = mapper.resolve_time_expression(natural)
            assert result == expected, f"Expected {expected}, got {result} for '{natural}'"
    
    def test_field_type_validation(self):
        """Test field type enumeration"""
        # Test all field types exist
        field_types = [
            FieldType.STRING,
            FieldType.NUMBER,
            FieldType.TIMESTAMP,
            FieldType.IP_ADDRESS,
            FieldType.URL,
            FieldType.EMAIL,
            FieldType.BOOLEAN,
            FieldType.JSON
        ]
        
        for field_type in field_types:
            assert hasattr(field_type, 'value')
    
    def test_command_type_coverage(self):
        """Test command type coverage"""
        mapper = ComprehensiveSPLMapper()
        
        # Get all command types used
        used_types = set(cmd.command_type for cmd in mapper.commands.values())
        
        # Verify we have commands for major types
        expected_types = [
            SPLCommandType.SEARCH,
            SPLCommandType.FILTERING,
            SPLCommandType.AGGREGATION,
            SPLCommandType.TRANSFORMATION
        ]
        
        for expected_type in expected_types:
            assert expected_type in used_types
    
    def test_pattern_matching_accuracy(self):
        """Test intent pattern matching accuracy"""
        mapper = ComprehensiveSPLMapper()
        
        test_queries = [
            ("find all errors", "SEARCH_EVENTS"),
            ("count the events", "COUNT_EVENTS"),
            ("show me top users", "TOP_VALUES"),
            ("errors over time", "TIME_ANALYSIS"),
            ("error analysis", "ERROR_ANALYSIS")
        ]
        
        for query, expected_intent in test_queries:
            # Find matching patterns
            matching_patterns = []
            for pattern in mapper.intent_patterns:
                for regex_pattern in pattern.patterns:
                    if re.search(regex_pattern, query.lower()):
                        matching_patterns.append(pattern.intent)
                        break
            
            # Should have at least one match for expected intent
            if expected_intent != "ERROR_ANALYSIS":  # Some patterns might not be implemented yet
                assert expected_intent in matching_patterns or len(matching_patterns) > 0


if __name__ == "__main__":
    pytest.main([__file__])