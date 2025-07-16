import { useSelector, useDispatch } from 'react-redux';
import { useCallback } from 'react';
import { RootState, AppDispatch } from '../store';
import { loginUser, logoutUser, getCurrentUser, refreshToken, clearError } from '../store/authSlice';
import { LoginCredentials } from '../types/auth';

export const useAuth = () => {
  const dispatch = useDispatch<AppDispatch>();
  const authState = useSelector((state: RootState) => state.auth);

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      return dispatch(loginUser(credentials)).unwrap();
    },
    [dispatch]
  );

  const logout = useCallback(async () => {
    return dispatch(logoutUser()).unwrap();
  }, [dispatch]);

  const fetchCurrentUser = useCallback(async () => {
    return dispatch(getCurrentUser()).unwrap();
  }, [dispatch]);

  const refreshAuthToken = useCallback(async () => {
    return dispatch(refreshToken()).unwrap();
  }, [dispatch]);

  const clearAuthError = useCallback(() => {
    dispatch(clearError());
  }, [dispatch]);

  const hasRole = useCallback(
    (role: string): boolean => {
      return authState.user?.roles.includes(role) || false;
    },
    [authState.user]
  );

  const hasPermission = useCallback(
    (permission: string): boolean => {
      return authState.user?.permissions.includes(permission) || false;
    },
    [authState.user]
  );

  const hasAnyRole = useCallback(
    (roles: string[]): boolean => {
      return roles.some(role => hasRole(role));
    },
    [hasRole]
  );

  const hasAnyPermission = useCallback(
    (permissions: string[]): boolean => {
      return permissions.some(permission => hasPermission(permission));
    },
    [hasPermission]
  );

  const hasAllRoles = useCallback(
    (roles: string[]): boolean => {
      return roles.every(role => hasRole(role));
    },
    [hasRole]
  );

  const hasAllPermissions = useCallback(
    (permissions: string[]): boolean => {
      return permissions.every(permission => hasPermission(permission));
    },
    [hasPermission]
  );

  const canAccessIndex = useCallback(
    (indexName: string): boolean => {
      return authState.user?.accessible_indexes.includes(indexName) || false;
    },
    [authState.user]
  );

  const isAdmin = useCallback((): boolean => {
    return hasRole('admin') || hasRole('super_admin');
  }, [hasRole]);

  const isSuperAdmin = useCallback((): boolean => {
    return hasRole('super_admin');
  }, [hasRole]);

  return {
    // State
    user: authState.user,
    isAuthenticated: authState.isAuthenticated,
    loading: authState.loading,
    error: authState.error,
    accessToken: authState.accessToken,

    // Actions
    login,
    logout,
    fetchCurrentUser,
    refreshAuthToken,
    clearAuthError,

    // Permission checking
    hasRole,
    hasPermission,
    hasAnyRole,
    hasAnyPermission,
    hasAllRoles,
    hasAllPermissions,
    canAccessIndex,
    isAdmin,
    isSuperAdmin,
  };
};