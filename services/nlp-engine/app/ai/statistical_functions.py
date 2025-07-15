"""
Statistical Functions Mapping System for SPL Translation

This module provides advanced statistical function mapping capabilities including:
- Comprehensive statistical function definitions and mappings
- Advanced statistical analysis patterns
- SPL generation for complex statistical operations
- Parameter handling for statistical functions
- Confidence intervals and hypothesis testing
- Time series analysis functions
- Distribution analysis
"""

import re
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import math
from datetime import datetime, timedelta

from ..core.logging import get_logger
from .spl_mapping import spl_mapper, FieldType
from .advanced_aggregation import AggregationFunction, AggregationType, AdvancedAggregation, AggregationParameter, AggregationCondition

logger = get_logger(__name__)


class StatisticalFunction(Enum):
    """Extended statistical functions for Splunk SPL"""
    
    # Basic descriptive statistics
    MEAN = "mean"
    MEDIAN = "median"
    MODE = "mode"
    STDEV = "stdev"
    VAR = "var"
    RANGE = "range"
    
    # Percentiles and quartiles
    PERCENTILE = "perc"
    QUARTILE = "quartile"
    IQR = "iqr"
    
    # Distribution analysis
    SKEWNESS = "skewness"
    KURTOSIS = "kurtosis"
    
    # Advanced statistics
    CORRELATION = "correlation"
    COVARIANCE = "covariance"
    ZSCORE = "zscore"
    
    # Time series analysis
    TREND = "trend"
    SEASONALITY = "seasonality"
    MOVING_AVERAGE = "moving_avg"
    EXPONENTIAL_SMOOTHING = "exp_smooth"
    
    # Statistical testing
    CONFIDENCE_INTERVAL = "confidence_interval"
    HYPOTHESIS_TEST = "hypothesis_test"
    
    # Outlier detection
    OUTLIERS = "outliers"
    ANOMALIES = "anomalies"
    
    # Regression analysis
    LINEAR_REGRESSION = "linear_regression"
    POLYNOMIAL_REGRESSION = "poly_regression"
    
    # Distribution fitting
    NORMAL_DISTRIBUTION = "normal_dist"
    POISSON_DISTRIBUTION = "poisson_dist"
    
    # Sampling and estimation
    SAMPLE_SIZE = "sample_size"
    BOOTSTRAP = "bootstrap"
    
    # Information theory
    ENTROPY = "entropy"
    MUTUAL_INFORMATION = "mutual_info"


class StatisticalCategory(Enum):
    """Categories of statistical functions"""
    DESCRIPTIVE = "descriptive"
    INFERENTIAL = "inferential"
    PREDICTIVE = "predictive"
    DIAGNOSTIC = "diagnostic"
    EXPLORATORY = "exploratory"
    TIME_SERIES = "time_series"
    MULTIVARIATE = "multivariate"
    DISTRIBUTION = "distribution"
    HYPOTHESIS = "hypothesis"
    REGRESSION = "regression"


@dataclass
class StatisticalParameter:
    """Parameters for statistical functions"""
    name: str
    value: Any
    parameter_type: str = "value"  # "value", "field", "expression", "list"
    required: bool = False
    default_value: Any = None
    validation_rule: Optional[str] = None
    description: Optional[str] = None


