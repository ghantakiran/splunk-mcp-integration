"""
Regex and Pattern Matching System for SPL Translation

This module provides comprehensive regex and pattern matching capabilities including:
- Natural language to regex conversion
- SPL regex command generation (rex, regex, replace)
- Pattern validation and optimization
- Text extraction and transformation patterns
- Field extraction pattern generation
- Log parsing and structured data extraction
"""

import re
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import string
from datetime import datetime

from ..core.logging import get_logger
from .spl_mapping import spl_mapper, FieldType

logger = get_logger(__name__)


class RegexComplexity(Enum):
    """Regex complexity levels"""
    SIMPLE = "simple"          # Basic character matching
    INTERMEDIATE = "intermediate"  # Character classes, quantifiers
    ADVANCED = "advanced"      # Groups, lookaheads, complex patterns
    EXPERT = "expert"         # Complex nested patterns, backreferences


class PatternType(Enum):
    """Types of pattern matching operations"""
    EXTRACTION = "extraction"     # Extract specific data
    VALIDATION = "validation"     # Validate data format
    REPLACEMENT = "replacement"   # Replace or transform data
    PARSING = "parsing"          # Parse structured data
    FILTERING = "filtering"      # Filter based on patterns
    CLEANING = "cleaning"        # Clean and normalize data


class RegexCommand(Enum):
    """SPL regex-related commands"""
    REX = "rex"                  # Extract fields using regex
    REGEX = "regex"              # Filter events using regex
    REPLACE = "replace"          # Replace text using regex
    EREX = "erex"               # Extract fields with examples
    MULTIKV = "multikv"         # Multi-value field extraction
    EXTRACT = "extract"         # Field extraction
    KV = "kv"                   # Key-value extraction


@dataclass
class RegexParameter:
    """Parameters for regex operations"""
    name: str
    value: Any
    parameter_type: str = "value"  # "value", "field", "expression"
    required: bool = False
    description: str = ""


