'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/useAuthStore';
import { apiErrorMessage } from '@/lib/api';
import { BrandMark } from '@/components/ui';
import {
  ArrowRight,
  ArrowLeft,
  Check,
  Building2,
  User,
  Shield,
  Brain,
  Sparkles,
  Eye,
  EyeOff,
  CheckCircle2,
  Loader2,
  Lock,
} from 'lucide-react';

const INDUSTRY_PRESETS = [
  'B2B SaaS',
  'Fintech',
  'Agency & Services',
  'E-Commerce',
  'Healthcare',
  'Developer Tools',
  'Other',
];

const TEMPLATE_PRESETS = [
  {
    label: 'SaaS Co',
    text: "We're a 25-person B2B SaaS company. Mark runs sales & customer success, Lisa leads marketing, and John heads engineering. Our core product is an analytics platform.",
  },
  {
    label: 'Agency',
    text: "We're a 15-person digital product studio. Sarah handles client accounts & delivery, Dave oversees design, and Priya leads web/mobile development.",
  },
  {
    label: 'Startup',
    text: "We're an early-stage startup of 8 people. Founder leads product and vision, Maya leads engineering, and Sam manages growth and operations.",
  },
];

const STEPS = [
  { id: 1, title: 'Founder', icon: User },
  { id: 2, title: 'Workspace', icon: Building2 },
  { id: 3, title: 'Memory', icon: Brain },
  { id: 4, title: 'Deploy', icon: Sparkles },
];

