import { create } from 'zustand';
import { Report, ReportSummary } from '../types';
import { api, apiErrorMessage } from '../lib/api';

interface ReportsState {
  current: Report | null;
  history: ReportSummary[];
  isLoading: boolean;
  isGenerating: boolean;
  error: string | null;
  /** True once today's briefing has been looked for, so "none yet" can be shown
   *  as a prompt rather than flashing before the fetch resolves. */
  checked: boolean;

  fetchToday: () => Promise<void>;
  fetchHistory: () => Promise<void>;
  generate: () => Promise<void>;
  open: (id: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
}

export const useReportsStore = create<ReportsState>((set, get) => ({
  current: null,
  history: [],
  isLoading: false,
  isGenerating: false,
  error: null,
  checked: false,

  fetchToday: async () => {
    set({ isLoading: true, error: null });
    try {
      // Null is a normal answer — today's briefing simply has not been asked for.
      const res = await api.get('/reports/today');
      set({ current: res.data ?? null, isLoading: false, checked: true });
    } catch (err) {
      set({
        isLoading: false,
        checked: true,
        error: apiErrorMessage(err, 'Could not load today’s briefing.'),
      });
    }
  },

  fetchHistory: async () => {
    try {
      const res = await api.get('/reports');
      set({ history: res.data });
    } catch {
      // The history strip is secondary; failing to load it must not blank the page.
    }
  },

  generate: async () => {
    set({ isGenerating: true, error: null });
    try {
      const res = await api.post('/reports/generate');
      set({ current: res.data, isGenerating: false, checked: true });
      await get().fetchHistory();
    } catch (err) {
      set({
        isGenerating: false,
        error: apiErrorMessage(err, 'Could not generate the briefing.'),
      });
    }
  },

  open: async (id) => {
    set({ isLoading: true, error: null });
    try {
      const res = await api.get(`/reports/${id}`);
      set({ current: res.data, isLoading: false });
    } catch (err) {
      set({ isLoading: false, error: apiErrorMessage(err, 'Could not open that briefing.') });
    }
  },

  remove: async (id) => {
    try {
      await api.delete(`/reports/${id}`);
      const { current } = get();
      set({
        history: get().history.filter((r) => r.id !== id),
        current: current?.id === id ? null : current,
      });
    } catch (err) {
      set({ error: apiErrorMessage(err, 'Could not delete that briefing.') });
    }
  },
}));