@dataclass
class StatisticalFunctionSpec:
    """Advanced statistical function specification"""
    function: StatisticalFunction
    category: StatisticalCategory
    fields: List[str]
    parameters: List[StatisticalParameter] = field(default_factory=list)
    conditions: List[AggregationCondition] = field(default_factory=list)
    confidence_level: Optional[float] = None
    sample_size: Optional[int] = None
    time_window: Optional[str] = None
    grouping_fields: List[str] = field(default_factory=list)
    output_format: str = "numeric"  # "numeric", "table", "chart", "text"
    
    def to_spl(self) -> str:
        """Convert statistical function to SPL syntax"""
        if self.function == StatisticalFunction.PERCENTILE:
            return self._generate_percentile_spl()
        elif self.function == StatisticalFunction.CORRELATION:
            return self._generate_correlation_spl()
        elif self.function == StatisticalFunction.MOVING_AVERAGE:
            return self._generate_moving_average_spl()
        elif self.function == StatisticalFunction.ZSCORE:
            return self._generate_zscore_spl()
        elif self.function == StatisticalFunction.OUTLIERS:
            return self._generate_outliers_spl()
        elif self.function == StatisticalFunction.TREND:
            return self._generate_trend_spl()
        elif self.function == StatisticalFunction.CONFIDENCE_INTERVAL:
            return self._generate_confidence_interval_spl()
        elif self.function == StatisticalFunction.LINEAR_REGRESSION:
            return self._generate_regression_spl()
        else:
            return self._generate_basic_statistical_spl()
    
    def _generate_percentile_spl(self) -> str:
        """Generate SPL for percentile calculations"""
        percentile_value = 50  # default
        for param in self.parameters:
            if param.name == "percentile":
                percentile_value = param.value
        
        field = self.fields[0] if self.fields else "_time"
        spl = f"perc{percentile_value}({field})"
        
        return spl
    
    def _generate_correlation_spl(self) -> str:
        """Generate SPL for correlation analysis"""
        if len(self.fields) < 2:
            return "eval correlation=null"
        
        field1, field2 = self.fields[0], self.fields[1]
        
        # Pearson correlation using SPL
        spl = f"""eval correlation=round(
            (sum({field1}*{field2}) - sum({field1})*sum({field2})/count) /
            sqrt((sum({field1}*{field1}) - sum({field1})*sum({field1})/count) *
                 (sum({field2}*{field2}) - sum({field2})*sum({field2})/count)), 4)"""
        
        return spl
    
    def _generate_moving_average_spl(self) -> str:
        """Generate SPL for moving average calculation"""
        window_size = 5  # default
        for param in self.parameters:
            if param.name == "window":
                window_size = param.value
        
        field = self.fields[0] if self.fields else "_time"
        
        # Use streamstats for moving average
        spl = f"streamstats avg({field}) as moving_avg window={window_size}"
        
        return spl
    
    def _generate_zscore_spl(self) -> str:
        """Generate SPL for Z-score calculation"""
        field = self.fields[0] if self.fields else "_time"
        
        # Z-score calculation using eventstats
        spl = f"""eventstats avg({field}) as field_mean, stdev({field}) as field_stdev |
                  eval zscore=round(({field}-field_mean)/field_stdev, 4)"""
        
        return spl
    
    def _generate_outliers_spl(self) -> str:
        """Generate SPL for outlier detection"""
        field = self.fields[0] if self.fields else "_time"
        threshold = 2.0  # default Z-score threshold
        
        for param in self.parameters:
            if param.name == "threshold":
                threshold = param.value
        
        # Outlier detection using Z-score method
        spl = f"""eventstats avg({field}) as field_mean, stdev({field}) as field_stdev |
                  eval zscore=abs(({field}-field_mean)/field_stdev) |
                  eval is_outlier=if(zscore>{threshold}, 1, 0)"""
        
        return spl
    
    def _generate_trend_spl(self) -> str:
        """Generate SPL for trend analysis"""
        field = self.fields[0] if self.fields else "_time"
        
        # Linear trend using regression
        spl = f"""sort _time |
                  streamstats count as x |
                  eventstats avg(x) as x_mean, avg({field}) as y_mean |
                  eval xy_dev = (x - x_mean) * ({field} - y_mean) |
                  eval x_dev_sq = (x - x_mean) * (x - x_mean) |
                  eventstats sum(xy_dev) as sum_xy_dev, sum(x_dev_sq) as sum_x_dev_sq |
                  eval trend_slope = sum_xy_dev / sum_x_dev_sq |
                  eval trend_intercept = y_mean - trend_slope * x_mean"""
        
        return spl
    
    def _generate_confidence_interval_spl(self) -> str:
        """Generate SPL for confidence interval calculation"""
        field = self.fields[0] if self.fields else "_time"
        confidence_level = self.confidence_level or 0.95
        
        # Calculate confidence interval assuming normal distribution
        alpha = 1 - confidence_level
        z_score = 1.96  # for 95% confidence interval
        
        if confidence_level == 0.99:
            z_score = 2.576
        elif confidence_level == 0.90:
            z_score = 1.645
        
        spl = f"""eventstats avg({field}) as field_mean, stdev({field}) as field_stdev, count as n |
                  eval margin_error = {z_score} * field_stdev / sqrt(n) |
                  eval ci_lower = field_mean - margin_error |
                  eval ci_upper = field_mean + margin_error"""
        
        return spl
    
    def _generate_regression_spl(self) -> str:
        """Generate SPL for linear regression"""
        if len(self.fields) < 2:
            return "eval regression_error='Insufficient fields for regression'"
        
        x_field, y_field = self.fields[0], self.fields[1]
        
        # Linear regression calculation
        spl = f"""eventstats avg({x_field}) as x_mean, avg({y_field}) as y_mean |
                  eval xy_dev = ({x_field} - x_mean) * ({y_field} - y_mean) |
                  eval x_dev_sq = ({x_field} - x_mean) * ({x_field} - x_mean) |
                  eventstats sum(xy_dev) as sum_xy_dev, sum(x_dev_sq) as sum_x_dev_sq |
                  eval slope = sum_xy_dev / sum_x_dev_sq |
                  eval intercept = y_mean - slope * x_mean |
                  eval predicted_y = slope * {x_field} + intercept |
                  eval residual = {y_field} - predicted_y"""
        
        return spl
    
    def _generate_basic_statistical_spl(self) -> str:
        """Generate SPL for basic statistical functions"""
        field = self.fields[0] if self.fields else "_time"
        
        if self.function == StatisticalFunction.MEAN:
            return f"avg({field})"
        elif self.function == StatisticalFunction.MEDIAN:
            return f"median({field})"
        elif self.function == StatisticalFunction.STDEV:
            return f"stdev({field})"
        elif self.function == StatisticalFunction.VAR:
            return f"var({field})"
        elif self.function == StatisticalFunction.RANGE:
            return f"range({field})"
        elif self.function == StatisticalFunction.IQR:
            return f"perc75({field}) - perc25({field}) as iqr"
        elif self.function == StatisticalFunction.SKEWNESS:
            # Skewness calculation using moment method
            return f"""eventstats avg({field}) as field_mean, stdev({field}) as field_stdev |
                       eval skewness_term = pow(({field} - field_mean) / field_stdev, 3) |
                       eventstats avg(skewness_term) as skewness"""
        elif self.function == StatisticalFunction.KURTOSIS:
            # Kurtosis calculation using moment method
            return f"""eventstats avg({field}) as field_mean, stdev({field}) as field_stdev |
                       eval kurtosis_term = pow(({field} - field_mean) / field_stdev, 4) |
                       eventstats avg(kurtosis_term) as kurtosis"""
        else:
            return f"stats count({field})"


