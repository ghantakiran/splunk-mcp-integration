"""
WebSocket manager for real-time chat communication
"""
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from fastapi.security import HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.core.security import verify_token
from app.models.user import User
from app.db.session import get_db

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    WebSocket connection manager for handling real-time chat connections
    """
    
    def __init__(self):
        # Active connections: {user_id: {connection_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # Connection metadata: {connection_id: {user_id, conversation_id, last_activity}}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        # Conversation subscribers: {conversation_id: set(user_ids)}
        self.conversation_subscribers: Dict[str, set] = {}
        # User typing status: {conversation_id: {user_id: timestamp}}
        self.typing_status: Dict[str, Dict[str, datetime]] = {}
        
    async def connect(self, websocket: WebSocket, user_id: str, conversation_id: Optional[str] = None):
        """
        Connect a new WebSocket client
        """
        await websocket.accept()
        
        connection_id = str(uuid4())
        
        # Store connection
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        self.active_connections[user_id][connection_id] = websocket
        
        # Store metadata
        self.connection_metadata[connection_id] = {
            'user_id': user_id,
            'conversation_id': conversation_id,
            'last_activity': datetime.utcnow(),
            'connection_time': datetime.utcnow()
        }
        
        # Subscribe to conversation if specified
        if conversation_id:
            await self.subscribe_to_conversation(user_id, conversation_id)
        
        logger.info(f"WebSocket connected: user={user_id}, connection={connection_id}")
        
        # Send connection confirmation
        await self.send_personal_message(user_id, {
            'type': 'connection_established',
            'connection_id': connection_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return connection_id
    
    async def disconnect(self, connection_id: str):
        """
        Disconnect a WebSocket client
        """
        if connection_id not in self.connection_metadata:
            return
        
        metadata = self.connection_metadata[connection_id]
        user_id = metadata['user_id']
        conversation_id = metadata.get('conversation_id')
        
        # Remove from active connections
        if user_id in self.active_connections:
            if connection_id in self.active_connections[user_id]:
                del self.active_connections[user_id][connection_id]
            
            # Remove user entirely if no more connections
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remove metadata
        del self.connection_metadata[connection_id]
        
        # Unsubscribe from conversation
        if conversation_id:
            await self.unsubscribe_from_conversation(user_id, conversation_id)
        
        # Clear typing status
        if conversation_id and conversation_id in self.typing_status:
            self.typing_status[conversation_id].pop(user_id, None)
            await self.broadcast_typing_status(conversation_id)
        
        logger.info(f"WebSocket disconnected: user={user_id}, connection={connection_id}")
    
    async def subscribe_to_conversation(self, user_id: str, conversation_id: str):
        """
        Subscribe user to a conversation
        """
        if conversation_id not in self.conversation_subscribers:
            self.conversation_subscribers[conversation_id] = set()
        
        self.conversation_subscribers[conversation_id].add(user_id)
        
        # Update connection metadata
        for conn_id, metadata in self.connection_metadata.items():
            if metadata['user_id'] == user_id:
                metadata['conversation_id'] = conversation_id
        
        logger.info(f"User {user_id} subscribed to conversation {conversation_id}")
    
    async def unsubscribe_from_conversation(self, user_id: str, conversation_id: str):
        """
        Unsubscribe user from a conversation
        """
        if conversation_id in self.conversation_subscribers:
            self.conversation_subscribers[conversation_id].discard(user_id)
            
            # Clean up empty conversation
            if not self.conversation_subscribers[conversation_id]:
                del self.conversation_subscribers[conversation_id]
        
        logger.info(f"User {user_id} unsubscribed from conversation {conversation_id}")
    
    async def send_personal_message(self, user_id: str, message: dict):
        """
        Send message to a specific user (all their connections)
        """
        if user_id not in self.active_connections:
            return
        
        message_data = json.dumps(message)
        
        # Send to all user's connections
        dead_connections = []
        for connection_id, websocket in self.active_connections[user_id].items():
            try:
                await websocket.send_text(message_data)
                # Update last activity
                if connection_id in self.connection_metadata:
                    self.connection_metadata[connection_id]['last_activity'] = datetime.utcnow()
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {e}")
                dead_connections.append(connection_id)
        
        # Clean up dead connections
        for conn_id in dead_connections:
            await self.disconnect(conn_id)
    
    async def broadcast_to_conversation(self, conversation_id: str, message: dict, exclude_user: Optional[str] = None):
        """
        Broadcast message to all users in a conversation
        """
        if conversation_id not in self.conversation_subscribers:
            return
        
        subscribers = self.conversation_subscribers[conversation_id].copy()
        if exclude_user:
            subscribers.discard(exclude_user)
        
        # Send to all subscribers
        for user_id in subscribers:
            await self.send_personal_message(user_id, message)
    
    async def handle_typing_status(self, user_id: str, conversation_id: str, is_typing: bool):
        """
        Handle typing status updates
        """
        if conversation_id not in self.typing_status:
            self.typing_status[conversation_id] = {}
        
        if is_typing:
            self.typing_status[conversation_id][user_id] = datetime.utcnow()
        else:
            self.typing_status[conversation_id].pop(user_id, None)
        
        await self.broadcast_typing_status(conversation_id)
    
    async def broadcast_typing_status(self, conversation_id: str):
        """
        Broadcast current typing status to conversation subscribers
        """
        if conversation_id not in self.typing_status:
            return
        
        # Clean up old typing status (>5 seconds old)
        now = datetime.utcnow()
        expired_users = []
        for user_id, timestamp in self.typing_status[conversation_id].items():
            if (now - timestamp).total_seconds() > 5:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.typing_status[conversation_id][user_id]
        
        typing_users = list(self.typing_status[conversation_id].keys())
        
        message = {
            'type': 'typing_status',
            'conversation_id': conversation_id,
            'typing_users': typing_users,
            'timestamp': now.isoformat()
        }
        
        await self.broadcast_to_conversation(conversation_id, message)
    
    async def broadcast_message(self, message: dict):
        """
        Broadcast message to all connected users
        """
        message_data = json.dumps(message)
        
        dead_connections = []
        for user_id, connections in self.active_connections.items():
            for connection_id, websocket in connections.items():
                try:
                    await websocket.send_text(message_data)
                except Exception as e:
                    logger.error(f"Error broadcasting to {user_id}: {e}")
                    dead_connections.append(connection_id)
        
        # Clean up dead connections
        for conn_id in dead_connections:
            await self.disconnect(conn_id)
    
    async def get_online_users(self) -> List[str]:
        """
        Get list of currently online users
        """
        return list(self.active_connections.keys())
    
    async def get_conversation_participants(self, conversation_id: str) -> List[str]:
        """
        Get list of users currently subscribed to a conversation
        """
        return list(self.conversation_subscribers.get(conversation_id, set()))
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get connection statistics
        """
        total_connections = sum(len(connections) for connections in self.active_connections.values())
        total_users = len(self.active_connections)
        total_conversations = len(self.conversation_subscribers)
        
        return {
            'total_connections': total_connections,
            'total_users': total_users,
            'total_conversations': total_conversations,
            'active_connections': {
                user_id: len(connections) 
                for user_id, connections in self.active_connections.items()
            }
        }

