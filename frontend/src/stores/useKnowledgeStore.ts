import { create } from 'zustand';
import { KnowledgeGraph } from '../types';
import { api, apiErrorMessage } from '../lib/api';

interface KnowledgeState {
  graph: KnowledgeGraph | null;
  isLoading: boolean;
  error: string | null;
  /**
   * Provenance edges ("Alex authored the Q1 review") are artifacts of how facts are
   * stored, not company knowledge — on live data they were four of ten edges and
   * turned the graph into an org chart. Off by default; the toggle is there because
   * they are genuinely useful when tracing where a claim came from.
   */
  showProvenance: boolean;
  /** Node id whose detail panel is open, or null. */
  selectedId: string | null;

  fetchGraph: (limit?: number) => Promise<void>;
  toggleProvenance: () => void;
  select: (id: string | null) => void;
}

export const useKnowledgeStore = create<KnowledgeState>((set) => ({
  graph: null,
  isLoading: false,
  error: null,
  showProvenance: false,
  selectedId: null,

  fetchGraph: async (limit = 150) => {
    set({ isLoading: true, error: null });
    try {
      const res = await api.get('/knowledge/graph', { params: { limit } });
      // An unavailable graph is a 200 carrying a note, not an error — the panel
      // renders it as a state. Only a transport failure lands in `error`.
      set({ graph: res.data, isLoading: false });
    } catch (err) {
      set({
        isLoading: false,
        error: apiErrorMessage(err, 'Could not load the knowledge graph.'),
      });
    }
  },

  toggleProvenance: () => set((s) => ({ showProvenance: !s.showProvenance })),
  select: (id) => set({ selectedId: id }),
}));
