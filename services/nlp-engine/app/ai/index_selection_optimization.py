"""
Index Selection Optimization System for SPL Query Enhancement

This module provides intelligent index selection optimization including:
- Index recommendation based on query analysis and field patterns
- Cost-benefit analysis for index selection strategies
- Index performance impact prediction and optimization
- Multi-index query optimization and strategy selection
- Index availability validation and alternative recommendation
- Historical index performance analysis and optimization suggestions
"""

import re
import json
import math
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import uuid

from ..core.logging import get_logger
from .spl_mapping import spl_mapper, SPLCommandType, FieldType

logger = get_logger(__name__)


class IndexSelectionStrategy(Enum):
    """Index selection optimization strategies"""
    SINGLE_INDEX = "single_index"           # Use single most optimal index
    MULTI_INDEX = "multi_index"             # Use multiple indexes with union
    WILDCARD_OPTIMIZED = "wildcard_optimized"  # Optimized wildcard patterns
    TIME_BASED = "time_based"               # Time-based index selection
    FIELD_BASED = "field_based"             # Field presence-based selection
    COST_OPTIMIZED = "cost_optimized"       # Cost-optimized selection
    PERFORMANCE_OPTIMIZED = "performance_optimized"  # Performance-first selection


class IndexCategory(Enum):
    """Index categories for optimization"""
    SECURITY = "security"                   # Security and authentication logs
    WEB = "web"                            # Web server and HTTP logs
    APPLICATION = "application"             # Application and service logs
    NETWORK = "network"                     # Network and infrastructure logs
    SYSTEM = "system"                       # System and OS logs
    DATABASE = "database"                   # Database and transaction logs
    BUSINESS = "business"                   # Business process and workflow logs
    CUSTOM = "custom"                       # Custom application logs


class IndexOptimizationLevel(Enum):
    """Levels of index optimization"""
    BASIC = "basic"                         # Basic index recommendation
    INTERMEDIATE = "intermediate"           # Multi-factor optimization
    ADVANCED = "advanced"                   # Advanced multi-index strategies
    EXPERT = "expert"                       # Expert-level optimization with cost analysis


@dataclass
class IndexMetadata:
    """Index metadata and characteristics"""
    name: str
    category: IndexCategory
    estimated_size: str  # "small", "medium", "large", "very_large"
    data_types: List[str]  # Types of data stored
    common_fields: List[str]  # Common field names
    time_range_typical: str  # Typical time range for queries
    search_patterns: List[str]  # Common search patterns
    performance_score: float  # 0-100 performance score
    cost_score: float  # 0-100 cost efficiency score
    availability_score: float  # 0-100 availability score
    field_coverage: Dict[str, float]  # Field coverage percentages
    query_frequency: float  # How often this index is queried
    
    
@dataclass
class IndexRecommendation:
    """Index selection recommendation"""
    index_name: str
    strategy: IndexSelectionStrategy
    confidence: float  # 0-1 confidence in recommendation
    performance_impact: str  # "excellent", "good", "moderate", "poor"
    cost_impact: str  # "low", "medium", "high"
    field_coverage: float  # 0-100 percentage of required fields covered
    time_coverage: float  # 0-100 percentage of time range covered
    reasoning: str  # Human-readable reasoning
    optimization_suggestions: List[str]
    estimated_improvement: str  # Estimated performance improvement
    implementation_complexity: str  # "easy", "medium", "hard"


@dataclass
class MultiIndexStrategy:
    """Multi-index optimization strategy"""
    primary_indexes: List[str]
    secondary_indexes: List[str] = field(default_factory=list)
    union_strategy: str = "search"  # "search", "multisearch", "append"
    optimization_order: List[str] = field(default_factory=list)
    parallel_execution: bool = False
    cost_benefit_ratio: float = 0.0
    expected_performance_gain: float = 0.0
    complexity_score: float = 0.0
    recommended_spl_pattern: str = ""


@dataclass
class IndexSelectionAnalysis:
    """Comprehensive index selection analysis"""
    query_id: str
    original_spl: str
    natural_query: Optional[str]
    detected_patterns: List[str]
    required_fields: List[str]
    time_range_detected: Optional[str]
    optimization_level: IndexOptimizationLevel
    recommended_strategy: IndexSelectionStrategy
    primary_recommendation: IndexRecommendation
    alternative_recommendations: List[IndexRecommendation] = field(default_factory=list)
    multi_index_strategy: Optional[MultiIndexStrategy] = None
    optimized_spl: str = ""
    confidence_score: float = 0.0
    performance_prediction: Dict[str, Any] = field(default_factory=dict)
    cost_analysis: Dict[str, Any] = field(default_factory=dict)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    analysis_timestamp: datetime = field(default_factory=datetime.now)


