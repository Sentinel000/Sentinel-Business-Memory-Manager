'use client';

import React, { useEffect } from 'react';
import {
  AlertTriangle, CalendarClock, Check, Clock, FileText, Quote, RefreshCw, Trash2, UserX,
} from 'lucide-react';
import { useReportsStore } from '@/stores/useReportsStore';
import { ReportItem, ReportSection } from '@/types';

/** Icon and accent per section. Order matches the server's, which is deliberate:
 *  what needs the founder first, context after. */
const SECTION_STYLE: Record<string, { icon: React.ComponentType<{ className?: string }>; accent: string }> = {
  needs_decision: { icon: AlertTriangle, accent: 'text-amber-500' },
  slipping: { icon: Clock, accent: 'text-red-500' },
  moved: { icon: Check, accent: 'text-emerald-500' },
  quiet: { icon: UserX, accent: 'text-warm-gray' },
};

const COUNT_LABELS: Record<string, string> = {
  open: 'Open',
  overdue: 'Overdue',
  blocked: 'Blocked',
  awaiting_you: 'Awaiting you',
  unowned: 'Unowned',
  no_deadline: 'No deadline',
};

function ItemRow({ item }: { item: ReportItem }) {
  return (
    <li className="border-l-2 border-stone-border pl-3 py-1.5 space-y-1">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm text-ink-black leading-snug">{item.title}</p>
        {item.overdue_days != null && item.overdue_days > 0 && (
          <span className="shrink-0 text-[10px] font-medium text-red-600 bg-red-500/10 rounded-full px-2 py-0.5">
            {item.overdue_days}d late
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-warm-gray">
        {item.owner ? <span>{item.owner}</span> : <span className="italic">unassigned</span>}
        {item.deadline && <span>due {item.deadline}</span>}
        {item.reason && <span className="text-amber-600">{item.reason}</span>}
        {item.moved_to && <span className="text-emerald-600">→ {item.moved_to.replace('_', ' ')}</span>}
        {item.days_silent != null && <span>silent {item.days_silent}d</span>}
        {item.chases && <span>chased {item.chases}</span>}
      </div>

      {item.note && <p className="text-[11px] text-warm-gray italic">“{item.note}”</p>}

      {/* Rule 6: the founder can check the claim rather than trust it. */}
      {item.source_quote && (
        <p className="text-[11px] text-warm-gray/80 flex gap-1.5">
          <Quote className="w-3 h-3 shrink-0 mt-0.5 opacity-50" />
          {item.source_quote}
        </p>
      )}
    </li>
  );
}

function SectionCard({ section }: { section: ReportSection }) {
  const style = SECTION_STYLE[section.key] ?? { icon: FileText, accent: 'text-warm-gray' };
  const Icon = style.icon;

  return (
    <div className="stone-card p-5 bg-white space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-ink-black flex items-center gap-2">
          <Icon className={`w-4 h-4 ${style.accent}`} />
          {section.title}
        </h3>
        {section.total > 0 && (
          <span className="text-[11px] text-warm-gray">{section.total}</span>
        )}
      </div>

      {section.items.length === 0 ? (
        // Never a blank box — an empty section is a real, reassuring answer.
        <p className="text-xs text-warm-gray">{section.empty}</p>
      ) : (
        <>
          <ul className="space-y-2.5">
            {section.items.map((item) => (
              <ItemRow key={`${section.key}-${item.task_id}`} item={item} />
            ))}
          </ul>
          {section.hidden > 0 && (
            <p className="text-[11px] text-warm-gray pt-1">
              and {section.hidden} more — see the task ledger
            </p>
          )}
        </>
      )}
    </div>
  );
}

export default function BriefingsPage() {
  const {
    current, history, isLoading, isGenerating, error, checked,
    fetchToday, fetchHistory, generate, open, remove,
  } = useReportsStore();

  useEffect(() => {
    fetchToday();
    fetchHistory();
  }, [fetchToday, fetchHistory]);

  const today = new Date().toISOString().slice(0, 10);
  const isToday = current?.report_date === today;

  return (
    <div className="space-y-6">
      <div className="stone-card p-6 bg-white flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-normal text-ink-black tracking-tight">
            Founder <span className="cyan-highlight">Briefings</span>
          </h1>
          <p className="text-xs text-warm-gray">
            Where your commitments stand — what needs you, what is slipping, who has gone quiet
          </p>
        </div>

        <button
          onClick={generate}
          disabled={isGenerating}
          className="btn-cyan text-xs px-4 py-2 flex items-center gap-1.5 w-fit disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
          {current && isToday ? 'Regenerate' : 'Generate briefing'}
        </button>
      </div>

      {error && (
        <div className="stone-card p-4 bg-white border-red-300/60 text-sm text-red-600">
          {error}
        </div>
      )}

      {checked && !current && !isLoading && (
        <div className="stone-card p-10 bg-white text-center space-y-2">
          <FileText className="w-8 h-8 text-warm-gray/50 mx-auto" />
          <h3 className="text-sm font-semibold text-ink-black">No briefing yet today</h3>
          <p className="text-xs text-warm-gray max-w-md mx-auto">
            Generate one to see what is waiting on you, what is about to slip, and who has
            not responded. It is built from your live task ledger, so it is accurate the
            moment you press the button.
          </p>
        </div>
      )}

      {current && (
        <>
          <div className="stone-card p-5 bg-white">
            <div className="flex flex-wrap items-baseline justify-between gap-2 mb-4">
              <h2 className="text-sm font-semibold text-ink-black">
                {isToday ? 'Today' : current.report_date}
                <span className="ml-2 font-normal text-warm-gray text-[11px]">
                  {/* Generated-at, not report date: the founder needs to know how
                      fresh this is, especially after a regenerate. */}
                  built {new Date(current.generated_at).toLocaleTimeString([], {
                    hour: 'numeric', minute: '2-digit',
                  })}
                </span>
              </h2>
            </div>

            <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
              {Object.entries(COUNT_LABELS).map(([key, label]) => (
                <div key={key} className="space-y-0.5">
                  <p className="text-xl font-normal text-ink-black tabular-nums">
                    {current.counts[key] ?? 0}
                  </p>
                  <p className="text-[10px] text-warm-gray uppercase tracking-wide">{label}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {current.sections.map((section) => (
              <SectionCard key={section.key} section={section} />
            ))}
          </div>
        </>
      )}

      {history.length > 0 && (
        <div className="stone-card p-5 bg-white space-y-3">
          <h3 className="text-sm font-semibold text-ink-black flex items-center gap-2">
            <CalendarClock className="w-4 h-4 text-warm-gray" />
            Past briefings
          </h3>
          <ul className="divide-y divide-stone-border">
            {history.map((row) => (
              <li key={row.id} className="flex items-center justify-between py-2 gap-3">
                <button
                  onClick={() => open(row.id)}
                  className={`text-xs text-left transition hover:text-ink-black ${
                    current?.id === row.id ? 'text-ink-black font-medium' : 'text-warm-gray'
                  }`}
                >
                  {row.report_date}
                  <span className="ml-2 text-[11px] text-warm-gray">
                    {row.counts.awaiting_you ?? 0} awaiting · {row.counts.overdue ?? 0} overdue
                  </span>
                </button>
                <button
                  onClick={() => remove(row.id)}
                  className="p-1 text-warm-gray hover:text-red-600 transition"
                  aria-label={`Delete the briefing for ${row.report_date}`}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
