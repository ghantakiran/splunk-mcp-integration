"""
Lookup Table Integration System for SPL Translation

This module provides comprehensive lookup table integration capabilities including:
- Natural language to lookup command generation
- Lookup table management and discovery
- Field enrichment and data transformation
- KV store integration and management
- External lookup configuration
- Performance optimization for lookup operations
"""

import re
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime

from ..core.logging import get_logger
from .spl_mapping import spl_mapper, FieldType

logger = get_logger(__name__)


class LookupType(Enum):
    """Types of lookup operations"""
    CSV_LOOKUP = "csv_lookup"           # CSV file lookup
    KV_STORE = "kv_store"              # KV store collection lookup
    EXTERNAL_LOOKUP = "external_lookup" # External command lookup
    AUTOMATIC_LOOKUP = "automatic"      # Automatic lookup based on field
    GEOSPATIAL_LOOKUP = "geospatial"   # Geographic lookup
    TEMPORAL_LOOKUP = "temporal"        # Time-based lookup


class LookupOperationType(Enum):
    """Lookup operations supported"""
    ENRICH = "enrich"                  # Add fields from lookup
    REPLACE = "replace"                # Replace field values
    VALIDATE = "validate"              # Validate against lookup
    TRANSFORM = "transform"            # Transform data using lookup
    FILTER = "filter"                  # Filter based on lookup
    JOIN = "join"                      # Join with lookup data


class LookupMatchType(Enum):
    """Lookup matching types"""
    EXACT = "exact"                    # Exact match
    WILDCARD = "wildcard"              # Wildcard matching  
    REGEX = "regex"                    # Regular expression
    RANGE = "range"                    # Range matching
    FUZZY = "fuzzy"                    # Fuzzy matching
    CIDR = "cidr"                      # CIDR notation for IPs


@dataclass
class LookupField:
    """Lookup field definition"""
    field_name: str
    field_type: FieldType
    is_key: bool = False
    is_output: bool = False
    description: str = ""
    default_value: Optional[str] = None
    validation_pattern: Optional[str] = None


@dataclass
class LookupTable:
    """Lookup table definition"""
    name: str
    lookup_type: LookupType
    file_path: Optional[str] = None
    collection_name: Optional[str] = None
    external_command: Optional[str] = None
    fields: List[LookupField] = field(default_factory=list)
    key_fields: List[str] = field(default_factory=list)
    output_fields: List[str] = field(default_factory=list)
    description: str = ""
    case_sensitive: bool = False
    max_matches: int = 1
    default_match: bool = True
    match_type: LookupMatchType = LookupMatchType.EXACT


@dataclass
class LookupOperation:
    """Lookup operation specification"""
    operation_type: LookupOperationType
    lookup_table: LookupTable
    source_fields: List[str]
    target_fields: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    output_mode: str = "append"  # append, replace, overwrite
    case_sensitive: bool = False
    max_matches: int = 1


@dataclass
class LookupTranslation:
    """Result of lookup operation translation"""
    spl_command: str
    lookup_operation: LookupOperation
    confidence: float
    explanation: str
    optimization_suggestions: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    performance_notes: List[str] = field(default_factory=list)


