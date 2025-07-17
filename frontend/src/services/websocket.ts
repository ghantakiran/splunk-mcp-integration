import { store } from '../store';
import { addMessage, setConnectionStatus, setTypingIndicator } from '../store/chatSlice';
import { Message } from '../types/chat';

export interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export class WebSocketService {
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private pingInterval: NodeJS.Timeout | null = null;
  private connectionPromise: Promise<void> | null = null;

  constructor() {
    this.handleVisibilityChange = this.handleVisibilityChange.bind(this);
    this.handleOnline = this.handleOnline.bind(this);
    this.handleOffline = this.handleOffline.bind(this);
  }

  async connect(token: string): Promise<void> {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return;
    }

    if (this.connectionPromise) {
      return this.connectionPromise;
    }

    this.connectionPromise = this.createConnection(token);
    return this.connectionPromise;
  }

  private async createConnection(token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const wsUrl = `${process.env.REACT_APP_WS_URL || 'ws://localhost:8000'}/ws?token=${encodeURIComponent(token)}`;
      
      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        store.dispatch(setConnectionStatus(true));
        this.startPingPong();
        this.setupEventListeners();
        resolve();
      };

      this.socket.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          this.handleMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      this.socket.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        store.dispatch(setConnectionStatus(false));
        this.stopPingPong();
        this.removeEventListeners();
        this.connectionPromise = null;
        
        if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect(token);
        }
      };

      this.socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        store.dispatch(setConnectionStatus(false));
        reject(error);
      };
    });
  }

  private handleMessage(message: WebSocketMessage) {
    switch (message.type) {
      case 'connection_established':
        console.log('WebSocket connection established:', message.connection_id);
        break;

      case 'new_message':
        if (message.message) {
          store.dispatch(addMessage(message.message));
        }
        break;

      case 'typing_status':
        store.dispatch(setTypingIndicator(message.typing_users?.length > 0));
        break;

      case 'message_status':
        // Handle message status updates (read, delivered, etc.)
        break;

      case 'conversation_update':
        // Handle conversation updates
        break;

      case 'pong':
        // Handle ping/pong for connection health
        break;

      case 'error':
        console.error('WebSocket error message:', message.message);
        break;

      default:
        console.warn('Unknown WebSocket message type:', message.type);
    }
  }

  private scheduleReconnect(token: string) {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
    
    setTimeout(() => {
      this.connect(token).catch(console.error);
    }, delay);
  }

  private startPingPong() {
    this.pingInterval = setInterval(() => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });
      }
    }, 30000); // Ping every 30 seconds
  }

  private stopPingPong() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private setupEventListeners() {
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
    window.addEventListener('online', this.handleOnline);
    window.addEventListener('offline', this.handleOffline);
  }

  private removeEventListeners() {
    document.removeEventListener('visibilitychange', this.handleVisibilityChange);
    window.removeEventListener('online', this.handleOnline);
    window.removeEventListener('offline', this.handleOffline);
  }

  private handleVisibilityChange() {
    if (document.hidden) {
      // Page is hidden, reduce activity
      this.stopPingPong();
    } else {
      // Page is visible, resume activity
      this.startPingPong();
    }
  }

  private handleOnline() {
    console.log('Network online');
    const state = store.getState();
    const token = state.auth.accessToken;
    if (token && this.socket?.readyState !== WebSocket.OPEN) {
      this.connect(token);
    }
  }

  private handleOffline() {
    console.log('Network offline');
    store.dispatch(setConnectionStatus(false));
  }

  send(message: WebSocketMessage) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send message:', message);
    }
  }

  // Chat-specific methods
  startTyping(conversationId: string) {
    this.send({
      type: 'typing_start',
      conversation_id: conversationId,
    });
  }

  stopTyping(conversationId: string) {
    this.send({
      type: 'typing_stop',
      conversation_id: conversationId,
    });
  }

  joinConversation(conversationId: string) {
    this.send({
      type: 'join_conversation',
      conversation_id: conversationId,
    });
  }

  leaveConversation(conversationId: string) {
    this.send({
      type: 'leave_conversation',
      conversation_id: conversationId,
    });
  }

  disconnect() {
    this.removeEventListeners();
    this.stopPingPong();
    
    if (this.socket) {
      this.socket.close(1000, 'Client disconnecting');
      this.socket = null;
    }
    
    this.connectionPromise = null;
    store.dispatch(setConnectionStatus(false));
  }

  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  getReadyState(): number {
    return this.socket?.readyState ?? WebSocket.CLOSED;
  }
}

// Create singleton instance
export const websocketService = new WebSocketService();

// Hook for React components
export const useWebSocket = () => {
  const connect = (token: string) => websocketService.connect(token);
  const disconnect = () => websocketService.disconnect();
  const send = (message: WebSocketMessage) => websocketService.send(message);
  const isConnected = () => websocketService.isConnected();
  
  return {
    connect,
    disconnect,
    send,
    isConnected,
    startTyping: websocketService.startTyping.bind(websocketService),
    stopTyping: websocketService.stopTyping.bind(websocketService),
    joinConversation: websocketService.joinConversation.bind(websocketService),
    leaveConversation: websocketService.leaveConversation.bind(websocketService),
  };
};