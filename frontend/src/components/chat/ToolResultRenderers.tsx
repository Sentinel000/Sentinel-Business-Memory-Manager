'use client';

import React from 'react';
import Link from 'next/link';
import { ToolExecution, ToolTaskSummary, TaskStatus } from '@/types';
import { CheckCircle2, Circle, CircleDashed, AlertTriangle, XCircle, Clock } from 'lucide-react';

/**
 * Renderers for structured tool results.
 *
 * A tool tags its own return with `kind` on its success path; this module maps
 * that tag to a component. An unknown or absent `kind` — every error return, and
 * every tool not yet given a renderer — falls through to the raw JSON view, which
 * is what the whole panel used to do. New renderers can be added one at a time.
 */

/** Which kinds are the answer itself rather than evidence behind it. */
const OUTCOME_KINDS = new Set([
  'task_created',
  'task_updated',
  'task_approved',
  'task_rejected',
]);

export const isOutcome = (execution: ToolExecution): boolean =>
  !!execution.kind && OUTCOME_KINDS.has(execution.kind);

export const hasRenderer = (execution: ToolExecution): boolean =>
  !!execution.kind && execution.kind in RENDERERS;

const STATUS_STYLE: Record<TaskStatus, { cls: string; Icon: typeof Circle }> = {
  pending_approval: { cls: 'text-amber-700 bg-amber-50 border-amber-200', Icon: CircleDashed },
  approved: { cls: 'text-sky-700 bg-sky-50 border-sky-200', Icon: Circle },
  in_progress: { cls: 'text-cyan-700 bg-cyan-50 border-cyan-200', Icon: Clock },
  blocked: { cls: 'text-rose-700 bg-rose-50 border-rose-200', Icon: AlertTriangle },
  done: { cls: 'text-emerald-700 bg-emerald-50 border-emerald-200', Icon: CheckCircle2 },
  rejected: { cls: 'text-stone-600 bg-stone-100 border-stone-border', Icon: XCircle },
  overdue: { cls: 'text-rose-700 bg-rose-50 border-rose-200', Icon: AlertTriangle },
};

const StatusChip: React.FC<{ status: TaskStatus }> = ({ status }) => {
  const { cls, Icon } = STATUS_STYLE[status] ?? STATUS_STYLE.approved;
  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px] font-medium shrink-0 ${cls}`}
    >
      <Icon className="w-2.5 h-2.5" />
      {status.replace(/_/g, ' ')}
    </span>
  );
};

const formatDeadline = (iso?: string | null): string | null => {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
};

/** One task line. Compact by design — the chat column is narrow. */
const TaskRow: React.FC<{ task: ToolTaskSummary }> = ({ task }) => {
  const due = formatDeadline(task.deadline);
  const late = (task.days_late ?? 0) > 0 && task.status !== 'done';

  return (
    <div className="flex items-center gap-2 px-2.5 py-1.5 border-b border-stone-border last:border-0">
      <span className="text-xs text-ink-black truncate flex-1 min-w-0">{task.title}</span>
      {task.owner_name && (
        <span className="text-[11px] text-warm-gray shrink-0 hidden sm:inline">
          {task.owner_name}
        </span>
      )}
      {due && (
        <span className={`text-[11px] shrink-0 ${late ? 'text-rose-600 font-medium' : 'text-warm-gray'}`}>
          {due}
          {late ? ` · ${task.days_late}d late` : ''}
        </span>
      )}
      <StatusChip status={task.status} />
    </div>
  );
};

/** `query_tasks` — the tasks the answer was read off. */
const TaskListResult: React.FC<{ execution: ToolExecution }> = ({ execution }) => {
  const data = execution.data as { items?: ToolTaskSummary[]; count?: number } | undefined;
  const items = data?.items ?? [];

  if (items.length === 0) {
    return <p className="text-[11px] text-warm-gray px-2.5 py-2">No matching tasks.</p>;
  }

  return (
    <div className="border border-stone-border rounded-lg bg-white overflow-hidden">
      {items.map((t) => (
        <TaskRow key={t.id} task={t} />
      ))}
    </div>
  );
};

const OUTCOME_LABEL: Record<string, string> = {
  task_created: 'Task created',
  task_updated: 'Task updated',
  task_approved: 'Task approved',
  task_rejected: 'Task rejected',
  task_detail: 'Task',
};

/**
 * A single task the agent read or wrote. Writes render expanded and inline: a
 * mutation to the founder's own data should not read as a footnote.
 */
const TaskResult: React.FC<{ execution: ToolExecution }> = ({ execution }) => {
  const data = execution.data as { task?: ToolTaskSummary } | undefined;
  const task = data?.task;
  if (!task) return null;

  return (
    <div className="border border-stone-border rounded-lg bg-white overflow-hidden">
      <div className="flex items-center gap-2 px-2.5 py-1.5 bg-stone-canvas/60 border-b border-stone-border">
        <span className="text-[10px] uppercase tracking-wider text-warm-gray font-medium">
          {OUTCOME_LABEL[execution.kind ?? ''] ?? 'Task'}
        </span>
        {/* No per-task route exists yet, so this lands on the list. */}
        <Link
          href="/tasks"
          className="ml-auto text-[10px] text-cyan-signal hover:text-cyan-edge transition"
        >
          View in tasks
        </Link>
      </div>
      <TaskRow task={task} />
    </div>
  );
};

const RENDERERS: Record<string, React.FC<{ execution: ToolExecution }>> = {
  task_list: TaskListResult,
  task_detail: TaskResult,
  task_created: TaskResult,
  task_updated: TaskResult,
  task_approved: TaskResult,
  task_rejected: TaskResult,
};

/** The renderer for this execution, or null when it should fall back to raw JSON. */
export const rendererFor = (
  execution: ToolExecution
): React.FC<{ execution: ToolExecution }> | null =>
  (execution.kind && RENDERERS[execution.kind]) || null;
