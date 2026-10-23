import { motion } from "framer-motion";
import AnimatedNumber from "./AnimatedNumber";
import { RESOURCES, formatNumber } from "../constants";

const HARD = [0.7, 0, 0.2, 1];

// Available stock per resource; after a run it also shows the total need and shortfall.
export default function StockSummary({ resources, result }) {
  const need = result
    ? Object.fromEntries(RESOURCES.map((r) => [r.key, result.zones.reduce((s, z) => s + z.demand[r.key], 0)]))
    : null;
  return (
    <section className="stock" aria-labelledby="stock-title">
      <h3 id="stock-title" className="subhead">
        Available stock
      </h3>
      <ul className="stock-grid">
        {RESOURCES.map((r) => {
          const total = need?.[r.key];
          const ratio = total ? Math.min(resources[r.key] / total, 1) : null;
          return (
            <li key={r.key} className="stock-tile">
              <span className="stock-label">{r.label}</span>
              <span className="stock-value">
                <AnimatedNumber value={resources[r.key]} />
              </span>
              {ratio == null ? (
                <span className="stock-hint">{r.hint}</span>
              ) : (
                <>
                  <span className="stock-bar" aria-hidden="true">
                    <motion.span initial={{ width: 0 }} animate={{ width: `${ratio * 100}%` }} transition={{ duration: 0.5, ease: HARD }} />
                  </span>
                  <span className="stock-hint">
                    need {formatNumber(total)} / {Math.round((1 - ratio) * 100)}% short
                  </span>
                </>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
