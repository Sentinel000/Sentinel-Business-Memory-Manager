import { create } from 'zustand';
import { Task, ApprovalItem, ApprovalEdit, TaskStatus } from '../types';
import { api } from '../lib/api';

/** GET /approvals item, as the API sends it. */
interface ApprovalApiItem {
  id: string;
  task_id: string;
  state: string;
  task: {
    title: string;
    status: TaskStatus;
    description?: string | null;
    owner_employee_id?: string | null;
    owner_name?: string | null;
    deadline?: string | null;
    source_quote?: string | null;
    source_ref?: string | null;
    confidence?: number | null;
  };
}

const toApprovalItem = (a: ApprovalApiItem): ApprovalItem => ({
  id: a.id,
  task_id: a.task_id,
  state: a.state,
  title: a.task.title,
  status: a.task.status,
  description: a.task.description ?? null,
  owner_employee_id: a.task.owner_employee_id ?? null,
  owner_name: a.task.owner_name ?? null,
  deadline: a.task.deadline ?? null,
  source_quote: a.task.source_quote ?? null,
  source_ref: a.task.source_ref ?? null,
  confidence_score: a.task.confidence ?? null,
});

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
  editApproval: (id: string, payload: ApprovalEdit) => Promise<void>;
  bulkApprove: (ids: string[]) => Promise<void>;
  fetchTasks: () => Promise<void>;
  createTask: (payload: { title: string; owner_employee_id?: string; deadline?: string; description?: string }) => Promise<void>;
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
      // Each item nests its task; the cards read flat fields, so flatten here, once.
      // Passing the raw items through rendered every card as an untitled,
      // unassigned task with no quote.
      const items: ApprovalApiItem[] = res.data.items ?? [];
      set({ approvals: items.map(toApprovalItem), isLoading: false });
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
      if (ownerFilter !== 'all') params.owner_employee_id = ownerFilter;
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
