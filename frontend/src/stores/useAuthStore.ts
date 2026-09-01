import { create } from 'zustand';
import { User } from '../types';
import { api } from '../lib/api';

/** Mirrors the backend SignupRequest schema exactly. Every field is required
 *  server-side except founder_full_name — a mismatch here surfaces as a 400. */
export interface SignupPayload {
  company_name: string;
  industry: string;
  company_description: string;
  founder_email: string;
  founder_password: string;
  founder_full_name?: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<User>;
  signup: (payload: SignupPayload) => Promise<User>;
  fetchCurrentUser: () => Promise<void>;
  /** Like fetchCurrentUser but throws on failure and returns the user. */
  loadCurrentUser: () => Promise<User>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: typeof window !== 'undefined' ? localStorage.getItem('sentinel_token') : null,
  isAuthenticated: false,
  isLoading: true,

  login: async (email, password) => {
    const res = await api.post('/auth/login', { email, password });
    // The backend returns a bare TokenResponse — the user is fetched separately.
    const { access_token } = res.data;
    localStorage.setItem('sentinel_token', access_token);
    set({ token: access_token, isAuthenticated: true });
    return await get().loadCurrentUser();
  },

  signup: async (payload) => {
    // Signup already issues a token, so there is no second login round trip.
    const res = await api.post('/auth/signup', payload);
    const { access_token } = res.data;
    localStorage.setItem('sentinel_token', access_token);
    set({ token: access_token, isAuthenticated: true });
    return await get().loadCurrentUser();
  },

  loadCurrentUser: async () => {
    const res = await api.get('/auth/me');
    set({ user: res.data, isAuthenticated: true, isLoading: false });
    return res.data as User;
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
