'use client';

import React, { useEffect, useState } from 'react';
import { useMeetingsStore } from '@/stores/useMeetingsStore';
import { Meeting, MeetingDeletePreview } from '@/types';
import { AlertTriangle, Loader2, X } from 'lucide-react';

/**
 * Confirmation for a permanent, non-recoverable delete.
 *
 * The count is fetched before the dialog can be confirmed, because "delete this
 * meeting" and "delete this meeting and the 14 decisions extracted from it" are
 * different decisions and only one of them is what the founder is being asked.
 */
export const DeleteMeetingDialog: React.FC<{
  meeting: Meeting;
  onClose: () => void;
}> = ({ meeting, onClose }) => {
  const { previewDelete, deleteMeeting } = useMeetingsStore();
  const [preview, setPreview] = useState<MeetingDeletePreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    previewDelete(meeting.id)
      .then((p) => alive && setPreview(p))
      .catch(() => alive && setError('Could not check what this delete would remove.'));
    return () => {
      alive = false;
    };
  }, [meeting.id, previewDelete]);

  const confirm = async () => {
    setBusy(true);
    setError(null);
    try {
      await deleteMeeting(meeting.id);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not delete that meeting.');
      setBusy(false);
    }
  };

  // Two meetings sharing a title share one knowledge address, so deleting either
  // would wipe both. The server refuses; the dialog says so before they try.
  const blocked = preview?.title_is_ambiguous === true;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-ink-black/40 animate-in fade-in duration-200" onClick={onClose} />
      <div className="relative stone-card bg-white w-full max-w-md p-5 space-y-4 animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-rose-50 border border-rose-200 flex items-center justify-center shrink-0">
            <AlertTriangle className="w-4 h-4 text-rose-600" />
          </div>
          <div className="min-w-0 flex-1">
            <h2 className="text-sm font-semibold text-ink-black">Delete this meeting?</h2>
            <p className="text-xs text-warm-gray truncate">{meeting.title}</p>
          </div>
          <button onClick={onClose} className="p-1 text-ash-gray hover:text-ink-black transition" aria-label="Close">
            <X className="w-4 h-4" />
          </button>
        </div>

        {!preview && !error && (
          <p className="text-xs text-warm-gray flex items-center gap-2">
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> Checking what this would remove…
          </p>
        )}

        {blocked && (
          <p className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg p-3">
            Another meeting is also titled &ldquo;{meeting.title}&rdquo;. Facts are stored under the
            meeting title, so deleting this one would erase the other&rsquo;s memory too. Rename one
            of them first.
          </p>
        )}

        {preview && !blocked && (
          <div className="text-xs text-ink-black space-y-2">
            <p>This permanently removes:</p>
            <ul className="space-y-1 pl-4 list-disc marker:text-ash-gray">
              <li>The transcript and its recording metadata.</li>
              <li>
                {preview.fact_count === null ? (
                  <span className="text-amber-700">
                    An unknown number of facts — the knowledge store could not be reached, so this
                    delete may not complete.
                  </span>
                ) : (
                  <>
                    <strong className="font-semibold">{preview.fact_count}</strong> extracted fact
                    {preview.fact_count === 1 ? '' : 's'}, decision
                    {preview.fact_count === 1 ? '' : 's'}, and context entr
                    {preview.fact_count === 1 ? 'y' : 'ies'} from company memory.
                  </>
                )}
              </li>
            </ul>
            {preview.task_count > 0 && (
              <p className="text-warm-gray">
                {preview.task_count} extracted task{preview.task_count === 1 ? '' : 's'} will be
                kept — they may be live commitments — but will lose their source citation.
              </p>
            )}
            <p className="text-rose-700 font-medium">This cannot be undone.</p>
          </div>
        )}

        {error && (
          <p className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg p-3">{error}</p>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <button onClick={onClose} className="btn-ghost text-xs py-1.5 px-3" disabled={busy}>
            Cancel
          </button>
          <button
            onClick={confirm}
            disabled={busy || !preview || blocked}
            className="text-xs py-1.5 px-3 rounded-lg bg-rose-600 text-white font-medium hover:bg-rose-700 transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
          >
            {busy && <Loader2 className="w-3 h-3 animate-spin" />}
            {busy ? 'Deleting…' : 'Delete permanently'}
          </button>
        </div>
      </div>
    </div>
  );
};
