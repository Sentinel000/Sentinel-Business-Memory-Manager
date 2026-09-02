'use client';

import React, { useState } from 'react';
import { useCompanyStore } from '../stores/useCompanyStore';
import { Sliders, Check } from 'lucide-react';

export const PersonaConfigForm: React.FC = () => {
  const { company, updateCompany } = useCompanyStore();
  const [instructions, setInstructions] = useState(company?.persona_instructions || '');
  const [escalationHours, setEscalationHours] = useState(company?.escalation_window_hours || 48);
  const [threshold, setThreshold] = useState(company?.auto_approve_threshold || 1.0);
  const [saved, setSaved] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await updateCompany({
      persona_instructions: instructions,
      escalation_window_hours: escalationHours,
      auto_approve_threshold: threshold,
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <form onSubmit={handleSubmit} className="stone-card p-6 space-y-5 bg-white">
      <div className="border-b border-stone-border pb-4 space-y-1">
        <h3 className="font-semibold text-ink-black text-base flex items-center gap-2">
          <Sliders className="w-4 h-4 text-cyan-signal" />
          Sentinel Persona & Chasing Controls
        </h3>
        <p className="text-xs text-warm-gray">Configure AI follow-up tone, escalation window, and approval thresholds</p>
      </div>

      <div className="space-y-4 text-xs">
        <div>
          <label className="block font-medium text-ink-black mb-1">Company Persona & Context Instructions</label>
          <textarea
            rows={4}
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder="e.g. Sentinel operates as a firm, concise Chief of Staff for a high-growth tech startup..."
            className="w-full p-3 border border-stone-border rounded-lg focus:outline-none focus:border-cyan-signal text-xs"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block font-medium text-ink-black mb-1">Escalation Window (Hours before manager notify)</label>
            <select
              value={escalationHours}
              onChange={(e) => setEscalationHours(Number(e.target.value))}
              className="w-full p-2.5 border border-stone-border rounded-lg bg-white"
            >
              <option value={24}>24 Hours (Aggressive)</option>
              <option value={48}>48 Hours (Standard)</option>
              <option value={72}>72 Hours (Relaxed)</option>
            </select>
          </div>

          <div>
            <label className="block font-medium text-ink-black mb-1">
              Auto-Approve Threshold ({threshold * 100}%)
            </label>
            <input
              type="range"
              min="0.5"
              max="1.0"
              step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-full accent-cyan-signal mt-2"
            />
          </div>
        </div>
      </div>

      <div className="pt-3 border-t border-stone-border flex items-center justify-between">
        {saved ? (
          <span className="text-xs text-emerald-600 font-semibold flex items-center gap-1">
            <Check className="w-4 h-4" /> Persona Configuration Saved!
          </span>
        ) : (
          <span></span>
        )}
        <button type="submit" className="btn-cyan text-xs px-5 py-2">
          Save Configuration
        </button>
      </div>
    </form>
  );
};
