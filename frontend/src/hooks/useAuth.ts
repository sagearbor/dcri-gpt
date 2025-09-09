import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/auth.store';

export const useAuth = () => {
  const { 
    user, 
    isAuthenticated, 
    isLoading, 
    error,
    login,
    register,
    logout,
    fetchUser,
    clearError
  } = useAuthStore();

  useEffect(() => {
    if (isAuthenticated && !user) {
      fetchUser();
    }
  }, [isAuthenticated, user, fetchUser]);

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    clearError,
  };
};

export const useRequireAuth = (redirectTo = '/login') => {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading, fetchUser } = useAuthStore();

  useEffect(() => {
    const checkAuth = async () => {
      if (!isAuthenticated && !isLoading) {
        await fetchUser();
        if (!useAuthStore.getState().isAuthenticated) {
          navigate(redirectTo);
        }
      }
    };
    
    checkAuth();
  }, [isAuthenticated, isLoading, navigate, redirectTo, fetchUser]);

  return { isAuthenticated, isLoading };
};