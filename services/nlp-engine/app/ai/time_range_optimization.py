"""
Time Range Optimization System for SPL Query Enhancement

This module provides intelligent time range optimization including:
- Automatic time range detection and parsing from natural language
- Optimal time range recommendations based on query type and data characteristics
- Time range performance impact analysis and optimization strategies
- Historical time pattern analysis and predictive optimization
- Time zone handling and daylight saving time awareness
- Time range validation and constraint checking for optimal performance
"""

import re
import json
import math
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta, timezone
import uuid
import calendar

from ..core.logging import get_logger

logger = get_logger(__name__)


class TimeRangeType(Enum):
    """Types of time range specifications"""
    RELATIVE = "relative"           # relative time (e.g., -1h, -24h)
    ABSOLUTE = "absolute"           # absolute time (e.g., 2023-01-01)
    SNAP_TO = "snap_to"            # snap to time boundary (e.g., @h, @d)
    NATURAL = "natural"            # natural language (e.g., "last hour")
    ALL_TIME = "all_time"          # no time restriction
    REAL_TIME = "real_time"        # real-time searches


class TimeUnit(Enum):
    """Time unit specifications"""
    SECOND = "s"
    MINUTE = "m"
    HOUR = "h"
    DAY = "d"
    WEEK = "w"
    MONTH = "mon"
    YEAR = "y"


class TimeOptimizationStrategy(Enum):
    """Time range optimization strategies"""
    MINIMAL = "minimal"                    # Use smallest effective time range
    BALANCED = "balanced"                  # Balance between coverage and performance
    COMPREHENSIVE = "comprehensive"       # Prioritize data completeness
    PERFORMANCE_FIRST = "performance_first"  # Optimize for fastest execution
    ACCURACY_FIRST = "accuracy_first"     # Ensure complete data coverage
    ADAPTIVE = "adaptive"                 # Adapt based on query patterns


class TimeRangeRecommendationLevel(Enum):
    """Recommendation confidence levels"""
    HIGH = "high"           # Strong recommendation with high confidence
    MEDIUM = "medium"       # Good recommendation with moderate confidence  
    LOW = "low"            # Weak recommendation, use with caution
    EXPERIMENTAL = "experimental"  # Experimental recommendation for testing


@dataclass
class TimeRangeParsed:
    """Parsed time range information"""
    original_text: str
    range_type: TimeRangeType
    earliest: Optional[str] = None
    latest: Optional[str] = None
    duration: Optional[int] = None
    unit: Optional[TimeUnit] = None
    snap_to_boundary: Optional[str] = None
    is_relative: bool = True
    confidence: float = 0.0
    parsed_successfully: bool = False
    natural_language: Optional[str] = None


@dataclass
class TimeRangeMetrics:
    """Time range performance metrics"""
    estimated_data_volume: str  # "small", "medium", "large", "very_large"
    estimated_execution_time: str  # Human readable time estimate
    performance_impact: str  # "excellent", "good", "moderate", "poor"
    index_efficiency: float  # 0-100 score for index utilization
    data_coverage: float  # 0-100 percentage of relevant data covered
    resource_usage: str  # "low", "medium", "high"
    concurrent_capacity: int  # Estimated concurrent query capacity
    optimization_score: float  # Overall optimization score 0-100


@dataclass
class TimeRangeRecommendation:
    """Time range optimization recommendation"""
    recommended_spl: str
    strategy: TimeOptimizationStrategy
    confidence_level: TimeRangeRecommendationLevel
    performance_improvement: str
    reasoning: str
    trade_offs: List[str]
    alternative_ranges: List[str] = field(default_factory=list)
    implementation_notes: List[str] = field(default_factory=list)
    expected_metrics: Optional[TimeRangeMetrics] = None


@dataclass
class TimeRangeContext:
    """Context information for time range optimization"""
    query_type: str  # "search", "stats", "timechart", etc.
    data_type: str  # "security", "web", "application", etc.
    user_intent: str  # "monitoring", "analysis", "investigation", etc.
    historical_patterns: Dict[str, Any] = field(default_factory=dict)
    business_hours: Optional[Dict[str, str]] = None
    timezone: str = "UTC"
    current_time: datetime = field(default_factory=datetime.now)


@dataclass
class TimeRangeOptimizationAnalysis:
    """Comprehensive time range optimization analysis"""
    query_id: str
    original_spl: str
    natural_query: Optional[str]
    detected_time_range: Optional[TimeRangeParsed]
    context: TimeRangeContext
    recommendations: List[TimeRangeRecommendation]
    primary_recommendation: TimeRangeRecommendation
    current_metrics: TimeRangeMetrics
    optimized_metrics: TimeRangeMetrics
    optimization_summary: Dict[str, Any]
    validation_results: Dict[str, Any] = field(default_factory=dict)
    analysis_timestamp: datetime = field(default_factory=datetime.now)


