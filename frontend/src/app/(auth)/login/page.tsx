'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/useAuthStore';
import { apiErrorMessage } from '@/lib/api';
import { ArrowRight } from 'lucide-react';
import { BrandMark } from '@/components/ui';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const user = await login(email, password);
      if (user.role === 'employee') {
        router.push('/me');
      } else {
        router.push('/approvals');
      }
    } catch (err) {
      setError(apiErrorMessage(err, 'Invalid credentials or network connection error.'));
    }
  };

  return (
    <main className="min-h-screen bg-stone-canvas flex items-center justify-center p-4">
      <div className="stone-card w-full max-w-md bg-white p-8 space-y-6 shadow-xl">
        <div className="text-center space-y-2">
          <div className="w-10 h-10 bg-inverse rounded-lg flex items-center justify-center text-white mx-auto">
            <BrandMark className="w-5 h-5" />
          </div>
          <h1 className="text-2xl font-normal text-ink-black tracking-tight font-sans">
            Sign in to <span className="cyan-highlight">Sentinel</span>
          </h1>
          <p className="text-xs text-warm-gray">Operational memory & commitment engine</p>
        </div>

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block font-medium text-ink-black mb-1">Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="founder@company.com"
              className="w-full px-3.5 py-2.5 border border-stone-border rounded-lg focus:outline-none focus:border-cyan-signal text-xs"
            />
          </div>

          <div>
            <label className="block font-medium text-ink-black mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3.5 py-2.5 border border-stone-border rounded-lg focus:outline-none focus:border-cyan-signal text-xs"
            />
          </div>

          <button type="submit" className="w-full btn-cyan py-3 text-xs flex items-center justify-center gap-2">
            <span>Sign In</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="text-center text-xs text-warm-gray pt-2 border-t border-stone-border">
          New founder?{' '}
          <Link href="/signup" className="text-cyan-edge font-semibold hover:underline">
            Register your company tenant
          </Link>
        </div>
      </div>
    </main>
  );
}
