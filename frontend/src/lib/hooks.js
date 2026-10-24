import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

// The value, updated only after it has stopped changing for `delay` ms.
export function useDebouncedValue(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

// Resolve with `promise`'s value, but never sooner than `ms` (lets each pipeline step be seen).
export async function withMinimum(promise, ms) {
  const [value] = await Promise.all([promise, new Promise((resolve) => window.setTimeout(resolve, ms))]);
  return value;
}

export function prefersReducedMotion() {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

// Calls `load({ signal })` now and every `intervalMs` while `enabled` (paused while the tab is hidden),
// so API helpers that take an options object can be passed directly.
// Returns { data, error, loading, refresh, updatedAt }.
export function usePolling(load, intervalMs, { enabled = true } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: true, updatedAt: null });
  const [tick, setTick] = useState(0);
  const loadRef = useRef(load);
  useLayoutEffect(() => {
    loadRef.current = load;
  });

  useEffect(() => {
    if (!enabled) return undefined;
    const controller = new AbortController();
    loadRef
      .current({ signal: controller.signal })
      .then((data) => setState({ data, error: null, loading: false, updatedAt: new Date() }))
      .catch((err) => err.name !== "AbortError" && setState((s) => ({ ...s, error: err.message, loading: false })));
    return () => controller.abort();
  }, [enabled, tick]);

  useEffect(() => {
    if (!enabled || !intervalMs) return undefined;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") setTick((n) => n + 1);
    }, intervalMs);
    const onVisible = () => document.visibilityState === "visible" && setTick((n) => n + 1);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [enabled, intervalMs]);

  const refresh = useCallback(() => setTick((n) => n + 1), []);
  const replace = useCallback((update) => setState((s) => ({ ...s, data: typeof update === "function" ? update(s.data) : update })), []);
  return { ...state, refresh, replace };
}

// The current time, refreshed every `ms` (for "4 min ago" labels).
export function useNow(ms = 30000) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), ms);
    return () => window.clearInterval(timer);
  }, [ms]);
  return now;
}
