import { renderHook, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import React from 'react';

import { 
  useWebSocketConnection, 
  useTypingIndicator, 
  useConversationSubscription,
  useWebSocketStatus 
} from '../../hooks/useWebSocket';
import { websocketService } from '../../services/websocket';
import authSlice from '../../store/authSlice';
import chatSlice from '../../store/chatSlice';
import dashboardSlice from '../../store/dashboardSlice';

// Mock websocket service
jest.mock('../../services/websocket', () => ({
  websocketService: {
    connect: jest.fn(),
    disconnect: jest.fn(),
    startTyping: jest.fn(),
    stopTyping: jest.fn(),
    joinConversation: jest.fn(),
    leaveConversation: jest.fn(),
  },
}));

const createMockStore = (initialState = {}) => {
  return configureStore({
    reducer: {
      auth: authSlice,
      chat: chatSlice,
      dashboard: dashboardSlice,
    },
    preloadedState: {
      auth: {
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        loading: false,
        error: null,
      },
      chat: {
        conversations: [],
        currentConversation: null,
        messages: [],
        loading: false,
        sendingMessage: false,
        error: null,
        isConnected: false,
        typingIndicator: false,
      },
      dashboard: {
        dashboards: [],
        currentDashboard: null,
        panels: [],
        loading: false,
        saving: false,
        error: null,
        selectedPanel: null,
        isEditing: false,
      },
      ...initialState,
    },
  });
};

const wrapper = ({ children, store }: { children: React.ReactNode; store: any }) => (
  <Provider store={store}>{children}</Provider>
);

describe('useWebSocketConnection', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('should connect when authenticated', () => {
    const store = createMockStore({
      auth: {
        user: { id: '1', username: 'test' },
        accessToken: 'test-token',
        refreshToken: 'refresh-token',
        isAuthenticated: true,
        loading: false,
        error: null,
      },
    });

    renderHook(() => useWebSocketConnection(), {
      wrapper: (props) => wrapper({ ...props, store }),
    });

    expect(websocketService.connect).toHaveBeenCalledWith('test-token');
  });

  test('should not connect when not authenticated', () => {
    const store = createMockStore();

    renderHook(() => useWebSocketConnection(), {
      wrapper: (props) => wrapper({ ...props, store }),
    });

    expect(websocketService.connect).not.toHaveBeenCalled();
  });

  test('should disconnect when authentication is lost', () => {
    const store = createMockStore({
      auth: {
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        loading: false,
        error: null,
      },
    });

    const { rerender } = renderHook(() => useWebSocketConnection(), {
      wrapper: (props) => wrapper({ ...props, store }),
    });

    // Simulate authentication loss
    rerender();

    expect(websocketService.disconnect).toHaveBeenCalled();
  });
});

describe('useTypingIndicator', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  test('should start typing', () => {
    const conversationId = 'test-conversation';
    const { result } = renderHook(() => useTypingIndicator(conversationId));

    act(() => {
      result.current.startTyping();
    });

    expect(websocketService.startTyping).toHaveBeenCalledWith(conversationId);
  });

  test('should stop typing', () => {
    const conversationId = 'test-conversation';
    const { result } = renderHook(() => useTypingIndicator(conversationId));

    act(() => {
      result.current.stopTyping();
    });

    expect(websocketService.stopTyping).toHaveBeenCalledWith(conversationId);
  });

  test('should auto-stop typing after timeout', () => {
    const conversationId = 'test-conversation';
    const { result } = renderHook(() => useTypingIndicator(conversationId));

    act(() => {
      result.current.startTyping();
    });

    // Fast forward time
    act(() => {
      jest.advanceTimersByTime(3000);
    });

    expect(websocketService.stopTyping).toHaveBeenCalledWith(conversationId);
  });

  test('should not start typing without conversation ID', () => {
    const { result } = renderHook(() => useTypingIndicator(null));

    act(() => {
      result.current.startTyping();
    });

    expect(websocketService.startTyping).not.toHaveBeenCalled();
  });
});

describe('useConversationSubscription', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('should join conversation', () => {
    const conversationId = 'test-conversation';
    
    renderHook(() => useConversationSubscription(conversationId));

    expect(websocketService.joinConversation).toHaveBeenCalledWith(conversationId);
  });

  test('should leave previous conversation when switching', () => {
    const firstConversationId = 'conversation-1';
    const secondConversationId = 'conversation-2';
    
    const { rerender } = renderHook(
      ({ conversationId }) => useConversationSubscription(conversationId),
      { initialProps: { conversationId: firstConversationId } }
    );

    expect(websocketService.joinConversation).toHaveBeenCalledWith(firstConversationId);

    // Switch to second conversation
    rerender({ conversationId: secondConversationId });

    expect(websocketService.leaveConversation).toHaveBeenCalledWith(firstConversationId);
    expect(websocketService.joinConversation).toHaveBeenCalledWith(secondConversationId);
  });

  test('should not join when conversation ID is null', () => {
    renderHook(() => useConversationSubscription(null));

    expect(websocketService.joinConversation).not.toHaveBeenCalled();
  });

  test('should leave conversation on unmount', () => {
    const conversationId = 'test-conversation';
    
    const { unmount } = renderHook(() => useConversationSubscription(conversationId));

    unmount();

    expect(websocketService.leaveConversation).toHaveBeenCalledWith(conversationId);
  });
});

describe('useWebSocketStatus', () => {
  test('should return connected status', () => {
    const store = createMockStore({
      auth: {
        user: { id: '1', username: 'test' },
        accessToken: 'test-token',
        refreshToken: 'refresh-token',
        isAuthenticated: true,
        loading: false,
        error: null,
      },
      chat: {
        conversations: [],
        currentConversation: null,
        messages: [],
        loading: false,
        sendingMessage: false,
        error: null,
        isConnected: true,
        typingIndicator: false,
      },
    });

    const { result } = renderHook(() => useWebSocketStatus(), {
      wrapper: (props) => wrapper({ ...props, store }),
    });

    expect(result.current.isConnected).toBe(true);
    expect(result.current.connectionStatus).toBe('connected');
    expect(result.current.connectionColor).toBe('success');
  });

  test('should return disconnected status when not authenticated', () => {
    const store = createMockStore({
      auth: {
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        loading: false,
        error: null,
      },
      chat: {
        conversations: [],
        currentConversation: null,
        messages: [],
        loading: false,
        sendingMessage: false,
        error: null,
        isConnected: false,
        typingIndicator: false,
      },
    });

    const { result } = renderHook(() => useWebSocketStatus(), {
      wrapper: (props) => wrapper({ ...props, store }),
    });

    expect(result.current.isConnected).toBe(false);
    expect(result.current.connectionStatus).toBe('disconnected');
    expect(result.current.connectionColor).toBe('error');
  });

  test('should return connecting status when authenticated but not connected', () => {
    const store = createMockStore({
      auth: {
        user: { id: '1', username: 'test' },
        accessToken: 'test-token',
        refreshToken: 'refresh-token',
        isAuthenticated: true,
        loading: false,
        error: null,
      },
      chat: {
        conversations: [],
        currentConversation: null,
        messages: [],
        loading: false,
        sendingMessage: false,
        error: null,
        isConnected: false,
        typingIndicator: false,
      },
    });

    const { result } = renderHook(() => useWebSocketStatus(), {
      wrapper: (props) => wrapper({ ...props, store }),
    });

    expect(result.current.isConnected).toBe(false);
    expect(result.current.connectionStatus).toBe('connecting');
    expect(result.current.connectionColor).toBe('warning');
  });
});