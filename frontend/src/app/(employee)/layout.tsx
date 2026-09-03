'use client';

import React, { useEffect } from 'react';
import { Header, Sidebar } from '@/components/layout';
import { useAuthStore } from '@/stores/useAuthStore';

/**
 * The employee shell. Mirrors the dashboard shell so the header's mobile menu
 * button has a Sidebar to open, and so `user` is loaded for the greeting,
 * the tenant chip, and the sidebar's role branch.
 */
export default function EmployeeLayout({ children }: { children: React.ReactNode }) {
  const { fetchCurrentUser } = useAuthStore();

  useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser]);

  return (
    <div className="min-h-screen bg-stone-canvas flex flex-col">
      <Header />
      <div className="flex-1 flex min-w-0">
        <Sidebar />
        <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto w-full space-y-6">
          {children}
        </main>
      </div>
    </div>
  );
}
