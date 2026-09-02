'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  CheckSquare, FileText, ListTodo, Mic, MessageSquare, Network, Settings, UserCheck, X,
  PanelLeftClose, PanelLeftOpen,
} from 'lucide-react';
import { useAuthStore } from '@/stores/useAuthStore';
import { useTasksStore } from '@/stores/useTasksStore';
import { useUIStore } from '@/stores/useUIStore';

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
  const { isNavOpen, toggleNav, isNavCollapsed, toggleNavCollapsed, hydrateNav } = useUIStore();

  // After mount, not during render — the server cannot read localStorage.
  useEffect(() => {
    hydrateNav();
  }, [hydrateNav]);

  // The rail is a desktop affordance. On mobile the drawer is either open or
  // gone, so a collapsed drawer would just be a narrower thing to dismiss.
  const collapsed = isNavCollapsed;

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
          { name: 'Briefings', href: '/briefings', icon: FileText },
          { name: 'Chat with Sentinel', href: '/chat', icon: MessageSquare },
          { name: 'Meetings & Audio', href: '/meetings', icon: Mic },
          { name: 'Knowledge Panel', href: '/knowledge', icon: Network },
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
          shrink-0 w-64 ${collapsed ? 'md:w-16' : 'md:w-64'}
          transition-[width] duration-200 ease-out
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
                // Collapsed, the label is gone — the native tooltip carries it.
                title={collapsed ? item.name : undefined}
                className={`relative flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                  collapsed ? 'md:justify-center md:px-0' : ''
                } ${
                  isActive
                    ? 'bg-white border border-stone-border text-ink-black shadow-subtle'
                    : 'text-warm-gray hover:text-ink-black hover:bg-stone-border/40'
                }`}
              >
                <div className={`flex items-center gap-3 min-w-0 ${collapsed ? 'md:gap-0' : ''}`}>
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-cyan-signal' : 'text-warm-gray'}`} />
                  <span className={`truncate ${collapsed ? 'md:hidden' : ''}`}>{item.name}</span>
                </div>
                {item.badge !== undefined && (
                  <>
                    <span
                      className={`px-2 py-0.5 text-xs font-semibold bg-cyan-signal text-white rounded-full shrink-0 ${
                        collapsed ? 'md:hidden' : ''
                      }`}
                    >
                      {item.badge}
                    </span>
                    {/* A pending queue must stay visible on the rail — it is the
                        one thing in this nav that is waiting on the founder. */}
                    {collapsed && (
                      <span className="hidden md:flex absolute top-1 right-1 min-w-[16px] h-4 px-1 items-center justify-center text-[10px] font-semibold bg-cyan-signal text-white rounded-full">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </Link>
            );
          })}
        </nav>

        {/* Desktop-only rail toggle. Mobile closes the drawer instead. */}
        <div className="hidden md:block p-3 pt-0 shrink-0">
          <button
            onClick={() => toggleNavCollapsed()}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-expanded={!collapsed}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-warm-gray hover:text-ink-black hover:bg-stone-border/40 transition ${
              collapsed ? 'justify-center px-0' : ''
            }`}
          >
            {collapsed ? (
              <PanelLeftOpen className="w-4 h-4 shrink-0" />
            ) : (
              <>
                <PanelLeftClose className="w-4 h-4 shrink-0" />
                <span>Collapse</span>
              </>
            )}
          </button>
        </div>
      </aside>
    </>
  );
};
