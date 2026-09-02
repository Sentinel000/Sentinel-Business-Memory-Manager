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
  createEmployee: (payload: { name: string; role_title?: string; manager_id?: string }) => Promise<void>;
  updateEmployee: (id: string, payload: Partial<Employee>) => Promise<void>;
  deleteEmployee: (id: string) => Promise<void>;
  provisionLogin: (employeeId: string, email: string, password: string, fullName?: string) => Promise<void>;
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
      set({ employees: res.data.items ?? [], isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  createEmployee: async (payload) => {
    await api.post('/employees', payload);
    await get().fetchEmployees();
  },

  updateEmployee: async (id, payload) => {
    await api.patch(`/employees/${id}`, payload);
    get().fetchEmployees();
  },

  deleteEmployee: async (id) => {
    await api.delete(`/employees/${id}`);
    get().fetchEmployees();
  },

  provisionLogin: async (employeeId, email, password, fullName) => {
    // The backend requires a password (min 8 chars) alongside the email —
    // sending only the email is rejected as a validation error.
    await api.post(`/employees/${employeeId}/login`, {
      email,
      password,
      full_name: fullName,
    });
    await get().fetchEmployees();
  },

  bulkImportEmployees: async (rawText) => {
    const lines = rawText.split('\n').filter((l) => l.trim());
    const employees = lines.map((line) => {
      const parts = line.split(',').map((p) => p.trim());
      // The import contract is {name, role_title, manager} — manager by name.
      return { name: parts[0], role_title: parts[1] || undefined, manager: parts[2] || undefined };
    });
    await api.post('/onboarding/employees/bulk', { employees });
    get().fetchEmployees();
  },
}));
