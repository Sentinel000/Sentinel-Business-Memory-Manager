'use client';

import React from 'react';
import { Task } from '@/types';
import { Clock, User, AlertCircle, CheckCircle2, PlayCircle, HelpCircle } from 'lucide-react';

interface Props {
  task: Task;
  onSelect: (task: Task) => void;
}

export const TaskCard: React.FC<Props> = ({ task, onSelect }) => {
  const getStatusBadge = () => {
    switch (task.status) {
      case 'done':
        return (
          <span className="px-2.5 py-0.5 text-xs font-medium bg-emerald-100 text-emerald-800 rounded-full flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Completed
          </span>
        );
      case 'in_progress':
        return (
          <span className="px-2.5 py-0.5 text-xs font-medium bg-sky-wash text-cyan-edge rounded-full flex items-center gap-1">
            <PlayCircle className="w-3 h-3" /> In Progress
          </span>
        );
      case 'blocked':
        return (
          <span className="px-2.5 py-0.5 text-xs font-medium bg-rose-100 text-rose-800 rounded-full flex items-center gap-1">
            <AlertCircle className="w-3 h-3" /> Blocked
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 text-xs font-medium bg-stone-canvas text-warm-gray border border-stone-border rounded-full capitalize flex items-center gap-1">
            <HelpCircle className="w-3 h-3" /> {task.status.replace('_', ' ')}
          </span>
        );
    }
  };

  return (
    <div
      onClick={() => onSelect(task)}
      className="stone-card p-4 hover:border-cyan-edge transition cursor-pointer flex flex-col justify-between space-y-3"
    >
      <div className="space-y-1.5">
        <div className="flex items-center justify-between gap-2">
          {getStatusBadge()}
          {task.days_late > 0 && task.status !== 'done' && (
            <span className="text-[11px] font-semibold text-rose-600 bg-rose-50 px-2 py-0.5 rounded-full">
              {task.days_late}d late
            </span>
          )}
        </div>
        <h4 className="font-semibold text-ink-black text-sm leading-snug line-clamp-2">{task.title}</h4>
      </div>

      <div className="flex items-center justify-between text-xs text-warm-gray pt-2 border-t border-stone-border/60">
        <div className="flex items-center gap-1 font-medium text-ink-black">
          <User className="w-3.5 h-3.5 text-warm-gray" />
          <span>{task.owner_name || 'Unassigned'}</span>
        </div>
        <div className="flex items-center gap-1">
          <Clock className="w-3.5 h-3.5 text-warm-gray" />
          <span>{task.deadline ? new Date(task.deadline).toLocaleDateString() : 'No date'}</span>
        </div>
      </div>
    </div>
  );
};
