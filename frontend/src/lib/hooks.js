import { useEffect, useState } from "react";

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
