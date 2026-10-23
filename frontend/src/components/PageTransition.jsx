import { motion } from "framer-motion";

const HARD = [0.7, 0, 0.2, 1];

// Pages slide in hard from the right and leave to the left.
export default function PageTransition({ children }) {
  return (
    <motion.main
      id="main"
      className="page"
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0, transition: { duration: 0.28, ease: HARD } }}
      exit={{ opacity: 0, x: -40, transition: { duration: 0.14, ease: HARD } }}
    >
      {children}
    </motion.main>
  );
}
