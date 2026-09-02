'use client';

import React, { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { Header, Sidebar } from '@/components/layout';
import { useAuthStore } from '@/stores/useAuthStore';
import { useTasksStore } from '@/stores/useTasksStore';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { fetchCurrentUser } = useAuthStore();
  const { fetchApprovals } = useTasksStore();
  const pathname = usePathname();
  // Chat owns its own scroll and runs full-bleed; every other page keeps the
  // centered, padded reading column.
  const isChat = pathname === '/chat';

  useEffect(() => {
    fetchCurrentUser();
    fetchApprovals();
  }, [fetchCurrentUser, fetchApprovals]);

  return (
    <div className="min-h-screen bg-stone-canvas flex flex-col">
      <Header />
      <div className="flex-1 flex min-w-0">
        <Sidebar />
        <main
          className={
            isChat
              ? 'flex-1 min-w-0 p-3 sm:p-4 h-[calc(100vh-4rem)]'
              : 'flex-1 min-w-0 p-4 sm:p-6 lg:p-8 max-w-[1200px] mx-auto w-full'
          }
        >
          {children}
        </main>
      </div>
    </div>
  );
}
