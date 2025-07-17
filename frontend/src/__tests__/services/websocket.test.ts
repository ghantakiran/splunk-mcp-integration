import { WebSocketService } from '../../services/websocket';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.(new Event('open'));
    }, 10);
  }

  send(data: string) {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    // Mock echo for testing
    setTimeout(() => {
      this.onmessage?.(new MessageEvent('message', { data }));
    }, 10);
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.(new CloseEvent('close', { code, reason }));
  }
}

// Mock store
jest.mock('../../store', () => ({
  store: {
    dispatch: jest.fn(),
    getState: () => ({
      auth: { accessToken: 'mock-token' },
    }),
  },
}));

// Mock store actions
jest.mock('../../store/chatSlice', () => ({
  addMessage: jest.fn(),
  setConnectionStatus: jest.fn(),
  setTypingIndicator: jest.fn(),
}));

// Mock environment
process.env.REACT_APP_WS_URL = 'ws://localhost:8000';

describe('WebSocketService', () => {
  let service: WebSocketService;

  beforeEach(() => {
    // Mock WebSocket globally
    global.WebSocket = MockWebSocket as any;
    service = new WebSocketService();
    jest.clearAllMocks();
  });

  afterEach(() => {
    service.disconnect();
  });

  describe('Connection Management', () => {
    test('should connect successfully', async () => {
      const token = 'test-token';
      
      await service.connect(token);
      
      expect(service.isConnected()).toBe(true);
      expect(service.getReadyState()).toBe(MockWebSocket.OPEN);
    });

    test('should handle connection with correct URL', async () => {
      const token = 'test-token';
      
      await service.connect(token);
      
      // Check if WebSocket was created with correct URL
      expect(global.WebSocket).toHaveBeenCalledWith(
        `ws://localhost:8000/ws?token=${encodeURIComponent(token)}`
      );
    });

    test('should not create multiple connections', async () => {
      const token = 'test-token';
      
      await service.connect(token);
      await service.connect(token);
      
      expect(global.WebSocket).toHaveBeenCalledTimes(1);
    });

    test('should disconnect properly', async () => {
      const token = 'test-token';
      
      await service.connect(token);
      service.disconnect();
      
      expect(service.isConnected()).toBe(false);
      expect(service.getReadyState()).toBe(MockWebSocket.CLOSED);
    });
  });

  describe('Message Handling', () => {
    test('should send ping message', async () => {
      const token = 'test-token';
      await service.connect(token);
      
      const mockSend = jest.spyOn(service as any, 'send');
      
      service.send({ type: 'ping' });
      
      expect(mockSend).toHaveBeenCalledWith({ type: 'ping' });
    });

    test('should handle typing indicators', async () => {
      const token = 'test-token';
      await service.connect(token);
      
      const conversationId = 'test-conversation';
      
      service.startTyping(conversationId);
      service.stopTyping(conversationId);
      
      // Should not throw errors
      expect(service.isConnected()).toBe(true);
    });

    test('should handle conversation management', async () => {
      const token = 'test-token';
      await service.connect(token);
      
      const conversationId = 'test-conversation';
      
      service.joinConversation(conversationId);
      service.leaveConversation(conversationId);
      
      // Should not throw errors
      expect(service.isConnected()).toBe(true);
    });
  });

  describe('Error Handling', () => {
    test('should handle send on closed connection', async () => {
      const token = 'test-token';
      await service.connect(token);
      
      service.disconnect();
      
      // Should not throw when trying to send on closed connection
      expect(() => {
        service.send({ type: 'test' });
      }).not.toThrow();
    });

    test('should handle invalid JSON messages', async () => {
      const token = 'test-token';
      await service.connect(token);
      
      const mockConsoleError = jest.spyOn(console, 'error').mockImplementation();
      
      // Simulate invalid JSON message
      const ws = (service as any).socket;
      ws.onmessage(new MessageEvent('message', { data: 'invalid-json' }));
      
      expect(mockConsoleError).toHaveBeenCalledWith('Error parsing WebSocket message:', expect.any(Error));
      
      mockConsoleError.mockRestore();
    });
  });

  describe('Reconnection Logic', () => {
    test('should attempt reconnection on unexpected close', async () => {
      const token = 'test-token';
      await service.connect(token);
      
      const mockConnect = jest.spyOn(service, 'connect');
      
      // Simulate unexpected close
      const ws = (service as any).socket;
      ws.onclose(new CloseEvent('close', { code: 1006 })); // Abnormal closure
      
      // Wait for reconnection attempt
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(mockConnect).toHaveBeenCalledWith(token);
    });

    test('should not reconnect on normal close', async () => {
      const token = 'test-token';
      await service.connect(token);
      
      const mockConnect = jest.spyOn(service, 'connect');
      
      // Simulate normal close
      const ws = (service as any).socket;
      ws.onclose(new CloseEvent('close', { code: 1000 })); // Normal closure
      
      await new Promise(resolve => setTimeout(resolve, 100));
      
      expect(mockConnect).not.toHaveBeenCalled();
    });
  });

  describe('Message Types', () => {
    test('should handle different message types', async () => {
      const token = 'test-token';
      await service.connect(token);
      
      const ws = (service as any).socket;
      
      // Test different message types
      const messages = [
        { type: 'connection_established', connection_id: 'test-id' },
        { type: 'new_message', message: { id: '1', content: 'test' } },
        { type: 'typing_status', typing_users: ['user1'] },
        { type: 'message_status', message_id: '1', status: 'delivered' },
        { type: 'pong' },
        { type: 'error', message: 'Test error' },
        { type: 'unknown_type' },
      ];
      
      messages.forEach(message => {
        expect(() => {
          ws.onmessage(new MessageEvent('message', { data: JSON.stringify(message) }));
        }).not.toThrow();
      });
    });
  });
});