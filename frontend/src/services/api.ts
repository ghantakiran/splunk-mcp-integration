import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import { store } from '../store';
import { updateToken, clearAuth } from '../store/authSlice';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export interface ApiResponse<T = any> {
  success: boolean;
  data: T;
  metadata: {
    timestamp: string;
    correlation_id: string;
    version: string;
  };
  errors: Array<{
    code: string;
    message: string;
    details?: any;
  }>;
}

class ApiClient {
  private instance: AxiosInstance;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (value?: any) => void;
    reject: (reason?: any) => void;
  }> = [];

  constructor() {
    this.instance = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor
    this.instance.interceptors.request.use(
      (config) => {
        const state = store.getState();
        const token = state.auth.accessToken;
        
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }

        // Add correlation ID for request tracking
        config.headers['X-Correlation-ID'] = this.generateCorrelationId();
        
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor
    this.instance.interceptors.response.use(
      (response: AxiosResponse<ApiResponse>) => {
        // Return the data from our standard API response format
        return {
          ...response,
          data: response.data.data || response.data,
        };
      },
      async (error: AxiosError<ApiResponse>) => {
        const originalRequest = error.config as any;

        if (error.response?.status === 401 && !originalRequest._retry) {
          if (this.isRefreshing) {
            // If already refreshing, queue this request
            return new Promise((resolve, reject) => {
              this.failedQueue.push({ resolve, reject });
            }).then((token) => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              return this.instance(originalRequest);
            }).catch((err) => {
              return Promise.reject(err);
            });
          }

          originalRequest._retry = true;
          this.isRefreshing = true;

          try {
            const state = store.getState();
            const refreshToken = state.auth.refreshToken;

            if (!refreshToken) {
              throw new Error('No refresh token available');
            }

            const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
              refresh_token: refreshToken,
            });

            const newToken = response.data.access_token;
            store.dispatch(updateToken(newToken));

            // Process failed queue
            this.processQueue(null, newToken);
            
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return this.instance(originalRequest);
          } catch (refreshError) {
            // Refresh failed, clear auth and redirect to login
            this.processQueue(refreshError, null);
            store.dispatch(clearAuth());
            window.location.href = '/login';
            return Promise.reject(refreshError);
          } finally {
            this.isRefreshing = false;
          }
        }

        return Promise.reject(error);
      }
    );
  }

  private processQueue(error: any, token: string | null = null) {
    this.failedQueue.forEach(({ resolve, reject }) => {
      if (error) {
        reject(error);
      } else {
        resolve(token);
      }
    });

    this.failedQueue = [];
  }

  private generateCorrelationId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  // HTTP Methods
  async get<T = any>(url: string, config = {}): Promise<T> {
    const response = await this.instance.get<ApiResponse<T>>(url, config);
    return response.data;
  }

  async post<T = any>(url: string, data = {}, config = {}): Promise<T> {
    const response = await this.instance.post<ApiResponse<T>>(url, data, config);
    return response.data;
  }

  async put<T = any>(url: string, data = {}, config = {}): Promise<T> {
    const response = await this.instance.put<ApiResponse<T>>(url, data, config);
    return response.data;
  }

  async patch<T = any>(url: string, data = {}, config = {}): Promise<T> {
    const response = await this.instance.patch<ApiResponse<T>>(url, data, config);
    return response.data;
  }

  async delete<T = any>(url: string, config = {}): Promise<T> {
    const response = await this.instance.delete<ApiResponse<T>>(url, config);
    return response.data;
  }

  // Utility methods
  setAuthToken(token: string) {
    this.instance.defaults.headers.common.Authorization = `Bearer ${token}`;
  }

  clearAuthToken() {
    delete this.instance.defaults.headers.common.Authorization;
  }

  getBaseURL(): string {
    return API_BASE_URL;
  }
}

export const apiClient = new ApiClient();
export default apiClient;