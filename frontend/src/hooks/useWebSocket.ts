import { useEffect, useRef } from 'react';
import { useSelector } from 'react-redux';
import { RootState } from '../store';
import { websocketService } from '../services/websocket';

export const useWebSocketConnection = () => {
  const { isAuthenticated, accessToken } = useSelector((state: RootState) => state.auth);
  const { isConnected } = useSelector((state: RootState) => state.chat);
  const connectionAttempted = useRef(false);

  useEffect(() => {
    if (isAuthenticated && accessToken && !connectionAttempted.current) {
      connectionAttempted.current = true;
      websocketService.connect(accessToken).catch(console.error);
    }

    if (!isAuthenticated && connectionAttempted.current) {
      connectionAttempted.current = false;
      websocketService.disconnect();
    }

    return () => {
      if (connectionAttempted.current) {
        websocketService.disconnect();
        connectionAttempted.current = false;
      }
    };
  }, [isAuthenticated, accessToken]);

  return { isConnected };
};

export const useTypingIndicator = (conversationId: string | null) => {
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const startTyping = () => {
    if (!conversationId) return;

    websocketService.startTyping(conversationId);
    
    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
    
    // Set timeout to stop typing after 3 seconds of inactivity
    typingTimeoutRef.current = setTimeout(() => {
      websocketService.stopTyping(conversationId);
    }, 3000);
  };

  const stopTyping = () => {
    if (!conversationId) return;

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = null;
    }
    
    websocketService.stopTyping(conversationId);
  };

  useEffect(() => {
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, []);

  return { startTyping, stopTyping };
};

export const useConversationSubscription = (conversationId: string | null) => {
  const previousConversationId = useRef<string | null>(null);

  useEffect(() => {
    if (conversationId && conversationId !== previousConversationId.current) {
      // Leave previous conversation
      if (previousConversationId.current) {
        websocketService.leaveConversation(previousConversationId.current);
      }
      
      // Join new conversation
      websocketService.joinConversation(conversationId);
      previousConversationId.current = conversationId;
    }

    return () => {
      if (previousConversationId.current) {
        websocketService.leaveConversation(previousConversationId.current);
      }
    };
  }, [conversationId]);
};

export const useWebSocketStatus = () => {
  const { isConnected } = useSelector((state: RootState) => state.chat);
  const { isAuthenticated } = useSelector((state: RootState) => state.auth);

  const getConnectionStatus = () => {
    if (!isAuthenticated) return 'disconnected';
    if (isConnected) return 'connected';
    return 'connecting';
  };

  const getConnectionColor = () => {
    const status = getConnectionStatus();
    switch (status) {
      case 'connected': return 'success';
      case 'connecting': return 'warning';
      case 'disconnected': return 'error';
      default: return 'default';
    }
  };

  return {
    isConnected,
    connectionStatus: getConnectionStatus(),
    connectionColor: getConnectionColor(),
  };
};