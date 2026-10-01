'use client';

/**
 * Where a one-tap email button lands. Public - the signed link is the permission.
 *
 * The status from the button is preselected, but nothing is recorded until the
 * person presses Confirm. That second tap is not friction for its own sake: mail
 * security scanners open every link in a message, and a page that acted on load
 * would have robots marking tasks done. It is also where a blocker gets its note,
 * which is what turns "Blocked" into something the founder can act on.
 */

import React, { Suspense, useEffect, useState } from 'react';
import axios from 'axios';
import { useParams, useSearchParams } from 'next/navigation';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Link2Off,
  Loader2,
  PlayCircle,
  type LucideIcon,
} from 'lucide-react';
import { apiErrorMessage, publicApi } from '@/lib/api';
import { BrandMark } from '@/components/ui';
import type { ActionPreview, ActionResult, ActionStatus } from '@/types';

interface Choice {
  status: ActionStatus;
  label: string;
  confirm: string;
  icon: LucideIcon;
  selected: string;
}

const CHOICES: Choice[] = [
  {
    status: 'done',
    label: 'Complete',
    confirm: 'Mark as complete',
    icon: CheckCircle2,
    selected: 'bg-emerald-50 border-emerald-200 text-emerald-700',
  },
  {
    status: 'in_progress',
    label: 'In progress',
    confirm: 'Mark as in progress',
    icon: PlayCircle,
    selected: 'bg-amber-50 border-amber-200 text-amber-700',
  },
  {
    status: 'blocked',
    label: 'Blocked',
    confirm: 'Flag as blocked',
    icon: AlertCircle,
    selected: 'bg-rose-50 border-rose-200 text-rose-700',
  },
];

const DONE_COPY: Record<ActionStatus, { title: string; body: string }> = {
  done: { title: 'Marked complete', body: 'It is off your list, and the founder can see it now.' },
  in_progress: { title: 'Marked in progress', body: 'The founder can see it is moving.' },
  blocked: {
    title: 'Flagged as blocked',
    body: 'It is with the founder now, and Sentinel will not chase you about it.',
  },
};

const STATUS_WORDS: Record<string, string> = {
  done: 'complete',
  in_progress: 'in progress',
  blocked: 'blocked',
  rejected: 'rejected',
  approved: 'open',
};

function isChoice(value: string | null): value is ActionStatus {
  return value === 'done' || value === 'in_progress' || value === 'blocked';
}

function sourceLine(ref: string | null): string | null {
  if (!ref) return null;
  if (ref.startsWith('Meeting:')) return `From the meeting “${ref.slice(8).trim()}”`;
  return `From ${ref}`;
}

function dueLine(deadline: string | null): string | null {
  if (!deadline) return null;
  const when = new Date(deadline);
  return `Due ${when.toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' })}`;
}

type View =
  | { kind: 'loading' }
  | { kind: 'error'; message: string; expired: boolean }
  | { kind: 'ready'; preview: ActionPreview }
  | { kind: 'finished'; preview: ActionPreview; result: ActionResult; status: ActionStatus };

function Shell({ children, company }: { children: React.ReactNode; company?: string }) {
  return (
    <main className="min-h-screen bg-stone-canvas flex items-start sm:items-center justify-center px-4 py-10">
      <div className="w-full max-w-md space-y-4">
        <div className="flex items-center gap-2 px-1">
          <span className="w-7 h-7 rounded-lg bg-inverse flex items-center justify-center">
            <BrandMark className="w-4 h-4" />
          </span>
          <span className="text-sm font-semibold text-ink-black">Sentinel</span>
          {company && <span className="text-xs text-ash-gray">&middot; {company}</span>}
        </div>
        <div className="stone-card bg-white p-5 sm:p-6 space-y-5">{children}</div>
      </div>
    </main>
  );
}

