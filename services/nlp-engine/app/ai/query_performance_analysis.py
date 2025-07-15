"""
Query Performance Analysis System for SPL Optimization

This module provides comprehensive query performance analysis and optimization including:
- Query complexity analysis and scoring
- Performance bottleneck detection and optimization suggestions
- Resource usage estimation and capacity planning
- Index selection optimization and recommendation
- Time range optimization and efficiency analysis
- Query execution plan analysis and improvement recommendations
"""

import re
import math
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime, timedelta

from ..core.logging import get_logger
from .spl_mapping import spl_mapper, SPLCommandType, FieldType

logger = get_logger(__name__)


class PerformanceLevel(Enum):
    """Query performance levels"""
    EXCELLENT = "excellent"     # Optimal performance, no issues
    GOOD = "good"              # Good performance, minor optimizations possible
    MODERATE = "moderate"      # Moderate performance, some optimization needed
    POOR = "poor"              # Poor performance, significant optimization required
    CRITICAL = "critical"      # Critical performance issues, major optimization needed


class OptimizationType(Enum):
    """Types of query optimizations"""
    INDEX_SELECTION = "index_selection"        # Index selection and specification
    TIME_RANGE = "time_range"                  # Time range optimization
    FIELD_EXTRACTION = "field_extraction"     # Field extraction efficiency
    AGGREGATION = "aggregation"               # Aggregation optimization
    SUBSEARCH = "subsearch"                   # Subsearch optimization
    JOIN_OPTIMIZATION = "join_optimization"   # Join and lookup optimization
    REGEX_OPTIMIZATION = "regex_optimization" # Regex pattern optimization
    COMMAND_ORDER = "command_order"           # Command ordering optimization
    FILTERING = "filtering"                   # Filtering and where clauses
    MEMORY_USAGE = "memory_usage"             # Memory usage optimization


class BottleneckType(Enum):
    """Types of performance bottlenecks"""
    DISK_IO = "disk_io"                       # Disk I/O intensive operations
    CPU_INTENSIVE = "cpu_intensive"           # CPU intensive operations
    MEMORY_USAGE = "memory_usage"             # High memory usage
    NETWORK_IO = "network_io"                 # Network I/O intensive
    INDEX_SCANNING = "index_scanning"         # Full index scanning
    FIELD_EXTRACTION = "field_extraction"    # Heavy field extraction
    REGEX_PROCESSING = "regex_processing"     # Complex regex operations
    AGGREGATION = "aggregation"               # Heavy aggregation operations
    SORTING = "sorting"                       # Large dataset sorting
    JOIN_OPERATIONS = "join_operations"       # Complex join operations


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    name: str
    value: float
    unit: str
    description: str
    threshold_good: float
    threshold_poor: float
    current_level: PerformanceLevel
    suggestions: List[str] = field(default_factory=list)


@dataclass
class OptimizationSuggestion:
    """Query optimization suggestion"""
    optimization_type: OptimizationType
    priority: int  # 1-10, 10 being highest priority
    impact: str  # "low", "medium", "high"
    description: str
    before_spl: str
    after_spl: str
    expected_improvement: str
    implementation_complexity: str  # "easy", "medium", "hard"
    estimated_time_savings: str


@dataclass
class PerformanceBottleneck:
    """Identified performance bottleneck"""
    bottleneck_type: BottleneckType
    severity: PerformanceLevel
    description: str
    affected_commands: List[str]
    impact_score: float  # 0-100
    optimization_suggestions: List[OptimizationSuggestion] = field(default_factory=list)


@dataclass
class ResourceEstimate:
    """Resource usage estimation"""
    cpu_usage: str  # "low", "medium", "high"
    memory_usage: str  # "low", "medium", "high"
    disk_io: str  # "low", "medium", "high"
    network_io: str  # "low", "medium", "high"
    estimated_execution_time: str
    estimated_data_volume: str
    concurrent_capacity: int  # Estimated number of concurrent queries
    scaling_recommendations: List[str] = field(default_factory=list)


@dataclass
class QueryComplexityAnalysis:
    """Query complexity analysis results"""
    complexity_score: float  # 0-100
    complexity_level: PerformanceLevel
    command_count: int
    join_count: int
    subsearch_count: int
    regex_count: int
    aggregation_count: int
    field_extraction_count: int
    complexity_factors: List[str]
    simplification_suggestions: List[str] = field(default_factory=list)


