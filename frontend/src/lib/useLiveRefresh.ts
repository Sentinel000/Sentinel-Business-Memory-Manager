'use client';

import { useEffect, useRef } from 'react';

/**
 * How often an open screen re-reads its data. Overridable per deployment: a live
 * demo wants the founder's screen to flip within a few seconds of a teammate
 * tapping a button, which is NEXT_PUBLIC_LIVE_REFRESH_MS=3000.
 */
const DEFAULT_INTERVAL_MS = Number(process.env.NEXT_PUBLIC_LIVE_REFRESH_MS) || 10_000;

/**
 * Keeps a screen current without a reload.
 *
 * The whole product is about status flowing back - an employee taps Blocked, and the
 * founder should see it. Without this, the approval queue and the task ledger only
 * changed when someone pressed refresh, so the loop closed in the database and
 * stayed open on the screen.
 *
 * Polls only while the tab is visible, refetches the moment it regains focus, and
 * never overlaps one request with the next on a slow connection.
 */
export function useLiveRefresh(
  refresh: () => unknown,
  intervalMs: number = DEFAULT_INTERVAL_MS,
): void {
  const latest = useRef(refresh);

  useEffect(() => {
    latest.current = refresh;
  }, [refresh]);

  useEffect(() => {
    let inFlight = false;

    const run = () => {
      if (inFlight || document.visibilityState !== 'visible') return;
      inFlight = true;
      Promise.resolve()
        .then(() => latest.current())
        .catch(() => undefined)
        .finally(() => {
          inFlight = false;
        });
    };

    const onVisibility = () => {
      if (document.visibilityState === 'visible') run();
    };

    const timer = window.setInterval(run, intervalMs);
    window.addEventListener('focus', run);
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      window.clearInterval(timer);
      window.removeEventListener('focus', run);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [intervalMs]);
}
