'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { CheckSquare, ListTodo, Mic, Settings, UserCheck } from 'lucide-react';
import { useAuthStore } from '../stores/useAuthStore';
import { useTasksStore } from '../stores/useTasksStore';

export const Sidebar: React.FC = () => {
  const pathname = usePathname();
  const { user } = useAuthStore();
  const { approvals } = useTasksStore();

  if (user?.role === 'EMPLOYEE') {
    return (
      <aside className="w-64 bg-stone-canvas border-r border-stone-border p-4 flex flex-col justify-between min-h-[calc(100vh-4rem)]">
        <nav className="space-y-1">
          <Link
            href="/me"
            className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
              pathname === '/me' ? 'bg-white border border-stone-border text-ink-black shadow-subtle' : 'text-warm-gray hover:text-ink-black'
            }`}
          >
            <UserCheck className="w-4 h-4 text-cyan-signal" />
            <span>My Commitments</span>
          </Link>
        </nav>
      </aside>
    );
  }

  const navItems = [
    {
      name: 'Approval Queue',
      href: '/approvals',
      icon: CheckSquare,
      badge: approvals.length > 0 ? approvals.length : undefined,
    },
    { name: 'Tasks & Ledger', href: '/tasks', icon: ListTodo },
    { name: 'Meetings & Audio', href: '/meetings', icon: Mic },
    { name: 'Team & Persona', href: '/settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-stone-canvas border-r border-stone-border p-4 flex flex-col justify-between min-h-[calc(100vh-4rem)]">
      <nav className="space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                isActive
                  ? 'bg-white border border-stone-border text-ink-black shadow-subtle'
                  : 'text-warm-gray hover:text-ink-black hover:bg-stone-border/40'
              }`}
            >
              <div className="flex items-center gap-3">
                <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-signal' : 'text-warm-gray'}`} />
                <span>{item.name}</span>
              </div>
              {item.badge !== undefined && (
                <span className="px-2 py-0.5 text-xs font-semibold bg-cyan-signal text-white rounded-full">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="stone-card p-3.5 text-xs space-y-2 bg-white">
        <div className="flex items-center justify-between text-warm-gray">
          <span>Daily Wakeup Cron</span>
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        </div>
        <p className="text-ink-black font-medium">Scheduled for 08:00 AM</p>
      </div>
    </aside>
  );
};
