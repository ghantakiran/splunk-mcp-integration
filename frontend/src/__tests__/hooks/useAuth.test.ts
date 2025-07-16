import { renderHook } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import React from 'react';

import { useAuth } from '../../hooks/useAuth';
import authSlice from '../../store/authSlice';
import chatSlice from '../../store/chatSlice';
import dashboardSlice from '../../store/dashboardSlice';
import { User } from '../../types/auth';

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

describe('useAuth Hook', () => {
  test('returns initial unauthenticated state', () => {
    const store = createMockStore();
    const { result } = renderHook(() => useAuth(), {
      wrapper: (props) => wrapper({ ...props, store }),
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBe(null);
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  test('returns authenticated state when user is logged in', () => {
    const mockUser: User = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      roles: ['user'],
      permissions: ['read'],
      accessible_indexes: ['main'],
      preferences: {},
      created_at: '2023-01-01T00:00:00Z',
      last_login: '2023-01-01T00:00:00Z',
      is_active: true,
    };

    const store = createMockStore({
      auth: {
        user: mockUser,
        accessToken: 'mock-token',
        refreshToken: 'mock-refresh-token',
        isAuthenticated: true,
        loading: false,
        error: null,
      },
    });

    const { result } = renderHook(() => useAuth(), {
      wrapper: (props) => wrapper({ ...props, store }),
    });

    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual(mockUser);
    expect(result.current.accessToken).toBe('mock-token');
  });

  test('hasRole returns correct boolean', () => {
    const mockUser: User = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      roles: ['admin', 'user'],
      permissions: ['read', 'write'],
      accessible_indexes: ['main'],
      preferences: {},
      created_at: '2023-01-01T00:00:00Z',
      last_login: '2023-01-01T00:00:00Z',
      is_active: true,
    };

    const store = createMockStore({
      auth: {
        user: mockUser,
        accessToken: 'mock-token',
        refreshToken: 'mock-refresh-token',
        isAuthenticated: true,
        loading: false,
        error: null,
      },
    });

    const { result } = renderHook(() => useAuth(), {
      wrapper: (props) => wrapper({ ...props, store }),
    });

    expect(result.current.hasRole('admin')).toBe(true);
    expect(result.current.hasRole('user')).toBe(true);
    expect(result.current.hasRole('super_admin')).toBe(false);
  });

  test('hasPermission returns correct boolean', () => {
    const mockUser: User = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      roles: ['user'],
      permissions: ['read', 'write'],
      accessible_indexes: ['main'],
      preferences: {},
      created_at: '2023-01-01T00:00:00Z',
      last_login: '2023-01-01T00:00:00Z',
      is_active: true,
    };

    const store = createMockStore({
      auth: {
        user: mockUser,
        accessToken: 'mock-token',
        refreshToken: 'mock-refresh-token',
        isAuthenticated: true,
        loading: false,
        error: null,
      },
    });

    const { result } = renderHook(() => useAuth(), {
      wrapper: (props) => wrapper({ ...props, store }),
    });

    expect(result.current.hasPermission('read')).toBe(true);
    expect(result.current.hasPermission('write')).toBe(true);
    expect(result.current.hasPermission('admin')).toBe(false);
  });

  test('isAdmin returns true for admin roles', () => {
    const mockUser: User = {
      id: '1',
      username: 'admin',
      email: 'admin@example.com',
      first_name: 'Admin',
      last_name: 'User',
      roles: ['admin'],
      permissions: ['read', 'write', 'admin'],
      accessible_indexes: ['main'],
      preferences: {},
      created_at: '2023-01-01T00:00:00Z',
      last_login: '2023-01-01T00:00:00Z',
      is_active: true,
    };

    const store = createMockStore({
      auth: {
        user: mockUser,
        accessToken: 'mock-token',
        refreshToken: 'mock-refresh-token',
        isAuthenticated: true,
        loading: false,
        error: null,
      },
    });

    const { result } = renderHook(() => useAuth(), {
      wrapper: (props) => wrapper({ ...props, store }),
    });

    expect(result.current.isAdmin()).toBe(true);
    expect(result.current.isSuperAdmin()).toBe(false);
  });

  test('canAccessIndex returns correct boolean', () => {
    const mockUser: User = {
      id: '1',
      username: 'testuser',
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      roles: ['user'],
      permissions: ['read'],
      accessible_indexes: ['main', 'security'],
      preferences: {},
      created_at: '2023-01-01T00:00:00Z',
      last_login: '2023-01-01T00:00:00Z',
      is_active: true,
    };

    const store = createMockStore({
      auth: {
        user: mockUser,
        accessToken: 'mock-token',
        refreshToken: 'mock-refresh-token',
        isAuthenticated: true,
        loading: false,
        error: null,
      },
    });

    const { result } = renderHook(() => useAuth(), {
      wrapper: (props) => wrapper({ ...props, store }),
    });

    expect(result.current.canAccessIndex('main')).toBe(true);
    expect(result.current.canAccessIndex('security')).toBe(true);
    expect(result.current.canAccessIndex('restricted')).toBe(false);
  });
});