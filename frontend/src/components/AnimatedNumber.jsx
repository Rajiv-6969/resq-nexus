import { useEffect, useLayoutEffect, useRef } from "react";
import { animate, motion, useMotionValue, useReducedMotion, useTransform } from "framer-motion";

const defaultFormat = (v) => Math.round(v).toLocaleString("en-IN");

// A mono number that ticks up to its value at a steady rate (and re-counts when the value changes).
export default function AnimatedNumber({ value, format = defaultFormat, duration = 0.9, className = "num" }) {
  const reduce = useReducedMotion();
  const motionValue = useMotionValue(0);
  const formatRef = useRef(format);
  useLayoutEffect(() => {
    formatRef.current = format;
  });
  const text = useTransform(motionValue, (v) => formatRef.current(v));
  const missing = value == null || Number.isNaN(value);

  useEffect(() => {
    if (missing) return undefined;
    if (reduce) {
      motionValue.set(value);
      return undefined;
    }
    const controls = animate(motionValue, value, { duration, ease: "linear" });
    return () => controls.stop();
  }, [value, missing, duration, reduce, motionValue]);

  if (missing) return <span className={className}>—</span>;
  return <motion.span className={className}>{text}</motion.span>;
}
