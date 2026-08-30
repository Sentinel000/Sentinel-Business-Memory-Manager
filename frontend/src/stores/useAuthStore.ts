import { create } from 'zustand';
import { User, Role } from '../types';
import { api } from '../lib/api';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<User>;
  signup: (companyName: string, name: string, email: string, password: string) => Promise<void>;
  fetchCurrentUser: () => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: typeof window !== 'undefined' ? localStorage.getItem('sentinel_token') : null,
  isAuthenticated: false,
  isLoading: true,

  login: async (email, password) => {
    const res = await api.post('/auth/login', { email, password });
    const { access_token, user } = res.data;
    localStorage.setItem('sentinel_token', access_token);
    set({ token: access_token, user, isAuthenticated: true, isLoading: false });
    return user;
  },

  signup: async (company_name, founder_name, email, password) => {
    await api.post('/auth/signup', { company_name, founder_name, email, password });
    await get().login(email, password);
  },

  fetchCurrentUser: async () => {
    try {
      const res = await api.get('/auth/me');
      set({ user: res.data, isAuthenticated: true, isLoading: false });
    } catch {
      localStorage.removeItem('sentinel_token');
      set({ user: null, token: null, isAuthenticated: false, isLoading: false });
    }
  },

  logout: () => {
    localStorage.removeItem('sentinel_token');
    set({ user: null, token: null, isAuthenticated: false, isLoading: false });
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  },
}));
