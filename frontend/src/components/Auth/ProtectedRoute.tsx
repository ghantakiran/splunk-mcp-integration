import React, { useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { Navigate, useLocation } from 'react-router-dom';
import { Box, CircularProgress, Typography } from '@mui/material';
import { RootState, AppDispatch } from '../../store';
import { getCurrentUser } from '../../store/authSlice';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermissions?: string[];
  requiredRoles?: string[];
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredPermissions = [],
  requiredRoles = [],
}) => {
  const dispatch = useDispatch<AppDispatch>();
  const location = useLocation();
  const { isAuthenticated, user, loading, accessToken } = useSelector((state: RootState) => state.auth);

  useEffect(() => {
    // If we have a token but no user data, fetch user data
    if (accessToken && !user && !loading) {
      dispatch(getCurrentUser());
    }
  }, [accessToken, user, loading, dispatch]);

  // Show loading while checking authentication
  if (loading || (accessToken && !user)) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          gap: 2,
        }}
      >
        <CircularProgress size={40} />
        <Typography variant="body1" color="text.secondary">
          Loading...
        </Typography>
      </Box>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated || !accessToken) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check required roles
  if (requiredRoles.length > 0 && user) {
    const hasRequiredRole = requiredRoles.some(role => user.roles.includes(role));
    if (!hasRequiredRole) {
      return (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            gap: 2,
            textAlign: 'center',
            p: 3,
          }}
        >
          <Typography variant="h5" color="error">
            Access Denied
          </Typography>
          <Typography variant="body1" color="text.secondary">
            You don't have the required role to access this page.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Required roles: {requiredRoles.join(', ')}
          </Typography>
        </Box>
      );
    }
  }

  // Check required permissions
  if (requiredPermissions.length > 0 && user) {
    const hasRequiredPermission = requiredPermissions.some(permission => 
      user.permissions.includes(permission)
    );
    if (!hasRequiredPermission) {
      return (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            gap: 2,
            textAlign: 'center',
            p: 3,
          }}
        >
          <Typography variant="h5" color="error">
            Access Denied
          </Typography>
          <Typography variant="body1" color="text.secondary">
            You don't have the required permissions to access this page.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Required permissions: {requiredPermissions.join(', ')}
          </Typography>
        </Box>
      );
    }
  }

  // Check if user account is active
  if (user && !user.is_active) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          gap: 2,
          textAlign: 'center',
          p: 3,
        }}
      >
        <Typography variant="h5" color="error">
          Account Inactive
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Your account has been deactivated. Please contact your administrator.
        </Typography>
      </Box>
    );
  }

  return <>{children}</>;
};

export default ProtectedRoute;