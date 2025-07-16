"""
Comprehensive test suite for interactive chart features

Tests the interactive chart service functionality including filtering,
drill-down, selection modes, and crossfilter capabilities.
"""
import pytest
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
import plotly.graph_objects as go

from app.models.chart import (
    ChartData, DataField, DataType, ChartConfig, ChartType, 
    ColorScheme, ChartFilter, ChartSelection, DrillDownConfig,
    InteractionEvent, ChartInteractiveConfig, InteractiveChartResponse,
    FilterOperation, SelectionMode, InteractionType
)
from app.services.interactive_charts import InteractiveChartService


class TestInteractiveChartService:
    """Test suite for InteractiveChartService"""
    
    def setup_method(self):
        """Setup test environment"""
        self.service = InteractiveChartService()
    
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
    
    def test_create_basic_interactive_chart(self):
        """Test basic interactive chart creation"""
        # Create test data
        fields = [
            {'name': 'category', 'data_type': DataType.CATEGORICAL, 'unique_count': 3},
            {'name': 'value', 'data_type': DataType.NUMERICAL, 'unique_count': 15}
        ]
        
        rows = [
            {'category': 'A', 'value': 10},
            {'category': 'B', 'value': 20},
            {'category': 'C', 'value': 15},
            {'category': 'A', 'value': 12},
            {'category': 'B', 'value': 18}
        ]
        
        data = self.create_test_data(fields, rows)
        config = ChartConfig(
            chart_type=ChartType.BAR,
            title="Test Interactive Chart",
            x_axis='category',
            y_axis='value',
            interactive=True,
            zoom_enabled=True,
            pan_enabled=True,
            hover_enabled=True
        )
        
        response = self.service.create_interactive_chart(data, config)
        
        # Validate response
        assert isinstance(response, InteractiveChartResponse)
        assert response.chart_type == ChartType.BAR
        assert response.config.interactive == True
        assert response.generation_time > 0
        assert response.plotly_json is not None
        
        # Validate the interactive config
        assert isinstance(response.interactive_config, ChartInteractiveConfig)
        assert response.interactive_config.zoom_level == 1.0
    
    def test_chart_filtering_capabilities(self):
        """Test chart data filtering functionality"""
        # Create test data with various data types
        fields = [
            {'name': 'department', 'data_type': DataType.CATEGORICAL, 'unique_count': 4},
            {'name': 'sales', 'data_type': DataType.NUMERICAL, 'unique_count': 10},
            {'name': 'date', 'data_type': DataType.TEMPORAL, 'unique_count': 10},
            {'name': 'description', 'data_type': DataType.TEXT, 'unique_count': 8}
        ]
        
        rows = []
        departments = ['Engineering', 'Marketing', 'Sales', 'Support']
        for i in range(20):
            rows.append({
                'department': departments[i % 4],
                'sales': 1000 + (i * 100),
                'date': (datetime(2024, 1, 1) + timedelta(days=i)).isoformat(),
                'description': f'Description for item {i}'
            })
        
        data = self.create_test_data(fields, rows)
        
        # Test various filter operations
        test_filters = [
            # Equals filter
            ChartFilter(field='department', operation=FilterOperation.EQUALS, value='Engineering'),
            # Greater than filter
            ChartFilter(field='sales', operation=FilterOperation.GREATER_THAN, value=1500),
            # Contains filter
            ChartFilter(field='description', operation=FilterOperation.CONTAINS, value='item 1')
        ]
        
        interactive_config = ChartInteractiveConfig(filters=test_filters)
        config = ChartConfig(
            chart_type=ChartType.BAR,
            x_axis='department',
            y_axis='sales'
        )
        
        response = self.service.create_interactive_chart(data, config, interactive_config)
        
        # Validate filtering worked
        assert response.data_summary['total_rows'] < 20  # Should be filtered
        assert len(response.interactive_config.filters) == 3
        
        # Validate filter application
        filtered_data = self.service._apply_filters(data, test_filters)
        assert filtered_data.total_rows < data.total_rows
    
    def test_single_filter_operations(self):
        """Test individual filter operations"""
        # Create test dataframe
        df = pd.DataFrame([
            {'name': 'Alice', 'age': 25, 'salary': 50000, 'department': 'Engineering'},
            {'name': 'Bob', 'age': 30, 'salary': 60000, 'department': 'Marketing'},
            {'name': 'Charlie', 'age': 35, 'salary': 70000, 'department': 'Sales'},
            {'name': 'Diana', 'age': 28, 'salary': 55000, 'department': 'Engineering'},
            {'name': 'Eve', 'age': 32, 'salary': 65000, 'department': 'Support'}
        ])
        
        # Test EQUALS filter
        filter_config = ChartFilter(field='department', operation=FilterOperation.EQUALS, value='Engineering')
        result = self.service._apply_single_filter(df, filter_config)
        assert len(result) == 2
        assert all(result['department'] == 'Engineering')
        
        # Test GREATER_THAN filter
        filter_config = ChartFilter(field='salary', operation=FilterOperation.GREATER_THAN, value=55000)
        result = self.service._apply_single_filter(df, filter_config)
        assert len(result) == 3
        assert all(result['salary'] > 55000)
        
        # Test CONTAINS filter (case sensitive)
        filter_config = ChartFilter(field='name', operation=FilterOperation.CONTAINS, value='a', case_sensitive=False)
        result = self.service._apply_single_filter(df, filter_config)
        assert len(result) == 3  # Alice, Diana, Charlie
        
        # Test IN filter
        filter_config = ChartFilter(field='department', operation=FilterOperation.IN, value=['Engineering', 'Sales'])
        result = self.service._apply_single_filter(df, filter_config)
        assert len(result) == 3
        
        # Test BETWEEN filter
        filter_config = ChartFilter(field='age', operation=FilterOperation.BETWEEN, value=[25, 30])
        result = self.service._apply_single_filter(df, filter_config)
        assert len(result) == 3  # Alice (25), Bob (30), Diana (28)
    
    def test_drill_down_functionality(self):
        """Test drill-down feature"""
        # Create hierarchical test data
        fields = [
            {'name': 'region', 'data_type': DataType.CATEGORICAL, 'unique_count': 3},
            {'name': 'country', 'data_type': DataType.CATEGORICAL, 'unique_count': 6},
            {'name': 'city', 'data_type': DataType.CATEGORICAL, 'unique_count': 12},
            {'name': 'revenue', 'data_type': DataType.NUMERICAL, 'unique_count': 20}
        ]
        
        rows = [
            {'region': 'North America', 'country': 'USA', 'city': 'New York', 'revenue': 100000},
            {'region': 'North America', 'country': 'USA', 'city': 'Los Angeles', 'revenue': 90000},
            {'region': 'North America', 'country': 'Canada', 'city': 'Toronto', 'revenue': 80000},
            {'region': 'Europe', 'country': 'Germany', 'city': 'Berlin', 'revenue': 75000},
            {'region': 'Europe', 'country': 'France', 'city': 'Paris', 'revenue': 85000},
            {'region': 'Asia', 'country': 'Japan', 'city': 'Tokyo', 'revenue': 95000}
        ]
        
        data = self.create_test_data(fields, rows)
        
        # Configure drill-down
        drill_config = DrillDownConfig(
            enabled=True,
            target_field='region',
            breadcrumb_enabled=True,
            max_levels=3
        )
        
        interactive_config = ChartInteractiveConfig(drill_down=drill_config)
        config = ChartConfig(
            chart_type=ChartType.BAR,
            x_axis='region',
            y_axis='revenue',
            drill_down_enabled=True
        )
        
        response = self.service.create_interactive_chart(data, config, interactive_config)
        
        # Validate drill-down configuration
        assert response.interactive_config.drill_down.enabled == True
        assert response.interactive_config.drill_down.target_field == 'region'
        assert response.interactive_config.drill_down.max_levels == 3
        
        # Test drill-down interaction
        drill_event_data = {
            'field': 'region',
            'value': 'North America',
            'point': {'x': 'North America', 'y': 100000}
        }
        
        result = self.service.handle_interaction_event(
            chart_id=response.chart_id,
            event_type=InteractionType.DRILL_DOWN,
            event_data=drill_event_data
        )
        
        assert result['status'] == 'drill_down'
        assert result['field'] == 'region'
        assert result['value'] == 'North America'
        assert len(result['suggested_filters']) == 1
    
    def test_chart_selection_events(self):
        """Test chart selection and interaction events"""
        # Create test data
        fields = [
            {'name': 'x_value', 'data_type': DataType.NUMERICAL, 'unique_count': 10},
            {'name': 'y_value', 'data_type': DataType.NUMERICAL, 'unique_count': 10}
        ]
        
        rows = [{'x_value': i, 'y_value': i * 2 + 5} for i in range(10)]
        
        data = self.create_test_data(fields, rows)
        config = ChartConfig(
            chart_type=ChartType.SCATTER,
            x_axis='x_value',
            y_axis='y_value',
            brush_enabled=True,
            lasso_enabled=True
        )
        
        response = self.service.create_interactive_chart(data, config)
        chart_id = response.chart_id
        
        # Test selection event
        selection_event_data = {
            'points': [
                {'x': 1, 'y': 7},
                {'x': 2, 'y': 9},
                {'x': 3, 'y': 11}
            ],
            'mode': 'multiple'
        }
        
        result = self.service.handle_interaction_event(
            chart_id=chart_id,
            event_type=InteractionType.SELECT,
            event_data=selection_event_data
        )
        
        assert result['status'] == 'selected'
        assert result['selected_count'] == 3
        assert result['selection_mode'] == 'multiple'
        
        # Test brush selection event
        brush_event_data = {
            'bounds': {'x0': 1, 'x1': 5, 'y0': 7, 'y1': 15},
            'points': [{'x': 2, 'y': 9}, {'x': 3, 'y': 11}, {'x': 4, 'y': 13}]
        }
        
        result = self.service.handle_interaction_event(
            chart_id=chart_id,
            event_type=InteractionType.BRUSH,
            event_data=brush_event_data
        )
        
        assert result['status'] == 'brushed'
        assert result['selected_count'] == 3
        assert result['crossfilter_ready'] == True
        assert 'bounds' in result
    
    def test_linked_charts_creation(self):
        """Test creation of linked charts with crossfilter"""
        # Create test data for multiple charts
        sales_data = self.create_test_data(
            [
                {'name': 'month', 'data_type': DataType.TEMPORAL, 'unique_count': 6},
                {'name': 'sales', 'data_type': DataType.NUMERICAL, 'unique_count': 6}
            ],
            [
                {'month': '2024-01', 'sales': 10000},
                {'month': '2024-02', 'sales': 12000},
                {'month': '2024-03', 'sales': 11000},
                {'month': '2024-04', 'sales': 13000},
                {'month': '2024-05', 'sales': 14000},
                {'month': '2024-06', 'sales': 15000}
            ]
        )
        
        region_data = self.create_test_data(
            [
                {'name': 'region', 'data_type': DataType.CATEGORICAL, 'unique_count': 4},
                {'name': 'revenue', 'data_type': DataType.NUMERICAL, 'unique_count': 4}
            ],
            [
                {'region': 'North', 'revenue': 25000},
                {'region': 'South', 'revenue': 20000},
                {'region': 'East', 'revenue': 22000},
                {'region': 'West', 'revenue': 23000}
            ]
        )
        
        # Create chart configurations
        chart_configs = [
            (sales_data, ChartConfig(chart_type=ChartType.LINE, x_axis='month', y_axis='sales')),
            (region_data, ChartConfig(chart_type=ChartType.BAR, x_axis='region', y_axis='revenue'))
        ]
        
        # Create linked charts
        linked_charts = self.service.create_linked_charts(chart_configs, crossfilter_enabled=True)
        
        # Validate linked charts
        assert len(linked_charts) == 2
        
        for chart in linked_charts:
            assert isinstance(chart, InteractiveChartResponse)
            assert chart.interactive_config.crossfilter_enabled == True
            assert len(chart.interactive_config.linked_charts) == 1
            
        # Validate cross-linking
        chart1, chart2 = linked_charts
        assert chart2.chart_id in chart1.interactive_config.linked_charts
        assert chart1.chart_id in chart2.interactive_config.linked_charts
    
    def test_chart_state_management(self):
        """Test chart state management functionality"""
        # Create test chart
        data = self.create_test_data(
            [{'name': 'value', 'data_type': DataType.NUMERICAL, 'unique_count': 5}],
            [{'value': i} for i in range(5)]
        )
        
        config = ChartConfig(chart_type=ChartType.BAR, y_axis='value')
        response = self.service.create_interactive_chart(data, config)
        chart_id = response.chart_id
        
        # Initially no state
        state = self.service.get_chart_state(chart_id)
        assert state['chart_id'] == chart_id
        assert state['has_selection'] == False
        
        # Create selection
        selection_event = {
            'points': [{'x': 0, 'y': 10}],
            'mode': 'single'
        }
        
        self.service.handle_interaction_event(
            chart_id=chart_id,
            event_type=InteractionType.SELECT,
            event_data=selection_event
        )
        
        # Check state after selection
        state = self.service.get_chart_state(chart_id)
        assert state['has_selection'] == True
        assert 'selection' in state
        
        # Clear state
        self.service.clear_chart_state(chart_id)
        
        # Check state after clearing
        state = self.service.get_chart_state(chart_id)
        assert state['has_selection'] == False
    
    def test_crossfilter_enhancement(self):
        """Test crossfilter feature enhancement"""
        data = self.create_test_data(
            [
                {'name': 'category', 'data_type': DataType.CATEGORICAL, 'unique_count': 3},
                {'name': 'value', 'data_type': DataType.NUMERICAL, 'unique_count': 10}
            ],
            [
                {'category': 'A', 'value': 10},
                {'category': 'B', 'value': 20},
                {'category': 'C', 'value': 15}
            ]
        )
        
        interactive_config = ChartInteractiveConfig(crossfilter_enabled=True)
        config = ChartConfig(
            chart_type=ChartType.BAR,
            x_axis='category',
            y_axis='value',
            crossfilter_enabled=True
        )
        
        response = self.service.create_interactive_chart(data, config, interactive_config)
        
        # Validate crossfilter configuration
        assert response.interactive_config.crossfilter_enabled == True
        
        # Parse the plotly figure to check enhancements
        fig = go.Figure.from_json(response.plotly_json)
        assert len(fig.data) > 0
        
        # Check that hover template includes crossfilter information
        for trace in fig.data:
            if hasattr(trace, 'hovertemplate') and trace.hovertemplate:
                assert 'filter' in trace.hovertemplate.lower() or 'click' in trace.hovertemplate.lower()
    
    def test_error_handling(self):
        """Test error handling in interactive features"""
        # Test with invalid filter field
        data = self.create_test_data(
            [{'name': 'valid_field', 'data_type': DataType.NUMERICAL, 'unique_count': 5}],
            [{'valid_field': i} for i in range(5)]
        )
        
        # Apply filter on non-existent field
        invalid_filter = ChartFilter(
            field='non_existent_field',
            operation=FilterOperation.EQUALS,
            value='test'
        )
        
        interactive_config = ChartInteractiveConfig(filters=[invalid_filter])
        config = ChartConfig(chart_type=ChartType.BAR, y_axis='valid_field')
        
        # Should not raise error, but log warning and return original data
        response = self.service.create_interactive_chart(data, config, interactive_config)
        assert response.data_summary['total_rows'] == 5  # No filtering applied
        
        # Test unhandled interaction type
        result = self.service.handle_interaction_event(
            chart_id='test_chart',
            event_type='invalid_type',  # Invalid interaction type
            event_data={}
        )
        
        assert result['status'] == 'unhandled'
    
    def test_complex_filtering_scenario(self):
        """Test complex multi-filter scenarios"""
        # Create comprehensive test data
        fields = [
            {'name': 'name', 'data_type': DataType.TEXT, 'unique_count': 20},
            {'name': 'age', 'data_type': DataType.NUMERICAL, 'unique_count': 15},
            {'name': 'department', 'data_type': DataType.CATEGORICAL, 'unique_count': 5},
            {'name': 'salary', 'data_type': DataType.NUMERICAL, 'unique_count': 18},
            {'name': 'active', 'data_type': DataType.BOOLEAN, 'unique_count': 2}
        ]
        
        rows = []
        departments = ['Engineering', 'Marketing', 'Sales', 'Support', 'Finance']
        for i in range(20):
            rows.append({
                'name': f'Employee_{i}',
                'age': 25 + (i % 15),
                'department': departments[i % 5],
                'salary': 50000 + (i * 2000),
                'active': i % 3 != 0  # Some inactive employees
            })
        
        data = self.create_test_data(fields, rows)
        
        # Apply multiple complex filters
        complex_filters = [
            ChartFilter(field='age', operation=FilterOperation.BETWEEN, value=[28, 35]),
            ChartFilter(field='department', operation=FilterOperation.IN, value=['Engineering', 'Marketing']),
            ChartFilter(field='salary', operation=FilterOperation.GREATER_THAN, value=55000),
            ChartFilter(field='name', operation=FilterOperation.CONTAINS, value='Employee_1', case_sensitive=True)
        ]
        
        interactive_config = ChartInteractiveConfig(filters=complex_filters)
        config = ChartConfig(
            chart_type=ChartType.SCATTER,
            x_axis='age',
            y_axis='salary',
            color_field='department'
        )
        
        response = self.service.create_interactive_chart(data, config, interactive_config)
        
        # Validate complex filtering
        assert response.data_summary['total_rows'] < 20
        assert len(response.interactive_config.filters) == 4
        
        # Manually validate filter logic
        filtered_data = self.service._apply_filters(data, complex_filters)
        df = pd.DataFrame(filtered_data.rows)
        
        # Check that all conditions are met
        assert all(df['age'].between(28, 35))
        assert all(df['department'].isin(['Engineering', 'Marketing']))
        assert all(df['salary'] > 55000)
        assert all(df['name'].str.contains('Employee_1'))


