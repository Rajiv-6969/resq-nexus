import { motion, useReducedMotion } from "framer-motion";

const HARD = [0.7, 0, 0.2, 1];

// Content that slides up hard the first time it scrolls into view.
export function Reveal({ as = "div", delay = 0, children, ...rest }) {
  const Tag = motion[as];
  return (
    <Tag
      initial={{ opacity: 0, y: 28 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.15 }}
      transition={{ duration: 0.36, ease: HARD, delay }}
      {...rest}
    >
      {children}
    </Tag>
  );
}

// Heading text that wipes in from the left (a clip, not a fade).
// The heading itself is observed; only its inner span is clipped, because
// IntersectionObserver counts a fully clipped target as 0% visible.
const WIPE = {
  hidden: { clipPath: "inset(-20% 100% -20% 0%)" },
  shown: { clipPath: "inset(-20% -4% -20% 0%)" },
};

export function Wipe({ as = "h2", delay = 0, children, ...rest }) {
  const reduce = useReducedMotion();
  if (reduce) {
    const Plain = as;
    return <Plain {...rest}>{children}</Plain>;
  }
  const Tag = motion[as];
  return (
    <Tag initial="hidden" whileInView="shown" viewport={{ once: true, amount: 0.3 }} {...rest}>
      <motion.span className="wipe" variants={WIPE} transition={{ duration: 0.7, ease: HARD, delay }}>
        {children}
      </motion.span>
    </Tag>
  );
}
