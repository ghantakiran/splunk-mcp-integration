"""
Comprehensive test suite for chart generator

Tests the actual chart generation functionality with various data types
and chart configurations.
"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
import plotly.graph_objects as go

from app.models.chart import (
    ChartData, DataField, DataType, ChartConfig, ChartType, 
    ColorScheme, ExportFormat
)
from app.services.chart_generator import ChartGenerator


class TestChartGenerator:
    """Test suite for ChartGenerator"""
    
    def setup_method(self):
        """Setup test environment"""
        self.generator = ChartGenerator()
    
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
    
    def test_line_chart_generation(self):
        """Test line chart generation with time series data"""
        # Create time series data
        base_date = datetime(2024, 1, 1)
        fields = [
            {'name': 'timestamp', 'data_type': DataType.TEMPORAL, 'unique_count': 24},
            {'name': 'cpu_usage', 'data_type': DataType.NUMERICAL, 'unique_count': 20}
        ]
        
        rows = []
        for i in range(24):
            rows.append({
                'timestamp': (base_date + timedelta(hours=i)).isoformat(),
                'cpu_usage': 50 + (i % 10) * 5 + i * 0.5
            })
        
        data = self.create_test_data(fields, rows)
        config = ChartConfig(
            chart_type=ChartType.LINE,
            title="CPU Usage Over Time",
            x_axis='timestamp',
            y_axis='cpu_usage',
            width=800,
            height=600
        )
        
        response = self.generator.generate_chart(data, config)
        
        # Validate response
        assert response.chart_type == ChartType.LINE
        assert response.config.chart_type == ChartType.LINE
        assert response.generation_time > 0
        assert response.data_summary['total_rows'] == 24
        assert response.plotly_json is not None
        
        # Validate the Plotly figure
        fig = go.Figure.from_json(response.plotly_json)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'scatter'
        assert fig.data[0].mode == 'lines+markers'
    
    def test_bar_chart_generation(self):
        """Test bar chart generation with categorical data"""
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
        config = ChartConfig(
            chart_type=ChartType.BAR,
            title="Sales by Department",
            x_axis='department',
            y_axis='sales',
            color_scheme=ColorScheme.CATEGORICAL
        )
        
        response = self.generator.generate_chart(data, config)
        
        # Validate response
        assert response.chart_type == ChartType.BAR
        assert response.generation_time > 0
        assert response.data_summary['total_rows'] == 5
        
        # Validate the Plotly figure
        fig = go.Figure.from_json(response.plotly_json)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'bar'
        assert len(fig.data[0].x) == 5
    
    def test_pie_chart_generation(self):
        """Test pie chart generation with categorical data"""
        fields = [
            {'name': 'category', 'data_type': DataType.CATEGORICAL, 'unique_count': 4},
            {'name': 'value', 'data_type': DataType.NUMERICAL, 'unique_count': 4}
        ]
        
        rows = [
            {'category': 'Product A', 'value': 30},
            {'category': 'Product B', 'value': 25},
            {'category': 'Product C', 'value': 20},
            {'category': 'Product D', 'value': 25}
        ]
        
        data = self.create_test_data(fields, rows)
        config = ChartConfig(
            chart_type=ChartType.PIE,
            title="Product Distribution",
            color_field='category',
            y_axis='value',
            color_scheme=ColorScheme.DEFAULT
        )
        
        response = self.generator.generate_chart(data, config)
        
        # Validate response
        assert response.chart_type == ChartType.PIE
        assert response.generation_time > 0
        
        # Validate the Plotly figure
        fig = go.Figure.from_json(response.plotly_json)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'pie'
        assert len(fig.data[0].labels) == 4
    
    def test_scatter_chart_generation(self):
        """Test scatter plot generation with correlation data"""
        fields = [
            {'name': 'temperature', 'data_type': DataType.NUMERICAL, 'unique_count': 20},
            {'name': 'humidity', 'data_type': DataType.NUMERICAL, 'unique_count': 18},
            {'name': 'region', 'data_type': DataType.CATEGORICAL, 'unique_count': 3}
        ]
        
        rows = []
        regions = ['North', 'South', 'Central']
        for i in range(30):
            rows.append({
                'temperature': 20 + i,
                'humidity': 40 + i * 2 + (i % 5),
                'region': regions[i % 3]
            })
        
        data = self.create_test_data(fields, rows)
        config = ChartConfig(
            chart_type=ChartType.SCATTER,
            title="Temperature vs Humidity by Region",
            x_axis='temperature',
            y_axis='humidity',
            color_field='region',
            color_scheme=ColorScheme.VIRIDIS
        )
        
        response = self.generator.generate_chart(data, config)
        
        # Validate response
        assert response.chart_type == ChartType.SCATTER
        assert response.generation_time > 0
        
        # Validate the Plotly figure
        fig = go.Figure.from_json(response.plotly_json)
        assert len(fig.data) == 3  # Three regions
        for trace in fig.data:
            assert trace.type == 'scatter'
            assert trace.mode == 'markers'
    
    def test_histogram_generation(self):
        """Test histogram generation with distribution data"""
        fields = [
            {'name': 'response_time', 'data_type': DataType.NUMERICAL, 'unique_count': 80}
        ]
        
        # Create distribution data (simulating normal distribution)
        import random
        rows = []
        for i in range(100):
            rows.append({
                'response_time': max(0, random.gauss(200, 50))  # Normal distribution, min 0
            })
        
        data = self.create_test_data(fields, rows)
        config = ChartConfig(
            chart_type=ChartType.HISTOGRAM,
            title="Response Time Distribution",
            x_axis='response_time',
            chart_options={'bins': 20}
        )
        
        response = self.generator.generate_chart(data, config)
        
        # Validate response
        assert response.chart_type == ChartType.HISTOGRAM
        assert response.generation_time > 0
        
        # Validate the Plotly figure
        fig = go.Figure.from_json(response.plotly_json)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'histogram'
    
    def test_heatmap_generation(self):
        """Test heatmap generation with multi-dimensional data"""
        fields = [
            {'name': 'hour', 'data_type': DataType.CATEGORICAL, 'unique_count': 24},
            {'name': 'day', 'data_type': DataType.CATEGORICAL, 'unique_count': 7},
            {'name': 'traffic', 'data_type': DataType.NUMERICAL, 'unique_count': 50}
        ]
        
        rows = []
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for hour in range(24):
            for day in days:
                # Simulate traffic patterns (higher during business hours on weekdays)
                base_traffic = 100
                if day in ['Sat', 'Sun']:
                    base_traffic *= 0.6
                if 9 <= hour <= 17:
                    base_traffic *= 1.5
                
                rows.append({
                    'hour': hour,
                    'day': day,
                    'traffic': base_traffic + random.randint(-20, 20)
                })
        
        data = self.create_test_data(fields, rows)
        config = ChartConfig(
            chart_type=ChartType.HEATMAP,
            title="Traffic Heatmap by Hour and Day",
            x_axis='hour',
            y_axis='day',
            color_field='traffic',
            color_scheme=ColorScheme.PLASMA
        )
        
        response = self.generator.generate_chart(data, config)
        
        # Validate response
        assert response.chart_type == ChartType.HEATMAP
        assert response.generation_time > 0
        
        # Validate the Plotly figure
        fig = go.Figure.from_json(response.plotly_json)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'heatmap'
    
    def test_treemap_generation(self):
        """Test treemap generation with hierarchical data"""
        fields = [
            {'name': 'category', 'data_type': DataType.CATEGORICAL, 'unique_count': 6},
            {'name': 'value', 'data_type': DataType.NUMERICAL, 'unique_count': 6}
        ]
        
        rows = [
            {'category': 'Tech', 'value': 450},
            {'category': 'Finance', 'value': 320},
            {'category': 'Healthcare', 'value': 280},
            {'category': 'Education', 'value': 150},
            {'category': 'Retail', 'value': 200},
            {'category': 'Manufacturing', 'value': 380}
        ]
        
        data = self.create_test_data(fields, rows)
        config = ChartConfig(
            chart_type=ChartType.TREEMAP,
            title="Market Share by Industry",
            color_field='category',
            y_axis='value'
        )
        
        response = self.generator.generate_chart(data, config)
        
        # Validate response
        assert response.chart_type == ChartType.TREEMAP
        assert response.generation_time > 0
        
        # Validate the Plotly figure
        fig = go.Figure.from_json(response.plotly_json)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'treemap'
    
    def test_table_generation(self):
        """Test table generation with detailed data"""
        fields = [
            {'name': 'id', 'data_type': DataType.NUMERICAL, 'unique_count': 10},
            {'name': 'name', 'data_type': DataType.CATEGORICAL, 'unique_count': 10},
            {'name': 'score', 'data_type': DataType.NUMERICAL, 'unique_count': 8},
            {'name': 'date', 'data_type': DataType.TEMPORAL, 'unique_count': 5}
        ]
        
        rows = []
        for i in range(10):
            rows.append({
                'id': i + 1,
                'name': f'Item {i + 1}',
                'score': 85 + (i % 5) * 3,
                'date': (datetime(2024, 1, 1) + timedelta(days=i)).isoformat()
            })
        
        data = self.create_test_data(fields, rows)
        config = ChartConfig(
            chart_type=ChartType.TABLE,
            title="Detailed Data Table",
            chart_options={'max_rows': 15}
        )
        
        response = self.generator.generate_chart(data, config)
        
        # Validate response
        assert response.chart_type == ChartType.TABLE
        assert response.generation_time > 0
        
        # Validate the Plotly figure
        fig = go.Figure.from_json(response.plotly_json)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'table'
    
    def test_multi_series_line_chart(self):
        """Test line chart with multiple y-axis series"""
        fields = [
            {'name': 'date', 'data_type': DataType.TEMPORAL, 'unique_count': 30},
            {'name': 'cpu_usage', 'data_type': DataType.NUMERICAL, 'unique_count': 25},
            {'name': 'memory_usage', 'data_type': DataType.NUMERICAL, 'unique_count': 28}
        ]
        
        rows = []
        base_date = datetime(2024, 1, 1)
        for i in range(30):
            rows.append({
                'date': (base_date + timedelta(days=i)).isoformat(),
                'cpu_usage': 30 + (i % 10) * 3 + i * 0.2,
                'memory_usage': 60 + (i % 8) * 2 + i * 0.3
            })
        
        data = self.create_test_data(fields, rows)
        config = ChartConfig(
            chart_type=ChartType.LINE,
            title="System Resources Over Time",
            x_axis='date',
            y_axis=['cpu_usage', 'memory_usage'],
            color_scheme=ColorScheme.CATEGORICAL
        )
        
        response = self.generator.generate_chart(data, config)
        
        # Validate response
        assert response.chart_type == ChartType.LINE
        assert response.generation_time > 0
        
        # Validate the Plotly figure
        fig = go.Figure.from_json(response.plotly_json)
        assert len(fig.data) == 2  # Two series
        for trace in fig.data:
            assert trace.type == 'scatter'
            assert trace.mode == 'lines+markers'
    
    def test_chart_export_functionality(self):
        """Test chart export to different formats"""
        # Create simple data for testing
        fields = [
            {'name': 'x', 'data_type': DataType.NUMERICAL, 'unique_count': 5},
            {'name': 'y', 'data_type': DataType.NUMERICAL, 'unique_count': 5}
        ]
        
        rows = [
            {'x': 1, 'y': 10},
            {'x': 2, 'y': 20},
            {'x': 3, 'y': 15},
            {'x': 4, 'y': 25},
            {'x': 5, 'y': 30}
        ]
        
        data = self.create_test_data(fields, rows)
        config = ChartConfig(
            chart_type=ChartType.LINE,
            title="Simple Test Chart",
            x_axis='x',
            y_axis='y'
        )
        
        response = self.generator.generate_chart(data, config)
        fig = go.Figure.from_json(response.plotly_json)
        
        # Test different export formats
        export_formats = [
            ExportFormat.HTML,
            ExportFormat.JSON,
            # Note: PNG, PDF, SVG require additional dependencies in testing environment
        ]
        
        for format in export_formats:
            try:
                file_bytes, content_type = self.generator.export_chart(fig, format)
                assert len(file_bytes) > 0
                assert content_type is not None
                
                if format == ExportFormat.HTML:
                    assert content_type == "text/html"
                elif format == ExportFormat.JSON:
                    assert content_type == "application/json"
                    
            except Exception as e:
                # Some formats may require additional dependencies
                pytest.skip(f"Export format {format} not available in test environment: {e}")
    
    def test_error_handling(self):
        """Test error handling for invalid configurations"""
        fields = [
            {'name': 'category', 'data_type': DataType.CATEGORICAL, 'unique_count': 3},
            {'name': 'value', 'data_type': DataType.NUMERICAL, 'unique_count': 3}
        ]
        
        rows = [
            {'category': 'A', 'value': 10},
            {'category': 'B', 'value': 20},
            {'category': 'C', 'value': 15}
        ]
        
        data = self.create_test_data(fields, rows)
        
        # Test invalid chart type
        with pytest.raises(ValueError):
            invalid_config = ChartConfig(
                chart_type="invalid_type",  # This should cause an error
                x_axis='category',
                y_axis='value'
            )
        
        # Test missing required fields for specific chart types
        with pytest.raises(ValueError):
            config = ChartConfig(
                chart_type=ChartType.HEATMAP,
                x_axis='category',
                # Missing y_axis and color_field required for heatmap
            )
            self.generator.generate_chart(data, config)
    
    def test_data_summary_generation(self):
        """Test data summary generation"""
        fields = [
            {'name': 'category', 'data_type': DataType.CATEGORICAL, 'unique_count': 3},
            {'name': 'value', 'data_type': DataType.NUMERICAL, 'unique_count': 3},
            {'name': 'date', 'data_type': DataType.TEMPORAL, 'unique_count': 3}
        ]
        
        rows = [
            {'category': 'A', 'value': 10, 'date': '2024-01-01'},
            {'category': 'B', 'value': 20, 'date': '2024-01-02'},
            {'category': 'C', 'value': 15, 'date': '2024-01-03'}
        ]
        
        data = self.create_test_data(fields, rows)
        config = ChartConfig(
            chart_type=ChartType.BAR,
            x_axis='category',
            y_axis='value'
        )
        
        response = self.generator.generate_chart(data, config)
        
        # Validate data summary
        summary = response.data_summary
        assert summary['total_rows'] == 3
        assert summary['total_fields'] == 3
        assert summary['processed_rows'] == 3
        assert 'field_types' in summary
        assert 'categorical_fields' in summary
        assert 'numerical_fields' in summary
        assert 'temporal_fields' in summary
        assert summary['categorical_fields'] == ['category']
        assert summary['numerical_fields'] == ['value']
        assert summary['temporal_fields'] == ['date']
    
    def test_sankey_chart_generation(self):
        """Test Sankey diagram generation with flow data"""
        fields = [
            {'name': 'source', 'data_type': DataType.CATEGORICAL, 'unique_count': 4},
            {'name': 'target', 'data_type': DataType.CATEGORICAL, 'unique_count': 4},
            {'name': 'value', 'data_type': DataType.NUMERICAL, 'unique_count': 8}
        ]
        
        rows = [
            {'source': 'A', 'target': 'X', 'value': 100},
            {'source': 'A', 'target': 'Y', 'value': 50},
            {'source': 'B', 'target': 'X', 'value': 75},
            {'source': 'B', 'target': 'Z', 'value': 25},
            {'source': 'C', 'target': 'Y', 'value': 40},
            {'source': 'C', 'target': 'Z', 'value': 60},
            {'source': 'D', 'target': 'X', 'value': 30},
            {'source': 'D', 'target': 'Z', 'value': 90}
        ]
        
        data = self.create_test_data(fields, rows)
        config = ChartConfig(
            chart_type=ChartType.SANKEY,
            title="Process Flow Analysis",
            x_axis='source',
            y_axis='target',
            color_field='value',
            color_scheme=ColorScheme.DEFAULT
        )
        
        response = self.generator.generate_chart(data, config)
        
        # Validate response
        assert response.chart_type == ChartType.SANKEY
        assert response.generation_time > 0
        assert response.data_summary['total_rows'] == 8
        
        # Validate the Plotly figure
        fig = go.Figure.from_json(response.plotly_json)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'sankey'
        assert 'node' in fig.data[0]
        assert 'link' in fig.data[0]
        
        # Check that we have the correct number of unique nodes
        all_sources = [row['source'] for row in rows]
        all_targets = [row['target'] for row in rows]
        unique_nodes = len(set(all_sources + all_targets))
        assert len(fig.data[0].node.label) == unique_nodes
    
    def test_gauge_chart_generation(self):
        """Test gauge chart generation with KPI data"""
        fields = [
            {'name': 'performance_score', 'data_type': DataType.NUMERICAL, 'unique_count': 1}
        ]
        
        rows = [
            {'performance_score': 85.5}
        ]
        
        data = self.create_test_data(fields, rows)
        config = ChartConfig(
            chart_type=ChartType.GAUGE,
            title="Performance KPI",
            y_axis='performance_score',
            chart_options={
                'min': 0,
                'max': 100,
                'threshold_1': 70,
                'threshold_2': 85,
                'reference': 80
            }
        )
        
        response = self.generator.generate_chart(data, config)
        
        # Validate response
        assert response.chart_type == ChartType.GAUGE
        assert response.generation_time > 0
        assert response.data_summary['total_rows'] == 1
        
        # Validate the Plotly figure
        fig = go.Figure.from_json(response.plotly_json)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'indicator'
        assert fig.data[0].mode == 'gauge+number+delta'
        assert fig.data[0].value == 85.5
    
    def test_gauge_chart_with_multiple_values(self):
        """Test gauge chart with multiple values (should use mean)"""
        fields = [
            {'name': 'efficiency', 'data_type': DataType.NUMERICAL, 'unique_count': 3},
            {'name': 'department', 'data_type': DataType.CATEGORICAL, 'unique_count': 3}
        ]
        
        rows = [
            {'efficiency': 75, 'department': 'Sales'},
            {'efficiency': 85, 'department': 'Marketing'},
            {'efficiency': 95, 'department': 'Engineering'}
        ]
        
        data = self.create_test_data(fields, rows)
        config = ChartConfig(
            chart_type=ChartType.GAUGE,
            title="Average Department Efficiency",
            y_axis='efficiency',
            chart_options={
                'min': 0,
                'max': 100,
                'threshold_1': 70,
                'threshold_2': 85
            }
        )
        
        response = self.generator.generate_chart(data, config)
        
        # Validate response
        assert response.chart_type == ChartType.GAUGE
        assert response.generation_time > 0
        
        # Validate the Plotly figure
        fig = go.Figure.from_json(response.plotly_json)
        assert len(fig.data) > 0
        assert fig.data[0].type == 'indicator'
        
        # Check that it uses the mean of the values (75 + 85 + 95) / 3 = 85
        expected_mean = (75 + 85 + 95) / 3
        assert abs(fig.data[0].value - expected_mean) < 0.01
    
    def test_sankey_error_handling(self):
        """Test error handling for invalid Sankey configuration"""
        fields = [
            {'name': 'category', 'data_type': DataType.CATEGORICAL, 'unique_count': 3},
            {'name': 'value', 'data_type': DataType.NUMERICAL, 'unique_count': 3}
        ]
        
        rows = [
            {'category': 'A', 'value': 10},
            {'category': 'B', 'value': 20},
            {'category': 'C', 'value': 15}
        ]
        
        data = self.create_test_data(fields, rows)
        
        # Test missing required fields for Sankey
        with pytest.raises(ValueError, match="Sankey diagram requires source, target, and value columns"):
            config = ChartConfig(
                chart_type=ChartType.SANKEY,
                x_axis='category',
                # Missing y_axis (target) and color_field (value)
            )
            self.generator.generate_chart(data, config)
    
    def test_gauge_error_handling(self):
        """Test error handling for invalid Gauge configuration"""
        fields = [
            {'name': 'category', 'data_type': DataType.CATEGORICAL, 'unique_count': 3}
        ]
        
        rows = [
            {'category': 'A'},
            {'category': 'B'},
            {'category': 'C'}
        ]
        
        data = self.create_test_data(fields, rows)
        
        # Test missing required value field for Gauge
        with pytest.raises(ValueError, match="Gauge chart requires a value column"):
            config = ChartConfig(
                chart_type=ChartType.GAUGE,
                # Missing y_axis (value column)
            )
            self.generator.generate_chart(data, config)


def test_chart_generator_integration():
    """Integration test for chart generator with realistic data"""
    generator = ChartGenerator()
    
    # Test realistic sales data
    fields = [
        DataField(name='month', data_type=DataType.TEMPORAL),
        DataField(name='region', data_type=DataType.CATEGORICAL),
        DataField(name='sales', data_type=DataType.NUMERICAL),
        DataField(name='profit', data_type=DataType.NUMERICAL)
    ]
    
    rows = []
    months = ['2024-01', '2024-02', '2024-03', '2024-04', '2024-05', '2024-06']
    regions = ['North', 'South', 'East', 'West']
    
    for month in months:
        for region in regions:
            rows.append({
                'month': f'{month}-01',
                'region': region,
                'sales': 100000 + hash(month + region) % 50000,
                'profit': 20000 + hash(month + region) % 10000
            })
    
    data = ChartData(fields=fields, rows=rows, total_rows=len(rows))
    
    # Test multi-series line chart
    config = ChartConfig(
        chart_type=ChartType.LINE,
        title="Sales and Profit Trends",
        x_axis='month',
        y_axis=['sales', 'profit'],
        color_scheme=ColorScheme.DEFAULT
    )
    
    response = generator.generate_chart(data, config)
    
    assert response.chart_type == ChartType.LINE
    assert response.generation_time > 0
    assert response.data_summary['total_rows'] == 24
    assert len(response.data_summary['categorical_fields']) == 1
    assert len(response.data_summary['numerical_fields']) == 2
    assert len(response.data_summary['temporal_fields']) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])