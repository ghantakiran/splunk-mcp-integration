"""
Automatic Chart Type Selection Service

This service analyzes data characteristics and automatically recommends
the most appropriate chart types based on data properties, statistical
analysis, and visualization best practices.
"""
import math
import statistics
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, date
import re

from ..models.chart import (
    ChartType, DataType, DataField, ChartData, ChartConfig, 
    ChartRecommendation, AggregationType, ColorScheme
)
from ..core.logging import get_logger

logger = get_logger(__name__)


class ChartTypeSelector:
    """Intelligent chart type selection based on data analysis"""
    
    def __init__(self):
        self.min_categorical_threshold = 20  # Max unique values for categorical
        self.max_pie_categories = 10  # Max categories for pie chart
        self.min_time_series_points = 3  # Min points for time series
        self.correlation_threshold = 0.7  # Threshold for scatter plot recommendation
    
    def recommend_chart_type(
        self, 
        data: ChartData, 
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> ChartRecommendation:
        """
        Recommend the best chart type for the given data
        
        Args:
            data: Chart data to analyze
            user_preferences: User preferences for chart selection
            
        Returns:
            ChartRecommendation with primary recommendation and alternatives
        """
        logger.info("Starting chart type recommendation", 
                   data_rows=data.total_rows, 
                   data_fields=len(data.fields))
        
        # Analyze data characteristics
        data_analysis = self._analyze_data(data)
        
        # Get recommendation based on data analysis
        recommendations = self._generate_recommendations(data_analysis, data, user_preferences)
        
        # Select primary recommendation
        primary = recommendations[0] if recommendations else self._fallback_recommendation(data)
        
        # Add alternatives
        primary.alternatives = recommendations[1:5]  # Top 4 alternatives
        
        logger.info("Chart recommendation completed", 
                   recommended_type=primary.chart_type,
                   confidence=primary.confidence,
                   alternatives_count=len(primary.alternatives))
        
        return primary
    
    def _analyze_data(self, data: ChartData) -> Dict[str, Any]:
        """Analyze data characteristics for chart recommendation"""
        analysis = {
            'field_count': len(data.fields),
            'row_count': data.total_rows,
            'field_types': {},
            'categorical_fields': [],
            'numerical_fields': [],
            'temporal_fields': [],
            'has_aggregation': data.is_aggregated,
            'data_density': 'high' if data.total_rows > 1000 else 'medium' if data.total_rows > 100 else 'low'
        }
        
        # Analyze each field
        for field in data.fields:
            field_analysis = self._analyze_field(field, data.rows)
            analysis['field_types'][field.name] = field_analysis
            
            if field_analysis['data_type'] == DataType.CATEGORICAL:
                analysis['categorical_fields'].append(field.name)
            elif field_analysis['data_type'] == DataType.NUMERICAL:
                analysis['numerical_fields'].append(field.name)
            elif field_analysis['data_type'] == DataType.TEMPORAL:
                analysis['temporal_fields'].append(field.name)
        
        # Determine data pattern
        analysis['data_pattern'] = self._determine_data_pattern(analysis)
        
        return analysis
    
    def _analyze_field(self, field: DataField, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze individual field characteristics"""
        values = [row.get(field.name) for row in rows if row.get(field.name) is not None]
        
        analysis = {
            'data_type': field.data_type,
            'unique_count': len(set(values)) if values else 0,
            'null_percentage': (len(rows) - len(values)) / len(rows) if rows else 0,
            'is_key_field': False,
            'distribution': 'unknown'
        }
        
        if not values:
            return analysis
        
        # Check if it's a key field (high uniqueness)
        uniqueness_ratio = analysis['unique_count'] / len(values)
        analysis['is_key_field'] = uniqueness_ratio > 0.9
        
        # Analyze distribution for numerical fields
        if field.data_type == DataType.NUMERICAL and len(values) > 1:
            try:
                numeric_values = [float(v) for v in values if v is not None]
                if numeric_values:
                    analysis['mean'] = statistics.mean(numeric_values)
                    analysis['median'] = statistics.median(numeric_values)
                    analysis['std_dev'] = statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0
                    analysis['min'] = min(numeric_values)
                    analysis['max'] = max(numeric_values)
                    analysis['range'] = analysis['max'] - analysis['min']
                    
                    # Determine distribution type
                    if analysis['std_dev'] > 0:
                        cv = analysis['std_dev'] / analysis['mean'] if analysis['mean'] != 0 else float('inf')
                        if cv < 0.1:
                            analysis['distribution'] = 'uniform'
                        elif cv < 0.5:
                            analysis['distribution'] = 'normal'
                        else:
                            analysis['distribution'] = 'skewed'
            except (ValueError, TypeError, statistics.StatisticsError):
                pass
        
        # Analyze categorical field characteristics
        elif field.data_type == DataType.CATEGORICAL:
            value_counts = {}
            for value in values:
                value_counts[value] = value_counts.get(value, 0) + 1
            
            analysis['value_counts'] = value_counts
            analysis['most_common'] = max(value_counts.items(), key=lambda x: x[1]) if value_counts else None
            analysis['is_ordinal'] = self._is_ordinal(values)
        
        return analysis
    
    def _is_ordinal(self, values: List[Any]) -> bool:
        """Check if categorical values are ordinal"""
        # Common ordinal patterns
        ordinal_patterns = [
            r'^(low|medium|high)$',
            r'^(small|medium|large)$',
            r'^(poor|fair|good|excellent)$',
            r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',
            r'^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'^\d+$'  # Pure numbers as strings
        ]
        
        string_values = [str(v).lower() for v in values[:10]]  # Sample first 10
        
        for pattern in ordinal_patterns:
            if any(re.match(pattern, v) for v in string_values):
                return True
        
        return False
    
    def _determine_data_pattern(self, analysis: Dict[str, Any]) -> str:
        """Determine the overall data pattern"""
        num_fields = analysis['field_count']
        num_categorical = len(analysis['categorical_fields'])
        num_numerical = len(analysis['numerical_fields'])
        num_temporal = len(analysis['temporal_fields'])
        
        # Time series pattern
        if num_temporal > 0 and num_numerical > 0:
            return 'time_series'
        
        # Correlation analysis pattern (2+ numerical fields)
        if num_numerical >= 2:
            return 'correlation'
        
        # Distribution analysis pattern (1 numerical field)
        if num_numerical == 1 and num_categorical <= 1:
            return 'distribution'
        
        # Categorical comparison pattern
        if num_categorical >= 1 and num_numerical >= 1:
            return 'categorical_comparison'
        
        # Categorical breakdown pattern
        if num_categorical >= 2:
            return 'categorical_breakdown'
        
        # Part-to-whole pattern
        if num_categorical == 1 and analysis['field_types'].get(analysis['categorical_fields'][0], {}).get('unique_count', 0) <= self.max_pie_categories:
            return 'part_to_whole'
        
        return 'general'
    
    def _generate_recommendations(
        self, 
        analysis: Dict[str, Any], 
        data: ChartData,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> List[ChartRecommendation]:
        """Generate chart recommendations based on data analysis"""
        recommendations = []
        pattern = analysis['data_pattern']
        
        # Apply pattern-specific recommendation logic
        if pattern == 'time_series':
            recommendations.extend(self._recommend_time_series(analysis, data))
        elif pattern == 'correlation':
            recommendations.extend(self._recommend_correlation(analysis, data))
        elif pattern == 'distribution':
            recommendations.extend(self._recommend_distribution(analysis, data))
        elif pattern == 'categorical_comparison':
            recommendations.extend(self._recommend_categorical_comparison(analysis, data))
        elif pattern == 'categorical_breakdown':
            recommendations.extend(self._recommend_categorical_breakdown(analysis, data))
        elif pattern == 'part_to_whole':
            recommendations.extend(self._recommend_part_to_whole(analysis, data))
        else:
            recommendations.extend(self._recommend_general(analysis, data))
        
        # Apply user preferences
        if user_preferences:
            recommendations = self._apply_user_preferences(recommendations, user_preferences)
        
        # Sort by confidence
        recommendations.sort(key=lambda x: x.confidence, reverse=True)
        
        return recommendations
    
    def _recommend_time_series(self, analysis: Dict[str, Any], data: ChartData) -> List[ChartRecommendation]:
        """Recommend charts for time series data"""
        recommendations = []
        temporal_field = analysis['temporal_fields'][0]
        numerical_fields = analysis['numerical_fields']
        
        # Line chart (primary recommendation for time series)
        config = ChartConfig(
            chart_type=ChartType.LINE,
            title="Time Series Analysis",
            x_axis=temporal_field,
            y_axis=numerical_fields[0] if numerical_fields else None,
            interactive=True,
            zoom_enabled=True
        )
        
        recommendations.append(ChartRecommendation(
            chart_type=ChartType.LINE,
            confidence=0.95,
            reasoning="Time series data is best visualized with line charts to show trends over time",
            config=config
        ))
        
        # Bar chart alternative for discrete time periods
        if analysis['row_count'] <= 50:
            bar_config = config.copy()
            bar_config.chart_type = ChartType.BAR
            
            recommendations.append(ChartRecommendation(
                chart_type=ChartType.BAR,
                confidence=0.75,
                reasoning="Bar charts work well for discrete time periods with fewer data points",
                config=bar_config
            ))
        
        return recommendations
    
    def _recommend_correlation(self, analysis: Dict[str, Any], data: ChartData) -> List[ChartRecommendation]:
        """Recommend charts for correlation analysis"""
        recommendations = []
        numerical_fields = analysis['numerical_fields']
        
        # Scatter plot (primary for correlation)
        config = ChartConfig(
            chart_type=ChartType.SCATTER,
            title="Correlation Analysis",
            x_axis=numerical_fields[0],
            y_axis=numerical_fields[1] if len(numerical_fields) > 1 else numerical_fields[0],
            interactive=True,
            hover_enabled=True
        )
        
        # Add color grouping if categorical field available
        if analysis['categorical_fields']:
            config.color_field = analysis['categorical_fields'][0]
        
        recommendations.append(ChartRecommendation(
            chart_type=ChartType.SCATTER,
            confidence=0.90,
            reasoning="Scatter plots are ideal for exploring correlations between numerical variables",
            config=config
        ))
        
        # Heatmap for multiple numerical fields
        if len(numerical_fields) > 2:
            heatmap_config = ChartConfig(
                chart_type=ChartType.HEATMAP,
                title="Correlation Heatmap",
                interactive=True
            )
            
            recommendations.append(ChartRecommendation(
                chart_type=ChartType.HEATMAP,
                confidence=0.80,
                reasoning="Heatmaps effectively show correlations between multiple numerical variables",
                config=heatmap_config
            ))
        
        return recommendations
    
    def _recommend_distribution(self, analysis: Dict[str, Any], data: ChartData) -> List[ChartRecommendation]:
        """Recommend charts for distribution analysis"""
        recommendations = []
        numerical_field = analysis['numerical_fields'][0]
        
        # Histogram (primary for distribution)
        config = ChartConfig(
            chart_type=ChartType.HISTOGRAM,
            title="Distribution Analysis",
            x_axis=numerical_field,
            interactive=True
        )
        
        recommendations.append(ChartRecommendation(
            chart_type=ChartType.HISTOGRAM,
            confidence=0.90,
            reasoning="Histograms clearly show the distribution of numerical data",
            config=config
        ))
        
        # Bar chart alternative for discrete numerical data
        field_analysis = analysis['field_types'].get(numerical_field, {})
        if field_analysis.get('unique_count', 0) <= 20:
            bar_config = config.copy()
            bar_config.chart_type = ChartType.BAR
            
            recommendations.append(ChartRecommendation(
                chart_type=ChartType.BAR,
                confidence=0.75,
                reasoning="Bar charts work well for discrete numerical data with few unique values",
                config=bar_config
            ))
        
        return recommendations
    
    def _recommend_categorical_comparison(self, analysis: Dict[str, Any], data: ChartData) -> List[ChartRecommendation]:
        """Recommend charts for categorical comparison"""
        recommendations = []
        categorical_field = analysis['categorical_fields'][0]
        numerical_field = analysis['numerical_fields'][0]
        
        categorical_analysis = analysis['field_types'].get(categorical_field, {})
        unique_count = categorical_analysis.get('unique_count', 0)
        
        # Bar chart (primary for categorical comparison)
        config = ChartConfig(
            chart_type=ChartType.BAR,
            title="Categorical Comparison",
            x_axis=categorical_field,
            y_axis=numerical_field,
            interactive=True
        )
        
        recommendations.append(ChartRecommendation(
            chart_type=ChartType.BAR,
            confidence=0.90,
            reasoning="Bar charts are excellent for comparing values across categories",
            config=config
        ))
        
        # Pie chart for part-to-whole with few categories
        if unique_count <= self.max_pie_categories:
            pie_config = ChartConfig(
                chart_type=ChartType.PIE,
                title="Category Distribution",
                color_field=categorical_field,
                y_axis=numerical_field,
                interactive=True
            )
            
            recommendations.append(ChartRecommendation(
                chart_type=ChartType.PIE,
                confidence=0.70,
                reasoning="Pie charts show part-to-whole relationships for a small number of categories",
                config=pie_config
            ))
        
        return recommendations
    
    def _recommend_categorical_breakdown(self, analysis: Dict[str, Any], data: ChartData) -> List[ChartRecommendation]:
        """Recommend charts for categorical breakdown"""
        recommendations = []
        categorical_fields = analysis['categorical_fields']
        
        # Treemap for hierarchical categorical data
        config = ChartConfig(
            chart_type=ChartType.TREEMAP,
            title="Categorical Breakdown",
            color_field=categorical_fields[0],
            interactive=True
        )
        
        if len(categorical_fields) > 1:
            config.chart_options = {
                'hierarchy_fields': categorical_fields[:2],
                'group_by': categorical_fields[0]
            }
        
        recommendations.append(ChartRecommendation(
            chart_type=ChartType.TREEMAP,
            confidence=0.80,
            reasoning="Treemaps effectively visualize hierarchical categorical data",
            config=config
        ))
        
        # Table for detailed categorical breakdown
        table_config = ChartConfig(
            chart_type=ChartType.TABLE,
            title="Detailed Breakdown",
            interactive=True
        )
        
        recommendations.append(ChartRecommendation(
            chart_type=ChartType.TABLE,
            confidence=0.70,
            reasoning="Tables provide detailed view of categorical breakdowns",
            config=table_config
        ))
        
        return recommendations
    
    def _recommend_part_to_whole(self, analysis: Dict[str, Any], data: ChartData) -> List[ChartRecommendation]:
        """Recommend charts for part-to-whole relationships"""
        recommendations = []
        categorical_field = analysis['categorical_fields'][0]
        
        # Pie chart (primary for part-to-whole)
        config = ChartConfig(
            chart_type=ChartType.PIE,
            title="Part-to-Whole Analysis",
            color_field=categorical_field,
            interactive=True
        )
        
        recommendations.append(ChartRecommendation(
            chart_type=ChartType.PIE,
            confidence=0.85,
            reasoning="Pie charts clearly show part-to-whole relationships",
            config=config
        ))
        
        # Treemap alternative
        treemap_config = ChartConfig(
            chart_type=ChartType.TREEMAP,
            title="Hierarchical View",
            color_field=categorical_field,
            interactive=True
        )
        
        recommendations.append(ChartRecommendation(
            chart_type=ChartType.TREEMAP,
            confidence=0.75,
            reasoning="Treemaps provide an alternative view of part-to-whole relationships",
            config=treemap_config
        ))
        
        return recommendations
    
    def _recommend_general(self, analysis: Dict[str, Any], data: ChartData) -> List[ChartRecommendation]:
        """General recommendations when specific pattern is not detected"""
        recommendations = []
        
        # Table as safe fallback
        config = ChartConfig(
            chart_type=ChartType.TABLE,
            title="Data Table",
            interactive=True
        )
        
        recommendations.append(ChartRecommendation(
            chart_type=ChartType.TABLE,
            confidence=0.60,
            reasoning="Table view provides a comprehensive view of all data",
            config=config
        ))
        
        # Bar chart if any categorical data
        if analysis['categorical_fields'] and analysis['numerical_fields']:
            bar_config = ChartConfig(
                chart_type=ChartType.BAR,
                title="General Comparison",
                x_axis=analysis['categorical_fields'][0],
                y_axis=analysis['numerical_fields'][0],
                interactive=True
            )
            
            recommendations.append(ChartRecommendation(
                chart_type=ChartType.BAR,
                confidence=0.65,
                reasoning="Bar charts work well for general categorical comparisons",
                config=bar_config
            ))
        
        return recommendations
    
    def _apply_user_preferences(
        self, 
        recommendations: List[ChartRecommendation], 
        preferences: Dict[str, Any]
    ) -> List[ChartRecommendation]:
        """Apply user preferences to adjust recommendations"""
        preferred_types = preferences.get('preferred_chart_types', [])
        avoid_types = preferences.get('avoid_chart_types', [])
        
        # Boost confidence for preferred types
        for rec in recommendations:
            if rec.chart_type in preferred_types:
                rec.confidence = min(1.0, rec.confidence + 0.1)
                rec.reasoning += " (User preference)"
            elif rec.chart_type in avoid_types:
                rec.confidence = max(0.1, rec.confidence - 0.2)
        
        return recommendations
    
    def _fallback_recommendation(self, data: ChartData) -> ChartRecommendation:
        """Fallback recommendation when analysis fails"""
        config = ChartConfig(
            chart_type=ChartType.TABLE,
            title="Data View",
            interactive=True
        )
        
        return ChartRecommendation(
            chart_type=ChartType.TABLE,
            confidence=0.50,
            reasoning="Table view as safe fallback for data visualization",
            config=config
        )