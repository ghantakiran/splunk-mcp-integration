"""
Comprehensive test suite for chart customization features

Tests the chart customization service functionality including:
- Theme and color scheme customization
- Font and typography configuration
- Axis, legend, and grid styling
- Chart templates and presets
- API endpoints for customization
"""
import pytest
import json
from datetime import datetime
from typing import Dict, Any, List

from app.models.chart import (
    ChartData, DataField, DataType, ChartConfig, ChartType, 
    ChartCustomization, ChartTemplate, ChartTheme, FontFamily, 
    ColorScheme, ChartFont, ChartAxis, ChartLegend, ChartGrid, 
    ChartMargin, ChartTitle, ChartAnnotation, LegendPosition,
    AxisType, GridStyle
)
from app.services.chart_customization import ChartCustomizationService
from app.services.chart_generator import ChartGenerator
import plotly.graph_objects as go


class TestChartCustomizationService:
    """Test suite for ChartCustomizationService"""
    
    def setup_method(self):
        """Setup test environment"""
        self.service = ChartCustomizationService()
        self.generator = ChartGenerator()
        
    def create_test_data(self) -> ChartData:
        """Create test chart data"""
        fields = [
            DataField(name='category', data_type=DataType.CATEGORICAL, unique_count=5),
            DataField(name='value', data_type=DataType.NUMERICAL, unique_count=5),
            DataField(name='date', data_type=DataType.TEMPORAL, unique_count=5)
        ]
        
        rows = [
            {'category': 'A', 'value': 10, 'date': '2024-01-01'},
            {'category': 'B', 'value': 20, 'date': '2024-01-02'},
            {'category': 'C', 'value': 15, 'date': '2024-01-03'},
            {'category': 'D', 'value': 25, 'date': '2024-01-04'},
            {'category': 'E', 'value': 18, 'date': '2024-01-05'}
        ]
        
        return ChartData(fields=fields, rows=rows, total_rows=len(rows))
    
    def test_theme_application(self):
        """Test theme application to charts"""
        data = self.create_test_data()
        config = ChartConfig(
            chart_type=ChartType.BAR,
            x_axis='category',
            y_axis='value'
        )
        
        # Test different themes
        themes = [ChartTheme.DEFAULT, ChartTheme.DARK, ChartTheme.MINIMAL]
        
        for theme in themes:
            customization = ChartCustomization(theme=theme)
            
            # Generate chart
            fig = self.generator._generate_chart_by_type(
                self.generator._prepare_dataframe(data), 
                config
            )
            
            # Apply customization
            customized_fig = self.service.apply_customization(fig, config, customization)
            
            # Validate theme application
            assert customized_fig is not None
            assert isinstance(customized_fig, go.Figure)
            
            # Check theme config
            theme_config = self.service.get_theme_config(theme)
            assert theme_config is not None
            assert theme_config["template"] is not None
    
    def test_font_customization(self):
        """Test font customization"""
        data = self.create_test_data()
        config = ChartConfig(
            chart_type=ChartType.LINE,
            x_axis='date',
            y_axis='value'
        )
        
        # Test font configuration
        customization = ChartCustomization(
            font_family=FontFamily.ARIAL,
            font_size=14,
            title=ChartTitle(
                text="Test Chart",
                font=ChartFont(
                    family=FontFamily.HELVETICA,
                    size=18,
                    color="#333333",
                    bold=True
                )
            )
        )
        
        # Generate and customize chart
        fig = self.generator._generate_chart_by_type(
            self.generator._prepare_dataframe(data), 
            config
        )
        
        customized_fig = self.service.apply_customization(fig, config, customization)
        
        # Validate font application
        assert customized_fig is not None
        layout = customized_fig.layout
        assert layout.font.family == FontFamily.ARIAL
        assert layout.font.size == 14
        assert layout.title.font.family == FontFamily.HELVETICA
        assert layout.title.font.size == 18
    
    def test_axis_customization(self):
        """Test axis customization"""
        data = self.create_test_data()
        config = ChartConfig(
            chart_type=ChartType.SCATTER,
            x_axis='category',
            y_axis='value'
        )
        
        # Test axis configuration
        customization = ChartCustomization(
            x_axis=ChartAxis(
                title="Custom X Axis",
                title_font=ChartFont(size=14, bold=True),
                label_font=ChartFont(size=12),
                type=AxisType.CATEGORY,
                show_line=True,
                line_color="#FF0000",
                line_width=2,
                tick_angle=45
            ),
            y_axis=ChartAxis(
                title="Custom Y Axis",
                type=AxisType.LINEAR,
                show_line=True,
                show_ticks=True,
                tick_format=".2f",
                range_min=0,
                range_max=30
            )
        )
        
        # Generate and customize chart
        fig = self.generator._generate_chart_by_type(
            self.generator._prepare_dataframe(data), 
            config
        )
        
        customized_fig = self.service.apply_customization(fig, config, customization)
        
        # Validate axis customization
        assert customized_fig is not None
        assert customized_fig.layout.xaxis.title.text == "Custom X Axis"
        assert customized_fig.layout.yaxis.title.text == "Custom Y Axis"
        assert customized_fig.layout.xaxis.type == "category"
        assert customized_fig.layout.yaxis.tickformat == ".2f"
        assert customized_fig.layout.yaxis.range == [0, 30]
    
    def test_legend_customization(self):
        """Test legend customization"""
        data = self.create_test_data()
        config = ChartConfig(
            chart_type=ChartType.PIE,
            x_axis='category',
            y_axis='value'
        )
        
        # Test legend configuration
        customization = ChartCustomization(
            legend=ChartLegend(
                show=True,
                position=LegendPosition.TOP,
                font=ChartFont(size=11, color="#333333"),
                background_color="rgba(255,255,255,0.9)",
                border_color="#000000",
                border_width=1,
                orientation="horizontal"
            )
        )
        
        # Generate and customize chart
        fig = self.generator._generate_chart_by_type(
            self.generator._prepare_dataframe(data), 
            config
        )
        
        customized_fig = self.service.apply_customization(fig, config, customization)
        
        # Validate legend customization
        assert customized_fig is not None
        legend = customized_fig.layout.legend
        assert legend.orientation == "horizontal"
        assert legend.bgcolor == "rgba(255,255,255,0.9)"
        assert legend.bordercolor == "#000000"
        assert legend.borderwidth == 1
        assert legend.font.size == 11
    
    def test_grid_customization(self):
        """Test grid customization"""
        data = self.create_test_data()
        config = ChartConfig(
            chart_type=ChartType.BAR,
            x_axis='category',
            y_axis='value'
        )
        
        # Test grid configuration
        customization = ChartCustomization(
            grid=ChartGrid(
                show_x=True,
                show_y=True,
                color="#CCCCCC",
                width=2,
                style=GridStyle.DASH
            )
        )
        
        # Generate and customize chart
        fig = self.generator._generate_chart_by_type(
            self.generator._prepare_dataframe(data), 
            config
        )
        
        customized_fig = self.service.apply_customization(fig, config, customization)
        
        # Validate grid customization
        assert customized_fig is not None
        assert customized_fig.layout.xaxis.showgrid == True
        assert customized_fig.layout.yaxis.showgrid == True
        assert customized_fig.layout.xaxis.gridcolor == "#CCCCCC"
        assert customized_fig.layout.yaxis.gridcolor == "#CCCCCC"
        assert customized_fig.layout.xaxis.gridwidth == 2
        assert customized_fig.layout.yaxis.gridwidth == 2
    
    def test_annotations(self):
        """Test chart annotations"""
        data = self.create_test_data()
        config = ChartConfig(
            chart_type=ChartType.LINE,
            x_axis='date',
            y_axis='value'
        )
        
        # Test annotations
        customization = ChartCustomization(
            annotations=[
                ChartAnnotation(
                    text="Peak Value",
                    x="2024-01-04",
                    y=25,
                    font=ChartFont(size=12, color="#FF0000"),
                    background_color="rgba(255,255,0,0.7)",
                    border_color="#FF0000",
                    border_width=1,
                    arrow_show=True,
                    arrow_color="#FF0000"
                ),
                ChartAnnotation(
                    text="Low Point",
                    x="2024-01-01",
                    y=10,
                    font=ChartFont(size=10, color="#0000FF"),
                    background_color="rgba(0,255,255,0.7)",
                    border_color="#0000FF",
                    border_width=1,
                    arrow_show=False
                )
            ]
        )
        
        # Generate and customize chart
        fig = self.generator._generate_chart_by_type(
            self.generator._prepare_dataframe(data), 
            config
        )
        
        customized_fig = self.service.apply_customization(fig, config, customization)
        
        # Validate annotations
        assert customized_fig is not None
        assert len(customized_fig.layout.annotations) == 2
        
        # Check first annotation
        ann1 = customized_fig.layout.annotations[0]
        assert ann1.text == "Peak Value"
        assert ann1.x == "2024-01-04"
        assert ann1.y == 25
        assert ann1.showarrow == True
        
        # Check second annotation
        ann2 = customized_fig.layout.annotations[1]
        assert ann2.text == "Low Point"
        assert ann2.showarrow == False
    
    def test_margin_customization(self):
        """Test margin customization"""
        data = self.create_test_data()
        config = ChartConfig(
            chart_type=ChartType.BAR,
            x_axis='category',
            y_axis='value'
        )
        
        # Test margin configuration
        customization = ChartCustomization(
            margin=ChartMargin(
                top=80,
                bottom=70,
                left=90,
                right=60
            )
        )
        
        # Generate and customize chart
        fig = self.generator._generate_chart_by_type(
            self.generator._prepare_dataframe(data), 
            config
        )
        
        customized_fig = self.service.apply_customization(fig, config, customization)
        
        # Validate margin customization
        assert customized_fig is not None
        margin = customized_fig.layout.margin
        assert margin.t == 80
        assert margin.b == 70
        assert margin.l == 90
        assert margin.r == 60
    
    def test_color_palette_retrieval(self):
        """Test color palette retrieval"""
        # Test different color schemes
        color_schemes = [
            ColorScheme.DEFAULT,
            ColorScheme.VIRIDIS,
            ColorScheme.CATEGORICAL,
            ColorScheme.DARK,
            ColorScheme.PASTEL
        ]
        
        for scheme in color_schemes:
            palette = self.service.get_color_palette(scheme, 5)
            assert len(palette) == 5
            assert all(isinstance(color, str) for color in palette)
            
            # Test larger palette
            large_palette = self.service.get_color_palette(scheme, 20)
            assert len(large_palette) == 20
    
    def test_template_management(self):
        """Test template creation and retrieval"""
        # Test default templates
        templates = self.service.list_templates()
        assert len(templates) >= 3  # corporate, dark, minimal
        
        template_names = [t.name for t in templates]
        assert "corporate" in template_names
        assert "dark" in template_names
        assert "minimal" in template_names
        
        # Test specific template retrieval
        corporate_template = self.service.get_template("corporate")
        assert corporate_template is not None
        assert corporate_template.name == "corporate"
        assert corporate_template.customization.theme == ChartTheme.DEFAULT
        
        # Test custom template creation
        custom_customization = ChartCustomization(
            theme=ChartTheme.SEABORN,
            font_family=FontFamily.TIMES,
            font_size=13,
            background_color="#F5F5F5",
            title=ChartTitle(text="Custom Template")
        )
        
        custom_template = ChartTemplate(
            name="custom_test",
            description="Test template",
            customization=custom_customization,
            tags=["test", "custom"]
        )
        
        created_template = self.service.create_template(custom_template)
        assert created_template.name == "custom_test"
        
        # Test retrieval of custom template
        retrieved_template = self.service.get_template("custom_test")
        assert retrieved_template is not None
        assert retrieved_template.name == "custom_test"
        assert retrieved_template.customization.theme == ChartTheme.SEABORN
    
    def test_customization_validation(self):
        """Test customization validation"""
        # Test valid customization
        valid_customization = ChartCustomization(
            theme=ChartTheme.DEFAULT,
            font_family=FontFamily.ARIAL,
            font_size=12,
            background_color="#FFFFFF",
            plot_background_color="#FAFAFA"
        )
        
        warnings = self.service.validate_customization(valid_customization)
        assert len(warnings) == 0
        
        # Test customization with warnings
        invalid_customization = ChartCustomization(
            theme=ChartTheme.DEFAULT,
            font_family=FontFamily.ARIAL,
            font_size=100,  # Too large
            background_color="invalid_color",  # Invalid color
            plot_background_color="rgb(256,256,256)"  # Invalid RGB
        )
        
        warnings = self.service.validate_customization(invalid_customization)
        assert len(warnings) > 0
        assert any("Font size" in warning for warning in warnings)
        assert any("background color" in warning for warning in warnings)
    
    def test_color_validation(self):
        """Test color format validation"""
        # Test valid colors
        valid_colors = [
            "#FF0000",
            "#fff",
            "rgb(255,0,0)",
            "rgba(255,0,0,0.5)",
            "red",
            "blue"
        ]
        
        for color in valid_colors:
            assert self.service._is_valid_color(color) == True
        
        # Test invalid colors
        invalid_colors = [
            "#GGGGGG",
            "rgb(256,0,0)",
            "invalid_color_name",
            "#FF",
            "rgba(255,0,0,1.5)"
        ]
        
        for color in invalid_colors:
            assert self.service._is_valid_color(color) == False
    
    def test_integration_with_chart_generator(self):
        """Test integration with chart generator"""
        data = self.create_test_data()
        
        # Test chart generation with customization
        customization = ChartCustomization(
            theme=ChartTheme.DARK,
            font_family=FontFamily.ROBOTO,
            font_size=14,
            title=ChartTitle(
                text="Integration Test Chart",
                font=ChartFont(size=16, bold=True)
            )
        )
        
        config = ChartConfig(
            chart_type=ChartType.BAR,
            x_axis='category',
            y_axis='value',
            customization=customization
        )
        
        response = self.generator.generate_chart(data, config, "test_chart")
        
        # Validate response
        assert response is not None
        assert response.chart_id == "test_chart"
        assert response.chart_type == ChartType.BAR
        assert response.generation_time > 0
        
        # Validate customization was applied
        fig = go.Figure.from_json(response.plotly_json)
        assert fig.layout.title.text == "Integration Test Chart"
        assert fig.layout.font.family == FontFamily.ROBOTO
        assert fig.layout.font.size == 14
    
    def test_template_application(self):
        """Test template application to charts"""
        data = self.create_test_data()
        
        # Test corporate template
        config = ChartConfig(
            chart_type=ChartType.LINE,
            x_axis='date',
            y_axis='value',
            template="corporate"
        )
        
        response = self.generator.generate_chart(data, config, "template_test")
        
        # Validate response
        assert response is not None
        assert response.chart_type == ChartType.LINE
        
        # Parse figure to check template application
        fig = go.Figure.from_json(response.plotly_json)
        assert fig.layout.font.family == FontFamily.ARIAL
        assert fig.layout.font.size == 12
        
        # Test dark template
        config.template = "dark"
        response = self.generator.generate_chart(data, config, "dark_template_test")
        
        fig = go.Figure.from_json(response.plotly_json)
        assert fig.layout.font.family == FontFamily.ROBOTO
        assert fig.layout.paper_bgcolor == "#2F2F2F"
    
    def test_chart_specific_options(self):
        """Test chart-specific customization options"""
        data = self.create_test_data()
        
        # Test line chart specific options
        config = ChartConfig(
            chart_type=ChartType.LINE,
            x_axis='date',
            y_axis='value',
            chart_options={
                "line_width": 3,
                "line_style": "dash",
                "marker_size": 8,
                "marker_symbol": "diamond"
            }
        )
        
        response = self.generator.generate_chart(data, config, "line_options_test")
        assert response is not None
        
        # Test bar chart specific options
        config = ChartConfig(
            chart_type=ChartType.BAR,
            x_axis='category',
            y_axis='value',
            chart_options={
                "bar_width": 0.8,
                "bar_opacity": 0.7,
                "bar_gap": 0.2
            }
        )
        
        response = self.generator.generate_chart(data, config, "bar_options_test")
        assert response is not None
        
        # Test pie chart specific options
        config = ChartConfig(
            chart_type=ChartType.PIE,
            x_axis='category',
            y_axis='value',
            chart_options={
                "donut": True,
                "hole_size": 0.4,
                "start_angle": 90,
                "text_info": "label+percent+value"
            }
        )
        
        response = self.generator.generate_chart(data, config, "pie_options_test")
        assert response is not None