def test_interactive_chart_integration():
    """Integration test for interactive chart functionality"""
    service = InteractiveChartService()
    
    # Create realistic business data
    fields = [
        DataField(name='quarter', data_type=DataType.TEMPORAL),
        DataField(name='product', data_type=DataType.CATEGORICAL),
        DataField(name='region', data_type=DataType.CATEGORICAL),
        DataField(name='sales', data_type=DataType.NUMERICAL),
        DataField(name='profit', data_type=DataType.NUMERICAL)
    ]
    
    rows = []
    quarters = ['2024-Q1', '2024-Q2', '2024-Q3', '2024-Q4']
    products = ['Product A', 'Product B', 'Product C']
    regions = ['North', 'South', 'East', 'West']
    
    for quarter in quarters:
        for product in products:
            for region in regions:
                sales = 10000 + hash(quarter + product + region) % 50000
                profit = sales * (0.15 + (hash(product + region) % 100) / 1000)
                rows.append({
                    'quarter': quarter,
                    'product': product,
                    'region': region,
                    'sales': sales,
                    'profit': profit
                })
    
    data = ChartData(fields=fields, rows=rows, total_rows=len(rows))
    
    # Test interactive scatter plot with filters
    filters = [
        ChartFilter(field='region', operation=FilterOperation.IN, value=['North', 'South']),
        ChartFilter(field='sales', operation=FilterOperation.GREATER_THAN, value=20000)
    ]
    
    interactive_config = ChartInteractiveConfig(
        filters=filters,
        crossfilter_enabled=True,
        drill_down=DrillDownConfig(enabled=True, target_field='product')
    )
    
    config = ChartConfig(
        chart_type=ChartType.SCATTER,
        title="Sales vs Profit Analysis",
        x_axis='sales',
        y_axis='profit',
        color_field='product',
        size_field='sales',
        interactive=True,
        drill_down_enabled=True,
        crossfilter_enabled=True
    )
    
    response = service.create_interactive_chart(data, config, interactive_config)
    
    # Validate comprehensive interactive features
    assert response.chart_type == ChartType.SCATTER
    assert response.generation_time > 0
    assert response.data_summary['total_rows'] < len(rows)  # Filtered
    assert response.interactive_config.crossfilter_enabled == True
    assert response.interactive_config.drill_down.enabled == True
    assert len(response.interactive_config.filters) == 2
    
    # Test interaction handling
    drill_event = {
        'field': 'product',
        'value': 'Product A',
        'point': {'x': 25000, 'y': 3750}
    }
    
    interaction_result = service.handle_interaction_event(
        chart_id=response.chart_id,
        event_type=InteractionType.DRILL_DOWN,
        event_data=drill_event,
        user_id='test_user'
    )
    
    assert interaction_result['status'] == 'drill_down'
    assert interaction_result['field'] == 'product'
    assert interaction_result['value'] == 'Product A'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])