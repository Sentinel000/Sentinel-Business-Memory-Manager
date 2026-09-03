'use client';

import React, { useId, useState } from 'react';
import { HelpCircle } from 'lucide-react';

interface Props {
  /** What the setting does, in plain language. Keep it to a sentence or two. */
  children: React.ReactNode;
}

/**
 * A hover/focus hint next to a setting label.
 *
 * Focusable and toggled on click as well as hover, so it works on touch and with a
 * keyboard — a tooltip that only opens on hover is invisible to half the people who
 * need it. Wired with aria-describedby rather than a title attribute so screen
 * readers announce it as help text.
 */
export const InfoTip: React.FC<Props> = ({ children }) => {
  const [open, setOpen] = useState(false);
  const id = useId();

  return (
    <span className="relative inline-flex align-middle ml-1.5">
      <button
        type="button"
        aria-label="What is this?"
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        className="text-warm-gray/70 hover:text-cyan-signal focus:text-cyan-signal transition outline-none"
      >
        <HelpCircle className="w-3.5 h-3.5" />
      </button>

      {open && (
        <span
          id={id}
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-30 w-60
                     rounded-lg border border-stone-border bg-surface shadow-card
                     px-3 py-2 text-[11px] font-normal leading-relaxed text-warm-gray
                     animate-in fade-in duration-150"
        >
          {children}
        </span>
      )}
    </span>
  );
};
