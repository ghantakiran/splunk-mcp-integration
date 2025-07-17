"""
Microsoft Teams Bot Handler

Main handler for processing Teams activities, messages, and interactions.
"""

import asyncio
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
import aiohttp
from botbuilder.core import (
    TurnContext, 
    MessageFactory, 
    ActivityHandler,
    ConversationState,
    UserState,
    MemoryStorage
)
from botbuilder.schema import (
    Activity, 
    ActivityTypes, 
    ChannelAccount,
    CardAction,
    ActionTypes,
    SuggestedActions
)
from botbuilder.core.conversation_state import ConversationState
from botbuilder.core.user_state import UserState

from ..core.config import settings
from ..core.logging import get_logger, LogContext
from ..services.splunk_service import SplunkService
from ..services.user_service import UserService
from ..services.session_service import SessionService
from ..utils.message_formatter import TeamsMessageFormatter
from ..utils.rate_limiter import RateLimiter
from ..utils.adaptive_cards import AdaptiveCardBuilder
from ..models.teams_models import TeamsUser, TeamsMessage, UserContext

logger = get_logger(__name__)

class TeamsHandler(ActivityHandler):
    """Main Microsoft Teams bot handler."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize storage
        self.memory_storage = MemoryStorage()
        self.conversation_state = ConversationState(self.memory_storage)
        self.user_state = UserState(self.memory_storage)
        
        # Initialize services
        self.splunk_service = SplunkService()
        self.user_service = UserService()
        self.session_service = SessionService()
        self.message_formatter = TeamsMessageFormatter()
        self.rate_limiter = RateLimiter()
        self.card_builder = AdaptiveCardBuilder()
        
        # Bot information
        self.bot_app_id = settings.microsoft_app_id
        self.bot_name = "Splunk MCP Assistant"
        
    async def initialize(self):
        """Initialize the Teams bot."""
        try:
            logger.info(
                "Teams bot initializing",
                bot_app_id=self.bot_app_id,
                bot_name=self.bot_name
            )
            
            # Initialize services
            await self.splunk_service.initialize()
            await self.user_service.initialize()
            await self.session_service.initialize()
            await self.rate_limiter.initialize()
            
            logger.info("Teams bot initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Teams bot: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.splunk_service.cleanup()
        await self.user_service.cleanup()
        await self.session_service.cleanup()
        await self.rate_limiter.cleanup()
    
    async def health_check(self) -> bool:
        """Check if the bot is healthy."""
        try:
            # Basic health check - could be expanded to check services
            return True
        except Exception:
            return False
    
    async def handle_message(self, activity: Dict[str, Any]):
        """Handle incoming message activities."""
        with LogContext(
            activity_type="message",
            channel_id=activity.get("channelId"),
            conversation_id=activity.get("conversation", {}).get("id")
        ):
            try:
                # Extract message information
                user_id = activity.get("from", {}).get("id")
                conversation_id = activity.get("conversation", {}).get("id")
                text = activity.get("text", "").strip()
                
                if not text:
                    return
                
                # Check if bot was mentioned
                is_mentioned = self._is_bot_mentioned(activity)
                conversation_type = activity.get("conversation", {}).get("conversationType", "")
                
                # Only respond to direct mentions in channels or all messages in personal/group chats
                if conversation_type == "channel" and not is_mentioned:
                    return
                
                # Check rate limiting
                if not await self.rate_limiter.check_rate_limit(user_id):
                    await self._send_rate_limit_message(activity)
                    return
                
                # Remove bot mention from text
                clean_text = self._clean_mention_text(text, activity)
                
                if not clean_text.strip():
                    await self._send_help_message(activity)
                    return
                
                # Process the query
                await self._process_query(activity, clean_text)
                
            except Exception as e:
                logger.error(f"Error handling message: {str(e)}")
                await self._send_error_message(
                    activity,
                    "I encountered an error processing your message. Please try again."
                )
    
    async def handle_invoke(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Handle invoke activities (adaptive cards, task modules)."""
        try:
            invoke_name = activity.get("name", "")
            
            if invoke_name == "adaptiveCard/action":
                return await self._handle_adaptive_card_action(activity)
            elif invoke_name == "task/fetch":
                return await self._handle_task_fetch(activity)
            elif invoke_name == "task/submit":
                return await self._handle_task_submit(activity)
            elif invoke_name == "composeExtension/query":
                return await self._handle_messaging_extension_query(activity)
            else:
                logger.warning(f"Unhandled invoke: {invoke_name}")
                return {"status": 200}
                
        except Exception as e:
            logger.error(f"Error handling invoke: {str(e)}")
            return {"status": 500, "body": {"error": str(e)}}
    
    async def handle_command(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Handle command activities."""
        try:
            command_id = activity.get("value", {}).get("commandId", "")
            
            if command_id == "splunk_query":
                return await self._handle_splunk_query_command(activity)
            elif command_id == "splunk_help":
                return await self._handle_help_command(activity)
            elif command_id == "splunk_status":
                return await self._handle_status_command(activity)
            else:
                logger.warning(f"Unhandled command: {command_id}")
                return {"status": 200}
                
        except Exception as e:
            logger.error(f"Error handling command: {str(e)}")
            return {"status": 500, "body": {"error": str(e)}}
    
    async def handle_member_added(self, activity: Dict[str, Any]):
        """Handle member added activities."""
        try:
            members_added = activity.get("membersAdded", [])
            
            for member in members_added:
                if member.get("id") != self.bot_app_id:
                    # Send welcome message to new member
                    await self._send_welcome_message(activity, member)
                    
        except Exception as e:
            logger.error(f"Error handling member added: {str(e)}")
    
    async def handle_installation_update(self, activity: Dict[str, Any]):
        """Handle installation update activities."""
        try:
            action = activity.get("action", "")
            
            if action == "add":
                await self._handle_bot_installed(activity)
            elif action == "remove":
                await self._handle_bot_uninstalled(activity)
                
        except Exception as e:
            logger.error(f"Error handling installation update: {str(e)}")
    
    async def _process_query(self, activity: Dict[str, Any], text: str):
        """Process a natural language query."""
        try:
            user_id = activity.get("from", {}).get("id")
            conversation_id = activity.get("conversation", {}).get("id")
            
            # Get or create user session
            session = await self.session_service.get_or_create_session(user_id, conversation_id)
            
            # Send typing indicator
            await self._send_typing_indicator(activity)
            
            # Check for special commands
            if text.lower().startswith(("help", "what can you do")):
                await self._send_help_message(activity)
                return
            
            if text.lower().startswith(("status", "health")):
                await self._send_status_message(activity)
                return
            
            # Process the Splunk query
            await self._send_initial_response(activity)
            
            # Get user context
            user_context = await self.user_service.get_user_context(user_id)
            
            # Send query to NLP engine
            query_response = await self.splunk_service.process_query(text, user_context, session)
            
            if query_response.get("success"):
                await self._send_query_results(activity, query_response)
            else:
                await self._send_error_message(
                    activity,
                    query_response.get("error", "Failed to process your query.")
                )
            
            # Update session
            await self.session_service.update_session(session["id"], text, query_response)
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            await self._send_error_message(
                activity,
                "I encountered an error processing your query. Please try again."
            )
    
    async def _send_query_results(self, activity: Dict[str, Any], response: Dict[str, Any]):
        """Send query results to Teams."""
        try:
            data = response.get("data", {})
            
            # Format the response
            message_activity = self.message_formatter.format_query_response(data)
            
            # Send main response
            await self._send_activity(activity, message_activity)
            
            # If there are visualizations, send them as adaptive cards
            if data.get("visualizations") and settings.enable_adaptive_cards:
                await self._send_visualizations(activity, data["visualizations"])
            
            logger.info(
                "Query results sent successfully",
                conversation_id=activity.get("conversation", {}).get("id")
            )
            
        except Exception as e:
            logger.error(f"Failed to send query results: {str(e)}")
            await self._send_error_message(
                activity,
                "I processed your query but couldn't send the results. Please try again."
            )
    
    async def _send_visualizations(self, activity: Dict[str, Any], visualizations: List[Dict]):
        """Send visualization cards to Teams."""
        for viz in visualizations:
            try:
                if viz.get("image_url"):
                    card = self.card_builder.create_visualization_card(viz)
                    message_activity = MessageFactory.attachment(card)
                    await self._send_activity(activity, message_activity)
            except Exception as e:
                logger.error(f"Failed to send visualization: {str(e)}")
    
    async def _send_help_message(self, activity: Dict[str, Any]):
        """Send help message."""
        help_card = self.card_builder.create_help_card()
        message_activity = MessageFactory.attachment(help_card)
        await self._send_activity(activity, message_activity)
    
    async def _send_status_message(self, activity: Dict[str, Any]):
        """Send status message."""
        try:
            user_id = activity.get("from", {}).get("id")
            status = await self.splunk_service.get_system_status()
            user_info = await self.user_service.get_user_info(user_id)
            
            status_card = self.card_builder.create_status_card(status, user_info)
            message_activity = MessageFactory.attachment(status_card)
            await self._send_activity(activity, message_activity)
            
        except Exception as e:
            logger.error(f"Failed to get status: {str(e)}")
            await self._send_error_message(
                activity,
                "Unable to retrieve system status at this time."
            )
    
    async def _send_welcome_message(self, activity: Dict[str, Any], member: Dict[str, Any]):
        """Send welcome message to new member."""
        welcome_card = self.card_builder.create_welcome_card()
        message_activity = MessageFactory.attachment(welcome_card)
        await self._send_activity(activity, message_activity)
    
    async def _send_initial_response(self, activity: Dict[str, Any]):
        """Send initial processing response."""
        message_activity = MessageFactory.text("🔍 Processing your query...")
        await self._send_activity(activity, message_activity)
    
    async def _send_error_message(self, activity: Dict[str, Any], message: str):
        """Send error message."""
        error_card = self.card_builder.create_error_card(message)
        message_activity = MessageFactory.attachment(error_card)
        await self._send_activity(activity, message_activity)
    
    async def _send_rate_limit_message(self, activity: Dict[str, Any]):
        """Send rate limit message."""
        message_activity = MessageFactory.text(
            "⚠️ You're sending requests too quickly. Please wait a moment before trying again."
        )
        await self._send_activity(activity, message_activity)
    
    async def _send_typing_indicator(self, activity: Dict[str, Any]):
        """Send typing indicator."""
        try:
            typing_activity = Activity(
                type=ActivityTypes.typing,
                conversation=activity.get("conversation"),
                recipient=activity.get("from"),
                from_property=activity.get("recipient")
            )
            await self._send_activity(activity, typing_activity)
        except Exception:
            # Typing indicators are not critical
            pass
    
    async def _send_activity(self, original_activity: Dict[str, Any], response_activity: Activity):
        """Send an activity to Teams."""
        # This would integrate with Bot Framework Connector
        # For now, we'll log the activity
        logger.info(
            "Sending activity to Teams",
            activity_type=response_activity.type,
            conversation_id=original_activity.get("conversation", {}).get("id")
        )
    
    def _is_bot_mentioned(self, activity: Dict[str, Any]) -> bool:
        """Check if the bot was mentioned in the activity."""
        entities = activity.get("entities", [])
        for entity in entities:
            if entity.get("type") == "mention":
                mentioned = entity.get("mentioned", {})
                if mentioned.get("id") == self.bot_app_id:
                    return True
        return False
    
    def _clean_mention_text(self, text: str, activity: Dict[str, Any]) -> str:
        """Remove bot mention from text."""
        # Remove @mentions
        entities = activity.get("entities", [])
        for entity in entities:
            if entity.get("type") == "mention":
                mention_text = entity.get("text", "")
                if mention_text:
                    text = text.replace(mention_text, "")
        
        # Clean up any remaining mention patterns
        text = re.sub(r'<at>[^<]*</at>', '', text)
        
        return text.strip()
    
    async def _handle_adaptive_card_action(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Handle adaptive card actions."""
        try:
            action_data = activity.get("value", {})
            action_type = action_data.get("action")
            
            if action_type == "run_query":
                query = action_data.get("query", "")
                await self._process_query(activity, query)
            elif action_type == "show_help":
                await self._send_help_message(activity)
            elif action_type == "show_status":
                await self._send_status_message(activity)
            
            return {"status": 200}
            
        except Exception as e:
            logger.error(f"Error handling adaptive card action: {str(e)}")
            return {"status": 500}
    
    async def _handle_task_fetch(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task module fetch."""
        try:
            # Return task module for advanced query interface
            task_info = {
                "type": "continue",
                "value": {
                    "title": "Advanced Splunk Query",
                    "height": 500,
                    "width": 600,
                    "url": f"{settings.api_gateway_url}/teams/task-module"
                }
            }
            
            return {"status": 200, "body": {"task": task_info}}
            
        except Exception as e:
            logger.error(f"Error handling task fetch: {str(e)}")
            return {"status": 500}
    
    async def _handle_task_submit(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task module submission."""
        try:
            data = activity.get("value", {}).get("data", {})
            query = data.get("query", "")
            
            if query:
                await self._process_query(activity, query)
            
            return {"status": 200}
            
        except Exception as e:
            logger.error(f"Error handling task submit: {str(e)}")
            return {"status": 500}
    
    async def _handle_messaging_extension_query(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Handle messaging extension query."""
        try:
            query_params = activity.get("value", {}).get("parameters", [])
            search_query = ""
            
            for param in query_params:
                if param.get("name") == "searchKeyword":
                    search_query = param.get("value", "")
                    break
            
            # Generate search results
            results = await self._generate_search_results(search_query)
            
            return {
                "status": 200,
                "body": {
                    "composeExtension": {
                        "type": "result",
                        "attachmentLayout": "list",
                        "attachments": results
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error handling messaging extension query: {str(e)}")
            return {"status": 500}
    
    async def _generate_search_results(self, query: str) -> List[Dict]:
        """Generate search results for messaging extension."""
        # This would integrate with Splunk search
        # For now, return sample results
        return [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": self.card_builder.create_search_result_card(query)
            }
        ]
    
    async def _handle_splunk_query_command(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Splunk query command."""
        try:
            query = activity.get("value", {}).get("data", {}).get("query", "")
            if query:
                await self._process_query(activity, query)
            else:
                await self._send_help_message(activity)
            
            return {"status": 200}
            
        except Exception as e:
            logger.error(f"Error handling Splunk query command: {str(e)}")
            return {"status": 500}
    
    async def _handle_help_command(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Handle help command."""
        await self._send_help_message(activity)
        return {"status": 200}
    
    async def _handle_status_command(self, activity: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status command."""
        await self._send_status_message(activity)
        return {"status": 200}
    
    async def _handle_bot_installed(self, activity: Dict[str, Any]):
        """Handle bot installation."""
        logger.info("Bot installed", conversation_id=activity.get("conversation", {}).get("id"))
        await self._send_welcome_message(activity, {})
    
    async def _handle_bot_uninstalled(self, activity: Dict[str, Any]):
        """Handle bot uninstallation."""
        logger.info("Bot uninstalled", conversation_id=activity.get("conversation", {}).get("id"))