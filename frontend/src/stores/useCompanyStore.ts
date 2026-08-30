import { create } from 'zustand';
import { Company, Employee } from '../types';
import { api } from '../lib/api';

interface CompanyState {
  company: Company | null;
  employees: Employee[];
  isLoading: boolean;
  fetchCompany: () => Promise<void>;
  updateCompany: (payload: Partial<Company>) => Promise<void>;
  fetchEmployees: () => Promise<void>;
  createEmployee: (payload: { name: string; title?: string; manager_id?: string }) => Promise<void>;
  updateEmployee: (id: string, payload: Partial<Employee>) => Promise<void>;
  deleteEmployee: (id: string) => Promise<void>;
  provisionLogin: (employeeId: string, email: string) => Promise<void>;
  bulkImportEmployees: (rawText: string) => Promise<void>;
}

export const useCompanyStore = create<CompanyState>((set, get) => ({
  company: null,
  employees: [],
  isLoading: false,

  fetchCompany: async () => {
    try {
      const res = await api.get('/company');
      set({ company: res.data });
    } catch {}
  },

  updateCompany: async (payload) => {
    const res = await api.patch('/company', payload);
    set({ company: res.data });
  },

  fetchEmployees: async () => {
    set({ isLoading: true });
    try {
      const res = await api.get('/employees');
      set({ employees: res.data, isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  createEmployee: async (payload) => {
    await api.post('/employees', payload);
    get().fetchEmployees();
  },

  updateEmployee: async (id, payload) => {
    await api.patch(`/employees/${id}`, payload);
    get().fetchEmployees();
  },

  deleteEmployee: async (id) => {
    await api.delete(`/employees/${id}`);
    get().fetchEmployees();
  },

  provisionLogin: async (employeeId, email) => {
    await api.post(`/employees/${employeeId}/login`, { email });
    get().fetchEmployees();
  },

  bulkImportEmployees: async (rawText) => {
    const lines = rawText.split('\n').filter((l) => l.trim());
    const employees = lines.map((line) => {
      const parts = line.split(',').map((p) => p.trim());
      return { name: parts[0], title: parts[1] || undefined, manager_name: parts[2] || undefined };
    });
    await api.post('/onboarding/employees/bulk', { employees });
    get().fetchEmployees();
  },
}));
