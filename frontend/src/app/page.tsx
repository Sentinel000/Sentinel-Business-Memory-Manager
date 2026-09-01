'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '../stores/useAuthStore';

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, user, fetchCurrentUser } = useAuthStore();

  useEffect(() => {
    fetchCurrentUser().then(() => {
      if (useAuthStore.getState().isAuthenticated) {
        if (useAuthStore.getState().user?.role === 'employee') {
          router.replace('/me');
        } else {
          router.replace('/approvals');
        }
      } else {
        router.replace('/login');
      }
    });
  }, [router, fetchCurrentUser]);

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-stone-canvas text-warm-gray text-sm">
      Connecting to Sentinel Business Engine...
    </div>
  );
}