def test_customization_integration():
    """Integration test for chart customization functionality"""
    service = ChartCustomizationService()
    generator = ChartGenerator()
    
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
    
    # Test comprehensive customization
    customization = ChartCustomization(
        theme=ChartTheme.PRESENTATION,
        font_family=FontFamily.CALIBRI,
        font_size=12,
        background_color="#FFFFFF",
        plot_background_color="#F8F9FA",
        title=ChartTitle(
            text="Quarterly Sales Analysis",
            font=ChartFont(size=18, bold=True, color="#1F4E79"),
            position="center"
        ),
        legend=ChartLegend(
            show=True,
            position=LegendPosition.RIGHT,
            font=ChartFont(size=11),
            background_color="rgba(255,255,255,0.9)"
        ),
        grid=ChartGrid(
            show_x=True,
            show_y=True,
            color="#E0E0E0",
            style=GridStyle.DOT
        ),
        x_axis=ChartAxis(
            title="Quarter",
            title_font=ChartFont(size=14, bold=True),
            type=AxisType.CATEGORY
        ),
        y_axis=ChartAxis(
            title="Sales ($)",
            title_font=ChartFont(size=14, bold=True),
            type=AxisType.LINEAR,
            tick_format="$,.0f"
        ),
        annotations=[
            ChartAnnotation(
                text="Peak Quarter",
                x="2024-Q4",
                y=45000,
                font=ChartFont(size=12, color="#FF0000"),
                background_color="rgba(255,255,0,0.7)",
                arrow_show=True
            )
        ]
    )
    
    config = ChartConfig(
        chart_type=ChartType.BAR,
        title="Quarterly Sales by Product and Region",
        x_axis='quarter',
        y_axis='sales',
        color_field='product',
        customization=customization
    )
    
    response = generator.generate_chart(data, config, "comprehensive_test")
    
    # Validate comprehensive customization
    assert response.chart_type == ChartType.BAR
    assert response.generation_time > 0
    assert response.plotly_json is not None
    
    # Parse and validate figure
    fig = go.Figure.from_json(response.plotly_json)
    assert fig.layout.title.text == "Quarterly Sales Analysis"
    assert fig.layout.font.family == FontFamily.CALIBRI
    assert fig.layout.font.size == 12
    assert fig.layout.paper_bgcolor == "#FFFFFF"
    assert fig.layout.plot_bgcolor == "#F8F9FA"
    assert len(fig.layout.annotations) == 1
    assert fig.layout.annotations[0].text == "Peak Quarter"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])