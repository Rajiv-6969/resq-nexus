import { useEffect, useLayoutEffect, useRef } from "react";
import { animate, motion, useMotionValue, useReducedMotion, useTransform } from "framer-motion";

const defaultFormat = (v) => Math.round(v).toLocaleString("en-IN");

// A number that counts up to its value (and re-animates when the value changes).
export default function AnimatedNumber({ value, format = defaultFormat, duration = 1.2, className = "num" }) {
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
    const controls = animate(motionValue, value, { duration, ease: [0.16, 1, 0.3, 1] });
    return () => controls.stop();
  }, [value, missing, duration, reduce, motionValue]);

  if (missing) return <span className={className}>—</span>;
  return <motion.span className={className}>{text}</motion.span>;
}