# Global connection manager instance
manager = ConnectionManager()

async def authenticate_websocket(websocket: WebSocket, token: str) -> Optional[User]:
    """
    Authenticate WebSocket connection using JWT token
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        
        # Get user from database
        db = get_db()
        user = await db.get(User, user_id)
        if user is None or not user.is_active:
            return None
        
        return user
    except JWTError:
        return None

async def handle_websocket_message(websocket: WebSocket, user_id: str, message_data: dict):
    """
    Handle incoming WebSocket messages
    """
    message_type = message_data.get('type')
    
    if message_type == 'typing_start':
        conversation_id = message_data.get('conversation_id')
        if conversation_id:
            await manager.handle_typing_status(user_id, conversation_id, True)
    
    elif message_type == 'typing_stop':
        conversation_id = message_data.get('conversation_id')
        if conversation_id:
            await manager.handle_typing_status(user_id, conversation_id, False)
    
    elif message_type == 'join_conversation':
        conversation_id = message_data.get('conversation_id')
        if conversation_id:
            await manager.subscribe_to_conversation(user_id, conversation_id)
    
    elif message_type == 'leave_conversation':
        conversation_id = message_data.get('conversation_id')
        if conversation_id:
            await manager.unsubscribe_from_conversation(user_id, conversation_id)
    
    elif message_type == 'ping':
        await manager.send_personal_message(user_id, {
            'type': 'pong',
            'timestamp': datetime.utcnow().isoformat()
        })
    
    else:
        logger.warning(f"Unknown message type: {message_type}")

async def websocket_endpoint(websocket: WebSocket, token: str):
    """
    Main WebSocket endpoint handler
    """
    user = await authenticate_websocket(websocket, token)
    if not user:
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    connection_id = await manager.connect(websocket, user.id)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message_data = json.loads(data)
                await handle_websocket_message(websocket, user.id, message_data)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON received from {user.id}: {data}")
                await manager.send_personal_message(user.id, {
                    'type': 'error',
                    'message': 'Invalid JSON format',
                    'timestamp': datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.error(f"Error handling message from {user.id}: {e}")
                await manager.send_personal_message(user.id, {
                    'type': 'error',
                    'message': 'Message processing failed',
                    'timestamp': datetime.utcnow().isoformat()
                })
    
    except WebSocketDisconnect:
        await manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user.id}: {e}")
        await manager.disconnect(connection_id)

# Message broadcasting functions for other services
async def broadcast_new_message(conversation_id: str, message: dict):
    """
    Broadcast new message to conversation participants
    """
    message_data = {
        'type': 'new_message',
        'conversation_id': conversation_id,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    await manager.broadcast_to_conversation(conversation_id, message_data)

async def broadcast_message_status(conversation_id: str, message_id: str, status: str):
    """
    Broadcast message status update
    """
    message_data = {
        'type': 'message_status',
        'conversation_id': conversation_id,
        'message_id': message_id,
        'status': status,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    await manager.broadcast_to_conversation(conversation_id, message_data)

async def broadcast_conversation_update(conversation_id: str, update_data: dict):
    """
    Broadcast conversation update
    """
    message_data = {
        'type': 'conversation_update',
        'conversation_id': conversation_id,
        'update': update_data,
        'timestamp': datetime.utcnow().isoformat()
    }
    
    await manager.broadcast_to_conversation(conversation_id, message_data)

# Cleanup task for idle connections
async def cleanup_idle_connections():
    """
    Cleanup idle connections (run as background task)
    """
    while True:
        try:
            now = datetime.utcnow()
            idle_connections = []
            
            for conn_id, metadata in manager.connection_metadata.items():
                last_activity = metadata.get('last_activity', metadata.get('connection_time'))
                if (now - last_activity).total_seconds() > 300:  # 5 minutes idle
                    idle_connections.append(conn_id)
            
            for conn_id in idle_connections:
                await manager.disconnect(conn_id)
            
            # Clean up old typing status
            for conversation_id in list(manager.typing_status.keys()):
                await manager.broadcast_typing_status(conversation_id)
            
            await asyncio.sleep(30)  # Check every 30 seconds
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(30)