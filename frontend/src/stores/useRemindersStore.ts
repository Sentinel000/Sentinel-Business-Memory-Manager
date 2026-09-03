import { create } from 'zustand';
import { Reminder } from '../types';
import { api } from '../lib/api';

interface RemindersState {
  reminders: Reminder[];
  isLoading: boolean;
  fetchReminders: () => Promise<void>;
}

export const useRemindersStore = create<RemindersState>((set) => ({
  reminders: [],
  isLoading: false,

  fetchReminders: async () => {
    set({ isLoading: true });
    try {
      const res = await api.get('/me/reminders');
      set({ reminders: res.data, isLoading: false });
    } catch {
      // Reminders are an overlay on the task list. Failing to load them must not
      // blank the page the employee came here to use.
      set({ isLoading: false });
    }
  },
}));

/** Reminders still awaiting a reply — what the badge counts. */
export const unanswered = (reminders: Reminder[]) => reminders.filter((r) => !r.answered);
