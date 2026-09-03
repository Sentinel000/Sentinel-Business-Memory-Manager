'use client';

import React from 'react';
import { Task, TaskStatus } from '@/types';
import { X, Clock, User, Quote, ShieldCheck } from 'lucide-react';

interface Props {
  task: Task | null;
  onClose: () => void;
  onUpdateStatus: (id: string, status: TaskStatus, note?: string) => void;
  onDelete: (id: string) => void;
}

export const TaskDetailModal: React.FC<Props> = ({ task, onClose, onUpdateStatus, onDelete }) => {
  if (!task) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/20 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="stone-card w-full max-w-xl bg-white p-5 sm:p-6 space-y-5 animate-in fade-in zoom-in-95 duration-150 shadow-xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between gap-4 border-b border-stone-border pb-4">
          <div className="space-y-1">
            <span className="text-xs font-semibold text-cyan-edge bg-sky-wash px-2.5 py-0.5 rounded-full">
              Task #{task.id.slice(0, 8)}
            </span>
            <h2 className="text-lg font-semibold text-ink-black leading-snug">{task.title}</h2>
          </div>
          <button onClick={onClose} className="p-1 text-warm-gray hover:text-ink-black rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Task Properties */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs bg-stone-canvas p-4 rounded-lg border border-stone-border">
          <div>
            <span className="text-warm-gray block mb-1">Owner</span>
            <span className="font-semibold text-ink-black flex items-center gap-1 text-sm">
              <User className="w-4 h-4 text-cyan-signal" />
              {task.owner_name || 'Unassigned'}
            </span>
          </div>

          <div>
            <span className="text-warm-gray block mb-1">Deadline</span>
            <span className="font-semibold text-ink-black flex items-center gap-1 text-sm">
              <Clock className="w-4 h-4 text-warm-gray" />
              {task.deadline ? new Date(task.deadline).toLocaleDateString() : 'None'}
            </span>
          </div>
        </div>

        {/* Verbatim Source Quote */}
        {task.source_quote && (
          <div className="space-y-1 text-xs">
            <span className="text-warm-gray font-medium flex items-center gap-1">
              <Quote className="w-3.5 h-3.5 text-cyan-signal" /> Verbatim Source Commitment:
            </span>
            <blockquote className="p-3 bg-stone-canvas border-l-2 border-cyan-signal italic text-warm-gray rounded-r">
              &quot;{task.source_quote}&quot;
            </blockquote>
          </div>
        )}

        {/* Status Actions Bar */}
        <div className="pt-4 border-t border-stone-border flex items-center justify-between">
          <button
            onClick={() => {
              onDelete(task.id);
              onClose();
            }}
            className="text-xs text-rose-600 hover:underline font-medium"
          >
            Delete Commitment
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={() => onUpdateStatus(task.id, 'in_progress')}
              className="btn-ghost text-xs py-1.5 px-3"
            >
              Mark In Progress
            </button>
            <button
              onClick={() => onUpdateStatus(task.id, 'done')}
              className="btn-cyan text-xs py-1.5 px-4"
            >
              Mark Completed
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
