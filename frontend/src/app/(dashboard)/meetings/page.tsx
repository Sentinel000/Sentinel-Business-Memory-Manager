'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useMeetingsStore } from '@/stores/useMeetingsStore';
import { AudioRecorderStudio, DeleteMeetingDialog } from '@/components/meetings';
import { Meeting } from '@/types';
import { FileText, CheckCircle2, Loader2, Trash2 } from 'lucide-react';

export default function MeetingsPage() {
  const { meetings, fetchMeetings } = useMeetingsStore();
  const [pendingDelete, setPendingDelete] = useState<Meeting | null>(null);

  useEffect(() => {
    fetchMeetings();
  }, [fetchMeetings]);

  return (
    <div className="space-y-6">
      <AudioRecorderStudio />

      <div className="stone-card p-6 bg-white space-y-4">
        <div className="border-b border-stone-border pb-3">
          <h3 className="font-semibold text-ink-black text-base">Meeting Archive & Transcripts</h3>
          <p className="text-xs text-warm-gray">Past transcribed audio sessions and extracted commitments</p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-stone-canvas border-b border-stone-border text-warm-gray uppercase text-[10px] tracking-wider">
              <tr>
                <th className="p-3">Meeting Title</th>
                <th className="p-3">Date</th>
                <th className="p-3">Duration</th>
                <th className="p-3">Format</th>
                <th className="p-3">Status</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-border text-ink-black font-medium">
              {meetings.map((m: Meeting) => (
                <tr key={m.id} className="hover:bg-stone-canvas/50">
                  <td className="p-3 font-semibold">{m.title}</td>
                  <td className="p-3 text-warm-gray">{new Date(m.recorded_at).toLocaleDateString()}</td>
                  <td className="p-3 text-warm-gray">
                    {m.duration_seconds ? `${Math.round(m.duration_seconds)}s` : '—'}
                  </td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 text-[10px] bg-stone-canvas border border-stone-border rounded font-mono">
                      {m.audio_format || 'text'}
                    </span>
                  </td>
                  <td className="p-3">
                    {m.status === 'completed' ? (
                      <span className="px-2 py-0.5 text-[10px] bg-emerald-100 text-emerald-800 rounded-full flex items-center gap-1 w-fit">
                        <CheckCircle2 className="w-3 h-3" /> Transcribed
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 text-[10px] bg-sky-wash text-cyan-edge rounded-full flex items-center gap-1 w-fit">
                        <Loader2 className="w-3 h-3 animate-spin" /> {m.status}
                      </span>
                    )}
                  </td>
                  <td className="p-3">
                    <div className="flex items-center gap-3 justify-end">
                      <Link
                        href={`/meetings/${m.id}`}
                        className="text-cyan-edge hover:underline font-semibold flex items-center gap-1"
                      >
                        <FileText className="w-3.5 h-3.5" /> Transcript
                      </Link>
                      <button
                        onClick={() => setPendingDelete(m)}
                        title="Delete meeting and its facts"
                        aria-label={`Delete ${m.title}`}
                        className="p-1 text-ash-gray hover:text-rose-600 transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {pendingDelete && (
        <DeleteMeetingDialog meeting={pendingDelete} onClose={() => setPendingDelete(null)} />
      )}
    </div>
  );
}
