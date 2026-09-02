'use client';

import React, { useEffect, useState } from 'react';
import { useCompanyStore } from '@/stores/useCompanyStore';
import { EmployeeRosterTable, PersonaConfigForm } from '@/components/settings';
import { SentinelBot } from '@/components/ui';
import { Users, Bot, Sparkles, ShieldCheck } from 'lucide-react';

export default function SettingsPage() {
  const { company, employees, fetchCompany, fetchEmployees } = useCompanyStore();
  const [activeTab, setActiveTab] = useState<'persona' | 'roster'>('persona');

  useEffect(() => {
    fetchCompany();
    fetchEmployees();
  }, [fetchCompany, fetchEmployees]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="stone-card p-6 bg-white space-y-1">
        <h1 className="text-2xl font-normal text-ink-black tracking-tight">
          Company & <span className="cyan-highlight">Settings</span>
        </h1>
        <p className="text-xs text-warm-gray">
          Configure Sentinel AI persona, escalation parameters, and manage team members
        </p>
      </div>

      {/* Tabs Switcher */}
      <div className="flex items-center gap-2 border-b border-stone-border pb-1">
        <button
          onClick={() => setActiveTab('persona')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition ${
            activeTab === 'persona'
              ? 'bg-inverse text-white shadow-subtle'
              : 'text-warm-gray hover:text-ink-black hover:bg-white/60'
          }`}
        >
          <Bot className="w-4 h-4" />
          <span>Sentinel Persona</span>
        </button>

        <button
          onClick={() => setActiveTab('roster')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition ${
            activeTab === 'roster'
              ? 'bg-inverse text-white shadow-subtle'
              : 'text-warm-gray hover:text-ink-black hover:bg-white/60'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Employee Roster</span>
          <span
            className={`px-1.5 py-0.2 rounded-full text-[10px] ${
              activeTab === 'roster'
                ? 'bg-white/20 text-white'
                : 'bg-stone-border text-ink-black'
            }`}
          >
            {employees.length}
          </span>
        </button>
      </div>

      {/* Tab 1: Sentinel Persona & Chasing Controls */}
      {activeTab === 'persona' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          {/* Animated Sentinel Bot Showcase Hero */}
          <div className="stone-card p-8 bg-white flex flex-col items-center justify-center text-center space-y-3.5 border-cyan-edge/25">
            <div className="relative shrink-0 flex items-center justify-center p-1">
              <SentinelBot size={96} state="idle" showGlow={true} />
            </div>

            <div className="space-y-2 max-w-lg mx-auto">
              <div>
                <span className="px-3 py-1 text-xs bg-cyan-50 text-cyan-700 border border-cyan-200 rounded-full font-medium inline-flex items-center gap-1.5 shadow-subtle">
                  <Sparkles className="w-3.5 h-3.5 text-cyan-signal" />
                  Business Companion
                </span>
              </div>

              <h2 className="text-xl font-semibold text-ink-black tracking-tight">
                Autonomous Operational Companion
              </h2>
              <p className="text-xs text-warm-gray leading-relaxed max-w-md mx-auto">
                Sentinel watches over your business commitments, extracts action items from transcripts,
                and follows up on assignments with your team in the background.
              </p>
            </div>
          </div>

          <PersonaConfigForm />
        </div>
      )}

      {/* Tab 2: Employee Roster */}
      {activeTab === 'roster' && (
        <div className="space-y-6 animate-in fade-in duration-200">
          <EmployeeRosterTable />
        </div>
      )}
    </div>
  );
}
