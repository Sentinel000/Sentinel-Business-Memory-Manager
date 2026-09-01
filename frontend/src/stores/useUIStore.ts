import { create } from 'zustand';

interface UIState {
  /** Whether the off-canvas navigation is showing on small screens. */
  isNavOpen: boolean;
  toggleNav: (open?: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  isNavOpen: false,
  toggleNav: (open) => set((state) => ({ isNavOpen: open ?? !state.isNavOpen })),
}));
