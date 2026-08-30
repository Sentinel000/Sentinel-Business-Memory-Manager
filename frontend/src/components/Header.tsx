'use client';

import React from 'react';
import { useAuthStore } from '../stores/useAuthStore';
import { useChatStore } from '../stores/useChatStore';
import { Sparkles, MessageSquare, LogOut, Shield } from 'lucide-react';

export const Header: React.FC = () => {
  const { user, logout } = useAuthStore();
  const { toggleDrawer } = useChatStore();

  return (
    <header className="h-16 bg-white border-b border-stone-border px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <div className="w-7 h-7 bg-ink-black rounded flex items-center justify-center text-white">
          <Sparkles className="w-4 h-4 text-cyan-signal" />
        </div>
        <span className="font-semibold text-ink-black text-lg tracking-tight">Sentinel</span>
        <span className="text-xs px-2 py-0.5 bg-stone-canvas border border-stone-border rounded-full text-warm-gray font-medium">
          {user?.company_id ? 'ACME Corp' : 'Business Companion'}
        </span>
      </div>

      <div className="flex items-center gap-3">
        {user?.role === 'FOUNDER' && (
          <button
            onClick={() => toggleDrawer(true)}
            className="flex items-center gap-2 btn-ghost text-sm py-1.5 px-3 border-cyan-edge/40 hover:border-cyan-signal text-cyan-edge hover:text-cyan-signal"
          >
            <MessageSquare className="w-4 h-4" />
            <span>Ask Sentinel AI</span>
          </button>
        )}

        <div className="flex items-center gap-2 pl-3 border-l border-stone-border">
          <div className="flex flex-col text-right">
            <span className="text-xs font-medium text-ink-black">{user?.email}</span>
            <span className="text-[10px] text-warm-gray flex items-center justify-end gap-1">
              <Shield className="w-3 h-3 text-cyan-signal" />
              {user?.role}
            </span>
          </div>
          <button
            onClick={logout}
            className="p-1.5 text-warm-gray hover:text-ink-black hover:bg-stone-canvas rounded-full transition"
            title="Sign out"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
