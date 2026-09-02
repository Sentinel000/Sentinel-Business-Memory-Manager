import React from 'react';

/**
 * The Sentinel mark: a shield (the approval gate) enclosing a pulse line
 * (the commitments it keeps watch over).
 *
 * Outline-only SVG in a single cyan stroke, per the design system's
 * "brand icon strokes" role for Cyan Signal.
 */
export const BrandMark: React.FC<{ className?: string }> = ({ className = 'w-4 h-4' }) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.75}
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden="true"
  >
    <path d="M12 2.75 4.75 5.6v5.9c0 4.36 2.94 8.16 7.25 9.75 4.31-1.59 7.25-5.39 7.25-9.75V5.6L12 2.75Z" />
    <path d="M8.1 12.4h2.15l1.4-2.85 1.55 4.35 1.15-1.5h1.55" />
  </svg>
);

/** Wordmark lockup: the mark in its dark tile, beside the product name. */
export const BrandLockup: React.FC<{ size?: 'sm' | 'lg' }> = ({ size = 'sm' }) => {
  const tile = size === 'lg' ? 'w-10 h-10 rounded-lg' : 'w-7 h-7 rounded-md';
  const icon = size === 'lg' ? 'w-5 h-5' : 'w-4 h-4';
  return (
    <div className={`${tile} bg-inverse flex items-center justify-center text-cyan-signal shrink-0`}>
      <BrandMark className={icon} />
    </div>
  );
};
