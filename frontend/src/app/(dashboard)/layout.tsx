'use client';

import React, { useEffect } from 'react';
import { Header } from '@/components/Header';
import { Sidebar } from '@/components/Sidebar';
import { ChatDrawer } from '@/components/ChatDrawer';
import { useAuthStore } from '@/stores/useAuthStore';
import { useTasksStore } from '@/stores/useTasksStore';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { fetchCurrentUser } = useAuthStore();
  const { fetchApprovals } = useTasksStore();

  useEffect(() => {
    fetchCurrentUser();
    fetchApprovals();
  }, [fetchCurrentUser, fetchApprovals]);

  return (
    <div className="min-h-screen bg-stone-canvas flex flex-col">
      <Header />
      <div className="flex-1 flex">
        <Sidebar />
        <main className="flex-1 p-8 max-w-[1200px] mx-auto w-full">{children}</main>
      </div>
      <ChatDrawer />
    </div>
  );
}
