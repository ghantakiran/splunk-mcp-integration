"""
Message formatting utilities for Slack responses.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

class MessageFormatter:
    """Formatter for Slack messages and blocks."""
    
    def __init__(self):
        self.max_text_length = 3000
        self.max_results_display = 10
    
    def format_query_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format query response into Slack blocks."""
        blocks = []
        
        # Add header
        if data.get("spl_query"):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Query Results*\n```{data['spl_query']}```"
                }
            })
        
        # Add metadata if available
        metadata_text = []
        if data.get("execution_time"):
            metadata_text.append(f"⏱️ *Execution time:* {data['execution_time']:.2f}s")
        if data.get("results_count"):
            metadata_text.append(f"📊 *Results:* {data['results_count']} records")
        if data.get("confidence_score"):
            metadata_text.append(f"🎯 *Confidence:* {data['confidence_score']:.1%}")
        
        if metadata_text:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": " | ".join(metadata_text)
                    }
                ]
            })
        
        # Add divider
        blocks.append({"type": "divider"})
        
        # Format results data
        if data.get("data"):
            result_blocks = self._format_results_data(data["data"])
            blocks.extend(result_blocks)
        
        # Add explanation if available
        if data.get("explanation"):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Analysis:*\n{data['explanation']}"
                }
            })
        
        # Add actions if visualizations are available
        if data.get("visualizations"):
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📈 View Charts"
                        },
                        "action_id": "view_charts",
                        "value": "show_visualizations"
                    }
                ]
            })
        
        return blocks
    
    def _format_results_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format results data into Slack blocks."""
        blocks = []
        
        if not data:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "No results found for your query."
                }
            })
            return blocks
        
        # Limit results for display
        display_data = data[:self.max_results_display]
        
        # If it's a simple count or single value, display prominently
        if len(data) == 1 and len(data[0]) == 1:
            key, value = next(iter(data[0].items()))
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{key}:* `{value}`"
                }
            })
            return blocks
        
        # Format as table for structured data
        if all(isinstance(row, dict) for row in display_data):
            table_text = self._format_as_table(display_data)
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```\n{table_text}\n```"
                }
            })
            
            # Add "more results" note if truncated
            if len(data) > self.max_results_display:
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Showing {self.max_results_display} of {len(data)} results"
                        }
                    ]
                })
        
        return blocks
    
    def _format_as_table(self, data: List[Dict[str, Any]]) -> str:
        """Format data as ASCII table."""
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
            # Limit column width
            col_widths[header] = min(col_widths[header], 20)
        
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
    
    def format_help_message(self) -> List[Dict[str, Any]]:
        """Format help message."""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🤖 Splunk MCP Bot Help*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*How to use:*\n• Mention me with your query: `@splunk-bot show me errors from last hour`\n• Send direct message for private results\n• Use slash commands: `/splunk <query>`"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Example queries:*\n• Show me errors from the last hour\n• Count events by source\n• Find failed login attempts\n• Show server performance metrics\n• Alert me when error rate exceeds 5%"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Available commands:*\n• `help` - Show this message\n• `status` - Check system health\n• `/splunk-help` - Detailed help\n• `/splunk-status` - System status"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🔍 Try Example Query"
                        },
                        "action_id": "run_query",
                        "value": "show me top 10 sources by event count"
                    }
                ]
            }
        ]
    
    def format_status_message(self, status: Dict[str, Any], user_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format system status message."""
        # System status indicator
        status_emoji = {
            "healthy": "🟢",
            "degraded": "🟡", 
            "error": "🔴"
        }.get(status.get("status", "unknown"), "⚪")
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{status_emoji} System Status: {status.get('status', 'Unknown').title()}*"
                }
            }
        ]
        
        # Service details
        if status.get("services"):
            service_lines = []
            for service_name, service_status in status["services"].items():
                service_emoji = "🟢" if service_status.get("status") == "healthy" else "🔴"
                service_lines.append(f"{service_emoji} {service_name.replace('_', ' ').title()}")
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Services:*\n{chr(10).join(service_lines)}"
                }
            })
        
        # User information
        if user_info:
            user_text = []
            if user_info.get("access_level"):
                user_text.append(f"*Access Level:* {user_info['access_level']}")
            if user_info.get("accessible_indexes"):
                user_text.append(f"*Available Indexes:* {len(user_info['accessible_indexes'])}")
            if user_info.get("roles"):
                user_text.append(f"*Roles:* {', '.join(user_info['roles'])}")
            
            if user_text:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "\n".join(user_text)
                    }
                })
        
        # Timestamp
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
                }
            ]
        })
        
        return blocks
    
    def format_error_message(self, error: str) -> List[Dict[str, Any]]:
        """Format error message."""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"❌ *Error*\n{error}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Try:*\n• Simplifying your query\n• Checking your spelling\n• Using `help` for examples\n• Contacting support if the issue persists"
                }
            }
        ]
    
    def format_alert_created_message(self, alert: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Format alert creation confirmation."""
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ *Alert Created Successfully*\n*Name:* {alert.get('name', 'Unnamed Alert')}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Condition:* {alert.get('condition', 'N/A')}\n*Notification:* {alert.get('notification_channels', ['Email'])[0]}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Alert ID: {alert.get('id', 'Unknown')}"
                    }
                ]
            }
        ]
    
    def truncate_text(self, text: str, max_length: Optional[int] = None) -> str:
        """Truncate text to fit Slack limits."""
        if max_length is None:
            max_length = self.max_text_length
        
        if len(text) <= max_length:
            return text
        
        return text[:max_length - 3] + "..."