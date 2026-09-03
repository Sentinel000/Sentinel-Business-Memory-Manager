import './globals.css';
import React from 'react';

export const metadata = {
  title: 'Sentinel — AI Business Companion',
  description: 'Operational memory and follow-up engine for founders.',
  icons: {
    icon: '/sentinel-logo.png',
    apple: '/sentinel-logo.png',
  },
};

/*
 * Runs before first paint, so a founder who chose dark never sees a white flash
 * on the way to it. It has to be inline and blocking — React hydration is far
 * too late, and reading localStorage during render would break SSR.
 */
const THEME_BOOTSTRAP = `(function(){try{
var t=localStorage.getItem('sentinel:theme');
if(t!=='light'&&t!=='dark'){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}
if(t==='dark'){document.documentElement.classList.add('dark');}
}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOTSTRAP }} />
      </head>
      <body>{children}</body>
    </html>
  );
}