class IndexSelectionOptimizer:
    """Intelligent index selection optimization engine"""
    
    def __init__(self):
        self.index_metadata = self._initialize_index_metadata()
        self.optimization_rules = self._initialize_optimization_rules()
        self.field_patterns = self._initialize_field_patterns()
        self.query_patterns = self._initialize_query_patterns()
        
    def _initialize_index_metadata(self) -> Dict[str, IndexMetadata]:
        """Initialize comprehensive index metadata"""
        return {
            # Security Indexes
            "security": IndexMetadata(
                name="security",
                category=IndexCategory.SECURITY,
                estimated_size="large",
                data_types=["authentication", "authorization", "access_control", "audit"],
                common_fields=["user", "src_ip", "dest_ip", "action", "result", "auth_method"],
                time_range_typical="last 7 days",
                search_patterns=["failed login", "authentication", "unauthorized", "security event"],
                performance_score=85.0,
                cost_score=75.0,
                availability_score=95.0,
                field_coverage={"user": 95.0, "src_ip": 90.0, "action": 98.0, "result": 92.0},
                query_frequency=8.5
            ),
            
            "auth": IndexMetadata(
                name="auth",
                category=IndexCategory.SECURITY,
                estimated_size="medium",
                data_types=["login", "logout", "session", "token"],
                common_fields=["user", "session_id", "auth_type", "status", "timestamp"],
                time_range_typical="last 24 hours",
                search_patterns=["login", "logout", "session", "authentication"],
                performance_score=90.0,
                cost_score=85.0,
                availability_score=98.0,
                field_coverage={"user": 98.0, "session_id": 85.0, "status": 95.0},
                query_frequency=9.2
            ),
            
            # Web Indexes
            "web": IndexMetadata(
                name="web",
                category=IndexCategory.WEB,
                estimated_size="very_large",
                data_types=["http_requests", "responses", "access_logs", "error_logs"],
                common_fields=["status", "method", "uri", "response_time", "user_agent", "src_ip"],
                time_range_typical="last 4 hours",
                search_patterns=["http", "status", "response", "web server", "apache", "nginx"],
                performance_score=75.0,
                cost_score=60.0,
                availability_score=92.0,
                field_coverage={"status": 99.0, "method": 98.0, "uri": 95.0, "response_time": 88.0},
                query_frequency=9.8
            ),
            
            "apache": IndexMetadata(
                name="apache",
                category=IndexCategory.WEB,
                estimated_size="large",
                data_types=["apache_access", "apache_error"],
                common_fields=["status", "method", "uri", "bytes", "referer"],
                time_range_typical="last 2 hours",
                search_patterns=["apache", "httpd", "access_log", "error_log"],
                performance_score=88.0,
                cost_score=78.0,
                availability_score=94.0,
                field_coverage={"status": 99.0, "method": 99.0, "uri": 96.0},
                query_frequency=7.5
            ),
            
            # Application Indexes
            "application": IndexMetadata(
                name="application",
                category=IndexCategory.APPLICATION,
                estimated_size="large",
                data_types=["application_logs", "service_logs", "microservices"],
                common_fields=["level", "message", "component", "thread", "exception"],
                time_range_typical="last 6 hours",
                search_patterns=["error", "exception", "application", "service", "component"],
                performance_score=80.0,
                cost_score=70.0,
                availability_score=90.0,
                field_coverage={"level": 95.0, "message": 90.0, "component": 85.0},
                query_frequency=8.8
            ),
            
            # Network Indexes
            "network": IndexMetadata(
                name="network",
                category=IndexCategory.NETWORK,
                estimated_size="very_large",
                data_types=["firewall", "router", "switch", "dns", "dhcp"],
                common_fields=["src_ip", "dest_ip", "src_port", "dest_port", "protocol", "action"],
                time_range_typical="last 1 hour",
                search_patterns=["firewall", "network", "router", "protocol", "bandwidth"],
                performance_score=70.0,
                cost_score=65.0,
                availability_score=88.0,
                field_coverage={"src_ip": 98.0, "dest_ip": 98.0, "protocol": 92.0},
                query_frequency=6.8
            ),
            
            # System Indexes
            "system": IndexMetadata(
                name="system",
                category=IndexCategory.SYSTEM,
                estimated_size="medium",
                data_types=["system_logs", "performance", "monitoring"],
                common_fields=["host", "cpu", "memory", "disk", "process"],
                time_range_typical="last 2 hours",
                search_patterns=["system", "performance", "cpu", "memory", "disk"],
                performance_score=85.0,
                cost_score=80.0,
                availability_score=96.0,
                field_coverage={"host": 99.0, "cpu": 85.0, "memory": 88.0},
                query_frequency=7.2
            ),
            
            # Default/Main Index
            "main": IndexMetadata(
                name="main",
                category=IndexCategory.CUSTOM,
                estimated_size="very_large",
                data_types=["mixed", "default", "catch_all"],
                common_fields=["_time", "host", "source", "sourcetype"],
                time_range_typical="last 24 hours",
                search_patterns=["*", "general", "miscellaneous"],
                performance_score=50.0,
                cost_score=40.0,
                availability_score=99.0,
                field_coverage={"_time": 100.0, "host": 95.0, "source": 90.0},
                query_frequency=5.0
            )
        }
    
    def _initialize_optimization_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize index optimization rules"""
        return {
            "security_patterns": {
                "keywords": ["login", "auth", "security", "failed", "unauthorized", "breach"],
                "preferred_indexes": ["security", "auth"],
                "field_requirements": ["user", "src_ip", "action"],
                "time_sensitivity": "high",
                "optimization_weight": 0.9
            },
            
            "web_patterns": {
                "keywords": ["http", "web", "apache", "nginx", "status", "response"],
                "preferred_indexes": ["web", "apache", "nginx"],
                "field_requirements": ["status", "method", "uri"],
                "time_sensitivity": "medium",
                "optimization_weight": 0.8
            },
            
            "application_patterns": {
                "keywords": ["error", "exception", "application", "service", "debug"],
                "preferred_indexes": ["application", "app"],
                "field_requirements": ["level", "message", "component"],
                "time_sensitivity": "medium",
                "optimization_weight": 0.8
            },
            
            "network_patterns": {
                "keywords": ["network", "firewall", "router", "bandwidth", "protocol"],
                "preferred_indexes": ["network", "firewall"],
                "field_requirements": ["src_ip", "dest_ip", "protocol"],
                "time_sensitivity": "high",
                "optimization_weight": 0.85
            },
            
            "system_patterns": {
                "keywords": ["system", "performance", "cpu", "memory", "disk", "host"],
                "preferred_indexes": ["system", "os"],
                "field_requirements": ["host", "cpu", "memory"],
                "time_sensitivity": "medium",
                "optimization_weight": 0.75
            }
        }
    
    def _initialize_field_patterns(self) -> Dict[str, List[str]]:
        """Initialize field-to-index mapping patterns"""
        return {
            "security_fields": ["user", "src_ip", "dest_ip", "auth_method", "result", "action"],
            "web_fields": ["status", "method", "uri", "response_time", "user_agent", "bytes"],
            "application_fields": ["level", "message", "component", "thread", "exception", "stack_trace"],
            "network_fields": ["src_ip", "dest_ip", "src_port", "dest_port", "protocol", "bytes_in", "bytes_out"],
            "system_fields": ["host", "cpu", "memory", "disk", "process", "pid", "load_avg"],
            "time_fields": ["_time", "timestamp", "event_time", "log_time", "created_at"]
        }
    
    def _initialize_query_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize query pattern analysis rules"""
        return {
            "aggregation_heavy": {
                "pattern": r"stats|chart|timechart|eventstats",
                "index_preference": "smaller_indexes",
                "optimization_strategy": "field_based",
                "performance_impact": "high"
            },
            
            "time_sensitive": {
                "pattern": r"earliest=|latest=|@[hdmy]|last\s+\d+\s+(minute|hour|day)",
                "index_preference": "time_optimized",
                "optimization_strategy": "time_based",
                "performance_impact": "medium"
            },
            
            "field_heavy": {
                "pattern": r"rex|extract|spath|eval",
                "index_preference": "field_rich_indexes",
                "optimization_strategy": "field_based",
                "performance_impact": "medium"
            },
            
            "search_intensive": {
                "pattern": r"\*.*\*|.*\s+OR\s+.*|.*\s+AND\s+.*",
                "index_preference": "optimized_indexes",
                "optimization_strategy": "performance_optimized",
                "performance_impact": "high"
            }
        }
    
    def analyze_index_selection(
        self, 
        spl_query: str, 
        natural_query: Optional[str] = None,
        available_indexes: Optional[List[str]] = None,
        optimization_level: IndexOptimizationLevel = IndexOptimizationLevel.INTERMEDIATE,
        context: Optional[Dict[str, Any]] = None
    ) -> IndexSelectionAnalysis:
        """
        Perform comprehensive index selection analysis
        
        Args:
            spl_query: The SPL query to analyze
            natural_query: Optional natural language query for additional context
            available_indexes: List of available indexes in the environment
            optimization_level: Level of optimization to perform
            context: Additional context for optimization
            
        Returns:
            Comprehensive index selection analysis with recommendations
        """
        query_id = str(uuid.uuid4())
        logger.info(f"Starting index selection analysis for query {query_id}")
        
        try:
            # Analyze current query patterns
            detected_patterns = self._detect_query_patterns(spl_query, natural_query)
            required_fields = self._extract_required_fields(spl_query)
            time_range = self._detect_time_range(spl_query)
            
            # Generate index recommendations
            recommendations = self._generate_index_recommendations(
                spl_query, detected_patterns, required_fields, time_range, available_indexes
            )
            
            # Select optimal strategy
            strategy = self._select_optimization_strategy(
                spl_query, detected_patterns, optimization_level
            )
            
            # Generate primary recommendation
            primary_rec = self._select_primary_recommendation(recommendations, strategy)
            
            # Generate alternative recommendations
            alternatives = [rec for rec in recommendations if rec.index_name != primary_rec.index_name][:3]
            
            # Generate multi-index strategy if applicable
            multi_index_strategy = None
            if optimization_level in [IndexOptimizationLevel.ADVANCED, IndexOptimizationLevel.EXPERT]:
                multi_index_strategy = self._generate_multi_index_strategy(
                    spl_query, recommendations, detected_patterns
                )
            
            # Generate optimized SPL
            optimized_spl = self._generate_optimized_spl(
                spl_query, primary_rec, multi_index_strategy
            )
            
            # Calculate confidence score
            confidence = self._calculate_confidence_score(
                primary_rec, detected_patterns, required_fields
            )
            
            # Generate performance predictions
            performance_prediction = self._predict_performance_impact(
                spl_query, optimized_spl, primary_rec
            )
            
            # Generate cost analysis
            cost_analysis = self._analyze_cost_impact(
                primary_rec, alternatives, multi_index_strategy
            )
            
            # Validate recommendations
            validation_results = self._validate_recommendations(
                primary_rec, alternatives, available_indexes
            )
            
            analysis = IndexSelectionAnalysis(
                query_id=query_id,
                original_spl=spl_query,
                natural_query=natural_query,
                detected_patterns=detected_patterns,
                required_fields=required_fields,
                time_range_detected=time_range,
                optimization_level=optimization_level,
                recommended_strategy=strategy,
                primary_recommendation=primary_rec,
                alternative_recommendations=alternatives,
                multi_index_strategy=multi_index_strategy,
                optimized_spl=optimized_spl,
                confidence_score=confidence,
                performance_prediction=performance_prediction,
                cost_analysis=cost_analysis,
                validation_results=validation_results
            )
            
            logger.info(
                f"Index selection analysis completed",
                query_id=query_id,
                primary_index=primary_rec.index_name,
                confidence=confidence,
                strategy=strategy.value
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Index selection analysis failed: {e}")
            # Return basic fallback analysis
            return self._create_fallback_analysis(query_id, spl_query, natural_query)
    
    def _detect_query_patterns(self, spl_query: str, natural_query: Optional[str] = None) -> List[str]:
        """Detect patterns in the query for index optimization"""
        patterns = []
        
        # Analyze SPL query patterns
        for pattern_name, pattern_info in self.query_patterns.items():
            if re.search(pattern_info["pattern"], spl_query, re.IGNORECASE):
                patterns.append(pattern_name)
        
        # Analyze natural query if provided
        if natural_query:
            query_lower = natural_query.lower()
            for rule_name, rule_info in self.optimization_rules.items():
                for keyword in rule_info["keywords"]:
                    if keyword in query_lower:
                        patterns.append(f"natural_{rule_name}")
                        break
        
        # Detect index-specific patterns in SPL
        if re.search(r'index=(\w+)', spl_query):
            patterns.append("explicit_index")
        
        if re.search(r'sourcetype=', spl_query):
            patterns.append("sourcetype_specified")
        
        if re.search(r'host=', spl_query):
            patterns.append("host_specified")
        
        # Detect query complexity patterns
        join_count = len(re.findall(r'join', spl_query, re.IGNORECASE))
        if join_count > 0:
            patterns.append(f"join_operations_{join_count}")
        
        subsearch_count = len(re.findall(r'\[.*search.*\]', spl_query))
        if subsearch_count > 0:
            patterns.append(f"subsearches_{subsearch_count}")
        
        return patterns
    
    def _extract_required_fields(self, spl_query: str) -> List[str]:
        """Extract fields that are required by the query"""
        fields = []
        
        # Extract explicit field references
        field_patterns = [
            r'by\s+(\w+)',  # group by fields
            r'eval\s+(\w+)\s*=',  # eval fields
            r'rex.*field=(\w+)',  # rex field references
            r'where\s+(\w+)',  # where clause fields
            r'sort\s+[+-]?(\w+)',  # sort fields
            r'stats.*(\w+)\(',  # stats function fields
        ]
        
        for pattern in field_patterns:
            matches = re.findall(pattern, spl_query, re.IGNORECASE)
            fields.extend(matches)
        
        # Extract fields from search terms
        search_terms = re.findall(r'(\w+)=', spl_query)
        fields.extend(search_terms)
        
        # Remove duplicates and common non-field terms
        fields = list(set(fields))
        common_terms = ['search', 'stats', 'eval', 'where', 'sort', 'head', 'tail', 'top']
        fields = [f for f in fields if f.lower() not in common_terms]
        
        return fields
    
    def _detect_time_range(self, spl_query: str) -> Optional[str]:
        """Detect time range specifications in the query"""
        time_patterns = [
            r'earliest=([^\s]+)',
            r'latest=([^\s]+)',
            r'@[hdmy]',
            r'last\s+\d+\s+(minute|hour|day|week|month)'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, spl_query, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _generate_index_recommendations(
        self,
        spl_query: str,
        patterns: List[str],
        required_fields: List[str],
        time_range: Optional[str],
        available_indexes: Optional[List[str]]
    ) -> List[IndexRecommendation]:
        """Generate index recommendations based on query analysis"""
        recommendations = []
        
        # Score each available index
        indexes_to_evaluate = available_indexes or list(self.index_metadata.keys())
        
        for index_name in indexes_to_evaluate:
            if index_name not in self.index_metadata:
                continue
                
            metadata = self.index_metadata[index_name]
            
            # Calculate field coverage score
            field_coverage = self._calculate_field_coverage(required_fields, metadata)
            
            # Calculate pattern match score
            pattern_score = self._calculate_pattern_match_score(patterns, metadata)
            
            # Calculate time compatibility score
            time_score = self._calculate_time_compatibility_score(time_range, metadata)
            
            # Calculate overall confidence
            confidence = (field_coverage * 0.4 + pattern_score * 0.4 + time_score * 0.2) / 100
            
            # Determine performance impact
            performance_impact = self._determine_performance_impact(
                metadata.performance_score, field_coverage, pattern_score
            )
            
            # Determine cost impact
            cost_impact = self._determine_cost_impact(metadata.cost_score, metadata.estimated_size)
            
            # Generate reasoning
            reasoning = self._generate_recommendation_reasoning(
                metadata, field_coverage, pattern_score, time_score, patterns
            )
            
            # Generate optimization suggestions
            suggestions = self._generate_optimization_suggestions(spl_query, metadata)
            
            # Estimate improvement
            improvement = self._estimate_improvement(confidence, metadata.performance_score)
            
            recommendation = IndexRecommendation(
                index_name=index_name,
                strategy=IndexSelectionStrategy.SINGLE_INDEX,
                confidence=confidence,
                performance_impact=performance_impact,
                cost_impact=cost_impact,
                field_coverage=field_coverage,
                time_coverage=time_score,
                reasoning=reasoning,
                optimization_suggestions=suggestions,
                estimated_improvement=improvement,
                implementation_complexity="easy" if confidence > 0.8 else "medium"
            )
            
            recommendations.append(recommendation)
        
        # Sort by confidence score
        recommendations.sort(key=lambda x: x.confidence, reverse=True)
        
        return recommendations
    
    def _calculate_field_coverage(self, required_fields: List[str], metadata: IndexMetadata) -> float:
        """Calculate how well an index covers the required fields"""
        if not required_fields:
            return 80.0  # Default score if no specific fields required
        
        covered_fields = 0
        total_weight = 0
        
        for field in required_fields:
            weight = 1.0
            coverage = 0.0
            
            # Check direct field coverage
            if field in metadata.field_coverage:
                coverage = metadata.field_coverage[field]
            elif field in metadata.common_fields:
                coverage = 85.0  # Assume good coverage for common fields
            else:
                # Check field category patterns
                for category, category_fields in self.field_patterns.items():
                    if field in category_fields:
                        if metadata.category.value in category:
                            coverage = 70.0  # Moderate coverage for category match
                        break
            
            covered_fields += coverage * weight
            total_weight += weight
        
        return covered_fields / total_weight if total_weight > 0 else 0.0
    
    def _calculate_pattern_match_score(self, patterns: List[str], metadata: IndexMetadata) -> float:
        """Calculate how well an index matches the detected patterns"""
        score = 0.0
        pattern_count = len(patterns)
        
        if pattern_count == 0:
            return 60.0  # Default score if no patterns detected
        
        # Check optimization rule matches
        for pattern in patterns:
            if pattern.startswith("natural_"):
                rule_name = pattern.replace("natural_", "")
                if rule_name in self.optimization_rules:
                    rule = self.optimization_rules[rule_name]
                    if metadata.name in rule["preferred_indexes"]:
                        score += rule["optimization_weight"] * 100
            
            # Check search pattern matches
            for search_pattern in metadata.search_patterns:
                if search_pattern in " ".join(patterns):
                    score += 20.0
        
        # Normalize score
        max_possible_score = pattern_count * 100
        return min(score / max_possible_score * 100, 100.0) if max_possible_score > 0 else 0.0
    
    def _calculate_time_compatibility_score(self, time_range: Optional[str], metadata: IndexMetadata) -> float:
        """Calculate time range compatibility score"""
        if not time_range:
            return 75.0  # Default score if no time range specified
        
        # Simple heuristic based on typical time ranges
        if "minute" in time_range or "@m" in time_range:
            if "minute" in metadata.time_range_typical or "hour" in metadata.time_range_typical:
                return 95.0
            return 70.0
        elif "hour" in time_range or "@h" in time_range:
            if "hour" in metadata.time_range_typical:
                return 90.0
            elif "day" in metadata.time_range_typical:
                return 80.0
            return 65.0
        elif "day" in time_range or "@d" in time_range:
            if "day" in metadata.time_range_typical:
                return 85.0
            return 75.0
        
        return 70.0  # Default for other time ranges
    
    def _determine_performance_impact(self, perf_score: float, field_coverage: float, pattern_score: float) -> str:
        """Determine the expected performance impact"""
        combined_score = (perf_score + field_coverage + pattern_score) / 3
        
        if combined_score >= 85:
            return "excellent"
        elif combined_score >= 70:
            return "good"
        elif combined_score >= 55:
            return "moderate"
        else:
            return "poor"
    
    def _determine_cost_impact(self, cost_score: float, estimated_size: str) -> str:
        """Determine the cost impact of using this index"""
        size_impact = {
            "small": 1.0,
            "medium": 0.8,
            "large": 0.6,
            "very_large": 0.4
        }
        
        adjusted_score = cost_score * size_impact.get(estimated_size, 0.5)
        
        if adjusted_score >= 70:
            return "low"
        elif adjusted_score >= 50:
            return "medium"
        else:
            return "high"
    
    def _generate_recommendation_reasoning(
        self,
        metadata: IndexMetadata,
        field_coverage: float,
        pattern_score: float,
        time_score: float,
        patterns: List[str]
    ) -> str:
        """Generate human-readable reasoning for the recommendation"""
        reasons = []
        
        # Field coverage reasoning
        if field_coverage >= 80:
            reasons.append(f"Excellent field coverage ({field_coverage:.1f}%)")
        elif field_coverage >= 60:
            reasons.append(f"Good field coverage ({field_coverage:.1f}%)")
        else:
            reasons.append(f"Limited field coverage ({field_coverage:.1f}%)")
        
        # Pattern matching reasoning
        if pattern_score >= 80:
            reasons.append("Strong pattern match for query type")
        elif pattern_score >= 60:
            reasons.append("Moderate pattern match")
        
        # Category-specific reasoning
        if metadata.category == IndexCategory.SECURITY:
            reasons.append("Optimized for security and authentication queries")
        elif metadata.category == IndexCategory.WEB:
            reasons.append("Specialized for web server and HTTP log analysis")
        elif metadata.category == IndexCategory.APPLICATION:
            reasons.append("Designed for application log analysis")
        
        # Performance reasoning
        if metadata.performance_score >= 85:
            reasons.append("High-performance index with fast query execution")
        
        return ". ".join(reasons) + "."
    
    def _generate_optimization_suggestions(self, spl_query: str, metadata: IndexMetadata) -> List[str]:
        """Generate specific optimization suggestions for the index"""
        suggestions = []
        
        # Check if time range is specified
        if not re.search(r'earliest=|latest=', spl_query):
            suggestions.append(f"Add specific time range appropriate for {metadata.name} index (typically {metadata.time_range_typical})")
        
        # Check for field optimization opportunities
        if metadata.common_fields:
            missing_fields = [f for f in metadata.common_fields[:3] if f not in spl_query]
            if missing_fields:
                suggestions.append(f"Consider filtering by common fields: {', '.join(missing_fields)}")
        
        # Index-specific suggestions
        if metadata.category == IndexCategory.SECURITY:
            suggestions.append("Use specific authentication event types for better performance")
        elif metadata.category == IndexCategory.WEB:
            suggestions.append("Filter by HTTP status codes or request methods when possible")
        elif metadata.category == IndexCategory.APPLICATION:
            suggestions.append("Filter by log level (ERROR, WARN, INFO) to reduce data volume")
        
        return suggestions
    
    def _estimate_improvement(self, confidence: float, perf_score: float) -> str:
        """Estimate the performance improvement from using this index"""
        improvement_factor = confidence * (perf_score / 100)
        
        if improvement_factor >= 0.8:
            return "70-90% faster execution"
        elif improvement_factor >= 0.6:
            return "40-70% faster execution"
        elif improvement_factor >= 0.4:
            return "20-40% faster execution"
        elif improvement_factor >= 0.2:
            return "10-20% faster execution"
        else:
            return "Minimal improvement expected"
    
    def _select_optimization_strategy(
        self,
        spl_query: str,
        patterns: List[str],
        optimization_level: IndexOptimizationLevel
    ) -> IndexSelectionStrategy:
        """Select the optimal index selection strategy"""
        
        # Count complexity indicators
        join_count = len(re.findall(r'join', spl_query, re.IGNORECASE))
        subsearch_count = len(re.findall(r'\[.*search.*\]', spl_query))
        
        # Strategy selection based on optimization level and query complexity
        if optimization_level == IndexOptimizationLevel.BASIC:
            return IndexSelectionStrategy.SINGLE_INDEX
        
        elif optimization_level == IndexOptimizationLevel.INTERMEDIATE:
            if join_count > 0 or subsearch_count > 0:
                return IndexSelectionStrategy.MULTI_INDEX
            elif "time_sensitive" in patterns:
                return IndexSelectionStrategy.TIME_BASED
            else:
                return IndexSelectionStrategy.FIELD_BASED
        
        elif optimization_level == IndexOptimizationLevel.ADVANCED:
            if join_count > 1 or subsearch_count > 1:
                return IndexSelectionStrategy.MULTI_INDEX
            elif "aggregation_heavy" in patterns:
                return IndexSelectionStrategy.PERFORMANCE_OPTIMIZED
            else:
                return IndexSelectionStrategy.FIELD_BASED
        
        else:  # EXPERT level
            if join_count > 0 or subsearch_count > 0:
                return IndexSelectionStrategy.COST_OPTIMIZED
            else:
                return IndexSelectionStrategy.PERFORMANCE_OPTIMIZED
    
    def _select_primary_recommendation(
        self,
        recommendations: List[IndexRecommendation],
        strategy: IndexSelectionStrategy
    ) -> IndexRecommendation:
        """Select the primary recommendation based on strategy"""
        if not recommendations:
            # Return fallback recommendation
            return IndexRecommendation(
                index_name="main",
                strategy=strategy,
                confidence=0.3,
                performance_impact="moderate",
                cost_impact="medium",
                field_coverage=50.0,
                time_coverage=60.0,
                reasoning="Fallback to main index due to lack of specific recommendations",
                optimization_suggestions=["Add more specific search criteria"],
                estimated_improvement="Minimal improvement expected",
                implementation_complexity="easy"
            )
        
        # Strategy-specific selection
        if strategy == IndexSelectionStrategy.COST_OPTIMIZED:
            return min(recommendations, key=lambda x: x.cost_impact == "low")
        elif strategy == IndexSelectionStrategy.PERFORMANCE_OPTIMIZED:
            return max(recommendations, key=lambda x: x.performance_impact == "excellent")
        else:
            return recommendations[0]  # Highest confidence
    
    def _generate_multi_index_strategy(
        self,
        spl_query: str,
        recommendations: List[IndexRecommendation],
        patterns: List[str]
    ) -> Optional[MultiIndexStrategy]:
        """Generate multi-index optimization strategy for complex queries"""
        if len(recommendations) < 2:
            return None
        
        # Select primary indexes (top 2-3 recommendations)
        primary_indexes = [rec.index_name for rec in recommendations[:2]]
        secondary_indexes = [rec.index_name for rec in recommendations[2:4]]
        
        # Determine union strategy based on query patterns
        join_count = len(re.findall(r'join', spl_query, re.IGNORECASE))
        subsearch_count = len(re.findall(r'\[.*search.*\]', spl_query))
        
        if join_count > 0:
            union_strategy = "multisearch"
            parallel_execution = True
        elif subsearch_count > 0:
            union_strategy = "append"
            parallel_execution = False
        else:
            union_strategy = "search"
            parallel_execution = True
        
        # Calculate optimization metrics
        avg_confidence = sum(rec.confidence for rec in recommendations[:2]) / 2
        cost_benefit_ratio = avg_confidence / len(primary_indexes)
        expected_performance_gain = min(avg_confidence * 1.5, 1.0)
        complexity_score = len(primary_indexes) * 0.3 + len(secondary_indexes) * 0.1
        
        # Generate recommended SPL pattern
        if union_strategy == "multisearch":
            pattern = f"| multisearch [search index={primary_indexes[0]} ] [search index={primary_indexes[1]} ]"
        elif union_strategy == "append":
            pattern = f"search index={primary_indexes[0]} | append [search index={primary_indexes[1]} ]"
        else:
            pattern = f"search index={','.join(primary_indexes)}"
        
        return MultiIndexStrategy(
            primary_indexes=primary_indexes,
            secondary_indexes=secondary_indexes,
            union_strategy=union_strategy,
            optimization_order=primary_indexes + secondary_indexes,
            parallel_execution=parallel_execution,
            cost_benefit_ratio=cost_benefit_ratio,
            expected_performance_gain=expected_performance_gain,
            complexity_score=complexity_score,
            recommended_spl_pattern=pattern
        )
    
    def _generate_optimized_spl(
        self,
        original_spl: str,
        primary_rec: IndexRecommendation,
        multi_index_strategy: Optional[MultiIndexStrategy]
    ) -> str:
        """Generate optimized SPL with recommended index selection"""
        
        # Use multi-index strategy if available and beneficial
        if multi_index_strategy and multi_index_strategy.cost_benefit_ratio > 0.7:
            # Apply multi-index pattern
            if "search" in original_spl:
                optimized = re.sub(
                    r'search\s+(?:index=\w+\s+)?',
                    multi_index_strategy.recommended_spl_pattern + " ",
                    original_spl,
                    count=1
                )
            else:
                optimized = multi_index_strategy.recommended_spl_pattern + " " + original_spl
        else:
            # Apply single index optimization
            if re.search(r'index=\w+', original_spl):
                # Replace existing index
                optimized = re.sub(
                    r'index=\w+',
                    f'index={primary_rec.index_name}',
                    original_spl
                )
            else:
                # Add index specification
                if original_spl.strip().startswith("search"):
                    optimized = original_spl.replace(
                        "search",
                        f"search index={primary_rec.index_name}",
                        1
                    )
                else:
                    optimized = f"search index={primary_rec.index_name} " + original_spl
        
        # Apply additional optimizations from recommendations
        if primary_rec.optimization_suggestions:
            for suggestion in primary_rec.optimization_suggestions:
                if "time range" in suggestion and not re.search(r'earliest=|latest=', optimized):
                    optimized += " earliest=-24h@h"
        
        return optimized
    
    def _calculate_confidence_score(
        self,
        primary_rec: IndexRecommendation,
        patterns: List[str],
        required_fields: List[str]
    ) -> float:
        """Calculate overall confidence in the index selection"""
        base_confidence = primary_rec.confidence
        
        # Adjust based on pattern strength
        pattern_boost = min(len(patterns) * 0.05, 0.2)
        
        # Adjust based on field coverage
        if primary_rec.field_coverage >= 80:
            field_boost = 0.1
        elif primary_rec.field_coverage >= 60:
            field_boost = 0.05
        else:
            field_boost = -0.1
        
        # Adjust based on implementation complexity
        complexity_penalty = 0.0
        if primary_rec.implementation_complexity == "hard":
            complexity_penalty = 0.1
        elif primary_rec.implementation_complexity == "medium":
            complexity_penalty = 0.05
        
        final_confidence = min(base_confidence + pattern_boost + field_boost - complexity_penalty, 1.0)
        return max(final_confidence, 0.0)
    
    def _predict_performance_impact(
        self,
        original_spl: str,
        optimized_spl: str,
        primary_rec: IndexRecommendation
    ) -> Dict[str, Any]:
        """Predict the performance impact of the optimization"""
        return {
            "query_complexity_reduction": "20-40%" if "index=" not in original_spl else "5-15%",
            "execution_time_improvement": primary_rec.estimated_improvement,
            "resource_usage_reduction": "Medium" if primary_rec.performance_impact in ["good", "excellent"] else "Low",
            "data_volume_reduction": "30-60%" if primary_rec.field_coverage > 70 else "10-30%",
            "confidence": primary_rec.confidence
        }
    
    def _analyze_cost_impact(
        self,
        primary_rec: IndexRecommendation,
        alternatives: List[IndexRecommendation],
        multi_index_strategy: Optional[MultiIndexStrategy]
    ) -> Dict[str, Any]:
        """Analyze the cost impact of the optimization"""
        analysis = {
            "primary_cost_impact": primary_rec.cost_impact,
            "alternative_costs": [alt.cost_impact for alt in alternatives],
            "cost_benefit_ratio": "High" if primary_rec.cost_impact == "low" and primary_rec.performance_impact in ["good", "excellent"] else "Medium"
        }
        
        if multi_index_strategy:
            analysis["multi_index_cost"] = "Higher complexity but potentially better performance"
            analysis["recommended_approach"] = "Multi-index" if multi_index_strategy.cost_benefit_ratio > 0.7 else "Single-index"
        
        return analysis
    
    def _validate_recommendations(
        self,
        primary_rec: IndexRecommendation,
        alternatives: List[IndexRecommendation],
        available_indexes: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Validate the recommendations against available indexes"""
        validation = {
            "primary_available": True,
            "alternatives_available": [],
            "missing_indexes": [],
            "fallback_required": False
        }
        
        if available_indexes:
            validation["primary_available"] = primary_rec.index_name in available_indexes
            
            for alt in alternatives:
                validation["alternatives_available"].append(alt.index_name in available_indexes)
            
            recommended_indexes = [primary_rec.index_name] + [alt.index_name for alt in alternatives]
            validation["missing_indexes"] = [idx for idx in recommended_indexes if idx not in available_indexes]
            
            validation["fallback_required"] = not validation["primary_available"]
        
        return validation
    
    def _create_fallback_analysis(
        self,
        query_id: str,
        spl_query: str,
        natural_query: Optional[str]
    ) -> IndexSelectionAnalysis:
        """Create a fallback analysis when the main analysis fails"""
        fallback_rec = IndexRecommendation(
            index_name="main",
            strategy=IndexSelectionStrategy.SINGLE_INDEX,
            confidence=0.3,
            performance_impact="moderate",
            cost_impact="medium",
            field_coverage=50.0,
            time_coverage=60.0,
            reasoning="Fallback recommendation due to analysis failure",
            optimization_suggestions=["Review query syntax and try again"],
            estimated_improvement="Baseline performance",
            implementation_complexity="easy"
        )
        
        return IndexSelectionAnalysis(
            query_id=query_id,
            original_spl=spl_query,
            natural_query=natural_query,
            detected_patterns=["fallback"],
            required_fields=[],
            time_range_detected=None,
            optimization_level=IndexOptimizationLevel.BASIC,
            recommended_strategy=IndexSelectionStrategy.SINGLE_INDEX,
            primary_recommendation=fallback_rec,
            alternative_recommendations=[],
            multi_index_strategy=None,
            optimized_spl=spl_query,
            confidence_score=0.3,
            performance_prediction={"note": "Fallback analysis - limited optimization"},
            cost_analysis={"note": "Standard cost profile"},
            validation_results={"note": "Fallback validation"}
        )
    
    def get_optimization_documentation(self) -> Dict[str, Any]:
        """Get comprehensive documentation for index optimization"""
        return {
            "index_categories": {cat.value: cat.name for cat in IndexCategory},
            "optimization_strategies": {strategy.value: strategy.name for strategy in IndexSelectionStrategy},
            "optimization_levels": {level.value: level.name for level in IndexOptimizationLevel},
            "available_indexes": list(self.index_metadata.keys()),
            "field_patterns": self.field_patterns,
            "optimization_rules": {
                rule_name: {
                    "keywords": rule["keywords"],
                    "preferred_indexes": rule["preferred_indexes"],
                    "optimization_weight": rule["optimization_weight"]
                }
                for rule_name, rule in self.optimization_rules.items()
            },
            "best_practices": [
                "Always specify an index when possible to avoid scanning all indexes",
                "Use time ranges appropriate for your analysis needs",
                "Filter by common fields early in the search pipeline",
                "Consider field coverage when selecting indexes",
                "Use multi-index strategies for complex queries spanning multiple data types",
                "Monitor query performance and adjust index selection based on results",
                "Validate index availability in your environment before implementation"
            ]
        }


# Initialize global index selection optimizer
index_selection_optimizer = IndexSelectionOptimizer()