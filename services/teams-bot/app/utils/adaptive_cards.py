"""
Adaptive Cards builder for Microsoft Teams rich interactions.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

class AdaptiveCardBuilder:
    """Builder for Microsoft Teams Adaptive Cards."""
    
    def __init__(self):
        self.schema_version = "1.5"
    
    def create_base_card(self, title: str = None) -> Dict[str, Any]:
        """Create base adaptive card structure."""
        card = {
            "type": "AdaptiveCard",
            "$schema": f"http://adaptivecards.io/schemas/adaptive-card-{self.schema_version}.json",
            "version": self.schema_version,
            "body": []
        }
        
        if title:
            card["body"].append({
                "type": "TextBlock",
                "text": title,
                "weight": "Bolder",
                "size": "Medium"
            })
        
        return card
    
    def create_visualization_card(self, visualization: Dict[str, Any]) -> Dict[str, Any]:
        """Create adaptive card for visualization display."""
        card = self.create_base_card(visualization.get("title", "Visualization"))
        
        # Add description if available
        if visualization.get("description"):
            card["body"].append({
                "type": "TextBlock",
                "text": visualization["description"],
                "wrap": True
            })
        
        # Add image
        if visualization.get("image_url"):
            card["body"].append({
                "type": "Image",
                "url": visualization["image_url"],
                "altText": visualization.get("title", "Chart"),
                "size": "Large"
            })
        
        # Add metadata
        metadata = []
        if visualization.get("chart_type"):
            metadata.append(f"**Type:** {visualization['chart_type']}")
        if visualization.get("data_points"):
            metadata.append(f"**Data Points:** {visualization['data_points']}")
        if visualization.get("created_at"):
            metadata.append(f"**Created:** {visualization['created_at']}")
        
        if metadata:
            card["body"].append({
                "type": "TextBlock",
                "text": " | ".join(metadata),
                "size": "Small",
                "color": "Accent"
            })
        
        # Add actions
        actions = []
        
        if visualization.get("download_url"):
            actions.append({
                "type": "Action.OpenUrl",
                "title": "Download",
                "url": visualization["download_url"]
            })
        
        actions.append({
            "type": "Action.Submit",
            "title": "Create Similar",
            "data": {
                "action": "create_similar_chart",
                "chart_type": visualization.get("chart_type"),
                "config": visualization.get("config", {})
            }
        })
        
        if actions:
            card["actions"] = actions
        
        return {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": card
        }
    
    def create_help_card(self) -> Dict[str, Any]:
        """Create help adaptive card."""
        card = self.create_base_card("🤖 Splunk MCP Assistant Help")
        
        # How to use section
        card["body"].extend([
            {
                "type": "TextBlock",
                "text": "**How to use:**",
                "weight": "Bolder"
            },
            {
                "type": "TextBlock",
                "text": "• Mention me with your query\n• Send direct message for private results\n• Use natural language to query Splunk data",
                "wrap": True
            }
        ])
        
        # Example queries section
        card["body"].extend([
            {
                "type": "TextBlock",
                "text": "**Example queries:**",
                "weight": "Bolder",
                "spacing": "Medium"
            },
            {
                "type": "TextBlock",
                "text": "• Show me errors from the last hour\n• Count events by source and create a chart\n• Find failed login attempts\n• Create alert when error rate exceeds 5%",
                "wrap": True
            }
        ])
        
        # Quick actions
        card["actions"] = [
            {
                "type": "Action.Submit",
                "title": "🔍 Example Query",
                "data": {
                    "action": "run_query",
                    "query": "show me top 10 sources by event count"
                }
            },
            {
                "type": "Action.Submit",
                "title": "📊 System Status",
                "data": {
                    "action": "show_status"
                }
            },
            {
                "type": "Action.Submit",
                "title": "📈 My Dashboards",
                "data": {
                    "action": "show_dashboards"
                }
            }
        ]
        
        return {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": card
        }
    
    def create_status_card(self, status: Dict[str, Any], user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create system status adaptive card."""
        # Status indicator emoji
        status_emoji = {
            "healthy": "🟢",
            "degraded": "🟡",
            "error": "🔴"
        }.get(status.get("status", "unknown"), "⚪")
        
        card = self.create_base_card(f"{status_emoji} System Status")
        
        # Overall status
        card["body"].append({
            "type": "FactSet",
            "facts": [
                {
                    "title": "Status",
                    "value": status.get("status", "Unknown").title()
                },
                {
                    "title": "Last Updated",
                    "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
                }
            ]
        })
        
        # Services status
        if status.get("services"):
            services_facts = []
            for service_name, service_status in status["services"].items():
                service_emoji = "🟢" if service_status.get("status") == "healthy" else "🔴"
                services_facts.append({
                    "title": f"{service_emoji} {service_name.replace('_', ' ').title()}",
                    "value": service_status.get("status", "unknown").title()
                })
            
            if services_facts:
                card["body"].extend([
                    {
                        "type": "TextBlock",
                        "text": "**Services:**",
                        "weight": "Bolder",
                        "spacing": "Medium"
                    },
                    {
                        "type": "FactSet",
                        "facts": services_facts
                    }
                ])
        
        # User information
        if user_info:
            user_facts = []
            if user_info.get("access_level"):
                user_facts.append({
                    "title": "Access Level",
                    "value": user_info["access_level"].title()
                })
            if user_info.get("accessible_indexes"):
                user_facts.append({
                    "title": "Available Indexes",
                    "value": str(len(user_info["accessible_indexes"]))
                })
            if user_info.get("roles"):
                user_facts.append({
                    "title": "Roles",
                    "value": ", ".join(user_info["roles"])
                })
            
            if user_facts:
                card["body"].extend([
                    {
                        "type": "TextBlock",
                        "text": "**Your Access:**",
                        "weight": "Bolder",
                        "spacing": "Medium"
                    },
                    {
                        "type": "FactSet",
                        "facts": user_facts
                    }
                ])
        
        # Actions
        card["actions"] = [
            {
                "type": "Action.Submit",
                "title": "🔄 Refresh Status",
                "data": {
                    "action": "show_status"
                }
            }
        ]
        
        return {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": card
        }
    
    def create_welcome_card(self) -> Dict[str, Any]:
        """Create welcome adaptive card for new users."""
        card = self.create_base_card("👋 Welcome to Splunk MCP Assistant!")
        
        card["body"].extend([
            {
                "type": "TextBlock",
                "text": "I'm here to help you query and analyze your Splunk data using natural language.",
                "wrap": True
            },
            {
                "type": "TextBlock",
                "text": "**Get started:**",
                "weight": "Bolder",
                "spacing": "Medium"
            },
            {
                "type": "TextBlock",
                "text": "• Type **help** to see what I can do\n• Try: \"Show me errors from the last hour\"\n• Ask: \"What's the system status?\"",
                "wrap": True
            },
            {
                "type": "TextBlock",
                "text": "**Key features:**",
                "weight": "Bolder",
                "spacing": "Medium"
            },
            {
                "type": "TextBlock",
                "text": "🔍 Natural language queries\n📊 Automatic visualizations\n🚨 Alert management\n📈 Dashboard integration",
                "wrap": True
            }
        ])
        
        # Quick start actions
        card["actions"] = [
            {
                "type": "Action.Submit",
                "title": "🔍 Try Example Query",
                "data": {
                    "action": "run_query",
                    "query": "show me system overview"
                }
            },
            {
                "type": "Action.Submit",
                "title": "❓ Show Help",
                "data": {
                    "action": "show_help"
                }
            },
            {
                "type": "Action.Submit",
                "title": "📊 Check Status", 
                "data": {
                    "action": "show_status"
                }
            }
        ]
        
        return {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": card
        }
    
    def create_error_card(self, error_message: str) -> Dict[str, Any]:
        """Create error adaptive card."""
        card = self.create_base_card("❌ Error")
        
        card["body"].extend([
            {
                "type": "TextBlock",
                "text": error_message,
                "wrap": True,
                "color": "Attention"
            },
            {
                "type": "TextBlock",
                "text": "**Try:**",
                "weight": "Bolder",
                "spacing": "Medium"
            },
            {
                "type": "TextBlock",
                "text": "• Simplifying your query\n• Checking your spelling\n• Using **help** for examples\n• Contacting support if the issue persists",
                "wrap": True
            }
        ])
        
        card["actions"] = [
            {
                "type": "Action.Submit",
                "title": "❓ Get Help",
                "data": {
                    "action": "show_help"
                }
            },
            {
                "type": "Action.Submit",
                "title": "🔍 Try Example",
                "data": {
                    "action": "run_query",
                    "query": "show me recent events"
                }
            }
        ]
        
        return {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": card
        }
    
    def create_search_result_card(self, query: str) -> Dict[str, Any]:
        """Create search result card for messaging extension."""
        card = self.create_base_card("🔍 Splunk Query")
        
        card["body"].extend([
            {
                "type": "TextBlock",
                "text": f"**Query:** {query}",
                "wrap": True
            },
            {
                "type": "TextBlock",
                "text": "Click to execute this Splunk query",
                "size": "Small",
                "color": "Accent"
            }
        ])
        
        card["actions"] = [
            {
                "type": "Action.Submit",
                "title": "🚀 Execute Query",
                "data": {
                    "action": "run_query",
                    "query": query
                }
            }
        ]
        
        return card
    
    def create_dashboard_card(self, dashboard: Dict[str, Any]) -> Dict[str, Any]:
        """Create dashboard display card."""
        card = self.create_base_card(f"📊 {dashboard.get('name', 'Dashboard')}")
        
        if dashboard.get("description"):
            card["body"].append({
                "type": "TextBlock",
                "text": dashboard["description"],
                "wrap": True
            })
        
        # Dashboard metadata
        facts = []
        if dashboard.get("panel_count"):
            facts.append({
                "title": "Panels",
                "value": str(dashboard["panel_count"])
            })
        if dashboard.get("updated_at"):
            facts.append({
                "title": "Last Updated",
                "value": dashboard["updated_at"]
            })
        if dashboard.get("owner"):
            facts.append({
                "title": "Owner",
                "value": dashboard["owner"]
            })
        
        if facts:
            card["body"].append({
                "type": "FactSet",
                "facts": facts
            })
        
        # Actions
        actions = []
        if dashboard.get("url"):
            actions.append({
                "type": "Action.OpenUrl",
                "title": "Open Dashboard",
                "url": dashboard["url"]
            })
        
        actions.append({
            "type": "Action.Submit",
            "title": "📊 View Details",
            "data": {
                "action": "view_dashboard",
                "dashboard_id": dashboard.get("id")
            }
        })
        
        if actions:
            card["actions"] = actions
        
        return {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": card
        }