function ActionPage() {
  const params = useParams<{ token: string }>();
  const search = useSearchParams();
  const token = params?.token ?? '';
  const requested = search?.get('s') ?? null;

  const [view, setView] = useState<View>({ kind: 'loading' });
  const [choice, setChoice] = useState<ActionStatus | null>(isChoice(requested) ? requested : null);
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    publicApi
      .get<ActionPreview>(`/actions/${token}`)
      .then((res) => setView({ kind: 'ready', preview: res.data }))
      .catch((err) =>
        setView({
          kind: 'error',
          message: apiErrorMessage(err, 'This link could not be opened.'),
          expired: axios.isAxiosError(err) && err.response?.status === 410,
        }),
      );
  }, [token]);

  const submit = async () => {
    if (view.kind !== 'ready' || !choice) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await publicApi.post<ActionResult>(`/actions/${token}`, {
        status: choice,
        note: choice === 'blocked' && note.trim() ? note.trim() : undefined,
      });
      setView({ kind: 'finished', preview: view.preview, result: res.data, status: choice });
    } catch (err) {
      setSubmitError(apiErrorMessage(err, 'That did not go through. Please try again.'));
    } finally {
      setSubmitting(false);
    }
  };

  if (view.kind === 'loading') {
    return (
      <Shell>
        <div className="flex items-center gap-2 text-sm text-warm-gray">
          <Loader2 className="w-4 h-4 animate-spin" /> Opening your task...
        </div>
      </Shell>
    );
  }

  if (view.kind === 'error') {
    return (
      <Shell>
        <div className="space-y-3">
          <Link2Off className="w-6 h-6 text-ash-gray" />
          <h1 className="text-lg font-medium text-ink-black">
            {view.expired ? 'This link has expired' : 'This link does not work'}
          </h1>
          <p className="text-sm text-warm-gray">{view.message}</p>
          <a href="/me" className="btn-cyan inline-flex text-xs py-2 px-4">
            Open Sentinel
          </a>
        </div>
      </Shell>
    );
  }

  const { preview } = view;
  const first = preview.owner_name.split(' ')[0];
  const meta = [dueLine(preview.deadline), sourceLine(preview.source_ref)].filter(Boolean);

  const taskCard = (
    <div className="space-y-2">
      <h1 className="text-lg sm:text-xl font-medium text-ink-black leading-snug">{preview.title}</h1>
      {meta.length > 0 && (
        <p className="text-xs text-warm-gray flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 shrink-0" />
          {meta.join('  ·  ')}
        </p>
      )}
      {preview.source_quote && (
        <blockquote className="p-3 bg-stone-canvas border-l-2 border-cyan-signal text-sm text-warm-gray rounded-r">
          &ldquo;{preview.source_quote}&rdquo;
        </blockquote>
      )}
    </div>
  );

  if (view.kind === 'finished') {
    const copy = view.result.changed
      ? DONE_COPY[view.status]
      : {
          title: `Already ${STATUS_WORDS[view.result.status] ?? view.result.status}`,
          body: 'Nothing else to do here.',
        };
    return (
      <Shell company={preview.company_name}>
        <div className="space-y-3">
          <CheckCircle2 className="w-8 h-8 text-emerald-700" />
          <div className="space-y-1">
            <h2 className="text-xl font-medium text-ink-black">{copy.title}</h2>
            <p className="text-sm text-warm-gray">{copy.body}</p>
          </div>
        </div>
        <div className="pt-4 border-t border-stone-border">{taskCard}</div>
        <a href="/me" className="text-xs text-cyan-edge hover:underline">
          See everything assigned to you
        </a>
      </Shell>
    );
  }

  if (preview.closed) {
    return (
      <Shell company={preview.company_name}>
        <p className="text-[11px] uppercase tracking-wider text-ash-gray font-medium">Already closed</p>
        {taskCard}
        <p className="text-sm text-warm-gray">
          This task is {STATUS_WORDS[preview.status] ?? preview.status}, so there is nothing to update.
        </p>
      </Shell>
    );
  }

  const active = CHOICES.find((c) => c.status === choice);

  return (
    <Shell company={preview.company_name}>
      <p className="text-[11px] uppercase tracking-wider text-ash-gray font-medium">
        Update for {first}
      </p>
      {taskCard}

      <div className="space-y-2">
        <p className="text-xs text-warm-gray">Where is it at?</p>
        <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Status">
          {CHOICES.map((c) => {
            const Icon = c.icon;
            const isOn = choice === c.status;
            return (
              <button
                key={c.status}
                type="button"
                role="radio"
                aria-checked={isOn}
                onClick={() => setChoice(c.status)}
                className={`flex flex-col items-center gap-1 rounded-cards border px-2 py-3 text-xs font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-signal ${
                  isOn ? c.selected : 'border-stone-border text-warm-gray hover:border-cyan-edge'
                }`}
              >
                <Icon className="w-4 h-4" />
                {c.label}
              </button>
            );
          })}
        </div>
      </div>

      {choice === 'blocked' && (
        <label className="block space-y-1.5">
          <span className="text-xs text-warm-gray">What is blocking you? The founder will see this.</span>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={2000}
            rows={3}
            placeholder="e.g. Still waiting on the dataset from the client"
            className="w-full rounded-inputs border border-stone-muted bg-white px-3 py-2 text-sm text-ink-black placeholder:text-ash-gray focus:outline-none focus:ring-2 focus:ring-cyan-signal"
          />
        </label>
      )}

      {submitError && (
        <p className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-inputs px-3 py-2">
          {submitError}
        </p>
      )}

      <button
        type="button"
        onClick={submit}
        disabled={!choice || submitting}
        className="btn-cyan w-full justify-center text-sm py-2.5 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
      >
        {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
        {active ? active.confirm : 'Choose a status'}
      </button>
      <p className="text-[11px] text-ash-gray text-center">No login needed. This link only works for this task.</p>
    </Shell>
  );
}

export default function ActionLinkPage() {
  return (
    <Suspense fallback={null}>
      <ActionPage />
    </Suspense>
  );
}
