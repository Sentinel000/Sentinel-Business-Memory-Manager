'use client';

import React, { useEffect, useState } from 'react';
import { useCompanyStore } from '@/stores/useCompanyStore';
import { InfoTip } from '@/components/ui';
import { Check, Sliders } from 'lucide-react';

export const PersonaConfigForm: React.FC = () => {
  const { company, updateCompany } = useCompanyStore();

  const [context, setContext] = useState('');
  const [cadence, setCadence] = useState(3);
  const [maxChases, setMaxChases] = useState(2);
  const [threshold, setThreshold] = useState(1.0);
  const [saved, setSaved] = useState(false);

  // Seeded from the server once it arrives. Without this the form renders its
  // defaults over the founder's real configuration and a save silently reverts it.
  useEffect(() => {
    if (!company) return;
    setContext(company.persona_config?.company_context ?? '');
    setCadence(company.escalation_after_days ?? 3);
    setMaxChases(company.max_chases ?? 2);
    setThreshold(company.auto_approve_threshold ?? 1.0);
  }, [company]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await updateCompany({
      persona_config: { ...company?.persona_config, company_context: context },
      escalation_after_days: cadence,
      max_chases: maxChases,
      auto_approve_threshold: threshold,
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  // The worst case a founder actually cares about: how long a commitment can sit
  // unanswered before it reaches them.
  const worstCase = cadence * maxChases;

  return (
    <form onSubmit={handleSubmit} className="stone-card p-6 space-y-5 bg-white">
      <div className="border-b border-stone-border pb-4 space-y-1">
        <h3 className="font-semibold text-ink-black text-base flex items-center gap-2">
          <Sliders className="w-4 h-4 text-cyan-signal" />
          Sentinel Persona &amp; Follow-up Controls
        </h3>
        <p className="text-xs text-warm-gray">
          What Sentinel knows about your company, and how hard it chases before handing
          work back to you
        </p>
      </div>

      <div className="space-y-5 text-xs">
        <div>
          <label htmlFor="company-context" className="block font-medium text-ink-black mb-1">
            Company context
            <InfoTip>
              Background Sentinel reads when extracting tasks — who does what, and what
              your shorthand means. This is what resolves “Mark” to a person and “ACV”
              to a meaning.
            </InfoTip>
          </label>
          <textarea
            id="company-context"
            rows={4}
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder="e.g. 25-person B2B SaaS. Mark runs sales, Lisa marketing, John engineering — all report to me."
            className="w-full p-3 border border-stone-border rounded-lg focus:outline-none focus:border-cyan-signal text-xs"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label htmlFor="cadence" className="block font-medium text-ink-black mb-1">
              Follow up every
              <InfoTip>
                Days of silence Sentinel tolerates before sending a reminder — and the
                gap between reminders. A task that is past its deadline is chased on the
                next run regardless.
              </InfoTip>
            </label>
            <div className="flex items-center gap-2">
              <input
                id="cadence"
                type="number"
                min={1}
                max={30}
                value={cadence}
                onChange={(e) => setCadence(Number(e.target.value))}
                className="w-20 p-2.5 border border-stone-border rounded-lg bg-white"
              />
              <span className="text-warm-gray">days</span>
            </div>
          </div>

          <div>
            <label htmlFor="max-chases" className="block font-medium text-ink-black mb-1">
              Give up after
              <InfoTip>
                How many reminders before Sentinel stops chasing and hands the task back
                to you. Kept low on purpose: a third nudge rarely persuades anyone, and
                every extra one delays the moment you find out a commitment is dead.
              </InfoTip>
            </label>
            <div className="flex items-center gap-2">
              <input
                id="max-chases"
                type="number"
                min={1}
                max={5}
                value={maxChases}
                onChange={(e) => setMaxChases(Number(e.target.value))}
                className="w-20 p-2.5 border border-stone-border rounded-lg bg-white"
              />
              <span className="text-warm-gray">reminders</span>
            </div>
          </div>

          <div>
            <label htmlFor="threshold" className="block font-medium text-ink-black mb-1">
              Auto-approve above {Math.round(threshold * 100)}%
              <InfoTip>
                Extracted tasks Sentinel is at least this confident about skip your
                approval queue and are delegated directly. At 100% nothing
                auto-approves — you review everything.
              </InfoTip>
            </label>
            <input
              id="threshold"
              type="range"
              min="0.5"
              max="1.0"
              step="0.05"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              className="w-full accent-cyan-signal mt-3"
            />
            <p className="text-[11px] text-warm-gray mt-1">
              {threshold >= 1
                ? 'Nothing auto-approves — you review every task.'
                : 'Tasks below this confidence still wait for you.'}
            </p>
          </div>
        </div>

        {/* The settings restated as behaviour. Two numbers mean little on their own;
            this sentence is the only place the ladder is explained. */}
        <div className="rounded-lg bg-stone-canvas border border-stone-border p-3.5 space-y-1">
          <p className="text-xs text-ink-black">
            Sentinel will send up to <strong>{maxChases}</strong>{' '}
            {maxChases === 1 ? 'reminder' : 'reminders'}, <strong>{cadence}</strong>{' '}
            {cadence === 1 ? 'day' : 'days'} apart, then hand the task back to you.
          </p>
          <p className="text-[11px] text-warm-gray">
            You will hear about an unanswered commitment after about{' '}
            <strong>{worstCase}</strong> {worstCase === 1 ? 'day' : 'days'}. Anyone who
            reports a blocker reaches you immediately.
          </p>
        </div>
      </div>

      <div className="pt-3 border-t border-stone-border flex items-center justify-between">
        {saved ? (
          <span className="text-xs text-emerald-600 font-semibold flex items-center gap-1">
            <Check className="w-4 h-4" /> Settings saved
          </span>
        ) : (
          <span />
        )}
        <button type="submit" className="btn-cyan text-xs px-5 py-2">
          Save Configuration
        </button>
      </div>
    </form>
  );
};