@dataclass
class PatternSpec:
    """Specification for a pattern matching operation"""
    pattern_type: PatternType
    regex_pattern: str
    source_field: str
    target_fields: List[str]
    command: RegexCommand
    parameters: List[RegexParameter] = field(default_factory=list)
    complexity: RegexComplexity = RegexComplexity.SIMPLE
    validation_pattern: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class RegexTranslation:
    """Result of regex pattern translation"""
    spl_command: str
    regex_pattern: str
    pattern_spec: PatternSpec
    confidence: float
    explanation: str
    optimization_suggestions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class RegexPatternMapper:
    """Comprehensive regex and pattern matching system"""
    
    def __init__(self):
        self.common_patterns = self._initialize_common_patterns()
        self.extraction_patterns = self._initialize_extraction_patterns()
        self.validation_patterns = self._initialize_validation_patterns()
        self.parsing_patterns = self._initialize_parsing_patterns()
        self.natural_language_patterns = self._initialize_nl_patterns()
        
    def _initialize_common_patterns(self) -> Dict[str, Dict[str, str]]:
        """Initialize common regex patterns"""
        return {
            # Network patterns
            "ip_address": {
                "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
                "description": "Match IPv4 addresses",
                "examples": ["192.168.1.1", "10.0.0.1"]
            },
            "ipv6_address": {
                "pattern": r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b",
                "description": "Match IPv6 addresses",
                "examples": ["2001:0db8:85a3:0000:0000:8a2e:0370:7334"]
            },
            "mac_address": {
                "pattern": r"\b(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\b",
                "description": "Match MAC addresses",
                "examples": ["00:1A:2B:3C:4D:5E", "00-1A-2B-3C-4D-5E"]
            },
            "url": {
                "pattern": r"https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*)?(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?",
                "description": "Match URLs",
                "examples": ["https://example.com", "http://test.org/path?param=value"]
            },
            
            # Time patterns
            "timestamp": {
                "pattern": r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}",
                "description": "Match timestamps (YYYY-MM-DD HH:MM:SS)",
                "examples": ["2023-01-15 14:30:45"]
            },
            "iso_timestamp": {
                "pattern": r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z?",
                "description": "Match ISO 8601 timestamps",
                "examples": ["2023-01-15T14:30:45.123Z"]
            },
            
            # Identifiers
            "email": {
                "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
                "description": "Match email addresses",
                "examples": ["user@example.com", "test.email+tag@domain.org"]
            },
            "phone": {
                "pattern": r"\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
                "description": "Match phone numbers",
                "examples": ["+1-555-123-4567", "(555) 123-4567"]
            },
            "ssn": {
                "pattern": r"\b\d{3}-?\d{2}-?\d{4}\b",
                "description": "Match Social Security Numbers",
                "examples": ["123-45-6789", "123456789"]
            },
            "credit_card": {
                "pattern": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
                "description": "Match credit card numbers",
                "examples": ["1234 5678 9012 3456", "1234-5678-9012-3456"]
            },
            
            # Log patterns
            "log_level": {
                "pattern": r"\b(?:TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b",
                "description": "Match log levels",
                "examples": ["INFO", "ERROR", "WARNING"]
            },
            "http_status": {
                "pattern": r"\b[1-5]\d{2}\b",
                "description": "Match HTTP status codes",
                "examples": ["200", "404", "500"]
            },
            "user_agent": {
                "pattern": r"Mozilla/[\d\.]+.*",
                "description": "Match user agent strings",
                "examples": ["Mozilla/5.0 (Windows NT 10.0; Win64; x64)"]
            },
            
            # Security patterns
            "hash_md5": {
                "pattern": r"\b[a-fA-F0-9]{32}\b",
                "description": "Match MD5 hashes",
                "examples": ["5d41402abc4b2a76b9719d911017c592"]
            },
            "hash_sha1": {
                "pattern": r"\b[a-fA-F0-9]{40}\b",
                "description": "Match SHA1 hashes",
                "examples": ["aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"]
            },
            "hash_sha256": {
                "pattern": r"\b[a-fA-F0-9]{64}\b",
                "description": "Match SHA256 hashes",
                "examples": ["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"]
            },
            
            # File patterns
            "file_path": {
                "pattern": r"(?:[a-zA-Z]:|/)?(?:[^<>:\"|?*\r\n/\\]+[/\\])*[^<>:\"|?*\r\n/\\]*",
                "description": "Match file paths",
                "examples": ["/var/log/messages", "C:\\Windows\\System32\\file.txt"]
            },
            "file_extension": {
                "pattern": r"\.[a-zA-Z0-9]+$",
                "description": "Match file extensions",
                "examples": [".txt", ".log", ".json"]
            }
        }
    
    def _initialize_extraction_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize field extraction patterns"""
        return {
            "key_value_pairs": {
                "pattern": r"(\w+)=([^\s,]+)",
                "description": "Extract key-value pairs",
                "spl_template": "rex field={source_field} \"(?<{field_name}>\\w+)=(?<{field_value}>[^\\s,]+)\"",
                "examples": ["user=john", "status=success"]
            },
            "quoted_strings": {
                "pattern": r"\"([^\"]*)\"|'([^']*)'",
                "description": "Extract quoted strings",
                "spl_template": "rex field={source_field} \"\\\"(?<{field_name}>[^\\\"]*)\\\"\"",
                "examples": ["\"hello world\"", "'test string'"]
            },
            "log_timestamp": {
                "pattern": r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})",
                "description": "Extract log timestamps",
                "spl_template": "rex field={source_field} \"(?<{field_name}>\\d{{4}}-\\d{{2}}-\\d{{2}}\\s+\\d{{2}}:\\d{{2}}:\\d{{2}})\"",
                "examples": ["2023-01-15 14:30:45"]
            },
            "bracketed_content": {
                "pattern": r"\[([^\]]*)\]",
                "description": "Extract content within brackets",
                "spl_template": "rex field={source_field} \"\\[(?<{field_name}>[^\\]]*)\\]\"",
                "examples": ["[INFO]", "[ERROR]"]
            },
            "parenthesized_content": {
                "pattern": r"\(([^\)]*)\)",
                "description": "Extract content within parentheses",
                "spl_template": "rex field={source_field} \"\\((?<{field_name}>[^\\)]*)\\)\"",
                "examples": ["(details)", "(status: ok)"]
            }
        }
    
    def _initialize_validation_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize validation patterns"""
        return {
            "valid_email": {
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                "description": "Validate email format",
                "spl_template": "regex {source_field}=\"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$\"",
                "examples": ["user@example.com"]
            },
            "valid_ip": {
                "pattern": r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",
                "description": "Validate IPv4 address",
                "spl_template": "regex {source_field}=\"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.)*\"",
                "examples": ["192.168.1.1"]
            },
            "valid_phone": {
                "pattern": r"^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$",
                "description": "Validate phone number format",
                "spl_template": "regex {source_field}=\"^\\+?1?[-\\.\\s]?\\(?[0-9]{{3}}\\)?[-\\.\\s]?[0-9]{{3}}[-\\.\\s]?[0-9]{{4}}$\"",
                "examples": ["+1-555-123-4567"]
            }
        }
    
    def _initialize_parsing_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize parsing patterns for structured data"""
        return {
            "apache_log": {
                "pattern": r'(\S+) \S+ \S+ \[([^\]]+)\] "([^"]*)" (\d+) (\d+|-)',
                "description": "Parse Apache access log format",
                "spl_template": "rex field={source_field} \"(?<client_ip>\\S+) \\S+ \\S+ \\[(?<timestamp>[^\\]]+)\\] \\\"(?<request>[^\\\"]*)\\\" (?<status>\\d+) (?<bytes>\\d+|-)\"",
                "field_names": ["client_ip", "timestamp", "request", "status", "bytes"],
                "examples": ['192.168.1.1 - - [01/Jan/2023:12:00:00 +0000] "GET /index.html HTTP/1.1" 200 1234']
            },
            "nginx_log": {
                "pattern": r'(\S+) - \S+ \[([^\]]+)\] "([^"]*)" (\d+) (\d+) "([^"]*)" "([^"]*)"',
                "description": "Parse Nginx access log format",
                "spl_template": "rex field={source_field} \"(?<remote_addr>\\S+) - \\S+ \\[(?<time_local>[^\\]]+)\\] \\\"(?<request>[^\\\"]*)\\\" (?<status>\\d+) (?<body_bytes_sent>\\d+) \\\"(?<http_referer>[^\\\"]*)\\\" \\\"(?<http_user_agent>[^\\\"]*)\\\"\"",
                "field_names": ["remote_addr", "time_local", "request", "status", "body_bytes_sent", "http_referer", "http_user_agent"],
                "examples": ['192.168.1.1 - - [01/Jan/2023:12:00:00 +0000] "GET /index.html HTTP/1.1" 200 1234 "http://example.com" "Mozilla/5.0"']
            },
            "csv_line": {
                "pattern": r'([^,]*),([^,]*),([^,]*)',
                "description": "Parse CSV line (3 columns)",
                "spl_template": "rex field={source_field} \"(?<field1>[^,]*),(?<field2>[^,]*),(?<field3>[^,]*)\"",
                "field_names": ["field1", "field2", "field3"],
                "examples": ["value1,value2,value3"]
            },
            "json_extract": {
                "pattern": r'"(\w+)"\s*:\s*"([^"]*)"',
                "description": "Extract JSON key-value pairs",
                "spl_template": "rex field={source_field} max_match=0 \"\\\"(?<json_key>\\w+)\\\"\\s*:\\s*\\\"(?<json_value>[^\\\"]*)\\\"\"",
                "field_names": ["json_key", "json_value"],
                "examples": ['"name": "value"', '"status": "success"']
            }
        }
    
    def _initialize_nl_patterns(self) -> Dict[str, List[str]]:
        """Initialize natural language patterns for regex operations"""
        return {
            "extract": [
                r"extract\s+(.+?)\s+from\s+(.+)",
                r"get\s+(.+?)\s+from\s+(.+)",
                r"find\s+(.+?)\s+in\s+(.+)",
                r"pull\s+out\s+(.+?)\s+from\s+(.+)",
                r"parse\s+(.+?)\s+from\s+(.+)"
            ],
            "match": [
                r"match\s+(.+?)\s+pattern\s+(.+)",
                r"find\s+(.+?)\s+matching\s+(.+)",
                r"filter\s+(.+?)\s+containing\s+(.+)",
                r"where\s+(.+?)\s+matches\s+(.+)"
            ],
            "replace": [
                r"replace\s+(.+?)\s+with\s+(.+?)\s+in\s+(.+)",
                r"substitute\s+(.+?)\s+with\s+(.+?)\s+in\s+(.+)",
                r"change\s+(.+?)\s+to\s+(.+?)\s+in\s+(.+)"
            ],
            "validate": [
                r"validate\s+(.+?)\s+format",
                r"check\s+if\s+(.+?)\s+is\s+valid\s+(.+)",
                r"verify\s+(.+?)\s+pattern"
            ],
            "clean": [
                r"clean\s+(.+?)\s+in\s+(.+)",
                r"remove\s+(.+?)\s+from\s+(.+)",
                r"strip\s+(.+?)\s+from\s+(.+)"
            ]
        }
    
    def detect_regex_patterns(self, query: str) -> List[PatternSpec]:
        """Detect regex and pattern matching requirements from natural language"""
        query_lower = query.lower()
        detected_patterns = []
        
        # Check for extraction patterns
        for pattern in self.natural_language_patterns["extract"]:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                what_to_extract = match.group(1).strip()
                source_field = match.group(2).strip()
                
                pattern_spec = PatternSpec(
                    pattern_type=PatternType.EXTRACTION,
                    regex_pattern=self._generate_extraction_pattern(what_to_extract),
                    source_field=self._normalize_field_name(source_field),
                    target_fields=[self._normalize_field_name(what_to_extract)],
                    command=RegexCommand.REX,
                    description=f"Extract {what_to_extract} from {source_field}"
                )
                detected_patterns.append(pattern_spec)
        
        # Check for matching/filtering patterns
        for pattern in self.natural_language_patterns["match"]:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                field_name = match.group(1).strip()
                pattern_desc = match.group(2).strip()
                
                pattern_spec = PatternSpec(
                    pattern_type=PatternType.FILTERING,
                    regex_pattern=self._generate_match_pattern(pattern_desc),
                    source_field=self._normalize_field_name(field_name),
                    target_fields=[],
                    command=RegexCommand.REGEX,
                    description=f"Filter {field_name} matching {pattern_desc}"
                )
                detected_patterns.append(pattern_spec)
        
        # Check for replacement patterns
        for pattern in self.natural_language_patterns["replace"]:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                find_text = match.group(1).strip()
                replace_text = match.group(2).strip()
                source_field = match.group(3).strip()
                
                pattern_spec = PatternSpec(
                    pattern_type=PatternType.REPLACEMENT,
                    regex_pattern=self._generate_replacement_pattern(find_text),
                    source_field=self._normalize_field_name(source_field),
                    target_fields=[self._normalize_field_name(source_field) + "_replaced"],
                    command=RegexCommand.REPLACE,
                    parameters=[
                        RegexParameter("find", find_text, "value", True),
                        RegexParameter("replace", replace_text, "value", True)
                    ],
                    description=f"Replace {find_text} with {replace_text} in {source_field}"
                )
                detected_patterns.append(pattern_spec)
        
        # Check for validation patterns
        for pattern in self.natural_language_patterns["validate"]:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                field_name = match.group(1).strip()
                
                pattern_spec = PatternSpec(
                    pattern_type=PatternType.VALIDATION,
                    regex_pattern=self._generate_validation_pattern(field_name),
                    source_field=self._normalize_field_name(field_name),
                    target_fields=[],
                    command=RegexCommand.REGEX,
                    description=f"Validate {field_name} format"
                )
                detected_patterns.append(pattern_spec)
        
        # Detect common pattern types from keywords
        detected_patterns.extend(self._detect_common_patterns(query_lower))
        
        return detected_patterns
    
    def _detect_common_patterns(self, query: str) -> List[PatternSpec]:
        """Detect common pattern types from keywords"""
        patterns = []
        
        # IP address extraction
        if any(word in query for word in ["ip", "ip address", "address"]):
            patterns.append(PatternSpec(
                pattern_type=PatternType.EXTRACTION,
                regex_pattern=self.common_patterns["ip_address"]["pattern"],
                source_field="_raw",
                target_fields=["ip_address"],
                command=RegexCommand.REX,
                description="Extract IP addresses"
            ))
        
        # Email extraction
        if any(word in query for word in ["email", "email address", "emails"]):
            patterns.append(PatternSpec(
                pattern_type=PatternType.EXTRACTION,
                regex_pattern=self.common_patterns["email"]["pattern"],
                source_field="_raw",
                target_fields=["email"],
                command=RegexCommand.REX,
                description="Extract email addresses"
            ))
        
        # URL extraction
        if any(word in query for word in ["url", "urls", "link", "links"]):
            patterns.append(PatternSpec(
                pattern_type=PatternType.EXTRACTION,
                regex_pattern=self.common_patterns["url"]["pattern"],
                source_field="_raw",
                target_fields=["url"],
                command=RegexCommand.REX,
                description="Extract URLs"
            ))
        
        # Log level extraction
        if any(word in query for word in ["log level", "level", "severity"]):
            patterns.append(PatternSpec(
                pattern_type=PatternType.EXTRACTION,
                regex_pattern=self.common_patterns["log_level"]["pattern"],
                source_field="_raw",
                target_fields=["log_level"],
                command=RegexCommand.REX,
                description="Extract log levels"
            ))
        
        # HTTP status extraction
        if any(word in query for word in ["status code", "http status", "response code"]):
            patterns.append(PatternSpec(
                pattern_type=PatternType.EXTRACTION,
                regex_pattern=self.common_patterns["http_status"]["pattern"],
                source_field="_raw",
                target_fields=["status_code"],
                command=RegexCommand.REX,
                description="Extract HTTP status codes"
            ))
        
        return patterns
    
    def _generate_extraction_pattern(self, what_to_extract: str) -> str:
        """Generate regex pattern for extracting specific content"""
        what_lower = what_to_extract.lower()
        
        # Common extraction patterns
        if "ip" in what_lower or "address" in what_lower:
            return self.common_patterns["ip_address"]["pattern"]
        elif "email" in what_lower:
            return self.common_patterns["email"]["pattern"]
        elif "url" in what_lower or "link" in what_lower:
            return self.common_patterns["url"]["pattern"]
        elif "timestamp" in what_lower or "time" in what_lower:
            return self.common_patterns["timestamp"]["pattern"]
        elif "phone" in what_lower:
            return self.common_patterns["phone"]["pattern"]
        elif "hash" in what_lower:
            return self.common_patterns["hash_md5"]["pattern"]
        else:
            # Generic word extraction
            return r"\b\w+\b"
    
    def _generate_match_pattern(self, pattern_desc: str) -> str:
        """Generate regex pattern for matching/filtering"""
        pattern_lower = pattern_desc.lower()
        
        if "error" in pattern_lower:
            return r"(?i)error|fail|exception"
        elif "success" in pattern_lower:
            return r"(?i)success|ok|complete"
        elif "warning" in pattern_lower:
            return r"(?i)warn|warning|caution"
        elif "number" in pattern_lower:
            return r"\d+"
        elif "word" in pattern_lower:
            return r"\b\w+\b"
        else:
            # Literal pattern matching
            return re.escape(pattern_desc)
    
    def _generate_replacement_pattern(self, find_text: str) -> str:
        """Generate regex pattern for replacement operations"""
        # Escape special regex characters for literal matching
        return re.escape(find_text)
    
    def _generate_validation_pattern(self, field_name: str) -> str:
        """Generate validation pattern for specific field types"""
        field_lower = field_name.lower()
        
        if "email" in field_lower:
            return self.validation_patterns["valid_email"]["pattern"]
        elif "ip" in field_lower:
            return self.validation_patterns["valid_ip"]["pattern"]
        elif "phone" in field_lower:
            return self.validation_patterns["valid_phone"]["pattern"]
        else:
            # Generic non-empty validation
            return r".+"
    
    def _normalize_field_name(self, field_name: str) -> str:
        """Normalize field names for SPL"""
        # Remove articles and common words
        field_name = re.sub(r'\b(the|a|an)\b', '', field_name.lower())
        # Replace spaces and special chars with underscores
        field_name = re.sub(r'[^\w]', '_', field_name)
        # Remove multiple underscores
        field_name = re.sub(r'_+', '_', field_name)
        # Remove leading/trailing underscores
        field_name = field_name.strip('_')
        return field_name or "extracted_field"
    
    def generate_spl_for_pattern(self, pattern_spec: PatternSpec) -> str:
        """Generate SPL command for a pattern specification"""
        if pattern_spec.command == RegexCommand.REX:
            return self._generate_rex_command(pattern_spec)
        elif pattern_spec.command == RegexCommand.REGEX:
            return self._generate_regex_command(pattern_spec)
        elif pattern_spec.command == RegexCommand.REPLACE:
            return self._generate_replace_command(pattern_spec)
        elif pattern_spec.command == RegexCommand.EXTRACT:
            return self._generate_extract_command(pattern_spec)
        else:
            return f"# Unsupported regex command: {pattern_spec.command.value}"
    
    def _generate_rex_command(self, pattern_spec: PatternSpec) -> str:
        """Generate rex command for field extraction"""
        if len(pattern_spec.target_fields) == 1:
            field_name = pattern_spec.target_fields[0]
            # Convert regex pattern to named capture group
            named_pattern = f"(?<{field_name}>{pattern_spec.regex_pattern})"
            return f"rex field={pattern_spec.source_field} \"{named_pattern}\""
        else:
            # Multiple fields - generate multiple named groups
            named_groups = []
            for i, field_name in enumerate(pattern_spec.target_fields):
                named_groups.append(f"(?<{field_name}>\\S+)")
            
            combined_pattern = "\\s+".join(named_groups)
            return f"rex field={pattern_spec.source_field} \"{combined_pattern}\""
    
    def _generate_regex_command(self, pattern_spec: PatternSpec) -> str:
        """Generate regex command for filtering"""
        return f"regex {pattern_spec.source_field}=\"{pattern_spec.regex_pattern}\""
    
    def _generate_replace_command(self, pattern_spec: PatternSpec) -> str:
        """Generate replace command for text replacement"""
        find_param = next((p for p in pattern_spec.parameters if p.name == "find"), None)
        replace_param = next((p for p in pattern_spec.parameters if p.name == "replace"), None)
        
        if find_param and replace_param:
            return f"eval {pattern_spec.target_fields[0]}=replace({pattern_spec.source_field}, \"{find_param.value}\", \"{replace_param.value}\")"
        else:
            return f"eval {pattern_spec.target_fields[0]}=replace({pattern_spec.source_field}, \"{pattern_spec.regex_pattern}\", \"\")"
    
    def _generate_extract_command(self, pattern_spec: PatternSpec) -> str:
        """Generate extract command for automatic field extraction"""
        return f"extract pairdelim=\",\" kvdelim=\"=\" from {pattern_spec.source_field}"
    
    def analyze_pattern_complexity(self, pattern: str) -> RegexComplexity:
        """Analyze regex pattern complexity"""
        complexity_score = 0
        
        # Basic patterns
        if re.search(r'[\.\*\+\?\[\]\\]', pattern):
            complexity_score += 1
        
        # Character classes
        if re.search(r'\[.*?\]', pattern):
            complexity_score += 1
        
        # Quantifiers
        if re.search(r'[\*\+\?]\??|\{.*?\}', pattern):
            complexity_score += 1
        
        # Groups
        if re.search(r'\(.*?\)', pattern):
            complexity_score += 2
        
        # Lookaheads/lookbehinds
        if re.search(r'\(\?[=!<]', pattern):
            complexity_score += 3
        
        # Backreferences
        if re.search(r'\\[1-9]', pattern):
            complexity_score += 3
        
        if complexity_score <= 1:
            return RegexComplexity.SIMPLE
        elif complexity_score <= 3:
            return RegexComplexity.INTERMEDIATE
        elif complexity_score <= 6:
            return RegexComplexity.ADVANCED
        else:
            return RegexComplexity.EXPERT
    
    def validate_regex_pattern(self, pattern: str) -> Dict[str, Any]:
        """Validate regex pattern and provide feedback"""
        validation = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": [],
            "complexity": self.analyze_pattern_complexity(pattern)
        }
        
        try:
            re.compile(pattern)
        except re.error as e:
            validation["valid"] = False
            validation["errors"].append(f"Invalid regex pattern: {str(e)}")
            return validation
        
        # Check for common issues
        if pattern.count('(') != pattern.count(')'):
            validation["warnings"].append("Unmatched parentheses in regex pattern")
        
        if pattern.count('[') != pattern.count(']'):
            validation["warnings"].append("Unmatched brackets in regex pattern")
        
        if '.*.*' in pattern:
            validation["warnings"].append("Multiple .* patterns may cause performance issues")
        
        if validation["complexity"] == RegexComplexity.EXPERT:
            validation["suggestions"].append("Consider simplifying complex regex for better performance")
        
        if len(pattern) > 100:
            validation["suggestions"].append("Very long regex patterns may be hard to maintain")
        
        return validation
    
    def optimize_regex_pattern(self, pattern: str) -> str:
        """Optimize regex pattern for performance"""
        optimized = pattern
        
        # Replace multiple .* with single .*
        optimized = re.sub(r'\.\*\.\*+', '.*', optimized)
        
        # Use non-capturing groups where possible
        optimized = re.sub(r'\((?!\?)', '(?:', optimized)
        
        # Use character classes instead of alternation where appropriate
        optimized = re.sub(r'\[a-zA-Z\]', r'[a-zA-Z]', optimized)
        
        return optimized
    
    def suggest_patterns_for_data(self, sample_data: List[str]) -> List[PatternSpec]:
        """Suggest patterns based on sample data analysis"""
        suggestions = []
        
        for data in sample_data[:10]:  # Analyze first 10 samples
            # Check for common patterns
            if re.search(self.common_patterns["ip_address"]["pattern"], data):
                suggestions.append(PatternSpec(
                    pattern_type=PatternType.EXTRACTION,
                    regex_pattern=self.common_patterns["ip_address"]["pattern"],
                    source_field="_raw",
                    target_fields=["ip_address"],
                    command=RegexCommand.REX,
                    description="Extract IP addresses from data"
                ))
            
            if re.search(self.common_patterns["email"]["pattern"], data):
                suggestions.append(PatternSpec(
                    pattern_type=PatternType.EXTRACTION,
                    regex_pattern=self.common_patterns["email"]["pattern"],
                    source_field="_raw",
                    target_fields=["email"],
                    command=RegexCommand.REX,
                    description="Extract email addresses from data"
                ))
            
            # Check for key-value patterns
            if re.search(r'\w+=\w+', data):
                suggestions.append(PatternSpec(
                    pattern_type=PatternType.EXTRACTION,
                    regex_pattern=r'(\w+)=([^\s,]+)',
                    source_field="_raw",
                    target_fields=["key", "value"],
                    command=RegexCommand.REX,
                    description="Extract key-value pairs from data"
                ))
        
        # Remove duplicates based on pattern and command
        unique_suggestions = []
        seen = set()
        for suggestion in suggestions:
            key = (suggestion.regex_pattern, suggestion.command.value)
            if key not in seen:
                seen.add(key)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions
    
    def get_pattern_documentation(self, pattern_type: str = None) -> Dict[str, Any]:
        """Get comprehensive documentation for patterns"""
        if pattern_type:
            if pattern_type in self.common_patterns:
                return self.common_patterns[pattern_type]
            elif pattern_type in self.extraction_patterns:
                return self.extraction_patterns[pattern_type]
            elif pattern_type in self.validation_patterns:
                return self.validation_patterns[pattern_type]
        
        return {
            "common_patterns": list(self.common_patterns.keys()),
            "extraction_patterns": list(self.extraction_patterns.keys()),
            "validation_patterns": list(self.validation_patterns.keys()),
            "pattern_types": [pt.value for pt in PatternType],
            "regex_commands": [rc.value for rc in RegexCommand],
            "complexity_levels": [rc.value for rc in RegexComplexity]
        }


# Global instance
regex_pattern_mapper = RegexPatternMapper()