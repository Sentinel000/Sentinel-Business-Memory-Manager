'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/useAuthStore';
import { Sparkles, ArrowRight } from 'lucide-react';

export default function SignupPage() {
  const router = useRouter();
  const { signup } = useAuthStore();
  const [companyName, setCompanyName] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await signup(companyName, name, email, password);
      router.push('/approvals');
    } catch {
      setError('Registration failed. Email may already be registered.');
    }
  };

  return (
    <main className="min-h-screen bg-stone-canvas flex items-center justify-center p-4">
      <div className="stone-card w-full max-w-md bg-white p-8 space-y-6 shadow-xl">
        <div className="text-center space-y-2">
          <div className="w-10 h-10 bg-ink-black rounded-lg flex items-center justify-center text-white mx-auto">
            <Sparkles className="w-5 h-5 text-cyan-signal" />
          </div>
          <h1 className="text-2xl font-normal text-ink-black tracking-tight">
            Deploy <span className="cyan-highlight">Sentinel Instance</span>
          </h1>
          <p className="text-xs text-warm-gray">Self-provision your company operational memory</p>
        </div>

        {error && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3 text-xs">
          <div>
            <label className="block font-medium text-ink-black mb-1">Company Name</label>
            <input
              type="text"
              required
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="e.g. Acme Tech Inc."
              className="w-full px-3.5 py-2 border border-stone-border rounded-lg focus:outline-none focus:border-cyan-signal"
            />
          </div>

          <div>
            <label className="block font-medium text-ink-black mb-1">Founder Full Name</label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Alex Rivers"
              className="w-full px-3.5 py-2 border border-stone-border rounded-lg focus:outline-none focus:border-cyan-signal"
            />
          </div>

          <div>
            <label className="block font-medium text-ink-black mb-1">Work Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="alex@acme.com"
              className="w-full px-3.5 py-2 border border-stone-border rounded-lg focus:outline-none focus:border-cyan-signal"
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
              className="w-full px-3.5 py-2 border border-stone-border rounded-lg focus:outline-none focus:border-cyan-signal"
            />
          </div>

          <button type="submit" className="w-full btn-cyan py-2.5 text-xs flex items-center justify-center gap-2 mt-2">
            <span>Deploy Instance</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>

        <div className="text-center text-xs text-warm-gray pt-2 border-t border-stone-border">
          Already have an account?{' '}
          <Link href="/login" className="text-cyan-edge font-semibold hover:underline">
            Sign in
          </Link>
        </div>
      </div>
    </main>
  );
}