@dataclass
class PerformanceAnalysisResult:
    """Complete performance analysis result"""
    query_id: str
    spl_query: str
    overall_performance: PerformanceLevel
    complexity_analysis: QueryComplexityAnalysis
    performance_metrics: List[PerformanceMetric]
    bottlenecks: List[PerformanceBottleneck]
    optimization_suggestions: List[OptimizationSuggestion]
    resource_estimates: ResourceEstimate
    performance_score: float  # 0-100
    confidence: float  # 0-1.0
    analysis_timestamp: datetime
    estimated_improvement_potential: str  # Percentage improvement possible


class QueryPerformanceAnalyzer:
    """Comprehensive query performance analysis system"""
    
    def __init__(self):
        self.command_weights = self._initialize_command_weights()
        self.optimization_patterns = self._initialize_optimization_patterns()
        self.bottleneck_indicators = self._initialize_bottleneck_indicators()
        self.performance_thresholds = self._initialize_performance_thresholds()
        self.index_patterns = self._initialize_index_patterns()
        
    def _initialize_command_weights(self) -> Dict[str, float]:
        """Initialize command complexity weights"""
        return {
            # Lightweight commands
            "search": 1.0,
            "where": 1.2,
            "eval": 1.5,
            "fields": 1.0,
            "table": 1.0,
            "head": 0.8,
            "tail": 0.8,
            
            # Medium complexity commands
            "stats": 3.0,
            "chart": 3.5,
            "timechart": 4.0,
            "sort": 2.5,
            "dedup": 2.8,
            "transaction": 5.0,
            "eventstats": 4.5,
            "streamstats": 3.8,
            
            # Heavy commands
            "join": 8.0,
            "append": 6.0,
            "union": 5.5,
            "lookup": 4.0,
            "inputlookup": 3.0,
            "subsearch": 7.0,
            "map": 9.0,
            "foreach": 4.5,
            
            # Very heavy commands
            "multisearch": 9.5,
            "dbconnect": 8.5,
            "script": 10.0,
            "collect": 7.5,
            "summary": 8.0
        }
    
    def _initialize_optimization_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize optimization patterns"""
        return {
            "inefficient_wildcards": {
                "pattern": r'\*\w+|\w+\*',
                "severity": "high",
                "description": "Inefficient wildcard usage",
                "suggestion": "Use specific field names instead of wildcards when possible"
            },
            "missing_index": {
                "pattern": r'^search\s+(?!index=)',
                "severity": "critical",
                "description": "No index specified",
                "suggestion": "Specify index= to limit search scope"
            },
            "broad_time_range": {
                "pattern": r'earliest=-\d+[mh]@|latest=now',
                "severity": "medium",
                "description": "Broad time range specified",
                "suggestion": "Use more specific time ranges to reduce data volume"
            },
            "multiple_stats": {
                "pattern": r'stats.*\|.*stats',
                "severity": "medium",
                "description": "Multiple stats commands",
                "suggestion": "Combine stats operations when possible"
            },
            "inefficient_regex": {
                "pattern": r'rex\s+".*\.\*.*"',
                "severity": "high",
                "description": "Inefficient regex patterns",
                "suggestion": "Optimize regex patterns to be more specific"
            },
            "unnecessary_sort": {
                "pattern": r'sort.*\|\s*head\s+\d+',
                "severity": "medium",
                "description": "Sort before head command",
                "suggestion": "Use top command instead of sort | head"
            },
            "heavy_aggregation": {
                "pattern": r'stats.*by\s+\w+,\s*\w+,\s*\w+',
                "severity": "medium",
                "description": "High cardinality aggregation",
                "suggestion": "Reduce number of grouping fields or pre-filter data"
            }
        }
    
    def _initialize_bottleneck_indicators(self) -> Dict[BottleneckType, Dict[str, Any]]:
        """Initialize bottleneck detection indicators"""
        return {
            BottleneckType.DISK_IO: {
                "commands": ["search", "inputlookup", "outputlookup", "collect"],
                "patterns": [r'index=\*', r'sourcetype=\*'],
                "weight": 8.0,
                "description": "High disk I/O operations"
            },
            BottleneckType.CPU_INTENSIVE: {
                "commands": ["rex", "replace", "eval", "foreach"],
                "patterns": [r'rex.*mode=sed', r'eval.*case\('],
                "weight": 7.0,
                "description": "CPU intensive operations"
            },
            BottleneckType.MEMORY_USAGE: {
                "commands": ["sort", "transaction", "stats", "join"],
                "patterns": [r'sort.*\d{4,}', r'transaction.*maxspan=\d+h'],
                "weight": 9.0,
                "description": "High memory usage operations"
            },
            BottleneckType.NETWORK_IO: {
                "commands": ["dbconnect", "lookup", "multisearch"],
                "patterns": [r'dbconnect.*query=', r'lookup.*external'],
                "weight": 6.0,
                "description": "Network I/O intensive operations"
            },
            BottleneckType.INDEX_SCANNING: {
                "commands": ["search"],
                "patterns": [r'search\s+(?!index=)', r'index=\*'],
                "weight": 10.0,
                "description": "Full index scanning"
            },
            BottleneckType.FIELD_EXTRACTION: {
                "commands": ["rex", "extract", "spath"],
                "patterns": [r'rex.*field=\w+.*".*\.\*', r'spath.*path='],
                "weight": 5.0,
                "description": "Heavy field extraction"
            },
            BottleneckType.REGEX_PROCESSING: {
                "commands": ["rex", "regex", "replace"],
                "patterns": [r'rex.*".*\.\*.*\.\*"', r'regex.*\.\*.*\.\*'],
                "weight": 7.5,
                "description": "Complex regex processing"
            },
            BottleneckType.AGGREGATION: {
                "commands": ["stats", "chart", "timechart", "eventstats"],
                "patterns": [r'stats.*by.*,.*,.*,', r'timechart.*span=\d+s'],
                "weight": 6.5,
                "description": "Heavy aggregation operations"
            },
            BottleneckType.SORTING: {
                "commands": ["sort"],
                "patterns": [r'sort.*-.*\+.*-', r'sort.*\d{4,}'],
                "weight": 8.0,
                "description": "Large dataset sorting"
            },
            BottleneckType.JOIN_OPERATIONS: {
                "commands": ["join", "append", "union"],
                "patterns": [r'join.*type=outer', r'join.*max=\d{4,}'],
                "weight": 9.0,
                "description": "Complex join operations"
            }
        }
    
    def _initialize_performance_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Initialize performance thresholds"""
        return {
            "complexity_score": {
                "excellent": 20.0,
                "good": 40.0,
                "moderate": 60.0,
                "poor": 80.0
            },
            "command_count": {
                "excellent": 3.0,
                "good": 6.0,
                "moderate": 10.0,
                "poor": 15.0
            },
            "estimated_execution_time": {
                "excellent": 5.0,  # seconds
                "good": 15.0,
                "moderate": 60.0,
                "poor": 300.0
            },
            "memory_usage_score": {
                "excellent": 20.0,
                "good": 40.0,
                "moderate": 60.0,
                "poor": 80.0
            }
        }
    
    def _initialize_index_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize index optimization patterns"""
        return {
            "security_logs": {
                "patterns": ["failed login", "authentication", "security", "auth", "login"],
                "recommended_indexes": ["security", "auth", "windows", "linux"],
                "time_range_suggestion": "last 24 hours for real-time, last 7 days for analysis"
            },
            "web_logs": {
                "patterns": ["http", "web", "apache", "nginx", "status", "response"],
                "recommended_indexes": ["web", "apache", "nginx", "access"],
                "time_range_suggestion": "last 1 hour for monitoring, last 24 hours for analysis"
            },
            "application_logs": {
                "patterns": ["application", "app", "error", "exception", "debug"],
                "recommended_indexes": ["application", "app", "java", "python"],
                "time_range_suggestion": "last 4 hours for troubleshooting"
            },
            "network_logs": {
                "patterns": ["network", "firewall", "router", "switch", "bandwidth"],
                "recommended_indexes": ["network", "firewall", "cisco", "juniper"],
                "time_range_suggestion": "last 15 minutes for real-time monitoring"
            },
            "system_logs": {
                "patterns": ["system", "cpu", "memory", "disk", "performance"],
                "recommended_indexes": ["system", "os", "perfmon", "vmware"],
                "time_range_suggestion": "last 1 hour for monitoring, last 24 hours for capacity planning"
            }
        }
    
    def analyze_query_performance(self, spl_query: str, context: Optional[Dict[str, Any]] = None) -> PerformanceAnalysisResult:
        """Analyze query performance comprehensively"""
        try:
            query_id = context.get("query_id", f"query_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            logger.info(f"Starting performance analysis for query {query_id}")
            
            # Perform individual analyses
            complexity_analysis = self._analyze_query_complexity(spl_query)
            performance_metrics = self._calculate_performance_metrics(spl_query, complexity_analysis)
            bottlenecks = self._detect_bottlenecks(spl_query)
            optimization_suggestions = self._generate_optimization_suggestions(spl_query, bottlenecks, complexity_analysis)
            resource_estimates = self._estimate_resource_usage(spl_query, complexity_analysis)
            
            # Calculate overall performance score
            performance_score = self._calculate_overall_performance_score(
                complexity_analysis, performance_metrics, bottlenecks
            )
            
            # Determine overall performance level
            overall_performance = self._determine_performance_level(performance_score)
            
            # Calculate confidence based on analysis completeness
            confidence = self._calculate_confidence(spl_query, complexity_analysis)
            
            # Estimate improvement potential
            improvement_potential = self._estimate_improvement_potential(optimization_suggestions, bottlenecks)
            
            result = PerformanceAnalysisResult(
                query_id=query_id,
                spl_query=spl_query,
                overall_performance=overall_performance,
                complexity_analysis=complexity_analysis,
                performance_metrics=performance_metrics,
                bottlenecks=bottlenecks,
                optimization_suggestions=optimization_suggestions,
                resource_estimates=resource_estimates,
                performance_score=performance_score,
                confidence=confidence,
                analysis_timestamp=datetime.now(),
                estimated_improvement_potential=improvement_potential
            )
            
            logger.info(
                f"Performance analysis completed for query {query_id}",
                performance_score=performance_score,
                overall_performance=overall_performance.value,
                bottleneck_count=len(bottlenecks),
                optimization_count=len(optimization_suggestions)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            raise
    
    def _analyze_query_complexity(self, spl_query: str) -> QueryComplexityAnalysis:
        """Analyze query complexity"""
        # Count different command types
        command_count = len(re.findall(r'\|\s*\w+', spl_query)) + 1  # +1 for initial search
        join_count = len(re.findall(r'\|\s*join', spl_query, re.IGNORECASE))
        subsearch_count = len(re.findall(r'\[.*search.*\]', spl_query))
        regex_count = len(re.findall(r'rex|regex|replace', spl_query, re.IGNORECASE))
        aggregation_count = len(re.findall(r'stats|chart|timechart|eventstats', spl_query, re.IGNORECASE))
        field_extraction_count = len(re.findall(r'rex|extract|spath', spl_query, re.IGNORECASE))
        
        # Calculate complexity score
        complexity_score = 0.0
        complexity_factors = []
        
        # Command count factor
        command_weight = min(command_count * 3, 20)
        complexity_score += command_weight
        if command_count > 5:
            complexity_factors.append(f"High command count ({command_count})")
        
        # Join complexity
        if join_count > 0:
            join_weight = join_count * 15
            complexity_score += join_weight
            complexity_factors.append(f"Join operations ({join_count})")
        
        # Subsearch complexity
        if subsearch_count > 0:
            subsearch_weight = subsearch_count * 12
            complexity_score += subsearch_weight
            complexity_factors.append(f"Subsearches ({subsearch_count})")
        
        # Regex complexity
        if regex_count > 0:
            regex_weight = regex_count * 8
            complexity_score += regex_weight
            complexity_factors.append(f"Regex operations ({regex_count})")
        
        # Aggregation complexity
        if aggregation_count > 0:
            agg_weight = aggregation_count * 6
            complexity_score += agg_weight
            complexity_factors.append(f"Aggregation operations ({aggregation_count})")
        
        # Field extraction complexity
        if field_extraction_count > 0:
            extract_weight = field_extraction_count * 4
            complexity_score += extract_weight
            complexity_factors.append(f"Field extraction operations ({field_extraction_count})")
        
        # Determine complexity level
        if complexity_score <= 20:
            complexity_level = PerformanceLevel.EXCELLENT
        elif complexity_score <= 40:
            complexity_level = PerformanceLevel.GOOD
        elif complexity_score <= 60:
            complexity_level = PerformanceLevel.MODERATE
        elif complexity_score <= 80:
            complexity_level = PerformanceLevel.POOR
        else:
            complexity_level = PerformanceLevel.CRITICAL
        
        # Generate simplification suggestions
        simplification_suggestions = []
        if command_count > 10:
            simplification_suggestions.append("Consider breaking query into multiple searches")
        if join_count > 2:
            simplification_suggestions.append("Review join operations for consolidation opportunities")
        if subsearch_count > 1:
            simplification_suggestions.append("Consider using lookup tables instead of subsearches")
        if regex_count > 3:
            simplification_suggestions.append("Optimize regex patterns for better performance")
        
        return QueryComplexityAnalysis(
            complexity_score=complexity_score,
            complexity_level=complexity_level,
            command_count=command_count,
            join_count=join_count,
            subsearch_count=subsearch_count,
            regex_count=regex_count,
            aggregation_count=aggregation_count,
            field_extraction_count=field_extraction_count,
            complexity_factors=complexity_factors,
            simplification_suggestions=simplification_suggestions
        )
    
    def _calculate_performance_metrics(self, spl_query: str, complexity_analysis: QueryComplexityAnalysis) -> List[PerformanceMetric]:
        """Calculate individual performance metrics"""
        metrics = []
        
        # Query complexity metric
        complexity_metric = PerformanceMetric(
            name="Query Complexity",
            value=complexity_analysis.complexity_score,
            unit="score",
            description="Overall query complexity score (lower is better)",
            threshold_good=40.0,
            threshold_poor=80.0,
            current_level=complexity_analysis.complexity_level,
            suggestions=complexity_analysis.simplification_suggestions
        )
        metrics.append(complexity_metric)
        
        # Command efficiency metric
        command_efficiency = 100 - min(complexity_analysis.command_count * 5, 50)
        command_level = self._score_to_performance_level(command_efficiency, reverse=True)
        command_metric = PerformanceMetric(
            name="Command Efficiency",
            value=command_efficiency,
            unit="percentage",
            description="Efficiency of command usage (higher is better)",
            threshold_good=70.0,
            threshold_poor=40.0,
            current_level=command_level,
            suggestions=["Reduce number of pipeline commands", "Combine operations where possible"]
        )
        metrics.append(command_metric)
        
        # Index specification metric
        has_index = bool(re.search(r'index=\w+', spl_query))
        index_score = 100 if has_index else 0
        index_level = PerformanceLevel.EXCELLENT if has_index else PerformanceLevel.CRITICAL
        index_metric = PerformanceMetric(
            name="Index Specification",
            value=index_score,
            unit="percentage",
            description="Whether specific indexes are specified",
            threshold_good=100.0,
            threshold_poor=0.0,
            current_level=index_level,
            suggestions=[] if has_index else ["Specify index= to limit search scope"]
        )
        metrics.append(index_metric)
        
        # Time range efficiency metric
        has_time_range = bool(re.search(r'earliest=|latest=', spl_query))
        time_score = 90 if has_time_range else 20
        time_level = self._score_to_performance_level(time_score, reverse=True)
        time_metric = PerformanceMetric(
            name="Time Range Efficiency",
            value=time_score,
            unit="percentage",
            description="Efficiency of time range specification",
            threshold_good=80.0,
            threshold_poor=40.0,
            current_level=time_level,
            suggestions=[] if has_time_range else ["Add specific time range to limit data volume"]
        )
        metrics.append(time_metric)
        
        # Resource usage estimation metric
        resource_score = max(20, 100 - complexity_analysis.complexity_score)
        resource_level = self._score_to_performance_level(resource_score, reverse=True)
        resource_metric = PerformanceMetric(
            name="Estimated Resource Usage",
            value=resource_score,
            unit="efficiency",
            description="Estimated resource efficiency (higher is better)",
            threshold_good=70.0,
            threshold_poor=40.0,
            current_level=resource_level,
            suggestions=["Optimize complex operations", "Add filters early in pipeline"]
        )
        metrics.append(resource_metric)
        
        return metrics
    
    def _detect_bottlenecks(self, spl_query: str) -> List[PerformanceBottleneck]:
        """Detect performance bottlenecks"""
        bottlenecks = []
        
        for bottleneck_type, indicators in self.bottleneck_indicators.items():
            impact_score = 0.0
            affected_commands = []
            
            # Check for problematic commands
            for command in indicators["commands"]:
                if re.search(rf'\|\s*{command}\b', spl_query, re.IGNORECASE):
                    impact_score += indicators["weight"]
                    affected_commands.append(command)
            
            # Check for problematic patterns
            for pattern in indicators["patterns"]:
                if re.search(pattern, spl_query, re.IGNORECASE):
                    impact_score += indicators["weight"] * 0.5
            
            if impact_score > 0:
                # Determine severity based on impact score
                if impact_score >= 20:
                    severity = PerformanceLevel.CRITICAL
                elif impact_score >= 15:
                    severity = PerformanceLevel.POOR
                elif impact_score >= 10:
                    severity = PerformanceLevel.MODERATE
                elif impact_score >= 5:
                    severity = PerformanceLevel.GOOD
                else:
                    severity = PerformanceLevel.EXCELLENT
                
                # Generate optimization suggestions for this bottleneck
                optimization_suggestions = self._generate_bottleneck_optimizations(
                    bottleneck_type, affected_commands, spl_query
                )
                
                bottleneck = PerformanceBottleneck(
                    bottleneck_type=bottleneck_type,
                    severity=severity,
                    description=indicators["description"],
                    affected_commands=affected_commands,
                    impact_score=min(impact_score, 100),
                    optimization_suggestions=optimization_suggestions
                )
                bottlenecks.append(bottleneck)
        
        # Sort bottlenecks by impact score
        bottlenecks.sort(key=lambda x: x.impact_score, reverse=True)
        return bottlenecks
    
    def _generate_optimization_suggestions(self, spl_query: str, bottlenecks: List[PerformanceBottleneck], 
                                         complexity_analysis: QueryComplexityAnalysis) -> List[OptimizationSuggestion]:
        """Generate comprehensive optimization suggestions"""
        suggestions = []
        
        # Index selection optimization
        if not re.search(r'index=\w+', spl_query):
            suggestions.append(OptimizationSuggestion(
                optimization_type=OptimizationType.INDEX_SELECTION,
                priority=10,
                impact="high",
                description="Add specific index specification to limit search scope",
                before_spl=spl_query.split('|')[0].strip(),
                after_spl=f"index=main {spl_query.split('|')[0].strip()}",
                expected_improvement="50-80% faster execution",
                implementation_complexity="easy",
                estimated_time_savings="Significant reduction in search time"
            ))
        
        # Time range optimization
        if not re.search(r'earliest=|latest=', spl_query):
            suggestions.append(OptimizationSuggestion(
                optimization_type=OptimizationType.TIME_RANGE,
                priority=9,
                impact="high",
                description="Add specific time range to reduce data volume",
                before_spl=spl_query.split('|')[0].strip(),
                after_spl=f"{spl_query.split('|')[0].strip()} earliest=-24h@h",
                expected_improvement="30-60% faster execution",
                implementation_complexity="easy",
                estimated_time_savings="Moderate reduction in search time"
            ))
        
        # Command ordering optimization
        if re.search(r'sort.*\|\s*head', spl_query, re.IGNORECASE):
            suggestions.append(OptimizationSuggestion(
                optimization_type=OptimizationType.COMMAND_ORDER,
                priority=7,
                impact="medium",
                description="Replace sort | head with top command for better performance",
                before_spl=re.search(r'sort[^|]*\|\s*head[^|]*', spl_query, re.IGNORECASE).group(),
                after_spl="top 10 field_name",
                expected_improvement="20-40% faster execution",
                implementation_complexity="easy",
                estimated_time_savings="Moderate improvement"
            ))
        
        # Join optimization
        if complexity_analysis.join_count > 0:
            suggestions.append(OptimizationSuggestion(
                optimization_type=OptimizationType.JOIN_OPTIMIZATION,
                priority=8,
                impact="high",
                description="Consider using lookup tables instead of joins for static data",
                before_spl="| join field_name [subsearch]",
                after_spl="| lookup lookup_table field_name OUTPUT other_fields",
                expected_improvement="40-70% faster execution",
                implementation_complexity="medium",
                estimated_time_savings="Significant improvement for large datasets"
            ))
        
        # Aggregation optimization
        if complexity_analysis.aggregation_count > 2:
            suggestions.append(OptimizationSuggestion(
                optimization_type=OptimizationType.AGGREGATION,
                priority=6,
                impact="medium",
                description="Combine multiple aggregation operations",
                before_spl="| stats count | stats sum(count)",
                after_spl="| stats count sum(count)",
                expected_improvement="15-30% faster execution",
                implementation_complexity="medium",
                estimated_time_savings="Moderate improvement"
            ))
        
        # Add bottleneck-specific suggestions
        for bottleneck in bottlenecks:
            suggestions.extend(bottleneck.optimization_suggestions)
        
        # Sort suggestions by priority
        suggestions.sort(key=lambda x: x.priority, reverse=True)
        return suggestions[:10]  # Return top 10 suggestions
    
    def _generate_bottleneck_optimizations(self, bottleneck_type: BottleneckType, 
                                         affected_commands: List[str], spl_query: str) -> List[OptimizationSuggestion]:
        """Generate optimizations for specific bottleneck types"""
        suggestions = []
        
        if bottleneck_type == BottleneckType.REGEX_PROCESSING:
            suggestions.append(OptimizationSuggestion(
                optimization_type=OptimizationType.REGEX_OPTIMIZATION,
                priority=8,
                impact="high",
                description="Optimize regex patterns to be more specific",
                before_spl='rex field=message "(?<error>.*error.*)"',
                after_spl='rex field=message "(?<error>\\w+\\s+error)"',
                expected_improvement="30-50% faster regex processing",
                implementation_complexity="medium",
                estimated_time_savings="Significant for regex-heavy queries"
            ))
        
        elif bottleneck_type == BottleneckType.MEMORY_USAGE:
            suggestions.append(OptimizationSuggestion(
                optimization_type=OptimizationType.MEMORY_USAGE,
                priority=9,
                impact="high",
                description="Add filters early to reduce memory usage",
                before_spl="search * | stats count by field1, field2, field3",
                after_spl="search field1=value | stats count by field1, field2",
                expected_improvement="40-70% reduction in memory usage",
                implementation_complexity="easy",
                estimated_time_savings="Prevents memory-related slowdowns"
            ))
        
        elif bottleneck_type == BottleneckType.DISK_IO:
            suggestions.append(OptimizationSuggestion(
                optimization_type=OptimizationType.INDEX_SELECTION,
                priority=10,
                impact="high",
                description="Specify indexes to reduce disk I/O",
                before_spl="search *",
                after_spl="search index=main OR index=security",
                expected_improvement="60-80% reduction in disk I/O",
                implementation_complexity="easy",
                estimated_time_savings="Major improvement for large datasets"
            ))
        
        return suggestions
    
    def _estimate_resource_usage(self, spl_query: str, complexity_analysis: QueryComplexityAnalysis) -> ResourceEstimate:
        """Estimate resource usage for the query"""
        # Base resource usage on complexity
        complexity_factor = complexity_analysis.complexity_score / 100.0
        
        # CPU usage estimation
        cpu_usage = "low"
        if complexity_analysis.regex_count > 2 or complexity_analysis.field_extraction_count > 3:
            cpu_usage = "high"
        elif complexity_analysis.regex_count > 0 or complexity_analysis.aggregation_count > 2:
            cpu_usage = "medium"
        
        # Memory usage estimation
        memory_usage = "low"
        if complexity_analysis.join_count > 1 or complexity_analysis.aggregation_count > 3:
            memory_usage = "high"
        elif complexity_analysis.join_count > 0 or complexity_analysis.aggregation_count > 1:
            memory_usage = "medium"
        
        # Disk I/O estimation
        has_index = bool(re.search(r'index=\w+', spl_query))
        disk_io = "low" if has_index else "high"
        if complexity_analysis.subsearch_count > 0:
            disk_io = "high"
        
        # Network I/O estimation
        network_io = "low"
        if re.search(r'lookup.*external|dbconnect', spl_query, re.IGNORECASE):
            network_io = "high"
        elif re.search(r'lookup', spl_query, re.IGNORECASE):
            network_io = "medium"
        
        # Execution time estimation
        base_time = 5  # seconds
        execution_time = base_time * (1 + complexity_factor * 10)
        if execution_time < 10:
            time_estimate = f"{execution_time:.1f} seconds"
        elif execution_time < 300:
            time_estimate = f"{execution_time/60:.1f} minutes"
        else:
            time_estimate = f"{execution_time/3600:.1f} hours"
        
        # Data volume estimation
        has_time_range = bool(re.search(r'earliest=|latest=', spl_query))
        if has_index and has_time_range:
            data_volume = "Small to Medium (optimized)"
        elif has_index or has_time_range:
            data_volume = "Medium to Large"
        else:
            data_volume = "Very Large (unoptimized)"
        
        # Concurrent capacity estimation
        if complexity_factor < 0.3:
            concurrent_capacity = 50
        elif complexity_factor < 0.6:
            concurrent_capacity = 20
        else:
            concurrent_capacity = 5
        
        # Scaling recommendations
        scaling_recommendations = []
        if memory_usage == "high":
            scaling_recommendations.append("Consider increasing search head memory")
        if cpu_usage == "high":
            scaling_recommendations.append("Consider adding more search peers")
        if disk_io == "high":
            scaling_recommendations.append("Optimize index configuration and storage")
        if concurrent_capacity < 10:
            scaling_recommendations.append("Limit concurrent execution of this query type")
        
        return ResourceEstimate(
            cpu_usage=cpu_usage,
            memory_usage=memory_usage,
            disk_io=disk_io,
            network_io=network_io,
            estimated_execution_time=time_estimate,
            estimated_data_volume=data_volume,
            concurrent_capacity=concurrent_capacity,
            scaling_recommendations=scaling_recommendations
        )
    
    def _calculate_overall_performance_score(self, complexity_analysis: QueryComplexityAnalysis,
                                           performance_metrics: List[PerformanceMetric],
                                           bottlenecks: List[PerformanceBottleneck]) -> float:
        """Calculate overall performance score"""
        # Start with base score
        score = 100.0
        
        # Penalize based on complexity
        score -= min(complexity_analysis.complexity_score, 50)
        
        # Penalize based on bottlenecks
        for bottleneck in bottlenecks:
            if bottleneck.severity == PerformanceLevel.CRITICAL:
                score -= 20
            elif bottleneck.severity == PerformanceLevel.POOR:
                score -= 15
            elif bottleneck.severity == PerformanceLevel.MODERATE:
                score -= 10
            elif bottleneck.severity == PerformanceLevel.GOOD:
                score -= 5
        
        # Factor in metrics
        metric_avg = sum(m.value for m in performance_metrics if m.unit == "percentage") / max(len([m for m in performance_metrics if m.unit == "percentage"]), 1)
        score = (score + metric_avg) / 2
        
        return max(0.0, min(100.0, score))
    
    def _determine_performance_level(self, performance_score: float) -> PerformanceLevel:
        """Determine performance level from score"""
        if performance_score >= 80:
            return PerformanceLevel.EXCELLENT
        elif performance_score >= 65:
            return PerformanceLevel.GOOD
        elif performance_score >= 45:
            return PerformanceLevel.MODERATE
        elif performance_score >= 25:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.CRITICAL
    
    def _score_to_performance_level(self, score: float, reverse: bool = False) -> PerformanceLevel:
        """Convert numeric score to performance level"""
        if reverse:  # Higher score is better
            if score >= 80:
                return PerformanceLevel.EXCELLENT
            elif score >= 65:
                return PerformanceLevel.GOOD
            elif score >= 45:
                return PerformanceLevel.MODERATE
            elif score >= 25:
                return PerformanceLevel.POOR
            else:
                return PerformanceLevel.CRITICAL
        else:  # Lower score is better
            if score <= 20:
                return PerformanceLevel.EXCELLENT
            elif score <= 40:
                return PerformanceLevel.GOOD
            elif score <= 60:
                return PerformanceLevel.MODERATE
            elif score <= 80:
                return PerformanceLevel.POOR
            else:
                return PerformanceLevel.CRITICAL
    
    def _calculate_confidence(self, spl_query: str, complexity_analysis: QueryComplexityAnalysis) -> float:
        """Calculate confidence in the analysis"""
        confidence = 0.8  # Base confidence
        
        # Increase confidence for well-structured queries
        if re.search(r'index=\w+', spl_query):
            confidence += 0.1
        if re.search(r'earliest=|latest=', spl_query):
            confidence += 0.05
        
        # Decrease confidence for very complex queries
        if complexity_analysis.complexity_score > 80:
            confidence -= 0.2
        elif complexity_analysis.complexity_score > 60:
            confidence -= 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _estimate_improvement_potential(self, optimization_suggestions: List[OptimizationSuggestion],
                                      bottlenecks: List[PerformanceBottleneck]) -> str:
        """Estimate potential improvement percentage"""
        if not optimization_suggestions and not bottlenecks:
            return "5-10% (already well optimized)"
        
        high_impact_count = len([s for s in optimization_suggestions if s.impact == "high"])
        critical_bottlenecks = len([b for b in bottlenecks if b.severity == PerformanceLevel.CRITICAL])
        
        if critical_bottlenecks > 2 or high_impact_count > 3:
            return "70-90% (major optimization opportunity)"
        elif critical_bottlenecks > 0 or high_impact_count > 1:
            return "40-70% (significant optimization opportunity)"
        elif high_impact_count > 0 or len(optimization_suggestions) > 2:
            return "20-40% (moderate optimization opportunity)"
        else:
            return "10-20% (minor optimization opportunity)"
    
    def suggest_index_optimization(self, natural_query: str) -> Dict[str, Any]:
        """Suggest optimal indexes based on natural language query"""
        query_lower = natural_query.lower()
        
        for category, info in self.index_patterns.items():
            for pattern in info["patterns"]:
                if pattern in query_lower:
                    return {
                        "category": category,
                        "recommended_indexes": info["recommended_indexes"],
                        "time_range_suggestion": info["time_range_suggestion"],
                        "confidence": 0.8,
                        "reasoning": f"Query contains '{pattern}' indicating {category} analysis"
                    }
        
        # Default suggestion
        return {
            "category": "general",
            "recommended_indexes": ["main", "_internal"],
            "time_range_suggestion": "last 24 hours",
            "confidence": 0.3,
            "reasoning": "Generic recommendation for unspecified query type"
        }
    
    def get_optimization_documentation(self) -> Dict[str, Any]:
        """Get comprehensive optimization documentation"""
        return {
            "optimization_types": {ot.value: ot.name for ot in OptimizationType},
            "performance_levels": {pl.value: pl.name for pl in PerformanceLevel},
            "bottleneck_types": {bt.value: bt.name for bt in BottleneckType},
            "command_weights": self.command_weights,
            "optimization_patterns": self.optimization_patterns,
            "performance_thresholds": self.performance_thresholds,
            "best_practices": [
                "Always specify index= to limit search scope",
                "Use specific time ranges instead of broad searches",
                "Place filters early in the search pipeline",
                "Use lookup tables instead of joins when possible",
                "Optimize regex patterns to be as specific as possible",
                "Use top command instead of sort | head",
                "Combine multiple stats operations when possible",
                "Use summary indexing for frequently run expensive searches"
            ]
        }


# Global instance
query_performance_analyzer = QueryPerformanceAnalyzer()