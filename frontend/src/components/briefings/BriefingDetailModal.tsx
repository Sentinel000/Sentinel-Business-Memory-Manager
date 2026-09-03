'use client';

import React, { useEffect } from 'react';
import { Report, ReportItem, ReportSection } from '@/types';
import {
  X,
  AlertTriangle,
  Clock,
  Check,
  UserX,
  Quote,
  FileText,
  Loader2,
  Calendar,
} from 'lucide-react';

interface BriefingDetailModalProps {
  briefing: Report | null;
  isOpen: boolean;
  onClose: () => void;
  isLoading?: boolean;
}

const SECTION_STYLE: Record<
  string,
  { icon: React.ComponentType<{ className?: string }>; accent: string; badgeCls: string }
> = {
  needs_decision: {
    icon: AlertTriangle,
    accent: 'text-amber-600',
    badgeCls: 'bg-amber-50 text-amber-700 border-amber-200',
  },
  slipping: {
    icon: Clock,
    accent: 'text-rose-600',
    badgeCls: 'bg-rose-50 text-rose-700 border-rose-200',
  },
  moved: {
    icon: Check,
    accent: 'text-emerald-600',
    badgeCls: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  },
  quiet: {
    icon: UserX,
    accent: 'text-warm-gray',
    badgeCls: 'bg-stone-100 text-ink-black border-stone-border',
  },
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
        <p className="text-xs font-medium text-ink-black leading-snug">{item.title}</p>
        {item.overdue_days != null && item.overdue_days > 0 && (
          <span className="shrink-0 text-[10px] font-semibold text-rose-700 bg-rose-50 border border-rose-200 rounded-full px-2 py-0.5">
            {item.overdue_days}d late
          </span>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-warm-gray">
        {item.owner ? (
          <span className="font-medium text-ink-black">{item.owner}</span>
        ) : (
          <span className="italic text-ash-gray">unassigned</span>
        )}
        {item.deadline && <span>due {item.deadline}</span>}
        {item.reason && <span className="text-amber-700 font-medium">{item.reason}</span>}
        {item.moved_to && (
          <span className="text-emerald-700 font-medium">→ {item.moved_to.replace('_', ' ')}</span>
        )}
        {item.days_silent != null && <span>silent {item.days_silent}d</span>}
        {item.chases && <span>chased {item.chases}</span>}
      </div>

      {item.note && <p className="text-[11px] text-warm-gray italic">“{item.note}”</p>}

      {item.source_quote && (
        <p className="text-[11px] text-warm-gray/85 flex gap-1.5 bg-stone-canvas p-1.5 rounded border border-stone-border/60">
          <Quote className="w-3 h-3 shrink-0 mt-0.5 text-ash-gray" />
          <span className="italic">{item.source_quote}</span>
        </p>
      )}
    </li>
  );
}

function SectionBlock({ section }: { section: ReportSection }) {
  const style = SECTION_STYLE[section.key] ?? {
    icon: FileText,
    accent: 'text-warm-gray',
    badgeCls: 'bg-stone-canvas text-ink-black border-stone-border',
  };
  const Icon = style.icon;

  return (
    <div className="p-4 rounded-xl bg-white border border-stone-border space-y-3 shadow-subtle">
      <div className="flex items-center justify-between pb-2 border-b border-stone-border">
        <h4 className="text-xs font-semibold text-ink-black flex items-center gap-2">
          <Icon className={`w-4 h-4 ${style.accent}`} />
          {section.title}
        </h4>
        {section.total > 0 && (
          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border ${style.badgeCls}`}
          >
            {section.total} {section.total === 1 ? 'item' : 'items'}
          </span>
        )}
      </div>

      {section.items.length === 0 ? (
        <p className="text-xs text-warm-gray italic py-2">{section.empty}</p>
      ) : (
        <>
          <ul className="space-y-3">
            {section.items.map((item) => (
              <ItemRow key={`${section.key}-${item.task_id}`} item={item} />
            ))}
          </ul>
          {section.hidden > 0 && (
            <p className="text-[11px] text-warm-gray pt-1 italic">
              and {section.hidden} more — check the operational task ledger
            </p>
          )}
        </>
      )}
    </div>
  );
}

export const BriefingDetailModal: React.FC<BriefingDetailModalProps> = ({
  briefing,
  isOpen,
  onClose,
  isLoading = false,
}) => {
  // ESC key support
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const builtTime = briefing
    ? (() => {
        try {
          return new Date(briefing.generated_at).toLocaleTimeString([], {
            hour: 'numeric',
            minute: '2-digit',
          });
        } catch {
          return '';
        }
      })()
    : '';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 animate-in fade-in duration-200">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-stone-900/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal Card */}
      <div className="relative w-full max-w-4xl max-h-[92vh] bg-white stone-card flex flex-col shadow-2xl overflow-hidden z-10 animate-in zoom-in-95 duration-200">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-stone-border flex items-center justify-between bg-white shrink-0">
          <div className="space-y-0.5">
            <div className="flex items-center gap-2">
              <Calendar className="w-4 h-4 text-cyan-signal" />
              <h3 className="text-base font-semibold text-ink-black tracking-tight">
                Founder Briefing — {briefing?.report_date || 'Loading...'}
              </h3>
            </div>
            {builtTime && (
              <p className="text-xs text-warm-gray">
                Generated at {builtTime} from live operational memory
              </p>
            )}
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-warm-gray hover:text-ink-black hover:bg-stone-canvas rounded-lg transition"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 min-h-0 bg-stone-canvas/50">
          {isLoading || !briefing ? (
            <div className="p-16 flex flex-col items-center justify-center gap-3 text-warm-gray">
              <Loader2 className="w-6 h-6 animate-spin text-cyan-signal" />
              <p className="text-xs">Loading complete briefing details...</p>
            </div>
          ) : (
            <>
              {/* Metrics Summary Strip */}
              <div className="p-4 bg-white border border-stone-border rounded-xl shadow-subtle">
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-center sm:text-left">
                  {Object.entries(COUNT_LABELS).map(([key, label]) => {
                    const val = briefing.counts?.[key] ?? 0;
                    return (
                      <div key={key} className="space-y-0.5">
                        <p className="text-xl font-semibold text-ink-black tabular-nums">{val}</p>
                        <p className="text-[10px] text-warm-gray uppercase tracking-wider">
                          {label}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 4 Structured Sections */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {briefing.sections.map((sec) => (
                  <SectionBlock key={sec.key} section={sec} />
                ))}
              </div>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-stone-border bg-white flex justify-end shrink-0">
          <button onClick={onClose} className="btn-ghost text-xs px-4 py-2">
            Close Briefing
          </button>
        </div>
      </div>
    </div>
  );
};
