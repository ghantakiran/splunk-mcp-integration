"""
Comprehensive test suite for chart type selector

Tests the automatic chart type selection logic with various data patterns
and validates recommendation accuracy.
"""
import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.models.chart import ChartData, DataField, DataType, ChartType
from app.services.chart_selector import ChartTypeSelector


class TestChartTypeSelector:
    """Test suite for ChartTypeSelector"""
    
    def setup_method(self):
        """Setup test environment"""
        self.selector = ChartTypeSelector()
    
    def create_test_data(
        self, 
        fields: List[Dict[str, Any]], 
        rows: List[Dict[str, Any]]
    ) -> ChartData:
        """Helper to create test chart data"""
        data_fields = []
        for field_def in fields:
            field = DataField(
                name=field_def['name'],
                data_type=field_def['data_type'],
                sample_values=field_def.get('sample_values', []),
                unique_count=field_def.get('unique_count'),
                null_count=field_def.get('null_count', 0)
            )
            data_fields.append(field)
        
        return ChartData(
            fields=data_fields,
            rows=rows,
            total_rows=len(rows)
        )
    
    def test_time_series_recommendation(self):
        """Test recommendation for time series data"""
        # Create time series data
        base_date = datetime(2024, 1, 1)
        fields = [
            {'name': 'timestamp', 'data_type': DataType.TEMPORAL, 'unique_count': 30},
            {'name': 'cpu_usage', 'data_type': DataType.NUMERICAL, 'unique_count': 25}
        ]
        
        rows = []
        for i in range(30):
            rows.append({
                'timestamp': base_date + timedelta(days=i),
                'cpu_usage': 50 + (i % 10) * 5
            })
        
        data = self.create_test_data(fields, rows)
        recommendation = self.selector.recommend_chart_type(data)
        
        # Should recommend line chart for time series
        assert recommendation.chart_type == ChartType.LINE
        assert recommendation.confidence > 0.8
        assert "time series" in recommendation.reasoning.lower()
        assert recommendation.config.x_axis == 'timestamp'
        assert recommendation.config.y_axis == 'cpu_usage'
    
    def test_categorical_comparison_recommendation(self):
        """Test recommendation for categorical comparison"""
        fields = [
            {'name': 'department', 'data_type': DataType.CATEGORICAL, 'unique_count': 5},
            {'name': 'sales', 'data_type': DataType.NUMERICAL, 'unique_count': 5}
        ]
        
        rows = [
            {'department': 'Engineering', 'sales': 150000},
            {'department': 'Marketing', 'sales': 120000},
            {'department': 'Sales', 'sales': 200000},
            {'department': 'HR', 'sales': 80000},
            {'department': 'Finance', 'sales': 90000}
        ]
        
        data = self.create_test_data(fields, rows)
        recommendation = self.selector.recommend_chart_type(data)
        
        # Should recommend bar chart for categorical comparison
        assert recommendation.chart_type == ChartType.BAR
        assert recommendation.confidence > 0.8
        assert "categorical comparison" in recommendation.reasoning.lower()
        assert recommendation.config.x_axis == 'department'
        assert recommendation.config.y_axis == 'sales'
    
    def test_correlation_analysis_recommendation(self):
        """Test recommendation for correlation analysis"""
        fields = [
            {'name': 'temperature', 'data_type': DataType.NUMERICAL, 'unique_count': 20},
            {'name': 'humidity', 'data_type': DataType.NUMERICAL, 'unique_count': 18},
            {'name': 'pressure', 'data_type': DataType.NUMERICAL, 'unique_count': 15}
        ]
        
        rows = []
        for i in range(20):
            rows.append({
                'temperature': 20 + i,
                'humidity': 40 + i * 2,
                'pressure': 1000 + i * 5
            })
        
        data = self.create_test_data(fields, rows)
        recommendation = self.selector.recommend_chart_type(data)
        
        # Should recommend scatter plot for correlation
        assert recommendation.chart_type == ChartType.SCATTER
        assert recommendation.confidence > 0.8
        assert "correlation" in recommendation.reasoning.lower()
        assert recommendation.config.x_axis == 'temperature'
        assert recommendation.config.y_axis == 'humidity'
    
    def test_distribution_analysis_recommendation(self):
        """Test recommendation for distribution analysis"""
        fields = [
            {'name': 'response_time', 'data_type': DataType.NUMERICAL, 'unique_count': 50}
        ]
        
        # Create distribution data
        import random
        rows = []
        for i in range(100):
            rows.append({
                'response_time': random.gauss(200, 50)  # Normal distribution
            })
        
        data = self.create_test_data(fields, rows)
        recommendation = self.selector.recommend_chart_type(data)
        
        # Should recommend histogram for distribution
        assert recommendation.chart_type == ChartType.HISTOGRAM
        assert recommendation.confidence > 0.8
        assert "distribution" in recommendation.reasoning.lower()
        assert recommendation.config.x_axis == 'response_time'
    
    def test_part_to_whole_recommendation(self):
        """Test recommendation for part-to-whole relationships"""
        fields = [
            {'name': 'category', 'data_type': DataType.CATEGORICAL, 'unique_count': 4},
            {'name': 'value', 'data_type': DataType.NUMERICAL, 'unique_count': 4}
        ]
        
        rows = [
            {'category': 'A', 'value': 30},
            {'category': 'B', 'value': 25},
            {'category': 'C', 'value': 20},
            {'category': 'D', 'value': 25}
        ]
        
        data = self.create_test_data(fields, rows)
        recommendation = self.selector.recommend_chart_type(data)
        
        # Should recommend pie chart for part-to-whole with few categories
        assert recommendation.chart_type in [ChartType.PIE, ChartType.BAR]
        assert recommendation.confidence > 0.7
    
    def test_user_preferences_application(self):
        """Test that user preferences affect recommendations"""
        fields = [
            {'name': 'category', 'data_type': DataType.CATEGORICAL, 'unique_count': 5},
            {'name': 'value', 'data_type': DataType.NUMERICAL, 'unique_count': 5}
        ]
        
        rows = [
            {'category': f'Cat{i}', 'value': i * 10}
            for i in range(5)
        ]
        
        data = self.create_test_data(fields, rows)
        
        # Test with preference for line charts
        preferences = {'preferred_chart_types': [ChartType.LINE]}
        recommendation = self.selector.recommend_chart_type(data, preferences)
        
        # Confidence should be boosted if line chart is recommended
        # or other factors should be considered
        assert recommendation.confidence > 0.0
        assert "preference" in recommendation.reasoning.lower() or recommendation.chart_type != ChartType.LINE
    
    def test_high_cardinality_categorical_data(self):
        """Test handling of high cardinality categorical data"""
        fields = [
            {'name': 'user_id', 'data_type': DataType.CATEGORICAL, 'unique_count': 1000},
            {'name': 'login_count', 'data_type': DataType.NUMERICAL, 'unique_count': 50}
        ]
        
        rows = [
            {'user_id': f'user_{i}', 'login_count': i % 10}
            for i in range(100)
        ]
        
        data = self.create_test_data(fields, rows)
        recommendation = self.selector.recommend_chart_type(data)
        
        # Should not recommend pie chart for high cardinality
        assert recommendation.chart_type != ChartType.PIE
        # Should likely recommend table or other suitable visualization
        assert recommendation.chart_type in [ChartType.TABLE, ChartType.TREEMAP, ChartType.BAR]
    
    def test_empty_data_handling(self):
        """Test handling of empty or minimal data"""
        fields = [
            {'name': 'field1', 'data_type': DataType.CATEGORICAL, 'unique_count': 0}
        ]
        
        rows = []
        
        data = self.create_test_data(fields, rows)
        recommendation = self.selector.recommend_chart_type(data)
        
        # Should fall back to table for empty data
        assert recommendation.chart_type == ChartType.TABLE
        assert recommendation.confidence <= 0.6  # Lower confidence for fallback
    
    def test_mixed_data_types_handling(self):
        """Test handling of mixed data types"""
        fields = [
            {'name': 'timestamp', 'data_type': DataType.TEMPORAL, 'unique_count': 10},
            {'name': 'category', 'data_type': DataType.CATEGORICAL, 'unique_count': 3},
            {'name': 'value', 'data_type': DataType.NUMERICAL, 'unique_count': 8},
            {'name': 'flag', 'data_type': DataType.BOOLEAN, 'unique_count': 2}
        ]
        
        rows = []
        base_date = datetime(2024, 1, 1)
        for i in range(10):
            rows.append({
                'timestamp': base_date + timedelta(days=i),
                'category': f'Cat{i % 3}',
                'value': i * 10,
                'flag': i % 2 == 0
            })
        
        data = self.create_test_data(fields, rows)
        recommendation = self.selector.recommend_chart_type(data)
        
        # Should handle mixed data appropriately
        assert recommendation.chart_type in [ChartType.LINE, ChartType.BAR, ChartType.TABLE]
        assert recommendation.confidence > 0.5
        assert recommendation.config is not None
    
    def test_recommendation_alternatives(self):
        """Test that recommendations include alternatives"""
        fields = [
            {'name': 'month', 'data_type': DataType.TEMPORAL, 'unique_count': 12},
            {'name': 'revenue', 'data_type': DataType.NUMERICAL, 'unique_count': 12}
        ]
        
        rows = []
        base_date = datetime(2024, 1, 1)
        for i in range(12):
            rows.append({
                'month': base_date.replace(month=i+1),
                'revenue': 100000 + i * 5000
            })
        
        data = self.create_test_data(fields, rows)
        recommendation = self.selector.recommend_chart_type(data)
        
        # Should include alternative recommendations
        assert len(recommendation.alternatives) > 0
        assert len(recommendation.alternatives) <= 4  # Max 4 alternatives
        
        # Alternatives should have lower confidence than primary
        for alt in recommendation.alternatives:
            assert alt.confidence <= recommendation.confidence
            assert alt.chart_type != recommendation.chart_type
    
    def test_data_analysis_method(self):
        """Test internal data analysis method"""
        fields = [
            {'name': 'category', 'data_type': DataType.CATEGORICAL, 'unique_count': 5},
            {'name': 'value', 'data_type': DataType.NUMERICAL, 'unique_count': 20}
        ]
        
        rows = [
            {'category': f'Cat{i%5}', 'value': i}
            for i in range(20)
        ]
        
        data = self.create_test_data(fields, rows)
        analysis = self.selector._analyze_data(data)
        
        # Validate analysis structure
        assert 'field_count' in analysis
        assert 'row_count' in analysis
        assert 'field_types' in analysis
        assert 'categorical_fields' in analysis
        assert 'numerical_fields' in analysis
        assert 'data_pattern' in analysis
        
        assert analysis['field_count'] == 2
        assert analysis['row_count'] == 20
        assert 'category' in analysis['categorical_fields']
        assert 'value' in analysis['numerical_fields']
        assert analysis['data_pattern'] == 'categorical_comparison'
    
    def test_field_analysis_method(self):
        """Test internal field analysis method"""
        field = DataField(
            name='test_field',
            data_type=DataType.NUMERICAL,
            unique_count=10
        )
        
        rows = [{'test_field': i * 2.5} for i in range(20)]
        
        analysis = self.selector._analyze_field(field, rows)
        
        # Validate field analysis structure
        assert 'data_type' in analysis
        assert 'unique_count' in analysis
        assert 'null_percentage' in analysis
        assert 'is_key_field' in analysis
        
        assert analysis['data_type'] == DataType.NUMERICAL
        assert analysis['unique_count'] == 20  # All unique values
        assert analysis['null_percentage'] == 0.0
        assert analysis['is_key_field'] == True  # High uniqueness