class LookupTableMapper:
    """Comprehensive lookup table integration system"""
    
    def __init__(self):
        self.predefined_lookups = self._initialize_predefined_lookups()
        self.lookup_patterns = self._initialize_lookup_patterns()
        self.field_enrichment_mappings = self._initialize_enrichment_mappings()
        self.common_lookup_operations = self._initialize_common_operations()
        
    def _initialize_predefined_lookups(self) -> Dict[str, LookupTable]:
        """Initialize predefined lookup tables"""
        lookups = {}
        
        # User information lookup
        lookups["users"] = LookupTable(
            name="users",
            lookup_type=LookupType.CSV_LOOKUP,
            file_path="users.csv",
            fields=[
                LookupField("username", FieldType.STRING, is_key=True, description="User login name"),
                LookupField("full_name", FieldType.STRING, is_output=True, description="Full user name"),
                LookupField("department", FieldType.STRING, is_output=True, description="User department"),
                LookupField("title", FieldType.STRING, is_output=True, description="Job title"),
                LookupField("manager", FieldType.STRING, is_output=True, description="Manager name"),
                LookupField("email", FieldType.EMAIL, is_output=True, description="Email address"),
                LookupField("phone", FieldType.STRING, is_output=True, description="Phone number"),
                LookupField("location", FieldType.STRING, is_output=True, description="Office location")
            ],
            key_fields=["username"],
            output_fields=["full_name", "department", "title", "manager", "email", "phone", "location"],
            description="User information lookup table"
        )
        
        # Host information lookup
        lookups["hosts"] = LookupTable(
            name="hosts",
            lookup_type=LookupType.CSV_LOOKUP,
            file_path="hosts.csv",
            fields=[
                LookupField("hostname", FieldType.STRING, is_key=True, description="Host name"),
                LookupField("ip_address", FieldType.IP_ADDRESS, is_key=True, description="IP address"),
                LookupField("os", FieldType.STRING, is_output=True, description="Operating system"),
                LookupField("environment", FieldType.STRING, is_output=True, description="Environment (prod/dev/test)"),
                LookupField("datacenter", FieldType.STRING, is_output=True, description="Data center location"),
                LookupField("owner", FieldType.STRING, is_output=True, description="System owner"),
                LookupField("criticality", FieldType.STRING, is_output=True, description="System criticality"),
                LookupField("patch_group", FieldType.STRING, is_output=True, description="Patching group")
            ],
            key_fields=["hostname", "ip_address"],
            output_fields=["os", "environment", "datacenter", "owner", "criticality", "patch_group"],
            description="Host and server information lookup"
        )
        
        # Geographic IP lookup
        lookups["geoip"] = LookupTable(
            name="geoip",
            lookup_type=LookupType.GEOSPATIAL_LOOKUP,
            file_path="geoip.csv",
            fields=[
                LookupField("ip", FieldType.IP_ADDRESS, is_key=True, description="IP address"),
                LookupField("country", FieldType.STRING, is_output=True, description="Country"),
                LookupField("region", FieldType.STRING, is_output=True, description="Region/State"),
                LookupField("city", FieldType.STRING, is_output=True, description="City"),
                LookupField("latitude", FieldType.NUMBER, is_output=True, description="Latitude"),
                LookupField("longitude", FieldType.NUMBER, is_output=True, description="Longitude"),
                LookupField("organization", FieldType.STRING, is_output=True, description="ISP/Organization"),
                LookupField("timezone", FieldType.STRING, is_output=True, description="Time zone")
            ],
            key_fields=["ip"],
            output_fields=["country", "region", "city", "latitude", "longitude", "organization", "timezone"],
            description="Geographic IP address lookup",
            match_type=LookupMatchType.CIDR
        )
        
        # HTTP status codes lookup
        lookups["http_status"] = LookupTable(
            name="http_status",
            lookup_type=LookupType.CSV_LOOKUP,
            file_path="http_status.csv",
            fields=[
                LookupField("status_code", FieldType.NUMBER, is_key=True, description="HTTP status code"),
                LookupField("status_description", FieldType.STRING, is_output=True, description="Status description"),
                LookupField("status_category", FieldType.STRING, is_output=True, description="Status category"),
                LookupField("is_error", FieldType.BOOLEAN, is_output=True, description="Is error status"),
                LookupField("is_client_error", FieldType.BOOLEAN, is_output=True, description="Is client error"),
                LookupField("is_server_error", FieldType.BOOLEAN, is_output=True, description="Is server error")
            ],
            key_fields=["status_code"],
            output_fields=["status_description", "status_category", "is_error", "is_client_error", "is_server_error"],
            description="HTTP status code descriptions and categorization"
        )
        
        # Application lookup
        lookups["applications"] = LookupTable(
            name="applications",
            lookup_type=LookupType.KV_STORE,
            collection_name="applications",
            fields=[
                LookupField("app_name", FieldType.STRING, is_key=True, description="Application name"),
                LookupField("app_id", FieldType.STRING, is_key=True, description="Application ID"),
                LookupField("owner", FieldType.STRING, is_output=True, description="Application owner"),
                LookupField("criticality", FieldType.STRING, is_output=True, description="Business criticality"),
                LookupField("environment", FieldType.STRING, is_output=True, description="Environment"),
                LookupField("support_team", FieldType.STRING, is_output=True, description="Support team"),
                LookupField("sla", FieldType.STRING, is_output=True, description="SLA requirements"),
                LookupField("monitoring_url", FieldType.URL, is_output=True, description="Monitoring dashboard")
            ],
            key_fields=["app_name", "app_id"],
            output_fields=["owner", "criticality", "environment", "support_team", "sla", "monitoring_url"],
            description="Application metadata and ownership information"
        )
        
        # Threat intelligence lookup
        lookups["threat_intel"] = LookupTable(
            name="threat_intel",
            lookup_type=LookupType.EXTERNAL_LOOKUP,
            external_command="threat_intel.py",
            fields=[
                LookupField("indicator", FieldType.STRING, is_key=True, description="Threat indicator"),
                LookupField("indicator_type", FieldType.STRING, is_output=True, description="Type of indicator"),
                LookupField("threat_level", FieldType.STRING, is_output=True, description="Threat level"),
                LookupField("malware_family", FieldType.STRING, is_output=True, description="Malware family"),
                LookupField("first_seen", FieldType.TIMESTAMP, is_output=True, description="First seen date"),
                LookupField("last_seen", FieldType.TIMESTAMP, is_output=True, description="Last seen date"),
                LookupField("confidence", FieldType.NUMBER, is_output=True, description="Confidence score"),
                LookupField("source", FieldType.STRING, is_output=True, description="Intelligence source")
            ],
            key_fields=["indicator"],
            output_fields=["indicator_type", "threat_level", "malware_family", "first_seen", "last_seen", "confidence", "source"],
            description="Threat intelligence enrichment"
        )
        
        return lookups
    
    def _initialize_lookup_patterns(self) -> Dict[str, List[str]]:
        """Initialize natural language patterns for lookup operations"""
        return {
            "enrich": [
                r"enrich\s+(.+?)\s+with\s+(.+)",
                r"add\s+(.+?)\s+(?:information|data)\s+(?:from|using)\s+(.+)",
                r"lookup\s+(.+?)\s+(?:in|from)\s+(.+)",
                r"get\s+(.+?)\s+(?:information|data)\s+for\s+(.+)",
                r"join\s+(.+?)\s+with\s+(.+)",
                r"merge\s+(.+?)\s+(?:information|data)\s+from\s+(.+)"
            ],
            "replace": [
                r"replace\s+(.+?)\s+with\s+(?:values|data)\s+from\s+(.+)",
                r"substitute\s+(.+?)\s+(?:using|with)\s+(.+)",
                r"map\s+(.+?)\s+(?:using|to)\s+(.+)"
            ],
            "validate": [
                r"validate\s+(.+?)\s+against\s+(.+)",
                r"check\s+(.+?)\s+(?:in|against)\s+(.+)",
                r"verify\s+(.+?)\s+(?:using|with)\s+(.+)"
            ],
            "filter": [
                r"filter\s+(?:by|using)\s+(.+?)\s+(?:in|from)\s+(.+)",
                r"(?:only|just)\s+show\s+(?:events|records)\s+(?:that|where)\s+(.+?)\s+(?:exists|is)\s+in\s+(.+)",
                r"exclude\s+(?:events|records)\s+(?:where|if)\s+(.+?)\s+(?:not\s+)?(?:in|found)\s+(.+)"
            ],
            "transform": [
                r"transform\s+(.+?)\s+(?:using|with)\s+(.+)",
                r"convert\s+(.+?)\s+(?:using|with)\s+(.+)",
                r"normalize\s+(.+?)\s+(?:using|with)\s+(.+)"
            ]
        }
    
    def _initialize_enrichment_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Initialize field enrichment mappings"""
        return {
            "user_enrichment": {
                "source_fields": ["user", "username", "userid", "login"],
                "lookup_table": "users",
                "common_outputs": ["full_name", "department", "manager", "email"],
                "description": "Enrich user information"
            },
            "host_enrichment": {
                "source_fields": ["host", "hostname", "server", "ip", "dest_ip", "src_ip"],
                "lookup_table": "hosts", 
                "common_outputs": ["os", "environment", "datacenter", "owner"],
                "description": "Enrich host/server information"
            },
            "geo_enrichment": {
                "source_fields": ["ip", "src_ip", "dest_ip", "client_ip"],
                "lookup_table": "geoip",
                "common_outputs": ["country", "region", "city", "latitude", "longitude"],
                "description": "Add geographic information for IP addresses"
            },
            "status_enrichment": {
                "source_fields": ["status", "status_code", "http_status", "response_code"],
                "lookup_table": "http_status",
                "common_outputs": ["status_description", "status_category", "is_error"],
                "description": "Enrich HTTP status codes with descriptions"
            },
            "app_enrichment": {
                "source_fields": ["app", "application", "app_name", "service"],
                "lookup_table": "applications",
                "common_outputs": ["owner", "criticality", "support_team", "environment"],
                "description": "Enrich application metadata"
            },
            "threat_enrichment": {
                "source_fields": ["ip", "hash", "domain", "url", "email"],
                "lookup_table": "threat_intel",
                "common_outputs": ["threat_level", "malware_family", "confidence", "source"],
                "description": "Add threat intelligence information"
            }
        }
    
    def _initialize_common_operations(self) -> Dict[str, Dict[str, Any]]:
        """Initialize common lookup operations"""
        return {
            "user_lookup": {
                "pattern": r"(?:get|find|lookup|show).*(?:user|username|employee).*(?:information|details|data)",
                "lookup_table": "users",
                "operation": LookupOperationType.ENRICH,
                "description": "Lookup user information"
            },
            "host_lookup": {
                "pattern": r"(?:get|find|lookup|show).*(?:host|server|machine).*(?:information|details|data)",
                "lookup_table": "hosts",
                "operation": LookupOperationType.ENRICH,
                "description": "Lookup host information"
            },
            "geo_lookup": {
                "pattern": r"(?:get|find|lookup|show).*(?:location|geographic|geo|country|city).*(?:information|data)",
                "lookup_table": "geoip",
                "operation": LookupOperationType.ENRICH,
                "description": "Geographic IP lookup"
            },
            "status_lookup": {
                "pattern": r"(?:get|find|lookup|show).*(?:status|response|http).*(?:code|description|meaning)",
                "lookup_table": "http_status",
                "operation": LookupOperationType.ENRICH,
                "description": "HTTP status code lookup"
            },
            "threat_lookup": {
                "pattern": r"(?:check|lookup|find|identify).*(?:threat|malware|malicious|suspicious).*(?:indicators|intelligence|data)",
                "lookup_table": "threat_intel",
                "operation": LookupOperationType.ENRICH,
                "description": "Threat intelligence lookup"
            }
        }
    
    def detect_lookup_operations(self, query: str) -> List[LookupOperation]:
        """Detect lookup operations from natural language"""
        query_lower = query.lower()
        detected_operations = []
        
        # Check for common lookup operations
        for operation_name, operation_info in self.common_lookup_operations.items():
            if re.search(operation_info["pattern"], query_lower):
                lookup_table = self.predefined_lookups.get(operation_info["lookup_table"])
                if lookup_table:
                    # Detect source fields from query
                    source_fields = self._detect_source_fields(query_lower, lookup_table)
                    
                    lookup_op = LookupOperation(
                        operation_type=operation_info["operation"],
                        lookup_table=lookup_table,
                        source_fields=source_fields or lookup_table.key_fields,
                        target_fields=lookup_table.output_fields[:3],  # Limit to first 3 outputs
                        output_mode="append"
                    )
                    detected_operations.append(lookup_op)
        
        # Check for explicit enrichment patterns
        for pattern in self.lookup_patterns["enrich"]:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                field_name = match.group(1).strip()
                lookup_name = match.group(2).strip()
                
                # Find appropriate lookup table
                lookup_table = self._find_lookup_table(field_name, lookup_name)
                if lookup_table:
                    lookup_op = LookupOperation(
                        operation_type=LookupOperationType.ENRICH,
                        lookup_table=lookup_table,
                        source_fields=[self._normalize_field_name(field_name)],
                        target_fields=lookup_table.output_fields[:3],
                        output_mode="append"
                    )
                    detected_operations.append(lookup_op)
        
        # Check for field-based enrichment
        detected_operations.extend(self._detect_field_enrichment(query_lower))
        
        return detected_operations
    
    def _detect_source_fields(self, query: str, lookup_table: LookupTable) -> List[str]:
        """Detect source fields for lookup operation"""
        detected_fields = []
        
        # Check for explicit field mentions
        for field in lookup_table.key_fields:
            if field in query or field.replace("_", " ") in query:
                detected_fields.append(field)
        
        # Check for field aliases
        field_aliases = {
            "user": ["username", "userid", "login", "user_id"],
            "host": ["hostname", "server", "machine", "host_name"],
            "ip": ["ip_address", "src_ip", "dest_ip", "client_ip"],
            "status": ["status_code", "http_status", "response_code"]
        }
        
        for alias_group, aliases in field_aliases.items():
            if any(alias in query for alias in aliases):
                if alias_group in [field.field_name for field in lookup_table.fields if field.is_key]:
                    detected_fields.append(alias_group)
        
        return detected_fields
    
    def _detect_field_enrichment(self, query: str) -> List[LookupOperation]:
        """Detect field-based enrichment opportunities"""
        operations = []
        
        for enrichment_name, enrichment_info in self.field_enrichment_mappings.items():
            # Check if any source fields are mentioned
            for source_field in enrichment_info["source_fields"]:
                if source_field in query or source_field.replace("_", " ") in query:
                    lookup_table = self.predefined_lookups.get(enrichment_info["lookup_table"])
                    if lookup_table:
                        lookup_op = LookupOperation(
                            operation_type=LookupOperationType.ENRICH,
                            lookup_table=lookup_table,
                            source_fields=[source_field],
                            target_fields=enrichment_info["common_outputs"],
                            output_mode="append"
                        )
                        operations.append(lookup_op)
                        break  # Only add once per enrichment type
        
        return operations
    
    def _find_lookup_table(self, field_name: str, lookup_name: str) -> Optional[LookupTable]:
        """Find appropriate lookup table based on field and lookup names"""
        field_lower = field_name.lower()
        lookup_lower = lookup_name.lower()
        
        # Direct lookup table name match
        if lookup_lower in self.predefined_lookups:
            return self.predefined_lookups[lookup_lower]
        
        # Field-based matching
        if any(term in field_lower for term in ["user", "username", "employee"]):
            return self.predefined_lookups.get("users")
        elif any(term in field_lower for term in ["host", "server", "machine"]):
            return self.predefined_lookups.get("hosts")
        elif any(term in field_lower for term in ["ip", "address"]):
            return self.predefined_lookups.get("geoip")
        elif any(term in field_lower for term in ["status", "code"]):
            return self.predefined_lookups.get("http_status")
        elif any(term in field_lower for term in ["app", "application", "service"]):
            return self.predefined_lookups.get("applications")
        
        # Lookup name-based matching
        if any(term in lookup_lower for term in ["user", "employee", "personnel"]):
            return self.predefined_lookups.get("users")
        elif any(term in lookup_lower for term in ["host", "server", "asset"]):
            return self.predefined_lookups.get("hosts")
        elif any(term in lookup_lower for term in ["geo", "location", "country"]):
            return self.predefined_lookups.get("geoip")
        elif any(term in lookup_lower for term in ["status", "http", "response"]):
            return self.predefined_lookups.get("http_status")
        elif any(term in lookup_lower for term in ["threat", "intelligence", "malware"]):
            return self.predefined_lookups.get("threat_intel")
        
        return None
    
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
        return field_name or "field"
    
    def generate_spl_for_lookup(self, lookup_operation: LookupOperation) -> str:
        """Generate SPL command for lookup operation"""
        lookup_table = lookup_operation.lookup_table
        
        if lookup_table.lookup_type == LookupType.CSV_LOOKUP:
            return self._generate_csv_lookup_spl(lookup_operation)
        elif lookup_table.lookup_type == LookupType.KV_STORE:
            return self._generate_kv_lookup_spl(lookup_operation)
        elif lookup_table.lookup_type == LookupType.EXTERNAL_LOOKUP:
            return self._generate_external_lookup_spl(lookup_operation)
        elif lookup_table.lookup_type == LookupType.AUTOMATIC_LOOKUP:
            return self._generate_automatic_lookup_spl(lookup_operation)
        else:
            return f"# Unsupported lookup type: {lookup_table.lookup_type.value}"
    
    def _generate_csv_lookup_spl(self, lookup_operation: LookupOperation) -> str:
        """Generate SPL for CSV lookup"""
        lookup_table = lookup_operation.lookup_table
        
        # Build lookup command
        lookup_fields = []
        
        # Add source fields
        for i, source_field in enumerate(lookup_operation.source_fields):
            if i < len(lookup_table.key_fields):
                lookup_fields.append(f"{source_field} AS {lookup_table.key_fields[i]}")
            else:
                lookup_fields.append(source_field)
        
        # Add output fields if specified
        if lookup_operation.target_fields:
            output_fields = " OUTPUT " + " ".join(lookup_operation.target_fields)
        else:
            output_fields = ""
        
        # Handle case sensitivity
        case_option = "" if lookup_table.case_sensitive else " case(ignore)"
        
        # Handle max matches
        max_option = f" max_matches={lookup_table.max_matches}" if lookup_table.max_matches != 1 else ""
        
        return f"lookup {lookup_table.name} {' '.join(lookup_fields)}{output_fields}{case_option}{max_option}"
    
    def _generate_kv_lookup_spl(self, lookup_operation: LookupOperation) -> str:
        """Generate SPL for KV store lookup"""
        lookup_table = lookup_operation.lookup_table
        
        # Build inputlookup for KV store
        collection_name = lookup_table.collection_name or lookup_table.name
        
        # Create where clause for key fields
        where_conditions = []
        for i, source_field in enumerate(lookup_operation.source_fields):
            if i < len(lookup_table.key_fields):
                where_conditions.append(f"{lookup_table.key_fields[i]}=${source_field}")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else ""
        
        if lookup_operation.operation_type == LookupOperationType.ENRICH:
            # Use join for enrichment
            return f"join {' '.join(lookup_operation.source_fields)} [| inputlookup {collection_name}" + \
                   (f" | where {where_clause}" if where_clause else "") + "]"
        else:
            return f"lookup {lookup_table.name} {' '.join(lookup_operation.source_fields)}"
    
    def _generate_external_lookup_spl(self, lookup_operation: LookupOperation) -> str:
        """Generate SPL for external lookup"""
        lookup_table = lookup_operation.lookup_table
        
        # Build external lookup command
        external_cmd = lookup_table.external_command
        lookup_fields = " ".join(lookup_operation.source_fields)
        
        if lookup_operation.target_fields:
            output_fields = " OUTPUT " + " ".join(lookup_operation.target_fields)
        else:
            output_fields = ""
        
        return f"lookup {lookup_table.name} {lookup_fields}{output_fields}"
    
    def _generate_automatic_lookup_spl(self, lookup_operation: LookupOperation) -> str:
        """Generate SPL for automatic lookup"""
        # Automatic lookups are handled by Splunk automatically
        return f"# Automatic lookup will be applied for fields: {', '.join(lookup_operation.source_fields)}"
    
    def validate_lookup_operation(self, lookup_operation: LookupOperation) -> Dict[str, Any]:
        """Validate lookup operation"""
        validation = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        lookup_table = lookup_operation.lookup_table
        
        # Check if source fields are valid
        if not lookup_operation.source_fields:
            validation["errors"].append("No source fields specified for lookup")
            validation["valid"] = False
        
        # Check if source fields match key fields
        for source_field in lookup_operation.source_fields:
            if source_field not in [f.field_name for f in lookup_table.fields if f.is_key]:
                validation["warnings"].append(f"Source field '{source_field}' may not match lookup key fields")
        
        # Check target fields
        available_outputs = [f.field_name for f in lookup_table.fields if f.is_output]
        for target_field in lookup_operation.target_fields:
            if target_field not in available_outputs:
                validation["warnings"].append(f"Target field '{target_field}' not available in lookup table")
        
        # Performance suggestions
        if len(lookup_operation.target_fields) > 5:
            validation["suggestions"].append("Consider limiting output fields to improve performance")
        
        if lookup_table.lookup_type == LookupType.EXTERNAL_LOOKUP:
            validation["suggestions"].append("External lookups may have performance impact - consider caching")
        
        if lookup_table.max_matches > 10:
            validation["warnings"].append("High max_matches value may impact performance")
        
        return validation
    
    def optimize_lookup_operation(self, lookup_operation: LookupOperation) -> LookupOperation:
        """Optimize lookup operation for performance"""
        optimized = LookupOperation(
            operation_type=lookup_operation.operation_type,
            lookup_table=lookup_operation.lookup_table,
            source_fields=lookup_operation.source_fields.copy(),
            target_fields=lookup_operation.target_fields.copy(),
            conditions=lookup_operation.conditions.copy(),
            output_mode=lookup_operation.output_mode,
            case_sensitive=lookup_operation.case_sensitive,
            max_matches=lookup_operation.max_matches
        )
        
        # Limit output fields for performance
        if len(optimized.target_fields) > 5:
            optimized.target_fields = optimized.target_fields[:5]
        
        # Optimize max_matches
        if optimized.max_matches > 100:
            optimized.max_matches = 100
        
        # Prefer case-insensitive for better performance
        if optimized.lookup_table.lookup_type == LookupType.CSV_LOOKUP:
            optimized.case_sensitive = False
        
        return optimized
    
    def suggest_lookup_tables(self, query: str, available_fields: List[str] = None) -> List[Dict[str, Any]]:
        """Suggest appropriate lookup tables based on query and available fields"""
        suggestions = []
        query_lower = query.lower()
        available_fields = available_fields or []
        
        for lookup_name, lookup_table in self.predefined_lookups.items():
            suggestion_score = 0
            reasons = []
            
            # Check if lookup table name is mentioned
            if lookup_name in query_lower or lookup_table.description.lower() in query_lower:
                suggestion_score += 10
                reasons.append(f"Lookup table '{lookup_name}' mentioned in query")
            
            # Check for key field matches
            for field in lookup_table.key_fields:
                if field in query_lower or field in available_fields:
                    suggestion_score += 5
                    reasons.append(f"Key field '{field}' found")
            
            # Check for output field requests
            for field in lookup_table.output_fields:
                if field in query_lower:
                    suggestion_score += 3
                    reasons.append(f"Output field '{field}' requested")
            
            # Check for operation type keywords
            if any(word in query_lower for word in ["enrich", "lookup", "join", "add information"]):
                suggestion_score += 2
                reasons.append("Enrichment operation detected")
            
            if suggestion_score > 0:
                suggestions.append({
                    "lookup_table": lookup_name,
                    "score": suggestion_score,
                    "description": lookup_table.description,
                    "reasons": reasons,
                    "key_fields": lookup_table.key_fields,
                    "output_fields": lookup_table.output_fields[:5]  # Limit to first 5
                })
        
        # Sort by score
        suggestions.sort(key=lambda x: x["score"], reverse=True)
        return suggestions[:10]  # Return top 10 suggestions
    
    def get_lookup_table_info(self, lookup_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a lookup table"""
        if lookup_name not in self.predefined_lookups:
            return None
        
        lookup_table = self.predefined_lookups[lookup_name]
        
        return {
            "name": lookup_table.name,
            "type": lookup_table.lookup_type.value,
            "description": lookup_table.description,
            "file_path": lookup_table.file_path,
            "collection_name": lookup_table.collection_name,
            "external_command": lookup_table.external_command,
            "key_fields": lookup_table.key_fields,
            "output_fields": lookup_table.output_fields,
            "case_sensitive": lookup_table.case_sensitive,
            "max_matches": lookup_table.max_matches,
            "match_type": lookup_table.match_type.value,
            "fields": [
                {
                    "name": field.field_name,
                    "type": field.field_type.value,
                    "is_key": field.is_key,
                    "is_output": field.is_output,
                    "description": field.description
                }
                for field in lookup_table.fields
            ]
        }
    
    def get_all_lookup_tables(self) -> Dict[str, Any]:
        """Get information about all available lookup tables"""
        return {
            "lookup_tables": list(self.predefined_lookups.keys()),
            "total_count": len(self.predefined_lookups),
            "by_type": {
                lookup_type.value: [
                    name for name, table in self.predefined_lookups.items()
                    if table.lookup_type == lookup_type
                ]
                for lookup_type in LookupType
            },
            "enrichment_mappings": list(self.field_enrichment_mappings.keys()),
            "common_operations": list(self.common_lookup_operations.keys())
        }


# Global instance
lookup_table_mapper = LookupTableMapper()