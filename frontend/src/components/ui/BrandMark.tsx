import React from 'react';

/**
 * The Sentinel mark (Variation 3: Continuous Memory Loop):
 * An intertwining 3D continuous Möbius loop forming the letter 'S',
 * symbolizing closed-loop operational memory (extract -> approve -> delegate -> chase -> collect -> remember).
 */
export const BrandMark: React.FC<{ className?: string }> = ({ className = 'w-4 h-4' }) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
    aria-hidden="true"
  >
    <defs>
      <linearGradient id="sentinelRibbonGrad" x1="5" y1="3.5" x2="19" y2="20.5" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stopColor="#3ba6f1" />
        <stop offset="50%" stopColor="#7dd3fc" />
        <stop offset="100%" stopColor="#ffffff" />
      </linearGradient>
      <linearGradient id="sentinelCorePulse" x1="16" y1="5" x2="8" y2="19" gradientUnits="userSpaceOnUse">
        <stop offset="0%" stopColor="#ffffff" />
        <stop offset="60%" stopColor="#3ba6f1" />
        <stop offset="100%" stopColor="#0284c7" />
      </linearGradient>
    </defs>

    {/* Primary Continuous Loop Ribbon */}
    <path
      d="M16 8C16 5.24 13.76 3 11 3C8.24 3 6 5.24 6 8C6 11.8 18 12.2 18 16C18 18.76 15.76 21 13 21C10.24 21 8 18.76 8 16"
      stroke="url(#sentinelRibbonGrad)"
      strokeWidth="2.4"
      strokeLinecap="round"
      strokeLinejoin="round"
    />

    {/* Inner Electrified Core Fiber */}
    <path
      d="M14.5 7.5C14.5 5.8 12.9 4.4 11 4.4C9.1 4.4 7.5 5.8 7.5 7.5C7.5 10.8 16.5 13.2 16.5 16.5C16.5 18.2 14.9 19.6 13 19.6C11.1 19.6 9.5 18.2 9.5 16.5"
      stroke="url(#sentinelCorePulse)"
      strokeWidth="1.1"
      strokeLinecap="round"
      strokeLinejoin="round"
    />

    {/* Focal Memory Spark Nodes */}
    <circle cx="16" cy="8" r="1.1" fill="#ffffff" />
    <circle cx="12" cy="12" r="1.3" fill="#3ba6f1" />
    <circle cx="8" cy="16" r="1.1" fill="#38bdf8" />
  </svg>
);

/** Wordmark lockup: the mark in its dark tile, beside the product name. */
export const BrandLockup: React.FC<{ size?: 'sm' | 'lg' }> = ({ size = 'sm' }) => {
  const tile = size === 'lg' ? 'w-10 h-10 rounded-xl' : 'w-8 h-8 rounded-lg';
  const icon = size === 'lg' ? 'w-6 h-6' : 'w-5 h-5';
  return (
    <div className={`${tile} bg-inverse flex items-center justify-center text-cyan-signal shrink-0 shadow-sm border border-stone-800`}>
      <BrandMark className={icon} />
    </div>
  );
};
