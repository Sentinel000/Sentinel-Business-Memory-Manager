'use client';

import React from 'react';
import { ReportSummary, Report } from '@/types';
import {
  Calendar,
  Clock,
  ArrowRight,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  UserX,
  FileText,
} from 'lucide-react';

interface BriefingCardProps {
  briefing: Report | ReportSummary;
  isToday?: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

export const BriefingCard: React.FC<BriefingCardProps> = ({
  briefing,
  isToday = false,
  onSelect,
  onDelete,
}) => {
  const counts = briefing.counts ?? {};
  const awaitingCount = counts.awaiting_you ?? 0;
  const overdueCount = counts.overdue ?? 0;
  const blockedCount = counts.blocked ?? 0;
  const openCount = counts.open ?? 0;

  const formattedDate = (() => {
    try {
      const d = new Date(briefing.report_date + 'T00:00:00');
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return briefing.report_date;
    }
  })();

  const builtTime = (() => {
    try {
      return new Date(briefing.generated_at).toLocaleTimeString([], {
        hour: 'numeric',
        minute: '2-digit',
      });
    } catch {
      return '';
    }
  })();

  return (
    <div
      onClick={onSelect}
      className={`stone-card p-5 bg-white flex flex-col justify-between space-y-4 hover:border-cyan-edge/60 hover:shadow-md transition cursor-pointer group relative ${
        isToday ? 'border-cyan-edge/40 ring-1 ring-cyan-signal/15' : ''
      }`}
    >
      {/* Top Row: Date & Status Badge */}
      <div className="flex items-start justify-between gap-2">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h3 className="text-base font-semibold text-ink-black group-hover:text-cyan-edge transition tracking-tight">
              {isToday ? "Today's Briefing" : formattedDate}
            </h3>
            {isToday && (
              <span className="px-2 py-0.5 text-[10px] bg-cyan-50 text-cyan-700 border border-cyan-200 rounded-full font-medium">
                Latest
              </span>
            )}
          </div>

          <p className="text-xs text-warm-gray flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-ash-gray" />
            <span>Built {builtTime}</span>
            {!isToday && <span>• {briefing.report_date}</span>}
          </p>
        </div>

        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="opacity-0 group-hover:opacity-100 p-1.5 text-ash-gray hover:text-rose-600 hover:bg-rose-50 rounded-lg transition"
          title="Delete briefing"
          aria-label={`Delete briefing for ${briefing.report_date}`}
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Middle: Metrics Highlights */}
      <div className="grid grid-cols-2 gap-2 text-xs py-1">
        <div className="p-2.5 rounded-lg bg-stone-canvas border border-stone-border space-y-0.5">
          <span className="text-[10px] text-warm-gray uppercase tracking-wider block">
            Awaiting You
          </span>
          <span className={`text-lg font-semibold tabular-nums ${awaitingCount > 0 ? 'text-amber-600' : 'text-ink-black'}`}>
            {awaitingCount}
          </span>
        </div>

        <div className="p-2.5 rounded-lg bg-stone-canvas border border-stone-border space-y-0.5">
          <span className="text-[10px] text-warm-gray uppercase tracking-wider block">
            Overdue
          </span>
          <span className={`text-lg font-semibold tabular-nums ${overdueCount > 0 ? 'text-rose-600' : 'text-ink-black'}`}>
            {overdueCount}
          </span>
        </div>

        <div className="p-2.5 rounded-lg bg-stone-canvas border border-stone-border space-y-0.5">
          <span className="text-[10px] text-warm-gray uppercase tracking-wider block">
            Blocked
          </span>
          <span className={`text-lg font-semibold tabular-nums ${blockedCount > 0 ? 'text-rose-700' : 'text-ink-black'}`}>
            {blockedCount}
          </span>
        </div>

        <div className="p-2.5 rounded-lg bg-stone-canvas border border-stone-border space-y-0.5">
          <span className="text-[10px] text-warm-gray uppercase tracking-wider block">
            Open Tasks
          </span>
          <span className="text-lg font-semibold tabular-nums text-ink-black">
            {openCount}
          </span>
        </div>
      </div>

      {/* Bottom Action */}
      <div className="pt-2 border-t border-stone-border flex items-center justify-between text-xs">
        <span className="text-warm-gray text-[11px] group-hover:text-ink-black transition">
          Click to inspect full brief
        </span>
        <span className="text-cyan-edge font-medium flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
          View Brief <ArrowRight className="w-3.5 h-3.5" />
        </span>
      </div>
    </div>
  );
};
