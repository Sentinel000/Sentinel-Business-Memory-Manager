import { create } from 'zustand';

const COLLAPSE_KEY = 'sentinel:nav-collapsed';
const THEME_KEY = 'sentinel:theme';

export type Theme = 'light' | 'dark';

/** Stored choice, else the OS preference. */
const readTheme = (): Theme => {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    if (stored === 'light' || stored === 'dark') return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  } catch {
    return 'light';
  }
};

/** Tailwind's class strategy reads this off <html>. */
const applyTheme = (theme: Theme) => {
  document.documentElement.classList.toggle('dark', theme === 'dark');
};

/** Restore the founder's last choice. Storage can throw in private windows. */
const readCollapsed = (): boolean => {
  try {
    return localStorage.getItem(COLLAPSE_KEY) === '1';
  } catch {
    return false;
  }
};

interface UIState {
  /** Whether the off-canvas navigation is showing on small screens. */
  isNavOpen: boolean;
  /** Whether the desktop sidebar is collapsed to an icon rail. */
  isNavCollapsed: boolean;
  theme: Theme;
  toggleNav: (open?: boolean) => void;
  toggleNavCollapsed: (collapsed?: boolean) => void;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  /** Read the stored preferences once the client has mounted. */
  hydrateNav: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  isNavOpen: false,
  // Always false on first render: the server has no localStorage, and seeding
  // from it here would make the markup differ from the client's and hydrate
  // mismatched. hydrateNav() applies the real value after mount.
  isNavCollapsed: false,
  // Matches the pre-paint script's default. The real value is read in hydrateNav.
  theme: 'light',
  toggleNav: (open) => set((state) => ({ isNavOpen: open ?? !state.isNavOpen })),
  toggleNavCollapsed: (collapsed) =>
    set((state) => {
      const next = collapsed ?? !state.isNavCollapsed;
      try {
        localStorage.setItem(COLLAPSE_KEY, next ? '1' : '0');
      } catch {
        // A remembered preference is a convenience, not a requirement.
      }
      return { isNavCollapsed: next };
    }),
  setTheme: (theme) => {
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      // Unremembered is acceptable; unstyled is not — apply it either way.
    }
    applyTheme(theme);
    set({ theme });
  },

  toggleTheme: () => {
    const next: Theme = useUIStore.getState().theme === 'dark' ? 'light' : 'dark';
    useUIStore.getState().setTheme(next);
  },

  hydrateNav: () => {
    const theme = readTheme();
    applyTheme(theme);
    set({ isNavCollapsed: readCollapsed(), theme });
  },
}));
