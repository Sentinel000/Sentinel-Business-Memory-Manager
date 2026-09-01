'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { CheckSquare, ListTodo, Mic, MessageSquare, Settings, UserCheck, X } from 'lucide-react';
import { useAuthStore } from '../stores/useAuthStore';
import { useTasksStore } from '../stores/useTasksStore';
import { useUIStore } from '../stores/useUIStore';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

export const Sidebar: React.FC = () => {
  const pathname = usePathname();
  const { user } = useAuthStore();
  const { approvals } = useTasksStore();
  const { isNavOpen, toggleNav } = useUIStore();

  const navItems: NavItem[] =
    user?.role === 'employee'
      ? [{ name: 'My Commitments', href: '/me', icon: UserCheck }]
      : [
          {
            name: 'Approval Queue',
            href: '/approvals',
            icon: CheckSquare,
            badge: approvals.length > 0 ? approvals.length : undefined,
          },
          { name: 'Tasks & Ledger', href: '/tasks', icon: ListTodo },
          { name: 'Chat with Sentinel', href: '/chat', icon: MessageSquare },
          { name: 'Meetings & Audio', href: '/meetings', icon: Mic },
          { name: 'Team & Persona', href: '/settings', icon: Settings },
        ];

  return (
    <>
      {/* Scrim — tapping outside closes the drawer on small screens. */}
      {isNavOpen && (
        <div
          onClick={() => toggleNav(false)}
          className="fixed inset-0 bg-ink-black/30 z-40 md:hidden animate-in fade-in duration-200"
          aria-hidden="true"
        />
      )}

      <aside
        className={`
          bg-stone-canvas border-r border-stone-border flex flex-col
          w-64 shrink-0
          fixed md:sticky top-0 md:top-16 left-0 z-50 md:z-auto
          h-screen md:h-[calc(100vh-4rem)]
          transition-transform duration-200 ease-out
          ${isNavOpen ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0
        `}
      >
        {/* Drawer header — only the mobile presentation needs a close affordance. */}
        <div className="flex items-center justify-between p-4 border-b border-stone-border md:hidden shrink-0">
          <span className="font-semibold text-ink-black tracking-tight">Menu</span>
          <button
            onClick={() => toggleNav(false)}
            className="p-1.5 text-warm-gray hover:text-ink-black hover:bg-stone-border/40 rounded-full transition"
            aria-label="Close navigation"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* The nav itself scrolls, so a long list never pushes the footer card away. */}
        <nav className="flex-1 min-h-0 overflow-y-auto p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => toggleNav(false)}
                className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                  isActive
                    ? 'bg-white border border-stone-border text-ink-black shadow-subtle'
                    : 'text-warm-gray hover:text-ink-black hover:bg-stone-border/40'
                }`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-cyan-signal' : 'text-warm-gray'}`} />
                  <span className="truncate">{item.name}</span>
                </div>
                {item.badge !== undefined && (
                  <span className="px-2 py-0.5 text-xs font-semibold bg-cyan-signal text-white rounded-full shrink-0">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {user?.role !== 'employee' && (
          <div className="p-4 pt-0 shrink-0">
            <div className="stone-card p-3.5 text-xs space-y-2 bg-white">
              <div className="flex items-center justify-between text-warm-gray">
                <span>Daily Wakeup Cron</span>
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              </div>
              <p className="text-ink-black font-medium">Scheduled for 08:00 AM</p>
            </div>
          </div>
        )}
      </aside>
    </>
  );
};