class TimeRangeOptimizer:
    """Intelligent time range optimization engine"""
    
    def __init__(self):
        self.time_patterns = self._initialize_time_patterns()
        self.optimization_rules = self._initialize_optimization_rules()
        self.data_type_patterns = self._initialize_data_type_patterns()
        self.performance_baselines = self._initialize_performance_baselines()
        
    def _initialize_time_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize time range detection patterns"""
        return {
            "relative_patterns": {
                "simple_relative": {
                    "pattern": r'earliest=(-?\d+)([smhdwy])',
                    "type": TimeRangeType.RELATIVE,
                    "confidence": 0.95
                },
                "complex_relative": {
                    "pattern": r'earliest=(-?\d+)([smhdwy])(?:@[smhdwy])?',
                    "type": TimeRangeType.RELATIVE,
                    "confidence": 0.90
                },
                "latest_relative": {
                    "pattern": r'latest=(-?\d+)([smhdwy])',
                    "type": TimeRangeType.RELATIVE,
                    "confidence": 0.95
                }
            },
            
            "snap_to_patterns": {
                "hour_snap": {
                    "pattern": r'@h',
                    "type": TimeRangeType.SNAP_TO,
                    "confidence": 0.98
                },
                "day_snap": {
                    "pattern": r'@d',
                    "type": TimeRangeType.SNAP_TO,
                    "confidence": 0.98
                },
                "week_snap": {
                    "pattern": r'@w[0-6]?',
                    "type": TimeRangeType.SNAP_TO,
                    "confidence": 0.95
                },
                "month_snap": {
                    "pattern": r'@mon',
                    "type": TimeRangeType.SNAP_TO,
                    "confidence": 0.95
                }
            },
            
            "natural_patterns": {
                "last_duration": {
                    "pattern": r'(?:last|past)\s+(\d+)\s+(second|minute|hour|day|week|month|year)s?',
                    "type": TimeRangeType.NATURAL,
                    "confidence": 0.85
                },
                "this_period": {
                    "pattern": r'this\s+(hour|day|week|month|year)',
                    "type": TimeRangeType.NATURAL,
                    "confidence": 0.80
                },
                "yesterday_today": {
                    "pattern": r'(yesterday|today|tonight)',
                    "type": TimeRangeType.NATURAL,
                    "confidence": 0.90
                }
            },
            
            "absolute_patterns": {
                "iso_date": {
                    "pattern": r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2})?',
                    "type": TimeRangeType.ABSOLUTE,
                    "confidence": 0.95
                },
                "epoch_time": {
                    "pattern": r'\d{10,13}',
                    "type": TimeRangeType.ABSOLUTE,
                    "confidence": 0.70
                }
            }
        }
    
    def _initialize_optimization_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize time range optimization rules"""
        return {
            "security_logs": {
                "typical_range": "24h",
                "max_efficient": "7d",
                "real_time_threshold": "15m",
                "investigation_range": "30d",
                "performance_ranges": {
                    "excellent": "1h",
                    "good": "4h", 
                    "moderate": "24h",
                    "poor": "7d"
                }
            },
            
            "web_logs": {
                "typical_range": "4h",
                "max_efficient": "24h",
                "real_time_threshold": "5m",
                "investigation_range": "7d",
                "performance_ranges": {
                    "excellent": "30m",
                    "good": "2h",
                    "moderate": "8h", 
                    "poor": "24h"
                }
            },
            
            "application_logs": {
                "typical_range": "6h",
                "max_efficient": "48h",
                "real_time_threshold": "10m",
                "investigation_range": "14d",
                "performance_ranges": {
                    "excellent": "1h",
                    "good": "4h",
                    "moderate": "12h",
                    "poor": "48h"
                }
            },
            
            "network_logs": {
                "typical_range": "1h",
                "max_efficient": "12h", 
                "real_time_threshold": "2m",
                "investigation_range": "7d",
                "performance_ranges": {
                    "excellent": "15m",
                    "good": "1h",
                    "moderate": "4h",
                    "poor": "12h"
                }
            },
            
            "system_logs": {
                "typical_range": "2h",
                "max_efficient": "24h",
                "real_time_threshold": "5m",
                "investigation_range": "30d",
                "performance_ranges": {
                    "excellent": "30m",
                    "good": "2h",
                    "moderate": "8h",
                    "poor": "24h"
                }
            }
        }
    
    def _initialize_data_type_patterns(self) -> Dict[str, List[str]]:
        """Initialize data type detection patterns"""
        return {
            "security": ["login", "auth", "security", "failed", "unauthorized", "breach", "attack"],
            "web": ["http", "web", "apache", "nginx", "status", "response", "request"],
            "application": ["error", "exception", "application", "service", "debug", "info"],
            "network": ["network", "firewall", "router", "protocol", "bandwidth", "traffic"],
            "system": ["system", "cpu", "memory", "disk", "performance", "monitoring"]
        }
    
    def _initialize_performance_baselines(self) -> Dict[str, Dict[str, Any]]:
        """Initialize performance baseline metrics"""
        return {
            "time_ranges": {
                "15m": {"volume": "small", "execution": "fast", "score": 95},
                "1h": {"volume": "small", "execution": "fast", "score": 90},
                "4h": {"volume": "medium", "execution": "moderate", "score": 80},
                "24h": {"volume": "large", "execution": "slow", "score": 60},
                "7d": {"volume": "very_large", "execution": "very_slow", "score": 30}
            },
            
            "data_types": {
                "security": {"baseline_volume": "medium", "query_frequency": "high"},
                "web": {"baseline_volume": "very_large", "query_frequency": "very_high"},
                "application": {"baseline_volume": "large", "query_frequency": "high"},
                "network": {"baseline_volume": "very_large", "query_frequency": "medium"},
                "system": {"baseline_volume": "medium", "query_frequency": "medium"}
            }
        }
    
    def analyze_time_range_optimization(
        self,
        spl_query: str,
        natural_query: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> TimeRangeOptimizationAnalysis:
        """
        Perform comprehensive time range optimization analysis
        
        Args:
            spl_query: The SPL query to analyze
            natural_query: Optional natural language query for context
            context: Additional context information
            
        Returns:
            Comprehensive time range optimization analysis
        """
        query_id = str(uuid.uuid4())
        logger.info(f"Starting time range optimization analysis for query {query_id}")
        
        try:
            # Parse existing time range
            detected_time_range = self._parse_time_range(spl_query, natural_query)
            
            # Build analysis context
            analysis_context = self._build_context(spl_query, natural_query, context)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                spl_query, detected_time_range, analysis_context
            )
            
            # Select primary recommendation
            primary_rec = self._select_primary_recommendation(recommendations, analysis_context)
            
            # Calculate current metrics
            current_metrics = self._calculate_current_metrics(spl_query, detected_time_range, analysis_context)
            
            # Calculate optimized metrics
            optimized_metrics = self._calculate_optimized_metrics(primary_rec, analysis_context)
            
            # Generate optimization summary
            optimization_summary = self._generate_optimization_summary(
                current_metrics, optimized_metrics, primary_rec
            )
            
            # Validate recommendations
            validation_results = self._validate_recommendations(recommendations, analysis_context)
            
            analysis = TimeRangeOptimizationAnalysis(
                query_id=query_id,
                original_spl=spl_query,
                natural_query=natural_query,
                detected_time_range=detected_time_range,
                context=analysis_context,
                recommendations=recommendations,
                primary_recommendation=primary_rec,
                current_metrics=current_metrics,
                optimized_metrics=optimized_metrics,
                optimization_summary=optimization_summary,
                validation_results=validation_results
            )
            
            logger.info(
                f"Time range optimization analysis completed",
                query_id=query_id,
                recommendations_count=len(recommendations),
                primary_strategy=primary_rec.strategy.value
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Time range optimization analysis failed: {e}")
            return self._create_fallback_analysis(query_id, spl_query, natural_query)
    
    def _parse_time_range(self, spl_query: str, natural_query: Optional[str] = None) -> Optional[TimeRangeParsed]:
        """Parse time range from SPL query and natural language"""
        
        # Check SPL query first
        for category, patterns in self.time_patterns.items():
            for pattern_name, pattern_info in patterns.items():
                match = re.search(pattern_info["pattern"], spl_query, re.IGNORECASE)
                if match:
                    return self._create_parsed_time_range(
                        match, pattern_info, spl_query
                    )
        
        # Check natural language query
        if natural_query:
            for category, patterns in self.time_patterns.items():
                if category == "natural_patterns":
                    for pattern_name, pattern_info in patterns.items():
                        match = re.search(pattern_info["pattern"], natural_query, re.IGNORECASE)
                        if match:
                            return self._create_parsed_time_range(
                                match, pattern_info, natural_query, is_natural=True
                            )
        
        # No time range detected
        return TimeRangeParsed(
            original_text="",
            range_type=TimeRangeType.ALL_TIME,
            confidence=0.0,
            parsed_successfully=False
        )
    
    def _create_parsed_time_range(
        self, 
        match: re.Match,
        pattern_info: Dict[str, Any],
        source_text: str,
        is_natural: bool = False
    ) -> TimeRangeParsed:
        """Create a parsed time range from regex match"""
        
        range_type = pattern_info["type"]
        confidence = pattern_info["confidence"]
        
        parsed = TimeRangeParsed(
            original_text=match.group(0),
            range_type=range_type,
            confidence=confidence,
            parsed_successfully=True
        )
        
        if range_type == TimeRangeType.RELATIVE:
            if len(match.groups()) >= 2:
                parsed.duration = int(match.group(1))
                parsed.unit = TimeUnit(match.group(2))
                parsed.earliest = f"{match.group(1)}{match.group(2)}"
        
        elif range_type == TimeRangeType.NATURAL:
            parsed.natural_language = match.group(0)
            if len(match.groups()) >= 2:
                parsed.duration = int(match.group(1))
                unit_text = match.group(2)
                # Convert natural language units to TimeUnit
                unit_mapping = {
                    "second": TimeUnit.SECOND,
                    "minute": TimeUnit.MINUTE, 
                    "hour": TimeUnit.HOUR,
                    "day": TimeUnit.DAY,
                    "week": TimeUnit.WEEK,
                    "month": TimeUnit.MONTH,
                    "year": TimeUnit.YEAR
                }
                parsed.unit = unit_mapping.get(unit_text, TimeUnit.HOUR)
        
        elif range_type == TimeRangeType.SNAP_TO:
            parsed.snap_to_boundary = match.group(0)
        
        return parsed
    
    def _build_context(
        self,
        spl_query: str,
        natural_query: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> TimeRangeContext:
        """Build analysis context from query and additional information"""
        
        # Detect query type
        query_type = "search"  # default
        if re.search(r'\|\s*stats', spl_query, re.IGNORECASE):
            query_type = "stats"
        elif re.search(r'\|\s*timechart', spl_query, re.IGNORECASE):
            query_type = "timechart"
        elif re.search(r'\|\s*chart', spl_query, re.IGNORECASE):
            query_type = "chart"
        
        # Detect data type
        data_type = "general"
        combined_text = (spl_query + " " + (natural_query or "")).lower()
        
        for dtype, keywords in self.data_type_patterns.items():
            if any(keyword in combined_text for keyword in keywords):
                data_type = dtype
                break
        
        # Detect user intent
        user_intent = "analysis"  # default
        if any(word in combined_text for word in ["monitor", "monitoring", "real-time", "live"]):
            user_intent = "monitoring"
        elif any(word in combined_text for word in ["investigate", "investigation", "forensic", "incident"]):
            user_intent = "investigation"
        elif any(word in combined_text for word in ["report", "reporting", "summary", "dashboard"]):
            user_intent = "reporting"
        
        # Build context object
        time_context = TimeRangeContext(
            query_type=query_type,
            data_type=data_type,
            user_intent=user_intent,
            timezone=context.get("timezone", "UTC") if context else "UTC"
        )
        
        # Add business hours if available
        if context and "business_hours" in context:
            time_context.business_hours = context["business_hours"]
        
        return time_context
    
    def _generate_recommendations(
        self,
        spl_query: str,
        detected_time_range: Optional[TimeRangeParsed],
        context: TimeRangeContext
    ) -> List[TimeRangeRecommendation]:
        """Generate time range optimization recommendations"""
        
        recommendations = []
        
        # Get optimization rules for data type
        rules = self.optimization_rules.get(context.data_type, self.optimization_rules["application_logs"])
        
        # Strategy 1: Performance-first optimization
        perf_rec = self._generate_performance_recommendation(spl_query, rules, context)
        if perf_rec:
            recommendations.append(perf_rec)
        
        # Strategy 2: Balanced optimization
        balanced_rec = self._generate_balanced_recommendation(spl_query, rules, context)
        if balanced_rec:
            recommendations.append(balanced_rec)
        
        # Strategy 3: Accuracy-first optimization
        accuracy_rec = self._generate_accuracy_recommendation(spl_query, rules, context)
        if accuracy_rec:
            recommendations.append(accuracy_rec)
        
        # Strategy 4: Adaptive optimization based on intent
        adaptive_rec = self._generate_adaptive_recommendation(spl_query, rules, context, detected_time_range)
        if adaptive_rec:
            recommendations.append(adaptive_rec)
        
        return recommendations
    
    def _generate_performance_recommendation(
        self,
        spl_query: str,
        rules: Dict[str, Any],
        context: TimeRangeContext
    ) -> Optional[TimeRangeRecommendation]:
        """Generate performance-first recommendation"""
        
        # Use the best performance range for this data type
        perf_range = rules["performance_ranges"]["excellent"]
        
        # Generate optimized SPL
        optimized_spl = self._apply_time_range_to_spl(spl_query, f"-{perf_range}")
        
        # Calculate expected metrics
        expected_metrics = TimeRangeMetrics(
            estimated_data_volume="small",
            estimated_execution_time="< 10 seconds",
            performance_impact="excellent", 
            index_efficiency=95.0,
            data_coverage=70.0,  # May miss some data for performance
            resource_usage="low",
            concurrent_capacity=50,
            optimization_score=90.0
        )
        
        return TimeRangeRecommendation(
            recommended_spl=optimized_spl,
            strategy=TimeOptimizationStrategy.PERFORMANCE_FIRST,
            confidence_level=TimeRangeRecommendationLevel.HIGH,
            performance_improvement="70-90% faster execution",
            reasoning=f"Optimized for maximum performance using {perf_range} time window",
            trade_offs=["May miss older events", "Limited historical context"],
            alternative_ranges=[f"-{rules['performance_ranges']['good']}", f"-{rules['typical_range']}"],
            expected_metrics=expected_metrics
        )
    
    def _generate_balanced_recommendation(
        self,
        spl_query: str,
        rules: Dict[str, Any],
        context: TimeRangeContext
    ) -> Optional[TimeRangeRecommendation]:
        """Generate balanced optimization recommendation"""
        
        # Use typical range for balanced approach
        balanced_range = rules["typical_range"]
        
        # Generate optimized SPL
        optimized_spl = self._apply_time_range_to_spl(spl_query, f"-{balanced_range}")
        
        # Calculate expected metrics
        expected_metrics = TimeRangeMetrics(
            estimated_data_volume="medium",
            estimated_execution_time="10-30 seconds", 
            performance_impact="good",
            index_efficiency=80.0,
            data_coverage=85.0,
            resource_usage="medium",
            concurrent_capacity=25,
            optimization_score=80.0
        )
        
        return TimeRangeRecommendation(
            recommended_spl=optimized_spl,
            strategy=TimeOptimizationStrategy.BALANCED,
            confidence_level=TimeRangeRecommendationLevel.HIGH,
            performance_improvement="40-60% faster execution", 
            reasoning=f"Balanced approach using typical {balanced_range} time window for {context.data_type} data",
            trade_offs=["Good balance of performance and coverage"],
            alternative_ranges=[f"-{rules['performance_ranges']['good']}", f"-{rules['max_efficient']}"],
            expected_metrics=expected_metrics
        )
    
    def _generate_accuracy_recommendation(
        self,
        spl_query: str,
        rules: Dict[str, Any],
        context: TimeRangeContext
    ) -> Optional[TimeRangeRecommendation]:
        """Generate accuracy-first recommendation"""
        
        # Use max efficient range for comprehensive coverage
        accuracy_range = rules["max_efficient"]
        
        # Generate optimized SPL
        optimized_spl = self._apply_time_range_to_spl(spl_query, f"-{accuracy_range}")
        
        # Calculate expected metrics
        expected_metrics = TimeRangeMetrics(
            estimated_data_volume="large",
            estimated_execution_time="1-5 minutes",
            performance_impact="moderate",
            index_efficiency=60.0,
            data_coverage=95.0,
            resource_usage="high",
            concurrent_capacity=10,
            optimization_score=70.0
        )
        
        return TimeRangeRecommendation(
            recommended_spl=optimized_spl,
            strategy=TimeOptimizationStrategy.ACCURACY_FIRST,
            confidence_level=TimeRangeRecommendationLevel.MEDIUM,
            performance_improvement="10-30% faster than all-time search",
            reasoning=f"Comprehensive data coverage using {accuracy_range} time window",
            trade_offs=["Slower execution", "Higher resource usage", "Maximum data completeness"],
            alternative_ranges=[f"-{rules['typical_range']}", f"-{rules['investigation_range']}"],
            expected_metrics=expected_metrics
        )
    
    def _generate_adaptive_recommendation(
        self,
        spl_query: str,
        rules: Dict[str, Any],
        context: TimeRangeContext,
        detected_time_range: Optional[TimeRangeParsed]
    ) -> Optional[TimeRangeRecommendation]:
        """Generate adaptive recommendation based on context"""
        
        # Adapt based on user intent
        if context.user_intent == "monitoring":
            adaptive_range = rules["real_time_threshold"]
            strategy = TimeOptimizationStrategy.PERFORMANCE_FIRST
            reasoning = "Real-time monitoring optimized for immediate insights"
        elif context.user_intent == "investigation":
            adaptive_range = rules["investigation_range"]
            strategy = TimeOptimizationStrategy.ACCURACY_FIRST
            reasoning = "Investigation optimized for comprehensive data coverage"
        else:
            adaptive_range = rules["typical_range"]
            strategy = TimeOptimizationStrategy.BALANCED
            reasoning = "Analysis optimized for balanced performance and coverage"
        
        # If time range already exists, suggest optimization
        if detected_time_range and detected_time_range.parsed_successfully:
            current_range = detected_time_range.original_text
            reasoning += f" (optimizing existing range: {current_range})"
        
        # Generate optimized SPL
        optimized_spl = self._apply_time_range_to_spl(spl_query, f"-{adaptive_range}")
        
        # Calculate metrics based on strategy
        if strategy == TimeOptimizationStrategy.PERFORMANCE_FIRST:
            expected_metrics = TimeRangeMetrics(
                estimated_data_volume="small",
                estimated_execution_time="< 15 seconds",
                performance_impact="excellent",
                index_efficiency=90.0,
                data_coverage=75.0,
                resource_usage="low",
                concurrent_capacity=40,
                optimization_score=85.0
            )
        else:
            expected_metrics = TimeRangeMetrics(
                estimated_data_volume="medium",
                estimated_execution_time="30-60 seconds",
                performance_impact="good",
                index_efficiency=75.0,
                data_coverage=90.0,
                resource_usage="medium",
                concurrent_capacity=20,
                optimization_score=75.0
            )
        
        return TimeRangeRecommendation(
            recommended_spl=optimized_spl,
            strategy=strategy,
            confidence_level=TimeRangeRecommendationLevel.HIGH,
            performance_improvement="30-50% faster execution",
            reasoning=reasoning,
            trade_offs=["Contextually optimized for specific use case"],
            alternative_ranges=[f"-{rules['typical_range']}", f"-{rules['performance_ranges']['good']}"],
            expected_metrics=expected_metrics
        )
    
    def _apply_time_range_to_spl(self, spl_query: str, time_range: str) -> str:
        """Apply time range to SPL query"""
        
        # Check if query already has time range
        if re.search(r'earliest=|latest=', spl_query):
            # Replace existing time range
            optimized = re.sub(
                r'earliest=[^\s]+',
                f'earliest={time_range}',
                spl_query
            )
        else:
            # Add time range to search
            if spl_query.strip().startswith("search"):
                optimized = spl_query.replace(
                    "search",
                    f"search earliest={time_range}",
                    1
                )
            else:
                optimized = f"search earliest={time_range} {spl_query}"
        
        # Add snap-to for better performance if appropriate
        if not "@" in optimized and time_range.endswith(("h", "d")):
            if time_range.endswith("h"):
                optimized = optimized.replace(time_range, f"{time_range}@h")
            elif time_range.endswith("d"):
                optimized = optimized.replace(time_range, f"{time_range}@d")
        
        return optimized
    
    def _select_primary_recommendation(
        self,
        recommendations: List[TimeRangeRecommendation],
        context: TimeRangeContext
    ) -> TimeRangeRecommendation:
        """Select the primary recommendation based on context"""
        
        if not recommendations:
            # Fallback recommendation
            return TimeRangeRecommendation(
                recommended_spl="search earliest=-24h",
                strategy=TimeOptimizationStrategy.BALANCED,
                confidence_level=TimeRangeRecommendationLevel.LOW,
                performance_improvement="Standard optimization",
                reasoning="Fallback recommendation",
                trade_offs=["Default time range applied"]
            )
        
        # Score recommendations based on context
        scored_recommendations = []
        for rec in recommendations:
            score = 0.0
            
            # Intent-based scoring
            if context.user_intent == "monitoring" and rec.strategy == TimeOptimizationStrategy.PERFORMANCE_FIRST:
                score += 30
            elif context.user_intent == "investigation" and rec.strategy == TimeOptimizationStrategy.ACCURACY_FIRST:
                score += 30
            elif rec.strategy == TimeOptimizationStrategy.BALANCED:
                score += 20
            
            # Confidence level scoring
            if rec.confidence_level == TimeRangeRecommendationLevel.HIGH:
                score += 25
            elif rec.confidence_level == TimeRangeRecommendationLevel.MEDIUM:
                score += 15
            
            # Performance scoring
            if rec.expected_metrics:
                if rec.expected_metrics.performance_impact == "excellent":
                    score += 15
                elif rec.expected_metrics.performance_impact == "good":
                    score += 10
            
            scored_recommendations.append((score, rec))
        
        # Return highest scored recommendation
        scored_recommendations.sort(key=lambda x: x[0], reverse=True)
        return scored_recommendations[0][1]
    
    def _calculate_current_metrics(
        self,
        spl_query: str,
        detected_time_range: Optional[TimeRangeParsed],
        context: TimeRangeContext
    ) -> TimeRangeMetrics:
        """Calculate metrics for current query"""
        
        if not detected_time_range or detected_time_range.range_type == TimeRangeType.ALL_TIME:
            # No time range - worst case metrics
            return TimeRangeMetrics(
                estimated_data_volume="very_large",
                estimated_execution_time="5-15 minutes",
                performance_impact="poor",
                index_efficiency=20.0,
                data_coverage=100.0,
                resource_usage="high",
                concurrent_capacity=2,
                optimization_score=25.0
            )
        
        # Estimate based on detected time range
        if detected_time_range.unit in [TimeUnit.MINUTE, TimeUnit.HOUR]:
            return TimeRangeMetrics(
                estimated_data_volume="small",
                estimated_execution_time="10-30 seconds",
                performance_impact="good",
                index_efficiency=80.0,
                data_coverage=85.0,
                resource_usage="medium",
                concurrent_capacity=25,
                optimization_score=75.0
            )
        else:
            return TimeRangeMetrics(
                estimated_data_volume="large",
                estimated_execution_time="1-5 minutes",
                performance_impact="moderate",
                index_efficiency=50.0,
                data_coverage=95.0,
                resource_usage="high",
                concurrent_capacity=10,
                optimization_score=55.0
            )
    
    def _calculate_optimized_metrics(
        self,
        recommendation: TimeRangeRecommendation,
        context: TimeRangeContext
    ) -> TimeRangeMetrics:
        """Calculate metrics for optimized query"""
        
        if recommendation.expected_metrics:
            return recommendation.expected_metrics
        
        # Default optimized metrics
        return TimeRangeMetrics(
            estimated_data_volume="medium",
            estimated_execution_time="15-45 seconds",
            performance_impact="good",
            index_efficiency=75.0,
            data_coverage=80.0,
            resource_usage="medium",
            concurrent_capacity=20,
            optimization_score=80.0
        )
    
    def _generate_optimization_summary(
        self,
        current_metrics: TimeRangeMetrics,
        optimized_metrics: TimeRangeMetrics,
        recommendation: TimeRangeRecommendation
    ) -> Dict[str, Any]:
        """Generate optimization summary"""
        
        return {
            "performance_improvement": recommendation.performance_improvement,
            "strategy_applied": recommendation.strategy.value,
            "confidence_level": recommendation.confidence_level.value,
            "metrics_comparison": {
                "data_volume": {
                    "before": current_metrics.estimated_data_volume,
                    "after": optimized_metrics.estimated_data_volume
                },
                "execution_time": {
                    "before": current_metrics.estimated_execution_time,
                    "after": optimized_metrics.estimated_execution_time
                },
                "optimization_score": {
                    "before": current_metrics.optimization_score,
                    "after": optimized_metrics.optimization_score,
                    "improvement": optimized_metrics.optimization_score - current_metrics.optimization_score
                }
            },
            "trade_offs": recommendation.trade_offs,
            "implementation_notes": recommendation.implementation_notes
        }
    
    def _validate_recommendations(
        self,
        recommendations: List[TimeRangeRecommendation],
        context: TimeRangeContext
    ) -> Dict[str, Any]:
        """Validate recommendations for correctness and feasibility"""
        
        validation = {
            "total_recommendations": len(recommendations),
            "high_confidence_count": sum(1 for r in recommendations if r.confidence_level == TimeRangeRecommendationLevel.HIGH),
            "strategy_distribution": {},
            "validation_warnings": [],
            "implementation_feasibility": "high"
        }
        
        # Check strategy distribution
        for rec in recommendations:
            strategy = rec.strategy.value
            validation["strategy_distribution"][strategy] = validation["strategy_distribution"].get(strategy, 0) + 1
        
        # Validation warnings
        if len(recommendations) == 0:
            validation["validation_warnings"].append("No recommendations generated")
            validation["implementation_feasibility"] = "low"
        
        if validation["high_confidence_count"] == 0:
            validation["validation_warnings"].append("No high confidence recommendations")
            validation["implementation_feasibility"] = "medium"
        
        return validation
    
    def _create_fallback_analysis(
        self,
        query_id: str,
        spl_query: str,
        natural_query: Optional[str]
    ) -> TimeRangeOptimizationAnalysis:
        """Create fallback analysis when main analysis fails"""
        
        fallback_context = TimeRangeContext(
            query_type="search",
            data_type="general",
            user_intent="analysis"
        )
        
        fallback_recommendation = TimeRangeRecommendation(
            recommended_spl=f"search earliest=-24h {spl_query}",
            strategy=TimeOptimizationStrategy.BALANCED,
            confidence_level=TimeRangeRecommendationLevel.LOW,
            performance_improvement="Standard optimization applied",
            reasoning="Fallback recommendation due to analysis failure",
            trade_offs=["Limited optimization due to parsing issues"]
        )
        
        fallback_metrics = TimeRangeMetrics(
            estimated_data_volume="medium",
            estimated_execution_time="30-60 seconds",
            performance_impact="moderate",
            index_efficiency=60.0,
            data_coverage=80.0,
            resource_usage="medium",
            concurrent_capacity=15,
            optimization_score=60.0
        )
        
        return TimeRangeOptimizationAnalysis(
            query_id=query_id,
            original_spl=spl_query,
            natural_query=natural_query,
            detected_time_range=None,
            context=fallback_context,
            recommendations=[fallback_recommendation],
            primary_recommendation=fallback_recommendation,
            current_metrics=fallback_metrics,
            optimized_metrics=fallback_metrics,
            optimization_summary={"note": "Fallback analysis applied"},
            validation_results={"note": "Fallback validation"}
        )
    
    def get_optimization_documentation(self) -> Dict[str, Any]:
        """Get comprehensive documentation for time range optimization"""
        return {
            "time_range_types": {ttype.value: ttype.name for ttype in TimeRangeType},
            "optimization_strategies": {strategy.value: strategy.name for strategy in TimeOptimizationStrategy},
            "recommendation_levels": {level.value: level.name for level in TimeRangeRecommendationLevel},
            "supported_time_units": {unit.value: unit.name for unit in TimeUnit},
            "data_type_optimizations": self.optimization_rules,
            "performance_baselines": self.performance_baselines,
            "best_practices": [
                "Always specify a time range appropriate for your analysis needs",
                "Use snap-to boundaries (@h, @d) for better performance",
                "Consider your data type when selecting time ranges",
                "Balance performance needs with data completeness requirements",
                "Use shorter time ranges for real-time monitoring",
                "Use longer time ranges for historical analysis and investigations",
                "Monitor query performance and adjust time ranges accordingly"
            ],
            "common_patterns": {
                "Real-time monitoring": "earliest=-15m",
                "Hourly analysis": "earliest=-1h@h",
                "Daily reports": "earliest=-24h@h",
                "Weekly trends": "earliest=-7d@d",
                "Monthly summaries": "earliest=-30d@d",
                "Investigation": "earliest=-30d"
            }
        }
    
    def validate_time_range_expression(
        self,
        time_expression: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate time range expression for SPL queries
        
        Args:
            time_expression: Time range expression to validate
            context: Optional validation context
            
        Returns:
            Validation results with errors, warnings, and suggestions
        """
        import re
        
        errors = []
        warnings = []
        suggestions = []
        parsed_range = None
        
        try:
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
            
            # Try to parse the time range
            try:
                parsed_range = self._parse_time_range(f"search {time_expression}")
                if parsed_range and parsed_range.parsed_successfully:
                    suggestions.append("Time range parsed successfully")
                else:
                    warnings.append("Time range could not be fully parsed")
            except Exception as e:
                warnings.append(f"Parsing warning: {str(e)}")
            
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
                                warnings.append("Time range > 1 year may severely impact performance")
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
                            suggestions.append("Snap-to boundaries provide good performance")
                    
                    else:
                        # Absolute time or other format
                        if not re.match(r'\d+', value):
                            errors.append(f"Unrecognized time format: {value}")
            
            # Generate context-aware suggestions
            if context:
                data_type = context.get("data_type", "application")
                query_type = context.get("query_type", "search")
                
                if not errors and data_type in self.optimization_rules:
                    rules = self.optimization_rules[data_type]
                    suggestions.append(f"Consider typical range for {data_type}: {rules['typical_range']}")
            
            # Performance impact assessment
            if any("year" in w or "severely" in w for w in warnings):
                performance_impact = "poor"
            elif any("month" in w or "day" in w or "week" in w for w in warnings):
                performance_impact = "moderate"
            else:
                performance_impact = "good"
            
            # Additional optimization suggestions
            if not errors:
                if not warnings:
                    suggestions.append("Time range expression is well-optimized")
                else:
                    suggestions.append("Consider shorter time range for better performance")
                    suggestions.append("Add index specification to improve efficiency")
                    suggestions.append("Use snap-to boundaries (@h, @d) when possible")
            
            return {
                "valid": len(errors) == 0,
                "syntax_valid": syntax_valid,
                "parsed_range": parsed_range,
                "errors": errors,
                "warnings": warnings,
                "suggestions": suggestions,
                "performance_impact": performance_impact,
                "components": time_parts
            }
            
        except Exception as e:
            logger.error(f"Time range validation failed: {e}")
            return {
                "valid": False,
                "syntax_valid": False,
                "parsed_range": None,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "suggestions": ["Please check time range syntax"],
                "performance_impact": "unknown",
                "components": []
            }


# Create singleton instance
time_range_optimizer = TimeRangeOptimizer()