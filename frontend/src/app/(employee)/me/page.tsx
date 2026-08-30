'use client';

import React, { useEffect } from 'react';
import { useTasksStore } from '@/stores/useTasksStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { Header } from '@/components/Header';
import { Task } from '@/types';
import { CheckCircle2, PlayCircle, AlertCircle, Clock } from 'lucide-react';

export default function EmployeePortalPage() {
  const { myTasks, fetchMyTasks, updateMyTaskStatus } = useTasksStore();
  const { user } = useAuthStore();

  useEffect(() => {
    fetchMyTasks();
  }, [fetchMyTasks]);

  return (
    <div className="min-h-screen bg-stone-canvas flex flex-col">
      <Header />
      <main className="flex-1 p-8 max-w-4xl mx-auto w-full space-y-6">
        <div className="stone-card p-6 bg-white space-y-1">
          <h1 className="text-2xl font-normal text-ink-black tracking-tight">
            My <span className="cyan-highlight">Assigned Commitments</span>
          </h1>
          <p className="text-xs text-warm-gray">
            Hello {user?.email}! Below are action items delegated to you by your team lead. Tap a status to report progress.
          </p>
        </div>

        <div className="space-y-4">
          {myTasks.length === 0 ? (
            <div className="stone-card p-12 text-center text-warm-gray text-xs bg-white">
              No open commitments assigned to you right now.
            </div>
          ) : (
            myTasks.map((task: Task) => (
              <div key={task.id} className="stone-card p-5 bg-white space-y-4 hover:border-cyan-edge transition">
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <span className="px-2.5 py-0.5 text-xs font-medium bg-sky-wash text-cyan-edge rounded-full">
                      Status: {task.status.replace('_', ' ')}
                    </span>
                    <h3 className="text-base font-semibold text-ink-black">{task.title}</h3>
                  </div>

                  {task.deadline && (
                    <span className="text-xs text-warm-gray flex items-center gap-1 shrink-0 font-medium">
                      <Clock className="w-3.5 h-3.5" /> Due: {new Date(task.deadline).toLocaleDateString()}
                    </span>
                  )}
                </div>

                {task.source_quote && (
                  <blockquote className="p-3 bg-stone-canvas border-l-2 border-cyan-signal text-xs text-warm-gray italic rounded-r">
                    &quot;{task.source_quote}&quot;
                  </blockquote>
                )}

                <div className="pt-3 border-t border-stone-border flex items-center justify-end gap-2">
                  <button
                    onClick={() => updateMyTaskStatus(task.id, 'BLOCKED', 'Flagged as blocked')}
                    className="btn-ghost text-xs py-1.5 px-3 text-rose-600 hover:bg-rose-50 border-stone-border flex items-center gap-1"
                  >
                    <AlertCircle className="w-3.5 h-3.5" /> Flag Blocker
                  </button>

                  <button
                    onClick={() => updateMyTaskStatus(task.id, 'IN_PROGRESS')}
                    className="btn-ghost text-xs py-1.5 px-3 flex items-center gap-1"
                  >
                    <PlayCircle className="w-3.5 h-3.5 text-cyan-signal" /> In Progress
                  </button>

                  <button
                    onClick={() => updateMyTaskStatus(task.id, 'COMPLETED')}
                    className="btn-cyan text-xs py-1.5 px-4 flex items-center gap-1"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" /> Complete
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}