export const SignupWizard: React.FC = () => {
  const router = useRouter();
  const { signup } = useAuthStore();

  const [currentStep, setCurrentStep] = useState(1);
  const [direction, setDirection] = useState<'forward' | 'backward'>('forward');

  // Form State
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const [companyName, setCompanyName] = useState('');
  const [industry, setIndustry] = useState('');

  const [companyDescription, setCompanyDescription] = useState('');

  // UI state
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [deploymentPhase, setDeploymentPhase] = useState<number>(0);

  // Validation
  const isEmailValid = (val: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
  const isStep1Valid = name.trim().length > 0 && isEmailValid(email) && password.length >= 8;
  const isStep2Valid = companyName.trim().length > 0 && industry.trim().length > 0;
  const isStep3Valid = companyDescription.trim().length > 10;

  const canAdvance = () => {
    if (currentStep === 1) return isStep1Valid;
    if (currentStep === 2) return isStep2Valid;
    if (currentStep === 3) return isStep3Valid;
    return true;
  };

  const handleNext = () => {
    if (!canAdvance()) return;
    setError('');
    setDirection('forward');
    setCurrentStep((prev) => Math.min(prev + 1, 4));
  };

  const handleBack = () => {
    setError('');
    setDirection('backward');
    setCurrentStep((prev) => Math.max(prev - 1, 1));
  };

  const handleStepClick = (stepId: number) => {
    if (stepId < currentStep) {
      setError('');
      setDirection('backward');
      setCurrentStep(stepId);
    } else if (stepId === currentStep + 1 && canAdvance()) {
      handleNext();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && currentStep < 4 && canAdvance()) {
      e.preventDefault();
      handleNext();
    }
  };

  const handleDeploy = async () => {
    setError('');
    setSubmitting(true);
    setDeploymentPhase(1);

    try {
      // Small visual delay for phase 1
      await new Promise((r) => setTimeout(r, 600));
      setDeploymentPhase(2);

      const signupPromise = signup({
        company_name: companyName,
        industry,
        company_description: companyDescription,
        founder_email: email,
        founder_password: password,
        founder_full_name: name,
      });

      await new Promise((r) => setTimeout(r, 600));
      setDeploymentPhase(3);

      await signupPromise;
      setDeploymentPhase(4);
      await new Promise((r) => setTimeout(r, 500));

      router.push('/approvals');
    } catch (err) {
      setSubmitting(false);
      setDeploymentPhase(0);
      setError(apiErrorMessage(err, 'Provisioning failed. Please check details and try again.'));
    }
  };

  return (
    <div className="w-full max-w-xl bg-white stone-card p-6 sm:p-8 shadow-xl space-y-6">
      {/* Header with Brand */}
      <div className="flex flex-col items-center text-center space-y-2">
        <div className="w-10 h-10 bg-inverse rounded-lg flex items-center justify-center text-white">
          <BrandMark className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-2xl font-normal text-ink-black tracking-tight">
            Deploy <span className="cyan-highlight">Sentinel Instance</span>
          </h1>
          <p className="text-xs text-warm-gray mt-0.5">
            Self-provision your company operational memory in minutes
          </p>
        </div>
      </div>

      {/* Stepper Indicator */}
      <div className="pt-1 pb-3">
        <div className="flex items-center justify-between relative">
          {/* Background track line */}
          <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-stone-border -translate-y-1/2 z-0" />
          {/* Active progress line */}
          <div
            className="absolute top-1/2 left-0 h-0.5 bg-cyan-signal -translate-y-1/2 z-0 transition-all duration-300"
            style={{ width: `${((currentStep - 1) / (STEPS.length - 1)) * 100}%` }}
          />

          {STEPS.map((s) => {
            const isDone = s.id < currentStep;
            const isCurrent = s.id === currentStep;
            const StepIcon = s.icon;

            return (
              <button
                key={s.id}
                type="button"
                onClick={() => handleStepClick(s.id)}
                disabled={s.id > currentStep || submitting}
                className={`relative z-10 flex flex-col items-center gap-1 group focus:outline-none ${
                  s.id <= currentStep ? 'cursor-pointer' : 'cursor-not-allowed opacity-60'
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-all duration-200 border ${
                    isDone
                      ? 'bg-cyan-signal border-cyan-edge text-white'
                      : isCurrent
                      ? 'bg-white border-cyan-signal text-cyan-signal shadow-sm ring-4 ring-cyan-signal/15'
                      : 'bg-white border-stone-border text-warm-gray'
                  }`}
                >
                  {isDone ? <Check className="w-4 h-4 stroke-[2.5]" /> : <StepIcon className="w-3.5 h-3.5" />}
                </div>
                <span
                  className={`text-[11px] font-medium hidden sm:block ${
                    isCurrent ? 'text-ink-black font-semibold' : 'text-warm-gray'
                  }`}
                >
                  {s.title}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 font-medium animate-in fade-in duration-200">
          {error}
        </div>
      )}

      {/* Step Content */}
      <div onKeyDown={handleKeyDown} className="min-h-[260px] flex flex-col justify-between">
        {/* STEP 1: Founder Account */}
        {currentStep === 1 && (
          <div className="space-y-4 animate-in fade-in slide-in-from-right-2 duration-200">
            <div>
              <h2 className="text-sm font-semibold text-ink-black">Founder Account</h2>
              <p className="text-xs text-warm-gray">Establish root ownership of your Sentinel tenant</p>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-ink-black mb-1">Founder Full Name</label>
                <input
                  type="text"
                  autoFocus
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Alex Rivers"
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
                <label className="block font-medium text-ink-black mb-1">Master Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    className="w-full px-3.5 py-2 pr-10 border border-stone-border rounded-lg focus:outline-none focus:border-cyan-signal"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-warm-gray hover:text-ink-black"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <div className="mt-1.5 flex items-center gap-2 text-[11px] text-warm-gray">
                  <span className={`flex items-center gap-1 ${password.length >= 8 ? 'text-emerald-700 font-medium' : ''}`}>
                    <CheckCircle2 className={`w-3 h-3 ${password.length >= 8 ? 'text-emerald-600' : 'text-stone-300'}`} />
                    8+ characters
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* STEP 2: Company Workspace */}
        {currentStep === 2 && (
          <div className="space-y-4 animate-in fade-in slide-in-from-right-2 duration-200">
            <div>
              <h2 className="text-sm font-semibold text-ink-black">Company Workspace</h2>
              <p className="text-xs text-warm-gray">Provision your company identity and industry sector</p>
            </div>

            <div className="space-y-3.5 text-xs">
              <div>
                <label className="block font-medium text-ink-black mb-1">Company Name</label>
                <input
                  type="text"
                  autoFocus
                  required
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="e.g. Acme Tech Inc."
                  className="w-full px-3.5 py-2 border border-stone-border rounded-lg focus:outline-none focus:border-cyan-signal"
                />
              </div>

              <div>
                <label className="block font-medium text-ink-black mb-1.5">Industry Sector</label>
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {INDUSTRY_PRESETS.map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => setIndustry(item === 'Other' ? '' : item)}
                      className={`px-3 py-1 rounded-full text-xs transition border ${
                        industry === item
                          ? 'bg-inverse text-white border-transparent'
                          : 'bg-stone-canvas text-warm-gray border-stone-border hover:text-ink-black hover:border-stone-muted'
                      }`}
                    >
                      {item}
                    </button>
                  ))}
                </div>
                <input
                  type="text"
                  required
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  placeholder="Or enter custom industry..."
                  className="w-full px-3.5 py-2 border border-stone-border rounded-lg focus:outline-none focus:border-cyan-signal"
                />
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: Operational Context */}
        {currentStep === 3 && (
          <div className="space-y-4 animate-in fade-in slide-in-from-right-2 duration-200">
            <div>
              <h2 className="text-sm font-semibold text-ink-black">Operational Memory & Team Vernacular</h2>
              <p className="text-xs text-warm-gray">
                Sentinel uses this context to resolve spoken names and team roles during extraction
              </p>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-medium text-ink-black">Quick Starters:</span>
                <div className="flex items-center gap-1.5">
                  {TEMPLATE_PRESETS.map((t) => (
                    <button
                      key={t.label}
                      type="button"
                      onClick={() => setCompanyDescription(t.text)}
                      className="px-2 py-0.5 text-[11px] rounded border border-stone-border hover:bg-stone-canvas text-cyan-edge font-medium transition"
                    >
                      + {t.label}
                    </button>
                  ))}
                </div>
              </div>

              <textarea
                autoFocus
                required
                rows={4}
                maxLength={4000}
                value={companyDescription}
                onChange={(e) => setCompanyDescription(e.target.value)}
                placeholder="Describe key leaders, departments, and products (e.g. 20-person SaaS co. Mark runs sales, Lisa marketing, John eng)."
                className="w-full px-3.5 py-2.5 border border-stone-border rounded-lg resize-none focus:outline-none focus:border-cyan-signal leading-relaxed"
              />

              <div className="flex items-center justify-between text-[11px] text-warm-gray">
                <span>Tip: Mention names and responsibilities for highest extraction accuracy</span>
                <span>{companyDescription.length} / 4000</span>
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: Review & Deploy */}
        {currentStep === 4 && (
          <div className="space-y-4 animate-in fade-in slide-in-from-right-2 duration-200">
            <div>
              <h2 className="text-sm font-semibold text-ink-black">Review & Deploy Instance</h2>
              <p className="text-xs text-warm-gray">Verify your tenant configuration before provisioning</p>
            </div>

            {!submitting ? (
              <div className="p-4 bg-stone-canvas border border-stone-border rounded-lg space-y-3 text-xs">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <span className="text-warm-gray text-[11px] block">Founder</span>
                    <span className="font-semibold text-ink-black block">{name}</span>
                    <span className="text-warm-gray text-[11px] block">{email}</span>
                  </div>
                  <div>
                    <span className="text-warm-gray text-[11px] block">Company</span>
                    <span className="font-semibold text-ink-black block">{companyName}</span>
                    <span className="text-cyan-edge text-[11px] font-medium block">{industry}</span>
                  </div>
                </div>

                <div className="border-t border-stone-border pt-2.5">
                  <span className="text-warm-gray text-[11px] block mb-0.5">Operational Context</span>
                  <p className="text-ink-black text-xs italic line-clamp-2">
                    &quot;{companyDescription}&quot;
                  </p>
                </div>
              </div>
            ) : (
              <div className="p-5 bg-stone-canvas border border-stone-border rounded-lg space-y-3 text-xs">
                <div className="flex items-center gap-2 font-medium text-ink-black pb-1 border-b border-stone-border">
                  <Loader2 className="w-4 h-4 text-cyan-signal animate-spin" />
                  <span>Deploying Sentinel Instance...</span>
                </div>

                <div className="space-y-2 text-xs">
                  <div className={`flex items-center gap-2 ${deploymentPhase >= 1 ? 'text-ink-black' : 'text-warm-gray'}`}>
                    {deploymentPhase > 1 ? (
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border-2 border-cyan-signal border-t-transparent animate-spin" />
                    )}
                    <span>Provisioning PostgreSQL tenant schemas...</span>
                  </div>

                  <div className={`flex items-center gap-2 ${deploymentPhase >= 2 ? 'text-ink-black' : 'text-warm-gray'}`}>
                    {deploymentPhase > 2 ? (
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                    ) : deploymentPhase === 2 ? (
                      <div className="w-3.5 h-3.5 rounded-full border-2 border-cyan-signal border-t-transparent animate-spin" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border border-stone-border" />
                    )}
                    <span>Generating cryptographic JWT boundary keys...</span>
                  </div>

                  <div className={`flex items-center gap-2 ${deploymentPhase >= 3 ? 'text-ink-black' : 'text-warm-gray'}`}>
                    {deploymentPhase > 3 ? (
                      <Check className="w-3.5 h-3.5 text-emerald-600" />
                    ) : deploymentPhase === 3 ? (
                      <div className="w-3.5 h-3.5 rounded-full border-2 border-cyan-signal border-t-transparent animate-spin" />
                    ) : (
                      <div className="w-3.5 h-3.5 rounded-full border border-stone-border" />
                    )}
                    <span>Initializing HydraDB temporal memory layer...</span>
                  </div>

                  {deploymentPhase >= 4 && (
                    <div className="flex items-center gap-2 text-emerald-700 font-medium">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      <span>Ready! Launching dashboard...</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Navigation Buttons */}
        <div className="flex items-center justify-between pt-5 border-t border-stone-border mt-4">
          {currentStep > 1 && !submitting ? (
            <button
              type="button"
              onClick={handleBack}
              className="btn-ghost text-xs px-4 py-2 flex items-center gap-1.5"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back
            </button>
          ) : (
            <div />
          )}

          {currentStep < 4 ? (
            <button
              type="button"
              onClick={handleNext}
              disabled={!canAdvance()}
              className="btn-cyan text-xs px-5 py-2 flex items-center gap-1.5 disabled:opacity-50"
            >
              Next <ArrowRight className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleDeploy}
              disabled={submitting}
              className="btn-cyan text-xs px-6 py-2.5 flex items-center gap-2 disabled:opacity-60 shadow-sm"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Provisioning...</span>
                </>
              ) : (
                <>
                  <span>Deploy Instance</span>
                  <Sparkles className="w-4 h-4" />
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Footer Link */}
      {!submitting && (
        <div className="text-center text-xs text-warm-gray pt-2 border-t border-stone-border">
          Already have an account?{' '}
          <Link href="/login" className="text-cyan-edge font-semibold hover:underline">
            Sign in
          </Link>
        </div>
      )}
    </div>
  );
};
