'use client';

import React, { useEffect } from 'react';
import { Bell } from 'lucide-react';
import { useRemindersStore, unanswered } from '@/stores/useRemindersStore';

/**
 * Reminders Sentinel has sent this employee.
 *
 * This is the whole of chasing now that Slack is gone, and it is deliberately
 * quiet about it: there is no push here, so a reminder sitting unread means only
 * that nobody has looked. The founder's briefing reports that silence rather than
 * assuming the message landed.
 *
 * Answered reminders are hidden rather than struck through — once someone has
 * replied, the nudge has done its job and keeping it on screen is just clutter.
 */
export const ReminderBanner: React.FC = () => {
  const { reminders, fetchReminders } = useRemindersStore();

  useEffect(() => {
    fetchReminders();
  }, [fetchReminders]);

  const open = unanswered(reminders);
  if (open.length === 0) return null;

  return (
    <div className="stone-card p-4 sm:p-5 bg-white border-amber-300/60 space-y-3">
      <h2 className="text-sm font-semibold text-ink-black flex items-center gap-2">
        <Bell className="w-4 h-4 text-amber-500" />
        {open.length} {open.length === 1 ? 'reminder' : 'reminders'} waiting on you
      </h2>

      <ul className="space-y-2">
        {open.map((reminder) => (
          <li key={reminder.id} className="border-l-2 border-amber-300/60 pl-3 space-y-0.5">
            <p className="text-sm text-ink-black leading-snug">{reminder.task_title}</p>
            <div className="flex flex-wrap items-center gap-x-3 text-[11px] text-warm-gray">
              {reminder.note && <span>{reminder.note}</span>}
              <span>
                {new Date(reminder.created_at).toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                })}
              </span>
            </div>
          </li>
        ))}
      </ul>

      <p className="text-[11px] text-warm-gray">
        Update the status below and these clear automatically.
      </p>
    </div>
  );
};