def test_chart_selector_integration():
    """Integration test for chart selector with realistic data"""
    selector = ChartTypeSelector()
    
    # Test realistic web analytics data
    fields = [
        DataField(name='date', data_type=DataType.TEMPORAL),
        DataField(name='page_views', data_type=DataType.NUMERICAL),
        DataField(name='unique_visitors', data_type=DataType.NUMERICAL),
        DataField(name='browser', data_type=DataType.CATEGORICAL)
    ]
    
    rows = []
    base_date = datetime(2024, 1, 1)
    browsers = ['Chrome', 'Firefox', 'Safari', 'Edge']
    
    for i in range(30):
        for browser in browsers:
            rows.append({
                'date': base_date + timedelta(days=i),
                'page_views': 1000 + i * 50 + hash(browser) % 200,
                'unique_visitors': 800 + i * 30 + hash(browser) % 150,
                'browser': browser
            })
    
    data = ChartData(fields=fields, rows=rows, total_rows=len(rows))
    
    # Should recommend line chart for time series data
    recommendation = selector.recommend_chart_type(data)
    
    assert recommendation.chart_type == ChartType.LINE
    assert recommendation.confidence > 0.8
    assert recommendation.config.x_axis == 'date'
    assert recommendation.config.y_axis in ['page_views', 'unique_visitors']
    assert len(recommendation.alternatives) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])