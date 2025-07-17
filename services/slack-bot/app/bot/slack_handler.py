"""
Slack Bot Handler

Main handler for processing Slack events, messages, and interactions.
"""

import asyncio
import json
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import aiohttp
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from ..core.config import settings
from ..core.logging import get_logger, LogContext
from ..services.splunk_service import SplunkService
from ..services.user_service import UserService
from ..services.session_service import SessionService
from ..utils.message_formatter import MessageFormatter
from ..utils.rate_limiter import RateLimiter
from ..models.slack_models import SlackUser, SlackMessage, SlackInteraction

logger = get_logger(__name__)

class SlackHandler:
    """Main Slack bot handler."""
    
    def __init__(self):
        self.client = AsyncWebClient(token=settings.slack_bot_token)
        self.splunk_service = SplunkService()
        self.user_service = UserService()
        self.session_service = SessionService()
        self.message_formatter = MessageFormatter()
        self.rate_limiter = RateLimiter()
        self.bot_user_id = None
        
    async def initialize(self):
        """Initialize the Slack bot."""
        try:
            # Get bot user info
            response = await self.client.auth_test()
            self.bot_user_id = response["user_id"]
            
            logger.info(
                "Slack bot initialized successfully",
                bot_user_id=self.bot_user_id,
                team_id=response.get("team_id")
            )
            
            # Initialize services
            await self.splunk_service.initialize()
            await self.session_service.initialize()
            
        except SlackApiError as e:
            logger.error(f"Failed to initialize Slack bot: {e.response['error']}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during initialization: {str(e)}")
            raise
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.splunk_service.cleanup()
        await self.session_service.cleanup()
    
    async def health_check(self) -> bool:
        """Check if the bot is healthy."""
        try:
            response = await self.client.auth_test()
            return response["ok"]
        except Exception:
            return False
    
    async def handle_mention(self, event: Dict[str, Any]):
        """Handle app mention events."""
        with LogContext(event_type="mention", channel=event.get("channel")):
            try:
                # Extract user and channel info
                user_id = event.get("user")
                channel_id = event.get("channel")
                text = event.get("text", "")
                thread_ts = event.get("thread_ts") or event.get("ts")
                
                # Check rate limiting
                if not await self.rate_limiter.check_rate_limit(user_id):
                    await self._send_rate_limit_message(channel_id, thread_ts)
                    return
                
                # Remove bot mention from text
                clean_text = self._clean_mention_text(text)
                
                if not clean_text.strip():
                    await self._send_help_message(channel_id, thread_ts)
                    return
                
                # Process the query
                await self._process_query(user_id, channel_id, clean_text, thread_ts)
                
            except Exception as e:
                logger.error(f"Error handling mention: {str(e)}")
                await self._send_error_message(
                    event.get("channel"), 
                    event.get("thread_ts") or event.get("ts"),
                    "I encountered an error processing your request. Please try again."
                )
    
    async def handle_direct_message(self, event: Dict[str, Any]):
        """Handle direct message events."""
        if not settings.enable_direct_messages:
            return
            
        with LogContext(event_type="direct_message", user=event.get("user")):
            try:
                # Skip bot messages
                if event.get("user") == self.bot_user_id:
                    return
                
                user_id = event.get("user")
                channel_id = event.get("channel")
                text = event.get("text", "").strip()
                
                if not text:
                    return
                
                # Check rate limiting
                if not await self.rate_limiter.check_rate_limit(user_id):
                    await self._send_rate_limit_message(channel_id)
                    return
                
                # Process the query
                await self._process_query(user_id, channel_id, text)
                
            except Exception as e:
                logger.error(f"Error handling direct message: {str(e)}")
                await self._send_error_message(
                    event.get("channel"),
                    None,
                    "I encountered an error processing your message. Please try again."
                )
    
    async def handle_slash_command(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle slash commands."""
        if not settings.enable_slash_commands:
            return {"text": "Slash commands are currently disabled."}
            
        with LogContext(command=command_data.get("command")):
            try:
                command = command_data.get("command")
                text = command_data.get("text", "").strip()
                user_id = command_data.get("user_id")
                channel_id = command_data.get("channel_id")
                
                # Check rate limiting
                if not await self.rate_limiter.check_rate_limit(user_id):
                    return {"text": "Rate limit exceeded. Please try again later."}
                
                if command == "/splunk":
                    return await self._handle_splunk_command(text, user_id, channel_id)
                elif command == "/splunk-help":
                    return await self._handle_help_command()
                elif command == "/splunk-status":
                    return await self._handle_status_command(user_id)
                else:
                    return {"text": f"Unknown command: {command}"}
                    
            except Exception as e:
                logger.error(f"Error handling slash command: {str(e)}")
                return {"text": "An error occurred processing your command."}
    
    async def handle_interactive(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle interactive components."""
        try:
            interaction_type = payload.get("type")
            
            if interaction_type == "block_actions":
                return await self._handle_block_actions(payload)
            elif interaction_type == "view_submission":
                return await self._handle_modal_submission(payload)
            else:
                logger.warning(f"Unhandled interaction type: {interaction_type}")
                return {}
                
        except Exception as e:
            logger.error(f"Error handling interactive component: {str(e)}")
            return {"text": "An error occurred processing your interaction."}
    
    async def _process_query(self, user_id: str, channel_id: str, text: str, thread_ts: Optional[str] = None):
        """Process a natural language query."""
        try:
            # Get or create user session
            session = await self.session_service.get_or_create_session(user_id, channel_id)
            
            # Send typing indicator
            await self._send_typing_indicator(channel_id)
            
            # Check for special commands
            if text.lower().startswith(("help", "what can you do")):
                await self._send_help_message(channel_id, thread_ts)
                return
            
            if text.lower().startswith(("status", "health")):
                await self._send_status_message(channel_id, user_id, thread_ts)
                return
            
            # Process the Splunk query
            await self._send_initial_response(channel_id, thread_ts)
            
            # Get user context
            user_context = await self.user_service.get_user_context(user_id)
            
            # Send query to NLP engine
            query_response = await self.splunk_service.process_query(text, user_context, session)
            
            if query_response.get("success"):
                await self._send_query_results(channel_id, query_response, thread_ts)
            else:
                await self._send_error_message(
                    channel_id, 
                    thread_ts,
                    query_response.get("error", "Failed to process your query.")
                )
            
            # Update session
            await self.session_service.update_session(session["id"], text, query_response)
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            await self._send_error_message(
                channel_id,
                thread_ts,
                "I encountered an error processing your query. Please try again."
            )
    
    async def _send_query_results(self, channel_id: str, response: Dict[str, Any], thread_ts: Optional[str] = None):
        """Send query results to Slack."""
        try:
            data = response.get("data", {})
            
            # Format the response
            blocks = await self.message_formatter.format_query_response(data)
            
            # Send main response
            result = await self.client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                thread_ts=thread_ts,
                unfurl_links=False,
                unfurl_media=False
            )
            
            # If there are visualizations, send them as images
            if data.get("visualizations"):
                await self._send_visualizations(channel_id, data["visualizations"], thread_ts)
            
            logger.info(
                "Query results sent successfully",
                channel=channel_id,
                thread_ts=thread_ts,
                message_ts=result["ts"]
            )
            
        except SlackApiError as e:
            logger.error(f"Failed to send query results: {e.response['error']}")
            await self._send_error_message(
                channel_id,
                thread_ts,
                "I processed your query but couldn't send the results. Please try again."
            )
    
    async def _send_visualizations(self, channel_id: str, visualizations: List[Dict], thread_ts: Optional[str] = None):
        """Send visualization images to Slack."""
        for viz in visualizations:
            try:
                if viz.get("image_url"):
                    await self.client.chat_postMessage(
                        channel=channel_id,
                        text=viz.get("title", "Visualization"),
                        attachments=[{
                            "image_url": viz["image_url"],
                            "title": viz.get("title", "Chart")
                        }],
                        thread_ts=thread_ts
                    )
            except Exception as e:
                logger.error(f"Failed to send visualization: {str(e)}")
    
    async def _send_help_message(self, channel_id: str, thread_ts: Optional[str] = None):
        """Send help message."""
        blocks = self.message_formatter.format_help_message()
        
        await self.client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            thread_ts=thread_ts
        )
    
    async def _send_status_message(self, channel_id: str, user_id: str, thread_ts: Optional[str] = None):
        """Send status message."""
        try:
            status = await self.splunk_service.get_system_status()
            user_info = await self.user_service.get_user_info(user_id)
            
            blocks = self.message_formatter.format_status_message(status, user_info)
            
            await self.client.chat_postMessage(
                channel=channel_id,
                blocks=blocks,
                thread_ts=thread_ts
            )
        except Exception as e:
            logger.error(f"Failed to get status: {str(e)}")
            await self._send_error_message(
                channel_id,
                thread_ts,
                "Unable to retrieve system status at this time."
            )
    
    async def _send_initial_response(self, channel_id: str, thread_ts: Optional[str] = None):
        """Send initial processing response."""
        await self.client.chat_postMessage(
            channel=channel_id,
            text="🔍 Processing your query...",
            thread_ts=thread_ts
        )
    
    async def _send_error_message(self, channel_id: str, thread_ts: Optional[str], message: str):
        """Send error message."""
        blocks = self.message_formatter.format_error_message(message)
        
        await self.client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            thread_ts=thread_ts
        )
    
    async def _send_rate_limit_message(self, channel_id: str, thread_ts: Optional[str] = None):
        """Send rate limit message."""
        await self.client.chat_postMessage(
            channel=channel_id,
            text="⚠️ You're sending requests too quickly. Please wait a moment before trying again.",
            thread_ts=thread_ts
        )
    
    async def _send_typing_indicator(self, channel_id: str):
        """Send typing indicator."""
        try:
            await self.client.conversations_typing(channel=channel_id)
        except SlackApiError:
            # Typing indicators are not critical
            pass
    
    def _clean_mention_text(self, text: str) -> str:
        """Remove bot mention from text."""
        if self.bot_user_id:
            # Remove <@BOTID> mentions
            text = re.sub(rf'<@{self.bot_user_id}>', '', text)
        
        # Remove any remaining @mentions that might be malformed
        text = re.sub(r'<@[A-Z0-9]+>', '', text)
        
        return text.strip()
    
    async def _handle_splunk_command(self, text: str, user_id: str, channel_id: str) -> Dict[str, Any]:
        """Handle /splunk command."""
        if not text:
            return {
                "response_type": "ephemeral",
                "text": "Please provide a query. Example: `/splunk show me errors from the last hour`"
            }
        
        # Process the query asynchronously and respond immediately
        asyncio.create_task(
            self._process_query(user_id, channel_id, text)
        )
        
        return {
            "response_type": "in_channel",
            "text": f"🔍 Processing query: {text}"
        }
    
    async def _handle_help_command(self) -> Dict[str, Any]:
        """Handle help command."""
        help_text = """
*Splunk MCP Bot Help*

*Commands:*
• `/splunk <query>` - Execute a natural language Splunk query
• `/splunk-help` - Show this help message
• `/splunk-status` - Check system status

*Examples:*
• `/splunk show me errors from the last hour`
• `/splunk count events by source`
• `/splunk find failed login attempts`

*Mentions:*
You can also mention me directly: `@splunk-bot show me server performance`

*Direct Messages:*
Send me a direct message with your query for private results.
        """
        
        return {
            "response_type": "ephemeral",
            "text": help_text
        }
    
    async def _handle_status_command(self, user_id: str) -> Dict[str, Any]:
        """Handle status command."""
        try:
            status = await self.splunk_service.get_system_status()
            user_info = await self.user_service.get_user_info(user_id)
            
            status_text = f"""
*System Status:* {status.get('status', 'Unknown')}
*Services:* {', '.join(status.get('services', {}).keys())}
*Your Access Level:* {user_info.get('access_level', 'Standard')}
*Available Indexes:* {len(user_info.get('accessible_indexes', []))}
            """
            
            return {
                "response_type": "ephemeral",
                "text": status_text
            }
        except Exception as e:
            logger.error(f"Failed to get status: {str(e)}")
            return {
                "response_type": "ephemeral",
                "text": "Unable to retrieve system status at this time."
            }
    
    async def _handle_block_actions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle block action interactions."""
        actions = payload.get("actions", [])
        
        for action in actions:
            action_id = action.get("action_id")
            
            if action_id == "run_query":
                query = action.get("value")
                user_id = payload["user"]["id"]
                channel_id = payload["channel"]["id"]
                
                # Process the query
                asyncio.create_task(
                    self._process_query(user_id, channel_id, query)
                )
                
                return {
                    "response_action": "update",
                    "text": f"🔍 Running query: {query}"
                }
            
            elif action_id == "show_help":
                blocks = self.message_formatter.format_help_message()
                return {
                    "response_action": "update",
                    "blocks": blocks
                }
        
        return {}
    
    async def _handle_modal_submission(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle modal submissions."""
        # This can be extended for complex modal interactions
        return {"response_action": "clear"}