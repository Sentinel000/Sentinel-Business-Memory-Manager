import { create } from 'zustand';
import { Task, ApprovalItem, TaskStatus } from '../types';
import { api } from '../lib/api';

interface TasksState {
  approvals: ApprovalItem[];
  tasks: Task[];
  selectedTask: Task | null;
  isLoading: boolean;
  statusFilter: string;
  ownerFilter: string;
  fetchApprovals: () => Promise<void>;
  approveTask: (id: string) => Promise<void>;
  rejectTask: (id: string, reason?: string) => Promise<void>;
  editApproval: (id: string, payload: Partial<Task>) => Promise<void>;
  bulkApprove: (ids: string[]) => Promise<void>;
  fetchTasks: () => Promise<void>;
  createTask: (payload: { title: string; owner_id?: string; deadline?: string; description?: string }) => Promise<void>;
  updateTaskStatus: (id: string, status: TaskStatus, note?: string) => Promise<void>;
  deleteTask: (id: string) => Promise<void>;
  setStatusFilter: (filter: string) => void;
  setOwnerFilter: (ownerId: string) => void;
  setSelectedTask: (task: Task | null) => void;
  fetchMyTasks: () => Promise<void>;
  myTasks: Task[];
  updateMyTaskStatus: (id: string, status: TaskStatus, note?: string) => Promise<void>;
}

export const useTasksStore = create<TasksState>((set, get) => ({
  approvals: [],
  tasks: [],
  myTasks: [],
  selectedTask: null,
  isLoading: false,
  statusFilter: 'all',
  ownerFilter: 'all',

  fetchApprovals: async () => {
    set({ isLoading: true });
    try {
      const res = await api.get('/approvals');
      // The list endpoints answer with an {items, total} envelope, not a bare array.
      set({ approvals: res.data.items ?? [], isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  approveTask: async (id) => {
    await api.post(`/approvals/${id}/approve`);
    set((state) => ({
      approvals: state.approvals.filter((a) => a.id !== id),
    }));
    get().fetchTasks();
  },

  rejectTask: async (id, reason) => {
    await api.post(`/approvals/${id}/reject`, { reason });
    set((state) => ({
      approvals: state.approvals.filter((a) => a.id !== id),
    }));
  },

  editApproval: async (id, payload) => {
    await api.post(`/approvals/${id}/edit`, payload);
    get().fetchApprovals();
  },

  bulkApprove: async (ids) => {
    await api.post('/approvals/bulk-approve', { approval_ids: ids });
    get().fetchApprovals();
    get().fetchTasks();
  },

  fetchTasks: async () => {
    set({ isLoading: true });
    try {
      const { statusFilter, ownerFilter } = get();
      const params: Record<string, string> = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      if (ownerFilter !== 'all') params.owner_id = ownerFilter;
      const res = await api.get('/tasks', { params });
      set({ tasks: res.data.items ?? [], isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  createTask: async (payload) => {
    await api.post('/tasks', payload);
    get().fetchTasks();
  },

  updateTaskStatus: async (id, status, note) => {
    await api.post(`/tasks/${id}/status`, { status, note });
    get().fetchTasks();
  },

  deleteTask: async (id) => {
    await api.delete(`/tasks/${id}`);
    set((state) => ({ tasks: state.tasks.filter((t) => t.id !== id) }));
  },

  setStatusFilter: (filter) => {
    set({ statusFilter: filter });
    get().fetchTasks();
  },

  setOwnerFilter: (ownerId) => {
    set({ ownerFilter: ownerId });
    get().fetchTasks();
  },

  setSelectedTask: (task) => set({ selectedTask: task }),

  fetchMyTasks: async () => {
    set({ isLoading: true });
    try {
      const res = await api.get('/me/tasks');
      set({ myTasks: res.data.items ?? [], isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  updateMyTaskStatus: async (id, status, note) => {
    await api.post(`/me/tasks/${id}/status`, { status, note });
    get().fetchMyTasks();
  },
}));
