"""
Message formatting utilities for Microsoft Teams responses.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

class TeamsMessageFormatter:
    """Formatter for Teams messages and activities."""
    
    def __init__(self):
        self.max_text_length = 28000  # Teams message limit
        self.max_results_display = 10
    
    def format_query_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format query response into Teams message activity."""
        text_parts = []
        
        # Add header with SPL query
        if data.get("spl_query"):
            text_parts.append(f"**Query Results**")
            text_parts.append(f"```\n{data['spl_query']}\n```")
        
        # Add metadata
        metadata_parts = []
        if data.get("execution_time"):
            metadata_parts.append(f"⏱️ **Execution time:** {data['execution_time']:.2f}s")
        if data.get("results_count"):
            metadata_parts.append(f"📊 **Results:** {data['results_count']} records")
        if data.get("confidence_score"):
            metadata_parts.append(f"🎯 **Confidence:** {data['confidence_score']:.1%}")
        
        if metadata_parts:
            text_parts.append(" | ".join(metadata_parts))
        
        # Format results data
        if data.get("data"):
            results_text = self._format_results_data(data["data"])
            text_parts.append(results_text)
        
        # Add explanation if available
        if data.get("explanation"):
            text_parts.append(f"**Analysis:**\n{data['explanation']}")
        
        message_text = "\n\n".join(text_parts)
        
        return {
            "type": "message",
            "text": self.truncate_text(message_text)
        }
    
    def _format_results_data(self, data: List[Dict[str, Any]]) -> str:
        """Format results data for Teams display."""
        if not data:
            return "No results found for your query."
        
        # Limit results for display
        display_data = data[:self.max_results_display]
        
        # If it's a simple count or single value, display prominently
        if len(data) == 1 and len(data[0]) == 1:
            key, value = next(iter(data[0].items()))
            return f"**{key}:** `{value}`"
        
        # Format as table for structured data
        if all(isinstance(row, dict) for row in display_data):
            table_text = self._format_as_teams_table(display_data)
            
            result_text = f"```\n{table_text}\n```"
            
            # Add "more results" note if truncated
            if len(data) > self.max_results_display:
                result_text += f"\n*Showing {self.max_results_display} of {len(data)} results*"
            
            return result_text
        
        return str(data)
    
    def _format_as_teams_table(self, data: List[Dict[str, Any]]) -> str:
        """Format data as ASCII table for Teams."""
        if not data:
            return "No data"
        
        # Get all unique keys
        all_keys = set()
        for row in data:
            all_keys.update(row.keys())
        
        headers = list(all_keys)
        
        # Calculate column widths
        col_widths = {}
        for header in headers:
            col_widths[header] = max(
                len(str(header)),
                max(len(str(row.get(header, ""))) for row in data)
            )
            # Limit column width for Teams display
            col_widths[header] = min(col_widths[header], 25)
        
        # Build table
        lines = []
        
        # Header row
        header_row = " | ".join(
            str(header)[:col_widths[header]].ljust(col_widths[header])
            for header in headers
        )
        lines.append(header_row)
        
        # Separator
        separator = "-+-".join("-" * col_widths[header] for header in headers)
        lines.append(separator)
        
        # Data rows
        for row in data:
            data_row = " | ".join(
                str(row.get(header, ""))[:col_widths[header]].ljust(col_widths[header])
                for header in headers
            )
            lines.append(data_row)
        
        return "\n".join(lines)
    
    def format_help_message(self) -> str:
        """Format help message for Teams."""
        help_text = """**🤖 Splunk MCP Assistant Help**

**How to use:**
• Mention me with your query: @Splunk MCP Assistant show me errors from last hour
• Send direct message for private results
• Use natural language to query your Splunk data

**Example queries:**
• Show me errors from the last hour
• Count events by source and create a chart
• Find failed login attempts with visualization
• Show server performance metrics for last 24 hours
• Create alert when error rate exceeds 5%

**Available commands:**
• `help` - Show this message
• `status` - Check system health
• `dashboards` - Show my dashboards
• `searches` - Show saved searches

**Features:**
• 🔍 Natural language to SPL translation
• 📊 Automatic chart generation
• 🚨 Alert creation and management
• 📈 Dashboard integration
• 🔒 Enterprise security compliance"""

        return help_text
    
    def format_status_message(self, status: Dict[str, Any], user_info: Dict[str, Any]) -> str:
        """Format system status message for Teams."""
        # System status indicator
        status_emoji = {
            "healthy": "🟢",
            "degraded": "🟡", 
            "error": "🔴"
        }.get(status.get("status", "unknown"), "⚪")
        
        text_parts = [
            f"**{status_emoji} System Status: {status.get('status', 'Unknown').title()}**"
        ]
        
        # Service details
        if status.get("services"):
            service_lines = []
            for service_name, service_status in status["services"].items():
                service_emoji = "🟢" if service_status.get("status") == "healthy" else "🔴"
                service_lines.append(f"{service_emoji} {service_name.replace('_', ' ').title()}")
            
            text_parts.append(f"**Services:**\n{chr(10).join(service_lines)}")
        
        # User information
        if user_info:
            user_text = []
            if user_info.get("access_level"):
                user_text.append(f"**Access Level:** {user_info['access_level']}")
            if user_info.get("accessible_indexes"):
                user_text.append(f"**Available Indexes:** {len(user_info['accessible_indexes'])}")
            if user_info.get("roles"):
                user_text.append(f"**Roles:** {', '.join(user_info['roles'])}")
            
            if user_text:
                text_parts.append("\n".join(user_text))
        
        # Timestamp
        text_parts.append(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}*")
        
        return "\n\n".join(text_parts)
    
    def format_error_message(self, error: str) -> str:
        """Format error message for Teams."""
        return f"""❌ **Error**
{error}

**Try:**
• Simplifying your query
• Checking your spelling
• Using `help` for examples
• Contacting support if the issue persists"""
    
    def format_welcome_message(self) -> str:
        """Format welcome message for new users."""
        return """👋 **Welcome to Splunk MCP Assistant!**

I'm here to help you query and analyze your Splunk data using natural language.

**Get started:**
• Type `help` to see what I can do
• Try: "Show me errors from the last hour"
• Ask: "What's the system status?"

**Key features:**
🔍 Natural language queries
📊 Automatic visualizations  
🚨 Alert management
📈 Dashboard integration

Just mention me or send a direct message to get started!"""
    
    def format_alert_created_message(self, alert: Dict[str, Any]) -> str:
        """Format alert creation confirmation for Teams."""
        return f"""✅ **Alert Created Successfully**

**Name:** {alert.get('name', 'Unnamed Alert')}
**Condition:** {alert.get('condition', 'N/A')}
**Notification:** {alert.get('notification_channels', ['Email'])[0]}

*Alert ID: {alert.get('id', 'Unknown')}*"""
    
    def format_dashboard_list(self, dashboards: List[Dict[str, Any]]) -> str:
        """Format dashboard list for Teams."""
        if not dashboards:
            return "📊 **Your Dashboards**\n\nNo dashboards found. Create your first dashboard by asking me to visualize some data!"
        
        text_parts = ["📊 **Your Dashboards**"]
        
        for i, dashboard in enumerate(dashboards[:10], 1):
            name = dashboard.get("name", f"Dashboard {i}")
            description = dashboard.get("description", "")
            updated = dashboard.get("updated_at", "")
            
            dashboard_text = f"{i}. **{name}**"
            if description:
                dashboard_text += f" - {description}"
            if updated:
                dashboard_text += f" *(Updated: {updated})*"
            
            text_parts.append(dashboard_text)
        
        if len(dashboards) > 10:
            text_parts.append(f"*... and {len(dashboards) - 10} more*")
        
        return "\n".join(text_parts)
    
    def format_saved_searches(self, searches: List[Dict[str, Any]]) -> str:
        """Format saved searches list for Teams."""
        if not searches:
            return "🔍 **Your Saved Searches**\n\nNo saved searches found. Save your frequently used queries for quick access!"
        
        text_parts = ["🔍 **Your Saved Searches**"]
        
        for i, search in enumerate(searches[:10], 1):
            name = search.get("name", f"Search {i}")
            query = search.get("query", "")
            updated = search.get("updated_at", "")
            
            search_text = f"{i}. **{name}**"
            if query and len(query) <= 50:
                search_text += f" - `{query}`"
            elif query:
                search_text += f" - `{query[:47]}...`"
            if updated:
                search_text += f" *(Updated: {updated})*"
            
            text_parts.append(search_text)
        
        if len(searches) > 10:
            text_parts.append(f"*... and {len(searches) - 10} more*")
        
        return "\n".join(text_parts)
    
    def truncate_text(self, text: str, max_length: Optional[int] = None) -> str:
        """Truncate text to fit Teams limits."""
        if max_length is None:
            max_length = self.max_text_length
        
        if len(text) <= max_length:
            return text
        
        return text[:max_length - 3] + "..."
    
    def format_typing_activity(self) -> Dict[str, Any]:
        """Create typing activity for Teams."""
        return {
            "type": "typing"
        }
    
    def format_simple_response(self, text: str) -> Dict[str, Any]:
        """Format simple text response for Teams."""
        return {
            "type": "message",
            "text": self.truncate_text(text)
        }