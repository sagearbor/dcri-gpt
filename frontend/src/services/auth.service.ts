import { api, handleApiError } from './api';

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

class AuthService {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      const formData = new FormData();
      formData.append('username', credentials.username);
      formData.append('password', credentials.password);
      
      const response = await api.post<AuthResponse>('/auth/token', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      if (response.data.access_token) {
        localStorage.setItem('access_token', response.data.access_token);
      }
      
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async register(data: RegisterData): Promise<User> {
    try {
      const response = await api.post<User>('/auth/register', data);
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  async getCurrentUser(): Promise<User> {
    try {
      const response = await api.get<User>('/users/me');
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  }

  logout(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = '/login';
  }

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  }
}

export const authService = new AuthService();