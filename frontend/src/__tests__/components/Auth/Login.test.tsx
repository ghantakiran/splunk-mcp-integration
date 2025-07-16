import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import { configureStore } from '@reduxjs/toolkit';
import '@testing-library/jest-dom';

import Login from '../../../components/Auth/Login';
import authSlice from '../../../store/authSlice';
import chatSlice from '../../../store/chatSlice';
import dashboardSlice from '../../../store/dashboardSlice';

// Mock API client
jest.mock('../../../services/api', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
  },
}));

// Mock auth service
jest.mock('../../../services/auth', () => ({
  authService: {
    login: jest.fn(),
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

const renderWithProviders = (component: React.ReactElement, initialState = {}) => {
  const store = createMockStore(initialState);
  return render(
    <Provider store={store}>
      <BrowserRouter>
        {component}
      </BrowserRouter>
    </Provider>
  );
};

describe('Login Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders login form correctly', () => {
    renderWithProviders(<Login />);

    expect(screen.getByText('Splunk MCP')).toBeInTheDocument();
    expect(screen.getByText('Sign in to your account')).toBeInTheDocument();
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  test('shows validation errors for empty fields', async () => {
    renderWithProviders(<Login />);

    const signInButton = screen.getByRole('button', { name: /sign in/i });
    fireEvent.click(signInButton);

    await waitFor(() => {
      expect(screen.getByText('Username is required')).toBeInTheDocument();
      expect(screen.getByText('Password is required')).toBeInTheDocument();
    });
  });

  test('allows typing in username and password fields', () => {
    renderWithProviders(<Login />);

    const usernameInput = screen.getByLabelText(/username/i);
    const passwordInput = screen.getByLabelText(/password/i);

    fireEvent.change(usernameInput, { target: { value: 'testuser' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    expect(usernameInput).toHaveValue('testuser');
    expect(passwordInput).toHaveValue('password123');
  });

  test('toggles password visibility', () => {
    renderWithProviders(<Login />);

    const passwordInput = screen.getByLabelText(/password/i);
    const toggleButton = screen.getByLabelText('toggle password visibility');

    expect(passwordInput).toHaveAttribute('type', 'password');

    fireEvent.click(toggleButton);
    expect(passwordInput).toHaveAttribute('type', 'text');

    fireEvent.click(toggleButton);
    expect(passwordInput).toHaveAttribute('type', 'password');
  });

  test('displays error message when login fails', () => {
    const initialState = {
      auth: {
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        loading: false,
        error: 'Invalid credentials',
      },
    };

    renderWithProviders(<Login />, initialState);

    expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
  });

  test('shows loading state during login', () => {
    const initialState = {
      auth: {
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        loading: true,
        error: null,
      },
    };

    renderWithProviders(<Login />, initialState);

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  test('shows links to register and forgot password', () => {
    renderWithProviders(<Login />);

    expect(screen.getByText('Sign up')).toBeInTheDocument();
    expect(screen.getByText('Forgot your password?')).toBeInTheDocument();
  });
});