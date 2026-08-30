'use client';

import React, { useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useMeetingsStore } from '@/stores/useMeetingsStore';
import { Task } from '@/types';
import { FileText, CheckCircle2 } from 'lucide-react';

export default function MeetingDetailPage() {
  const params = useParams();
  const id = params?.id as string;
  const { currentMeeting, fetchMeetingDetail, isLoading } = useMeetingsStore();

  useEffect(() => {
    if (id) fetchMeetingDetail(id);
  }, [id, fetchMeetingDetail]);

  if (isLoading || !currentMeeting) {
    return <div className="stone-card p-12 text-center text-warm-gray text-xs">Loading transcript...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="stone-card p-6 bg-white flex items-center justify-between">
        <div className="space-y-1">
          <span className="px-2.5 py-0.5 text-xs bg-emerald-100 text-emerald-800 rounded-full font-medium inline-flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Transcribed & Extracted
          </span>
          <h1 className="text-2xl font-normal text-ink-black tracking-tight">{currentMeeting.title}</h1>
          <p className="text-xs text-warm-gray flex items-center gap-2">
            <span>Recorded: {new Date(currentMeeting.recorded_at).toLocaleString()}</span>
            <span>•</span>
            <span>Duration: {currentMeeting.duration_seconds ? `${Math.round(currentMeeting.duration_seconds)}s` : 'N/A'}</span>
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 stone-card p-6 bg-white space-y-4">
          <div className="border-b border-stone-border pb-3 flex items-center gap-2">
            <FileText className="w-4 h-4 text-cyan-signal" />
            <h3 className="font-semibold text-ink-black text-base">Raw Speech Transcript</h3>
          </div>
          <div className="p-4 bg-stone-canvas border border-stone-border rounded-lg text-xs text-ink-black leading-relaxed whitespace-pre-wrap font-mono">
            {currentMeeting.raw_transcript || 'No transcript text available.'}
          </div>
        </div>

        <div className="stone-card p-6 bg-white space-y-4 h-fit">
          <div className="border-b border-stone-border pb-3">
            <h3 className="font-semibold text-ink-black text-base">Extracted Commitments</h3>
            <p className="text-xs text-warm-gray">Piped into Approval Queue</p>
          </div>
          <div className="space-y-2">
            {currentMeeting.extracted_tasks && currentMeeting.extracted_tasks.length > 0 ? (
              currentMeeting.extracted_tasks.map((t: Partial<Task>, idx: number) => (
                <div key={idx} className="p-3 bg-stone-canvas border border-stone-border rounded-lg text-xs space-y-1">
                  <span className="font-semibold text-ink-black block">{t.title}</span>
                  <span className="text-[10px] text-cyan-edge font-medium block">Owner: {t.owner_name || 'Unassigned'}</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-warm-gray italic">No action items extracted.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
