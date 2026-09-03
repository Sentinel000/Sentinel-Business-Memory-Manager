'use client';

import React from 'react';

export type BotState = 'idle' | 'thinking' | 'active';
export type BotSize = 'sm' | 'md' | 'lg' | 'xl';

interface SentinelBotProps {
  size?: BotSize | number;
  state?: BotState;
  className?: string;
  showGlow?: boolean;
}

const SIZE_MAP: Record<BotSize, number> = {
  sm: 28,
  md: 44,
  lg: 96,
  xl: 120,
};

export const SentinelBot: React.FC<SentinelBotProps> = ({
  size = 'md',
  state = 'idle',
  className = '',
  showGlow = false,
}) => {
  const pixelSize = typeof size === 'number' ? size : SIZE_MAP[size] ?? 44;

  return (
    <div
      className={`relative inline-flex items-center justify-center select-none ${className}`}
      style={{ width: pixelSize, height: pixelSize }}
    >
      {/* Delicate, soft ambient glow (tamed to be subtle and refined) */}
      {(showGlow || state === 'thinking') && (
        <div
          className="absolute inset-0 rounded-full bg-cyan-signal/10 blur-xl pointer-events-none transition-all duration-700"
          style={{ transform: 'scale(1.18)' }}
        />
      )}

      {/* Main 3D Bot SVG */}
      <svg
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`w-full h-full ${state === 'idle' ? 'animate-bot-float' : ''}`}
        style={{
          filter: 'drop-shadow(0 6px 14px rgba(0, 0, 0, 0.16))',
        }}
      >
        <defs>
          {/* Main 3D spherical shading with key light from top-left */}
          <radialGradient
            id="sphere3DGradient"
            cx="34%"
            cy="26%"
            r="68%"
            fx="32%"
            fy="24%"
          >
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="38%" stopColor="#faf9f8" />
            <stop offset="68%" stopColor="#e4e0dc" />
            <stop offset="88%" stopColor="#c5beb7" />
            <stop offset="100%" stopColor="#9a928a" />
          </radialGradient>

          {/* Diffused bottom-right wrap shadow for realistic spherical curvature */}
          <radialGradient
            id="sphereDepthShadow"
            cx="50%"
            cy="84%"
            r="55%"
            fx="50%"
            fy="90%"
          >
            <stop offset="0%" stopColor="#57514b" stopOpacity="0.45" />
            <stop offset="45%" stopColor="#78716c" stopOpacity="0.25" />
            <stop offset="85%" stopColor="#a8a29e" stopOpacity="0.05" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
          </radialGradient>

          {/* Subtle soft edge ambient occlusion shadow */}
          <linearGradient
            id="edgeOcclusion"
            x1="10"
            y1="10"
            x2="85"
            y2="95"
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.3" />
            <stop offset="60%" stopColor="#d6d3d1" stopOpacity="0" />
            <stop offset="100%" stopColor="#44403c" stopOpacity="0.35" />
          </linearGradient>

          {/* Top gloss specular highlight */}
          <linearGradient
            id="specularGloss"
            x1="50"
            y1="6"
            x2="50"
            y2="36"
            gradientUnits="userSpaceOnUse"
          >
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0.9" />
            <stop offset="65%" stopColor="#ffffff" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0" />
          </linearGradient>

          {/* Subtle contact shadow under the sphere */}
          <radialGradient
            id="ambientContactShadow"
            cx="50%"
            cy="50%"
            r="50%"
          >
            <stop offset="0%" stopColor="#000000" stopOpacity="0.3" />
            <stop offset="60%" stopColor="#000000" stopOpacity="0.1" />
            <stop offset="100%" stopColor="#000000" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* 0. Soft ambient contact shadow below sphere for depth */}
        <ellipse cx="50" cy="94" rx="32" ry="5" fill="url(#ambientContactShadow)" />

        {/* 1. Base 3D Sphere */}
        <circle cx="50" cy="48" r="44" fill="url(#sphere3DGradient)" />

        {/* 2. Bottom curvature depth shadow layer */}
        <circle cx="50" cy="48" r="44" fill="url(#sphereDepthShadow)" />

        {/* 3. Directional ambient occlusion overlay */}
        <circle cx="50" cy="48" r="44" fill="url(#edgeOcclusion)" />

        {/* 4. Top specular highlight curve */}
        <path
          d="M 18 40 C 24 16, 76 16, 82 40 C 70 22, 30 22, 18 40 Z"
          fill="url(#specularGloss)"
        />

        {/* 5. Animated Eyes (Capsule shapes looking straight forward) */}
        <g className={`bot-eyes-container ${state === 'thinking' ? 'animate-bot-thinking' : 'animate-bot-blink'}`}>
          {/* Left Eye */}
          <rect
            x="34"
            y="41"
            width="9"
            height="17"
            rx="4.5"
            fill={state === 'thinking' ? '#3ba6f1' : '#1c1917'}
            className="transition-colors duration-300"
          />
          {/* Left Eye reflection */}
          <circle cx="37" cy="45" r="1.3" fill="#ffffff" opacity={state === 'thinking' ? '0.9' : '0.45'} />

          {/* Right Eye */}
          <rect
            x="57"
            y="41"
            width="9"
            height="17"
            rx="4.5"
            fill={state === 'thinking' ? '#3ba6f1' : '#1c1917'}
            className="transition-colors duration-300"
          />
          {/* Right Eye reflection */}
          <circle cx="60" cy="45" r="1.3" fill="#ffffff" opacity={state === 'thinking' ? '0.9' : '0.45'} />
        </g>
      </svg>

      {/* Component-scoped style for keyframes */}
      <style jsx>{`
        @keyframes botFloat {
          0%, 100% {
            transform: translateY(0px);
          }
          50% {
            transform: translateY(-2.5px);
          }
        }

        @keyframes botBlink {
          0%, 45%, 49%, 100% {
            transform: scaleY(1);
          }
          47% {
            transform: scaleY(0.08);
          }
        }

        @keyframes botThinking {
          0%, 100% {
            transform: scaleY(1) translateY(0px);
            opacity: 1;
          }
          50% {
            transform: scaleY(0.85) translateY(-1px);
            opacity: 0.8;
          }
        }

        .animate-bot-float {
          animation: botFloat 3.8s ease-in-out infinite;
        }

        .animate-bot-blink {
          transform-origin: 50px 49px;
          animation: botBlink 4.2s infinite ease-in-out;
        }

        .animate-bot-thinking {
          transform-origin: 50px 49px;
          animation: botThinking 1.4s infinite ease-in-out;
        }
      `}</style>
    </div>
  );
};
