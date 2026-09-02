'use client';

import React from 'react';
import { SignupWizard } from '@/components/auth';

export default function SignupPage() {
  return (
    <main className="min-h-screen bg-stone-canvas flex items-center justify-center p-4 sm:p-6">
      <SignupWizard />
    </main>
  );
}
