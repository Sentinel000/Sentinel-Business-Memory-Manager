'use client';

import React, { useEffect, useState } from 'react';
import { RefreshCw, FileText, Sparkles, Plus } from 'lucide-react';
import { useReportsStore } from '@/stores/useReportsStore';
import { BriefingCard, BriefingDetailModal } from '@/components/briefings';
import { ReportSummary } from '@/types';

export default function BriefingsPage() {
  const {
    current,
    history,
    isLoading,
    isGenerating,
    error,
    checked,
    fetchToday,
    fetchHistory,
    generate,
    open,
    remove,
  } = useReportsStore();

  const [isModalOpen, setIsModalOpen] = useState(false);

  useEffect(() => {
    fetchToday();
    fetchHistory();
  }, [fetchToday, fetchHistory]);

  const today = new Date().toISOString().slice(0, 10);
  const isTodayGenerated = current?.report_date === today || history.some((h) => h.report_date === today);

  const handleSelectBriefing = async (id: string) => {
    if (current?.id === id) {
      setIsModalOpen(true);
      return;
    }
    setIsModalOpen(true);
    await open(id);
  };

  const handleGenerate = async () => {
    await generate();
    setIsModalOpen(true);
  };

  // Build unified list of briefings (today's current report + history, deduplicated by id)
  const allBriefings: Array<ReportSummary | typeof current> = [];
  const seenIds = new Set<string>();

  if (current) {
    allBriefings.push(current);
    seenIds.add(current.id);
  }

  history.forEach((h) => {
    if (!seenIds.has(h.id)) {
      allBriefings.push(h);
      seenIds.add(h.id);
    }
  });

  const hasBriefings = allBriefings.length > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="stone-card p-6 bg-white flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl font-normal text-ink-black tracking-tight">
            Founder <span className="cyan-highlight">Briefings</span>
          </h1>
          <p className="text-xs text-warm-gray">
            Where your commitments stand — what needs you, what is slipping, and who has gone quiet
          </p>
        </div>

        <button
          onClick={handleGenerate}
          disabled={isGenerating}
          className="btn-cyan text-xs px-4 py-2 flex items-center gap-1.5 w-fit disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
          <span>{isTodayGenerated ? 'Regenerate Today' : 'Generate briefing'}</span>
        </button>
      </div>

      {/* Error notification */}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-700 font-medium">
          {error}
        </div>
      )}

      {/* Empty State: No briefings exist at all */}
      {checked && !hasBriefings && !isLoading && (
        <div className="stone-card p-12 bg-white text-center space-y-4 max-w-lg mx-auto">
          <div className="w-12 h-12 bg-stone-canvas border border-stone-border rounded-xl flex items-center justify-center text-warm-gray mx-auto">
            <FileText className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-ink-black">No briefings generated yet</h3>
            <p className="text-xs text-warm-gray leading-relaxed">
              Generate one to see what is waiting on you, what is about to slip, and who has not
              responded. It is computed in real time from your live operational task ledger.
            </p>
          </div>
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="btn-cyan text-xs px-5 py-2.5 inline-flex items-center gap-2 disabled:opacity-50 shadow-sm"
          >
            <Sparkles className="w-4 h-4" />
            <span>Generate First Briefing</span>
          </button>
        </div>
      )}

      {/* Briefing Cards Grid */}
      {hasBriefings && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold text-warm-gray uppercase tracking-wider">
              Available Briefings ({allBriefings.length})
            </h2>
            <span className="text-[11px] text-warm-gray">Click any card to open full brief</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {allBriefings.map((briefing) => {
              if (!briefing) return null;
              const isToday = briefing.report_date === today;
              return (
                <BriefingCard
                  key={briefing.id}
                  briefing={briefing}
                  isToday={isToday}
                  onSelect={() => handleSelectBriefing(briefing.id)}
                  onDelete={() => remove(briefing.id)}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Full Briefing Detail Modal */}
      <BriefingDetailModal
        briefing={current}
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        isLoading={isLoading}
      />
    </div>
  );
}
