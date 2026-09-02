'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/stores/useAuthStore';
import { useUIStore } from '@/stores/useUIStore';
import { BrandLockup } from '@/components/ui';
import { MessageSquare, LogOut, Shield, Menu, Sun, Moon } from 'lucide-react';

export const Header: React.FC = () => {
  const { user, logout } = useAuthStore();
  const { toggleNav, theme, toggleTheme, hydrateNav } = useUIStore();

  // The pre-paint script already set the class; this syncs the store to it so
  // the toggle's icon matches what is actually on screen.
  useEffect(() => {
    hydrateNav();
  }, [hydrateNav]);
  const assistantName = user?.company?.persona_config?.assistant_name || 'Sentinel';

  return (
    <header className="h-16 bg-white border-b border-stone-border px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30 gap-3">
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        <button
          onClick={() => toggleNav(true)}
          className="md:hidden p-1.5 -ml-1 text-warm-gray hover:text-ink-black hover:bg-stone-canvas rounded-lg transition shrink-0"
          aria-label="Open navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        <BrandLockup />
        <span className="font-semibold text-ink-black text-base sm:text-lg tracking-tight">Sentinel</span>
        {/* The tenant chip is context, not identity — first thing to go when narrow. */}
        <span className="hidden sm:inline text-xs px-2 py-0.5 bg-stone-canvas border border-stone-border rounded-full text-warm-gray font-medium truncate max-w-[12rem]">
          {user?.company?.name ?? 'Business Companion'}
        </span>
      </div>

      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {user?.role === 'founder' && (
          <Link
            href="/chat"
            className="hidden lg:flex items-center gap-2 btn-ghost text-sm py-1.5 px-3 border-cyan-edge/40 hover:border-cyan-signal text-cyan-edge hover:text-cyan-signal"
          >
            <MessageSquare className="w-4 h-4" />
            <span>Chat with {assistantName}</span>
          </Link>
        )}

        <div className="flex items-center gap-2 sm:pl-3 sm:border-l border-stone-border">
          <div className="hidden sm:flex flex-col text-right min-w-0">
            <span className="text-xs font-medium text-ink-black truncate max-w-[14rem]">{user?.email}</span>
            <span className="text-[10px] text-warm-gray flex items-center justify-end gap-1 capitalize">
              <Shield className="w-3 h-3 text-cyan-signal" />
              {user?.role}
            </span>
          </div>
          <button
            onClick={toggleTheme}
            className="p-1.5 text-warm-gray hover:text-ink-black hover:bg-stone-canvas rounded-full transition"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
          <button
            onClick={logout}
            className="p-1.5 text-warm-gray hover:text-ink-black hover:bg-stone-canvas rounded-full transition"
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
