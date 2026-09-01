'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/useAuthStore';
import { apiErrorMessage } from '@/lib/api';
import { ArrowRight } from 'lucide-react';
import { BrandMark } from '@/components/BrandMark';

export default function SignupPage() {
  const router = useRouter();
  const { signup } = useAuthStore();
  const [companyName, setCompanyName] = useState('');
  const [industry, setIndustry] = useState('');
  const [companyDescription, setCompanyDescription] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await signup({
        company_name: companyName,
        industry,
        company_description: companyDescription,
        founder_email: email,
        founder_password: password,
        founder_full_name: name,
      });
      router.push('/approvals');
    } catch (err) {
      setError(apiErrorMessage(err, 'Registration failed. Please try again.'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen bg-stone-canvas flex items-center justify-center p-4">
      <div className="stone-card w-full max-w-md bg-white p-8 space-y-6 shadow-xl">
        <div className="text-center space-y-2">
          <div className="w-10 h-10 bg-ink-black rounded-lg flex items-center justify-center text-white mx-auto">
            <BrandMark className="w-5 h-5" />
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
            <label className="block font-medium text-ink-black mb-1">Industry</label>
            <input
              type="text"
              required
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              placeholder="e.g. B2B SaaS"
              className="w-full px-3.5 py-2 border border-stone-border rounded-lg focus:outline-none focus:border-cyan-signal"
            />
          </div>

          <div>
            <label className="block font-medium text-ink-black mb-1">About Your Company</label>
            <textarea
              required
              rows={3}
              maxLength={4000}
              value={companyDescription}
              onChange={(e) => setCompanyDescription(e.target.value)}
              placeholder="We're a 25-person SaaS co. Mark runs sales, Lisa marketing, John eng."
              className="w-full px-3.5 py-2 border border-stone-border rounded-lg resize-none focus:outline-none focus:border-cyan-signal"
            />
            <p className="mt-1 text-[11px] text-warm-gray">
              Sentinel uses this to resolve names and terms your team actually uses.
            </p>
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
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3.5 py-2 border border-stone-border rounded-lg focus:outline-none focus:border-cyan-signal"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full btn-cyan py-2.5 text-xs flex items-center justify-center gap-2 mt-2 disabled:opacity-60"
          >
            <span>{submitting ? 'Deploying…' : 'Deploy Instance'}</span>
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
