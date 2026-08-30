import './globals.css';
import React from 'react';

export const metadata = {
  title: 'Sentinel — AI Business Companion',
  description: 'Operational memory and follow-up engine for founders.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