class StatisticalFunctionMapper:
    """Advanced statistical function mapping system"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Initialize statistical patterns and mappings
        self.statistical_patterns = self._initialize_statistical_patterns()
        self.function_mappings = self._initialize_function_mappings()
        self.parameter_mappings = self._initialize_parameter_mappings()
        self.category_mappings = self._initialize_category_mappings()
        
        # Initialize advanced statistical operations
        self.advanced_operations = self._initialize_advanced_operations()
        self.time_series_operations = self._initialize_time_series_operations()
        
    def _initialize_statistical_patterns(self) -> Dict[str, Any]:
        """Initialize statistical function patterns"""
        return {
            # Descriptive statistics
            "descriptive": {
                "patterns": [
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?(?:mean|average)\s+(?:of\s+)?(.+)",
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?median\s+(?:of\s+)?(.+)",
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?mode\s+(?:of\s+)?(.+)",
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?(?:standard deviation|stdev)\s+(?:of\s+)?(.+)",
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?variance\s+(?:of\s+)?(.+)",
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?range\s+(?:of\s+)?(.+)",
                ],
                "functions": {
                    "mean": StatisticalFunction.MEAN,
                    "average": StatisticalFunction.MEAN,
                    "median": StatisticalFunction.MEDIAN,
                    "mode": StatisticalFunction.MODE,
                    "standard deviation": StatisticalFunction.STDEV,
                    "stdev": StatisticalFunction.STDEV,
                    "variance": StatisticalFunction.VAR,
                    "range": StatisticalFunction.RANGE
                }
            },
            
            # Percentiles and quartiles
            "percentiles": {
                "patterns": [
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?(\d+)(?:th|st|nd|rd)?\s+percentile\s+(?:of\s+)?(.+)",
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?(?:first|1st)\s+quartile\s+(?:of\s+)?(.+)",
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?(?:third|3rd)\s+quartile\s+(?:of\s+)?(.+)",
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?(?:interquartile range|iqr)\s+(?:of\s+)?(.+)",
                ],
                "functions": {
                    "percentile": StatisticalFunction.PERCENTILE,
                    "quartile": StatisticalFunction.QUARTILE,
                    "iqr": StatisticalFunction.IQR,
                    "interquartile range": StatisticalFunction.IQR
                }
            },
            
            # Distribution analysis
            "distribution": {
                "patterns": [
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?skewness\s+(?:of\s+)?(.+)",
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?kurtosis\s+(?:of\s+)?(.+)",
                    r"(?:analyze|check)\s+(?:the\s+)?distribution\s+(?:of\s+)?(.+)",
                    r"(?:test|check)\s+(?:for\s+)?normality\s+(?:of\s+)?(.+)",
                ],
                "functions": {
                    "skewness": StatisticalFunction.SKEWNESS,
                    "kurtosis": StatisticalFunction.KURTOSIS,
                    "distribution": StatisticalFunction.NORMAL_DISTRIBUTION,
                    "normality": StatisticalFunction.NORMAL_DISTRIBUTION
                }
            },
            
            # Correlation and relationships
            "correlation": {
                "patterns": [
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?correlation\s+(?:between\s+)?(.+?)\s+(?:and|with)\s+(.+)",
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?covariance\s+(?:between\s+)?(.+?)\s+(?:and|with)\s+(.+)",
                    r"(?:correlate|relate)\s+(.+?)\s+(?:with|to)\s+(.+)",
                ],
                "functions": {
                    "correlation": StatisticalFunction.CORRELATION,
                    "covariance": StatisticalFunction.COVARIANCE,
                    "correlate": StatisticalFunction.CORRELATION,
                    "relate": StatisticalFunction.CORRELATION
                }
            },
            
            # Time series analysis
            "time_series": {
                "patterns": [
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?(?:moving average|rolling average)\s+(?:of\s+)?(.+?)(?:\s+(?:over|with)\s+(\d+)\s+(?:period|window)s?)?",
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?trend\s+(?:of\s+)?(.+?)(?:\s+over\s+time)?",
                    r"(?:detect|find|identify)\s+(?:the\s+)?seasonality\s+(?:in\s+)?(.+)",
                    r"(?:smooth|apply smoothing to)\s+(.+?)(?:\s+using\s+exponential\s+smoothing)?",
                ],
                "functions": {
                    "moving average": StatisticalFunction.MOVING_AVERAGE,
                    "rolling average": StatisticalFunction.MOVING_AVERAGE,
                    "trend": StatisticalFunction.TREND,
                    "seasonality": StatisticalFunction.SEASONALITY,
                    "smooth": StatisticalFunction.EXPONENTIAL_SMOOTHING,
                    "exponential smoothing": StatisticalFunction.EXPONENTIAL_SMOOTHING
                }
            },
            
            # Outlier detection
            "outliers": {
                "patterns": [
                    r"(?:detect|find|identify)\s+(?:the\s+)?outliers\s+(?:in\s+)?(.+)",
                    r"(?:detect|find|identify)\s+(?:the\s+)?anomalies\s+(?:in\s+)?(.+)",
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?(?:z-score|z score)\s+(?:of\s+)?(.+)",
                ],
                "functions": {
                    "outliers": StatisticalFunction.OUTLIERS,
                    "anomalies": StatisticalFunction.ANOMALIES,
                    "z-score": StatisticalFunction.ZSCORE,
                    "z score": StatisticalFunction.ZSCORE
                }
            },
            
            # Regression analysis
            "regression": {
                "patterns": [
                    r"(?:perform|run|calculate)\s+(?:linear\s+)?regression\s+(?:of\s+)?(.+?)\s+(?:on|against)\s+(.+)",
                    r"(?:fit|create)\s+(?:a\s+)?(?:linear\s+)?regression\s+(?:model|line)\s+(?:for\s+)?(.+?)\s+(?:and|with)\s+(.+)",
                    r"(?:predict|forecast)\s+(.+?)\s+(?:using|based on)\s+(.+)",
                ],
                "functions": {
                    "regression": StatisticalFunction.LINEAR_REGRESSION,
                    "linear regression": StatisticalFunction.LINEAR_REGRESSION,
                    "fit": StatisticalFunction.LINEAR_REGRESSION,
                    "predict": StatisticalFunction.LINEAR_REGRESSION,
                    "forecast": StatisticalFunction.LINEAR_REGRESSION
                }
            },
            
            # Statistical inference
            "inference": {
                "patterns": [
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?(?:confidence interval|ci)\s+(?:of\s+)?(.+?)(?:\s+(?:at|with)\s+(\d+)%\s+confidence)?",
                    r"(?:test|perform)\s+(?:hypothesis\s+)?test\s+(?:for\s+)?(.+)",
                    r"(?:calculate|compute|find|get)\s+(?:the\s+)?sample\s+size\s+(?:for\s+)?(.+)",
                ],
                "functions": {
                    "confidence interval": StatisticalFunction.CONFIDENCE_INTERVAL,
                    "ci": StatisticalFunction.CONFIDENCE_INTERVAL,
                    "hypothesis test": StatisticalFunction.HYPOTHESIS_TEST,
                    "test": StatisticalFunction.HYPOTHESIS_TEST,
                    "sample size": StatisticalFunction.SAMPLE_SIZE
                }
            }
        }
    
    def _initialize_function_mappings(self) -> Dict[str, StatisticalFunction]:
        """Initialize natural language to statistical function mappings"""
        return {
            # Descriptive statistics
            "mean": StatisticalFunction.MEAN,
            "average": StatisticalFunction.MEAN,
            "median": StatisticalFunction.MEDIAN,
            "mode": StatisticalFunction.MODE,
            "standard deviation": StatisticalFunction.STDEV,
            "stdev": StatisticalFunction.STDEV,
            "variance": StatisticalFunction.VAR,
            "range": StatisticalFunction.RANGE,
            
            # Percentiles
            "percentile": StatisticalFunction.PERCENTILE,
            "quartile": StatisticalFunction.QUARTILE,
            "iqr": StatisticalFunction.IQR,
            "interquartile range": StatisticalFunction.IQR,
            
            # Distribution analysis
            "skewness": StatisticalFunction.SKEWNESS,
            "kurtosis": StatisticalFunction.KURTOSIS,
            "distribution": StatisticalFunction.NORMAL_DISTRIBUTION,
            "normality": StatisticalFunction.NORMAL_DISTRIBUTION,
            
            # Correlation
            "correlation": StatisticalFunction.CORRELATION,
            "covariance": StatisticalFunction.COVARIANCE,
            "correlate": StatisticalFunction.CORRELATION,
            
            # Time series
            "moving average": StatisticalFunction.MOVING_AVERAGE,
            "rolling average": StatisticalFunction.MOVING_AVERAGE,
            "trend": StatisticalFunction.TREND,
            "seasonality": StatisticalFunction.SEASONALITY,
            "exponential smoothing": StatisticalFunction.EXPONENTIAL_SMOOTHING,
            
            # Outliers
            "outliers": StatisticalFunction.OUTLIERS,
            "anomalies": StatisticalFunction.ANOMALIES,
            "z-score": StatisticalFunction.ZSCORE,
            "z score": StatisticalFunction.ZSCORE,
            
            # Regression
            "regression": StatisticalFunction.LINEAR_REGRESSION,
            "linear regression": StatisticalFunction.LINEAR_REGRESSION,
            "polynomial regression": StatisticalFunction.POLYNOMIAL_REGRESSION,
            
            # Inference
            "confidence interval": StatisticalFunction.CONFIDENCE_INTERVAL,
            "ci": StatisticalFunction.CONFIDENCE_INTERVAL,
            "hypothesis test": StatisticalFunction.HYPOTHESIS_TEST,
            "sample size": StatisticalFunction.SAMPLE_SIZE,
            
            # Information theory
            "entropy": StatisticalFunction.ENTROPY,
            "mutual information": StatisticalFunction.MUTUAL_INFORMATION
        }
    
    def _initialize_parameter_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Initialize parameter mappings for statistical functions"""
        return {
            "percentile": {
                "parameters": ["percentile_value"],
                "defaults": {"percentile_value": 50},
                "patterns": [r"(\d+)(?:th|st|nd|rd)?\s+percentile"],
                "validation": {"percentile_value": "0 <= value <= 100"}
            },
            "moving_average": {
                "parameters": ["window_size"],
                "defaults": {"window_size": 5},
                "patterns": [r"(?:over|with)\s+(\d+)\s+(?:period|window)s?"],
                "validation": {"window_size": "value > 0"}
            },
            "confidence_interval": {
                "parameters": ["confidence_level"],
                "defaults": {"confidence_level": 0.95},
                "patterns": [r"(?:at|with)\s+(\d+)%\s+confidence"],
                "validation": {"confidence_level": "0 < value < 1"}
            },
            "outliers": {
                "parameters": ["threshold"],
                "defaults": {"threshold": 2.0},
                "patterns": [r"(?:with|using)\s+(?:threshold|z-score)\s+(?:of\s+)?([0-9.]+)"],
                "validation": {"threshold": "value > 0"}
            },
            "trend": {
                "parameters": ["method"],
                "defaults": {"method": "linear"},
                "patterns": [r"(?:using|with)\s+(linear|polynomial|exponential)\s+(?:trend|method)"],
                "validation": {"method": "value in ['linear', 'polynomial', 'exponential']"}
            },
            "regression": {
                "parameters": ["degree"],
                "defaults": {"degree": 1},
                "patterns": [r"(?:degree|order)\s+(\d+)"],
                "validation": {"degree": "value >= 1"}
            }
        }
    
    def _initialize_category_mappings(self) -> Dict[str, StatisticalCategory]:
        """Initialize statistical function categories"""
        return {
            StatisticalFunction.MEAN: StatisticalCategory.DESCRIPTIVE,
            StatisticalFunction.MEDIAN: StatisticalCategory.DESCRIPTIVE,
            StatisticalFunction.MODE: StatisticalCategory.DESCRIPTIVE,
            StatisticalFunction.STDEV: StatisticalCategory.DESCRIPTIVE,
            StatisticalFunction.VAR: StatisticalCategory.DESCRIPTIVE,
            StatisticalFunction.RANGE: StatisticalCategory.DESCRIPTIVE,
            
            StatisticalFunction.PERCENTILE: StatisticalCategory.DESCRIPTIVE,
            StatisticalFunction.QUARTILE: StatisticalCategory.DESCRIPTIVE,
            StatisticalFunction.IQR: StatisticalCategory.DESCRIPTIVE,
            
            StatisticalFunction.SKEWNESS: StatisticalCategory.DISTRIBUTION,
            StatisticalFunction.KURTOSIS: StatisticalCategory.DISTRIBUTION,
            StatisticalFunction.NORMAL_DISTRIBUTION: StatisticalCategory.DISTRIBUTION,
            
            StatisticalFunction.CORRELATION: StatisticalCategory.MULTIVARIATE,
            StatisticalFunction.COVARIANCE: StatisticalCategory.MULTIVARIATE,
            
            StatisticalFunction.TREND: StatisticalCategory.TIME_SERIES,
            StatisticalFunction.SEASONALITY: StatisticalCategory.TIME_SERIES,
            StatisticalFunction.MOVING_AVERAGE: StatisticalCategory.TIME_SERIES,
            StatisticalFunction.EXPONENTIAL_SMOOTHING: StatisticalCategory.TIME_SERIES,
            
            StatisticalFunction.OUTLIERS: StatisticalCategory.DIAGNOSTIC,
            StatisticalFunction.ANOMALIES: StatisticalCategory.DIAGNOSTIC,
            StatisticalFunction.ZSCORE: StatisticalCategory.DIAGNOSTIC,
            
            StatisticalFunction.LINEAR_REGRESSION: StatisticalCategory.REGRESSION,
            StatisticalFunction.POLYNOMIAL_REGRESSION: StatisticalCategory.REGRESSION,
            
            StatisticalFunction.CONFIDENCE_INTERVAL: StatisticalCategory.INFERENTIAL,
            StatisticalFunction.HYPOTHESIS_TEST: StatisticalCategory.HYPOTHESIS,
            StatisticalFunction.SAMPLE_SIZE: StatisticalCategory.INFERENTIAL,
            
            StatisticalFunction.ENTROPY: StatisticalCategory.EXPLORATORY,
            StatisticalFunction.MUTUAL_INFORMATION: StatisticalCategory.EXPLORATORY
        }
    
    def _initialize_advanced_operations(self) -> Dict[str, Any]:
        """Initialize advanced statistical operations"""
        return {
            "multivariate_analysis": {
                "correlation_matrix": "Calculate correlation matrix for multiple variables",
                "principal_components": "Perform principal component analysis",
                "cluster_analysis": "Perform clustering analysis",
                "factor_analysis": "Perform factor analysis"
            },
            "hypothesis_testing": {
                "t_test": "Perform t-test for means",
                "chi_square": "Perform chi-square test",
                "anova": "Perform analysis of variance",
                "mann_whitney": "Perform Mann-Whitney U test"
            },
            "time_series_advanced": {
                "autocorrelation": "Calculate autocorrelation function",
                "partial_autocorrelation": "Calculate partial autocorrelation function",
                "arima": "Fit ARIMA model",
                "decomposition": "Perform time series decomposition"
            }
        }
    
    def _initialize_time_series_operations(self) -> Dict[str, Any]:
        """Initialize time series specific operations"""
        return {
            "trend_analysis": {
                "patterns": [
                    r"(?:analyze|detect|find)\s+(?:the\s+)?trend\s+(?:in\s+)?(.+?)(?:\s+over\s+time)?",
                    r"(?:is\s+there\s+a\s+)?(?:upward|downward|increasing|decreasing)\s+trend\s+(?:in\s+)?(.+)",
                    r"(?:calculate|compute)\s+(?:the\s+)?trend\s+(?:slope|direction)\s+(?:of\s+)?(.+)"
                ],
                "spl_template": "sort _time | streamstats count as x | eventstats avg(x) as x_mean, avg({field}) as y_mean | eval trend_slope = sum((x - x_mean) * ({field} - y_mean)) / sum((x - x_mean) * (x - x_mean))"
            },
            "seasonality_detection": {
                "patterns": [
                    r"(?:detect|find|identify)\s+(?:the\s+)?seasonality\s+(?:in\s+)?(.+)",
                    r"(?:is\s+there\s+)?(?:seasonal|cyclical)\s+(?:pattern|behavior)\s+(?:in\s+)?(.+)",
                    r"(?:analyze|check)\s+(?:for\s+)?seasonal\s+(?:patterns|trends)\s+(?:in\s+)?(.+)"
                ],
                "spl_template": "bin _time span=1d | stats avg({field}) as daily_avg by _time | eventstats stdev(daily_avg) as season_stdev | eval seasonality_index = daily_avg / season_stdev"
            },
            "change_point_detection": {
                "patterns": [
                    r"(?:detect|find|identify)\s+(?:change\s+points|breakpoints)\s+(?:in\s+)?(.+)",
                    r"(?:when\s+did\s+)?(.+?)\s+(?:change|shift)\s+(?:significantly)?",
                    r"(?:find|detect)\s+(?:structural\s+)?(?:breaks|changes)\s+(?:in\s+)?(.+)"
                ],
                "spl_template": "sort _time | streamstats avg({field}) as running_avg window=10 | eval change_magnitude = abs({field} - running_avg) | eventstats perc90(change_magnitude) as change_threshold | eval is_change_point = if(change_magnitude > change_threshold, 1, 0)"
            }
        }
    
    def detect_statistical_functions(self, query: str) -> List[StatisticalFunctionSpec]:
        """Detect statistical functions from natural language query"""
        query_lower = query.lower()
        detected_functions = []
        
        try:
            # Check each statistical pattern category
            for category, category_info in self.statistical_patterns.items():
                for pattern in category_info["patterns"]:
                    matches = re.finditer(pattern, query_lower)
                    for match in matches:
                        # Extract function name and parameters
                        function_name = self._extract_function_name(pattern, match)
                        if function_name and function_name in category_info["functions"]:
                            stat_func = category_info["functions"][function_name]
                            
                            # Extract fields from match groups
                            fields = []
                            for group in match.groups():
                                if group:
                                    fields.append(group.strip())
                            
                            # Extract parameters
                            parameters = self._extract_parameters(query_lower, stat_func)
                            
                            # Create statistical function object
                            stat_function = StatisticalFunctionSpec(
                                function=stat_func,
                                category=self.category_mappings.get(stat_func, StatisticalCategory.DESCRIPTIVE),
                                fields=fields,
                                parameters=parameters
                            )
                            
                            detected_functions.append(stat_function)
            
            self.logger.info(f"Detected {len(detected_functions)} statistical functions", query=query[:100])
            return detected_functions
            
        except Exception as e:
            self.logger.error(f"Statistical function detection failed: {e}")
            return []
    
    def _extract_function_name(self, pattern: str, match: re.Match) -> Optional[str]:
        """Extract function name from pattern match"""
        # Extract function name from pattern regex
        pattern_lower = pattern.lower()
        
        # Common function name patterns
        function_patterns = [
            r"(?:mean|average)",
            r"median",
            r"mode",
            r"(?:standard deviation|stdev)",
            r"variance",
            r"range",
            r"percentile",
            r"quartile",
            r"iqr",
            r"skewness",
            r"kurtosis",
            r"correlation",
            r"covariance",
            r"(?:moving average|rolling average)",
            r"trend",
            r"seasonality",
            r"outliers",
            r"anomalies",
            r"(?:z-score|z score)",
            r"regression",
            r"(?:confidence interval|ci)"
        ]
        
        for func_pattern in function_patterns:
            if re.search(func_pattern, pattern_lower):
                func_match = re.search(func_pattern, pattern_lower)
                if func_match:
                    return func_match.group(0)
        
        return None
    
    def _extract_parameters(self, query: str, stat_func: StatisticalFunction) -> List[StatisticalParameter]:
        """Extract parameters for statistical function"""
        parameters = []
        
        func_name = stat_func.value
        if func_name in self.parameter_mappings:
            param_info = self.parameter_mappings[func_name]
            
            for pattern in param_info["patterns"]:
                matches = re.finditer(pattern, query)
                for match in matches:
                    if match.groups():
                        param_value = match.group(1)
                        
                        # Convert parameter value to appropriate type
                        if param_value.isdigit():
                            param_value = int(param_value)
                        elif param_value.replace('.', '').isdigit():
                            param_value = float(param_value)
                        
                        # Create parameter object
                        param = StatisticalParameter(
                            name=param_info["parameters"][0],
                            value=param_value,
                            parameter_type="value"
                        )
                        parameters.append(param)
        
        return parameters
    
    def generate_spl_for_statistical_function(self, stat_func: StatisticalFunctionSpec) -> str:
        """Generate SPL code for statistical function"""
        try:
            return stat_func.to_spl()
        except Exception as e:
            self.logger.error(f"SPL generation failed for {stat_func.function}: {e}")
            return "stats count"
    
    def get_statistical_function_suggestions(self, partial_query: str) -> List[Tuple[str, float]]:
        """Get statistical function suggestions based on partial query"""
        partial_query = partial_query.lower().strip()
        suggestions = []
        
        for natural_func, stat_func in self.function_mappings.items():
            score = 0.0
            
            # Check if function name is in query
            if natural_func in partial_query:
                score += 1.0
            
            # Check partial matches
            query_words = partial_query.split()
            func_words = natural_func.split()
            
            # Calculate word overlap
            overlap = len(set(query_words) & set(func_words))
            if overlap > 0:
                score += overlap / len(func_words) * 0.8
            
            if score > 0:
                suggestions.append((natural_func, score))
        
        # Sort by score descending
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:5]
    
    def validate_statistical_function(self, stat_func: StatisticalFunctionSpec) -> Tuple[bool, List[str]]:
        """Validate statistical function parameters and requirements"""
        errors = []
        
        # Check required fields
        if not stat_func.fields:
            errors.append("Statistical function requires at least one field")
        
        # Check field count for specific functions
        if stat_func.function in [StatisticalFunction.CORRELATION, StatisticalFunction.COVARIANCE]:
            if len(stat_func.fields) < 2:
                errors.append("Correlation and covariance require at least two fields")
        
        # Validate parameters
        func_name = stat_func.function.value
        if func_name in self.parameter_mappings:
            param_info = self.parameter_mappings[func_name]
            
            for param in stat_func.parameters:
                if param.name in param_info.get("validation", {}):
                    validation_rule = param_info["validation"][param.name]
                    
                    # Simple validation (could be enhanced)
                    if ">" in validation_rule:
                        min_val = float(validation_rule.split(">")[1].strip())
                        if param.value <= min_val:
                            errors.append(f"Parameter {param.name} must be greater than {min_val}")
                    
                    if "<=" in validation_rule:
                        max_val = float(validation_rule.split("<=")[1].strip())
                        if param.value > max_val:
                            errors.append(f"Parameter {param.name} must be less than or equal to {max_val}")
        
        return len(errors) == 0, errors
    
    def get_statistical_function_info(self, stat_func: StatisticalFunctionSpec) -> Dict[str, Any]:
        """Get detailed information about a statistical function"""
        return {
            "function": stat_func.function.value,
            "category": self.category_mappings.get(stat_func.function, StatisticalCategory.DESCRIPTIVE).value,
            "description": self._get_function_description(stat_func.function),
            "parameters": [
                {
                    "name": param.name,
                    "type": param.parameter_type,
                    "required": param.required,
                    "default": param.default_value,
                    "description": param.description
                }
                for param in stat_func.parameters
            ],
            "fields_required": self._get_required_fields_count(stat_func.function),
            "output_type": stat_func.output_format,
            "complexity": self._get_function_complexity(stat_func.function)
        }
    
    def _get_function_description(self, stat_func: StatisticalFunction) -> str:
        """Get description for statistical function"""
        descriptions = {
            StatisticalFunction.MEAN: "Calculate the arithmetic mean (average) of values",
            StatisticalFunction.MEDIAN: "Calculate the median (middle value) of values",
            StatisticalFunction.MODE: "Find the most frequently occurring value",
            StatisticalFunction.STDEV: "Calculate the standard deviation of values",
            StatisticalFunction.VAR: "Calculate the variance of values",
            StatisticalFunction.RANGE: "Calculate the range (max - min) of values",
            StatisticalFunction.PERCENTILE: "Calculate the nth percentile of values",
            StatisticalFunction.QUARTILE: "Calculate quartiles of values",
            StatisticalFunction.IQR: "Calculate the interquartile range (Q3 - Q1)",
            StatisticalFunction.SKEWNESS: "Calculate the skewness (asymmetry) of distribution",
            StatisticalFunction.KURTOSIS: "Calculate the kurtosis (tail heaviness) of distribution",
            StatisticalFunction.CORRELATION: "Calculate the correlation coefficient between two variables",
            StatisticalFunction.COVARIANCE: "Calculate the covariance between two variables",
            StatisticalFunction.ZSCORE: "Calculate the z-score (standard score) of values",
            StatisticalFunction.MOVING_AVERAGE: "Calculate the moving average over a window",
            StatisticalFunction.TREND: "Analyze trend direction and magnitude",
            StatisticalFunction.SEASONALITY: "Detect seasonal patterns in time series",
            StatisticalFunction.OUTLIERS: "Detect outliers using statistical methods",
            StatisticalFunction.ANOMALIES: "Detect anomalies in data patterns",
            StatisticalFunction.LINEAR_REGRESSION: "Perform linear regression analysis",
            StatisticalFunction.CONFIDENCE_INTERVAL: "Calculate confidence interval for mean",
            StatisticalFunction.HYPOTHESIS_TEST: "Perform statistical hypothesis testing",
            StatisticalFunction.SAMPLE_SIZE: "Calculate required sample size for analysis"
        }
        
        return descriptions.get(stat_func, "Advanced statistical function")
    
    def _get_required_fields_count(self, stat_func: StatisticalFunction) -> int:
        """Get required number of fields for statistical function"""
        if stat_func in [StatisticalFunction.CORRELATION, StatisticalFunction.COVARIANCE]:
            return 2
        else:
            return 1
    
    def _get_function_complexity(self, stat_func: StatisticalFunction) -> str:
        """Get complexity level of statistical function"""
        simple_functions = [
            StatisticalFunction.MEAN, StatisticalFunction.MEDIAN, StatisticalFunction.MODE,
            StatisticalFunction.STDEV, StatisticalFunction.VAR, StatisticalFunction.RANGE
        ]
        
        intermediate_functions = [
            StatisticalFunction.PERCENTILE, StatisticalFunction.QUARTILE, StatisticalFunction.IQR,
            StatisticalFunction.ZSCORE, StatisticalFunction.MOVING_AVERAGE, StatisticalFunction.OUTLIERS
        ]
        
        if stat_func in simple_functions:
            return "simple"
        elif stat_func in intermediate_functions:
            return "intermediate"
        else:
            return "advanced"


# Global instance
statistical_function_mapper = StatisticalFunctionMapper()