import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { authService, User } from '../services/auth.service';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  login: (username: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  devtools(
    persist(
      (set) => ({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,

        login: async (username: string, password: string) => {
          set({ isLoading: true, error: null });
          try {
            await authService.login({ username, password });
            const user = await authService.getCurrentUser();
            set({ 
              user, 
              isAuthenticated: true, 
              isLoading: false 
            });
          } catch (error: any) {
            set({ 
              error: error.message || 'Login failed', 
              isLoading: false,
              isAuthenticated: false 
            });
            throw error;
          }
        },

        register: async (email: string, password: string) => {
          set({ isLoading: true, error: null });
          try {
            await authService.register({ email, password });
            set({ isLoading: false });
          } catch (error: any) {
            set({ 
              error: error.message || 'Registration failed', 
              isLoading: false 
            });
            throw error;
          }
        },

        logout: () => {
          authService.logout();
          set({ 
            user: null, 
            isAuthenticated: false,
            error: null 
          });
        },

        fetchUser: async () => {
          if (!authService.isAuthenticated()) {
            set({ isAuthenticated: false, user: null });
            return;
          }
          
          set({ isLoading: true });
          try {
            const user = await authService.getCurrentUser();
            set({ 
              user, 
              isAuthenticated: true, 
              isLoading: false 
            });
          } catch (error) {
            set({ 
              user: null, 
              isAuthenticated: false, 
              isLoading: false 
            });
            authService.logout();
          }
        },

        clearError: () => set({ error: null }),
      }),
      {
        name: 'auth-storage',
        partialize: (state) => ({ 
          isAuthenticated: state.isAuthenticated 
        }),
      }
    )
  )
);