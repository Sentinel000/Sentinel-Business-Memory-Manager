'use client';

import React, { useState } from 'react';
import { ToolExecution } from '@/types';
import { rendererFor, isOutcome } from './ToolResultRenderers';
import { ChevronRight, Wrench, AlertTriangle, Check } from 'lucide-react';

/** "search_tasks" -> "Search tasks" */
const humanize = (name: string) =>
  name.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());

/** Pretty-print a tool result when it is JSON, otherwise show it verbatim. */
const formatResult = (raw: string): string => {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
};

const ToolRow: React.FC<{ execution: ToolExecution }> = ({ execution }) => {
  const [open, setOpen] = useState(false);
  const argEntries = Object.entries(execution.args ?? {}).filter(
    ([, v]) => v !== null && v !== '' && v !== undefined
  );
  const Renderer = rendererFor(execution);

  return (
    <div className="border border-stone-border rounded-lg bg-white overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-stone-canvas transition"
      >
        <ChevronRight
          className={`w-3.5 h-3.5 text-ash-gray shrink-0 transition-transform duration-200 ${
            open ? 'rotate-90' : ''
          }`}
        />
        {execution.ok ? (
          <Wrench className="w-3.5 h-3.5 text-cyan-signal shrink-0" />
        ) : (
          <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
        )}
        <span className="text-xs font-medium text-ink-black">{humanize(execution.tool)}</span>
        {argEntries.length > 0 && (
          <span className="text-[11px] text-warm-gray truncate">
            {argEntries.map(([k, v]) => `${k}: ${String(v)}`).join(' · ')}
          </span>
        )}
        <span className="ml-auto shrink-0">
          {execution.ok ? (
            <span className="flex items-center gap-1 text-[10px] font-medium text-emerald-700">
              <Check className="w-3 h-3" /> ok
            </span>
          ) : (
            <span className="text-[10px] font-medium text-rose-700">failed</span>
          )}
        </span>
      </button>

      {open && (
        <div className="border-t border-stone-border px-3 py-2.5 space-y-2.5 bg-stone-canvas/60">
          {argEntries.length > 0 && (
            <div className="space-y-1">
              <p className="text-[10px] uppercase tracking-wider text-warm-gray font-medium">Arguments</p>
              <dl className="text-[11px] grid grid-cols-[auto,1fr] gap-x-3 gap-y-0.5">
                {argEntries.map(([k, v]) => (
                  <React.Fragment key={k}>
                    <dt className="text-warm-gray font-mono">{k}</dt>
                    <dd className="text-ink-black break-words font-mono">{String(v)}</dd>
                  </React.Fragment>
                ))}
              </dl>
            </div>
          )}
          <div className="space-y-1">
            <p className="text-[10px] uppercase tracking-wider text-warm-gray font-medium">Result</p>
            {Renderer ? (
              <Renderer execution={execution} />
            ) : (
              <>
                <pre className="text-[11px] text-ink-black bg-white border border-stone-border rounded p-2 overflow-x-auto max-h-64 whitespace-pre-wrap break-words">
                  {formatResult(execution.result) || '—'}
                </pre>
                {/* Only the raw view is cut — a rendered result reads from `data`. */}
                {execution.truncated && (
                  <p className="text-[10px] text-warm-gray italic">
                    Result truncated — Sentinel received a summary of the full record.
                  </p>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * What the agent did this turn.
 *
 * Two registers, because they are not the same claim. A write changed the
 * founder's data and renders as a card, open, in the flow of the answer. A read
 * is evidence and stays a collapsed row under a "sources consulted" heading —
 * available to verify, not competing with the reply.
 */
export const ToolExecutionPanel: React.FC<{ executions: ToolExecution[] }> = ({ executions }) => {
  if (!executions?.length) return null;

  const outcomes = executions.filter((e) => isOutcome(e) && rendererFor(e));
  // Only the last read is shown. A turn that queries three times to narrow an
  // answer produced one answer, and three near-identical rows above it read as
  // noise rather than as evidence.
  //
  // Writes are deliberately not collapsed this way. A model that verifies with a
  // read *after* creating something would otherwise hide the write behind the
  // trailing query — the mutation is the part the founder most needs to see.
  const reads = executions.filter((e) => !outcomes.includes(e));
  const evidence = reads.slice(-1);
  const hiddenReads = reads.length - evidence.length;

  return (
    <div className="space-y-2 mb-2">
      {outcomes.map((execution, i) => {
        const Renderer = rendererFor(execution)!;
        return <Renderer key={execution.id || `o${i}`} execution={execution} />;
      })}

      {evidence.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[10px] uppercase tracking-wider text-warm-gray font-medium">
            Source consulted
            {hiddenReads > 0 && (
              <span className="normal-case tracking-normal text-ash-gray">
                {' '}· {hiddenReads} earlier lookup{hiddenReads > 1 ? 's' : ''} hidden
              </span>
            )}
          </p>
          {evidence.map((execution, i) => (
            <ToolRow key={execution.id || `e${i}`} execution={execution} />
          ))}
        </div>
      )}
    </div>
  );
};
