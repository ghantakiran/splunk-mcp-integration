import { LoginCredentials, AuthResponse, User, RegisterData, TokenRefreshResponse } from '../types/auth';
import apiClient from './api';

export class AuthService {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const formData = new FormData();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);

    return apiClient.post<AuthResponse>('/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }

  async register(userData: RegisterData): Promise<AuthResponse> {
    return apiClient.post<AuthResponse>('/auth/register', userData);
  }

  async logout(): Promise<void> {
    return apiClient.post('/auth/logout');
  }

  async refreshToken(): Promise<TokenRefreshResponse> {
    const refreshToken = localStorage.getItem('refresh_token');
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    return apiClient.post<TokenRefreshResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });
  }

  async getCurrentUser(): Promise<User> {
    return apiClient.get<User>('/auth/me');
  }

  async updateProfile(userData: Partial<User>): Promise<User> {
    return apiClient.put<User>('/auth/profile', userData);
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    return apiClient.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  async resetPassword(email: string): Promise<void> {
    return apiClient.post('/auth/reset-password', { email });
  }

  async confirmPasswordReset(token: string, newPassword: string): Promise<void> {
    return apiClient.post('/auth/confirm-reset', {
      token,
      new_password: newPassword,
    });
  }

  // Utility methods
  isTokenExpired(token: string): boolean {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const currentTime = Date.now() / 1000;
      return payload.exp < currentTime;
    } catch {
      return true;
    }
  }

  getTokenExpirationTime(token: string): Date | null {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return new Date(payload.exp * 1000);
    } catch {
      return null;
    }
  }
}

export const authService = new AuthService();