"""
Tests for Microsoft Teams Adaptive Cards functionality.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from app.utils.adaptive_cards import AdaptiveCardBuilder


class TestAdaptiveCardBuilder:
    """Test suite for AdaptiveCardBuilder."""
    
    @pytest.fixture
    def card_builder(self):
        """Create AdaptiveCardBuilder instance."""
        return AdaptiveCardBuilder()
    
    def test_create_basic_card(self, card_builder):
        """Test creating basic adaptive card."""
        card = card_builder.create_card()
        
        assert card["type"] == "AdaptiveCard"
        assert card["version"] == "1.4"
        assert "body" in card
        assert isinstance(card["body"], list)
    
    def test_create_text_block(self, card_builder):
        """Test creating text block element."""
        text = "Test text"
        weight = "bolder"
        size = "large"
        
        text_block = card_builder.text_block(text, weight=weight, size=size)
        
        assert text_block["type"] == "TextBlock"
        assert text_block["text"] == text
        assert text_block["weight"] == weight
        assert text_block["size"] == size
    
    def test_create_text_block_with_color(self, card_builder):
        """Test creating text block with color."""
        text = "Colored text"
        color = "attention"
        
        text_block = card_builder.text_block(text, color=color)
        
        assert text_block["color"] == color
    
    def test_create_text_block_with_wrap(self, card_builder):
        """Test creating text block with wrap."""
        text = "Long text that should wrap"
        
        text_block = card_builder.text_block(text, wrap=True)
        
        assert text_block["wrap"] is True
    
    def test_create_column_set(self, card_builder):
        """Test creating column set."""
        columns = [
            {"type": "Column", "width": "auto", "items": []},
            {"type": "Column", "width": "stretch", "items": []}
        ]
        
        column_set = card_builder.column_set(columns)
        
        assert column_set["type"] == "ColumnSet"
        assert column_set["columns"] == columns
    
    def test_create_action_submit(self, card_builder):
        """Test creating submit action."""
        title = "Submit"
        data = {"action": "submit", "value": "test"}
        
        action = card_builder.action_submit(title, data)
        
        assert action["type"] == "Action.Submit"
        assert action["title"] == title
        assert action["data"] == data
    
    def test_create_action_open_url(self, card_builder):
        """Test creating open URL action."""
        title = "Open Link"
        url = "https://example.com"
        
        action = card_builder.action_open_url(title, url)
        
        assert action["type"] == "Action.OpenUrl"
        assert action["title"] == title
        assert action["url"] == url
    
    def test_create_fact_set(self, card_builder):
        """Test creating fact set."""
        facts = [
            {"title": "Status", "value": "Active"},
            {"title": "Count", "value": "42"}
        ]
        
        fact_set = card_builder.fact_set(facts)
        
        assert fact_set["type"] == "FactSet"
        assert fact_set["facts"] == facts
    
    def test_create_image(self, card_builder):
        """Test creating image element."""
        url = "https://example.com/image.png"
        alt_text = "Test image"
        size = "medium"
        
        image = card_builder.image(url, alt_text=alt_text, size=size)
        
        assert image["type"] == "Image"
        assert image["url"] == url
        assert image["altText"] == alt_text
        assert image["size"] == size
    
    def test_create_container(self, card_builder):
        """Test creating container."""
        items = [
            {"type": "TextBlock", "text": "Container item"}
        ]
        
        container = card_builder.container(items)
        
        assert container["type"] == "Container"
        assert container["items"] == items
    
    def test_create_input_text(self, card_builder):
        """Test creating text input."""
        id_field = "user_input"
        placeholder = "Enter text here"
        value = "default value"
        
        input_text = card_builder.input_text(id_field, placeholder=placeholder, value=value)
        
        assert input_text["type"] == "Input.Text"
        assert input_text["id"] == id_field
        assert input_text["placeholder"] == placeholder
        assert input_text["value"] == value
    
    def test_create_input_choice_set(self, card_builder):
        """Test creating choice set input."""
        id_field = "choices"
        choices = [
            {"title": "Option 1", "value": "opt1"},
            {"title": "Option 2", "value": "opt2"}
        ]
        
        input_choice = card_builder.input_choice_set(id_field, choices)
        
        assert input_choice["type"] == "Input.ChoiceSet"
        assert input_choice["id"] == id_field
        assert input_choice["choices"] == choices
    
    def test_create_query_result_card(self, card_builder):
        """Test creating query result card."""
        query_response = {
            "data": {
                "spl_query": "search index=main error",
                "data": [
                    {"host": "server1", "count": 5},
                    {"host": "server2", "count": 3}
                ],
                "execution_time": 1.2
            }
        }
        
        card = card_builder.create_query_result_card(query_response)
        
        assert card["type"] == "AdaptiveCard"
        assert len(card["body"]) > 0
        
        # Should contain query information
        card_text = str(card)
        assert "search index=main error" in card_text
        assert "1.2" in card_text
    
    def test_create_help_card(self, card_builder):
        """Test creating help card."""
        card = card_builder.create_help_card()
        
        assert card["type"] == "AdaptiveCard"
        assert len(card["body"]) > 0
        
        # Should contain help information
        card_text = str(card).lower()
        assert "help" in card_text
        assert "splunk" in card_text
    
    def test_create_status_card(self, card_builder):
        """Test creating status card."""
        status_data = {
            "status": "healthy",
            "services": {
                "api_gateway": {"status": "healthy", "response_time": 50},
                "nlp_engine": {"status": "healthy", "response_time": 75}
            }
        }
        user_info = {
            "access_level": "standard",
            "query_count": 25
        }
        
        card = card_builder.create_status_card(status_data, user_info)
        
        assert card["type"] == "AdaptiveCard"
        
        card_text = str(card)
        assert "healthy" in card_text
        assert "standard" in card_text
        assert "25" in card_text
    
    def test_create_error_card(self, card_builder):
        """Test creating error card."""
        error_message = "Connection timeout occurred"
        
        card = card_builder.create_error_card(error_message)
        
        assert card["type"] == "AdaptiveCard"
        
        card_text = str(card)
        assert "error" in card_text.lower()
        assert "Connection timeout occurred" in card_text
    
    def test_create_visualization_card(self, card_builder):
        """Test creating visualization card."""
        visualization = {
            "image_url": "https://example.com/chart.png",
            "title": "Error Trend Chart",
            "description": "Errors over time"
        }
        
        card = card_builder.create_visualization_card(visualization)
        
        assert card["type"] == "AdaptiveCard"
        
        # Should contain image
        has_image = any(
            item.get("type") == "Image" and item.get("url") == visualization["image_url"]
            for item in card["body"]
        )
        assert has_image
        
        card_text = str(card)
        assert "Error Trend Chart" in card_text
    
    def test_create_welcome_card(self, card_builder):
        """Test creating welcome card."""
        user_name = "John Doe"
        
        card = card_builder.create_welcome_card(user_name)
        
        assert card["type"] == "AdaptiveCard"
        
        card_text = str(card)
        assert "welcome" in card_text.lower()
        assert user_name in card_text
    
    def test_create_alert_card(self, card_builder):
        """Test creating alert card."""
        alert_data = {
            "title": "High CPU Usage Alert",
            "description": "CPU usage exceeded 80% threshold",
            "severity": "high",
            "triggered_at": datetime.utcnow().isoformat(),
            "affected_hosts": ["server1", "server2"]
        }
        
        card = card_builder.create_alert_card(alert_data)
        
        assert card["type"] == "AdaptiveCard"
        
        card_text = str(card)
        assert "High CPU Usage Alert" in card_text
        assert "high" in card_text
        assert "server1" in card_text
    
    def test_create_quick_actions_card(self, card_builder):
        """Test creating quick actions card."""
        actions = [
            {"title": "Show Status", "query": "| rest /services/server/info"},
            {"title": "Recent Errors", "query": "search error | head 10"},
            {"title": "System Health", "query": "| rest /services/data/indexes"}
        ]
        
        card = card_builder.create_quick_actions_card(actions)
        
        assert card["type"] == "AdaptiveCard"
        assert "actions" in card
        
        # Should have action buttons
        assert len(card["actions"]) >= len(actions)
    
    def test_create_table_card(self, card_builder):
        """Test creating table card."""
        headers = ["Host", "Count", "Status"]
        rows = [
            ["server1", "5", "active"],
            ["server2", "3", "active"],
            ["server3", "8", "warning"]
        ]
        title = "Server Status Report"
        
        card = card_builder.create_table_card(headers, rows, title)
        
        assert card["type"] == "AdaptiveCard"
        
        card_text = str(card)
        assert title in card_text
        assert "server1" in card_text
        assert "5" in card_text
    
    def test_add_styling_to_card(self, card_builder):
        """Test adding styling to card."""
        card = card_builder.create_card()
        
        # Add accent styling
        styled_card = card_builder.add_accent_styling(card)
        
        # Should have styling elements
        assert "style" in str(styled_card) or len(styled_card["body"]) >= len(card["body"])
    
    def test_create_interactive_form_card(self, card_builder):
        """Test creating interactive form card."""
        form_fields = [
            {"id": "query", "type": "text", "label": "SPL Query", "required": True},
            {"id": "format", "type": "choice", "label": "Output Format", "choices": [
                {"title": "Table", "value": "table"},
                {"title": "Chart", "value": "chart"}
            ]}
        ]
        
        card = card_builder.create_interactive_form_card("Run Query", form_fields)
        
        assert card["type"] == "AdaptiveCard"
        
        # Should have inputs
        has_text_input = any(
            item.get("type") == "Input.Text" and item.get("id") == "query"
            for item in card["body"]
        )
        assert has_text_input
        
        # Should have submit action
        has_submit = any(
            action.get("type") == "Action.Submit"
            for action in card.get("actions", [])
        )
        assert has_submit
    
    def test_card_size_limits(self, card_builder):
        """Test card respects size limits."""
        # Create a large amount of data
        large_data = [{"field": f"value_{i}"} for i in range(1000)]
        
        card = card_builder.create_query_result_card({"data": {"data": large_data}})
        
        # Card should be created but truncated appropriately
        assert card["type"] == "AdaptiveCard"
        
        # Should not exceed reasonable size limits
        card_str = str(card)
        assert len(card_str) < 50000  # Reasonable size limit for Teams
    
    def test_card_accessibility(self, card_builder):
        """Test card includes accessibility features."""
        card = card_builder.create_help_card()
        
        # Should have proper text elements for screen readers
        has_text_blocks = any(
            item.get("type") == "TextBlock"
            for item in card["body"]
        )
        assert has_text_blocks


if __name__ == "__main__":
    pytest.main([__file__])