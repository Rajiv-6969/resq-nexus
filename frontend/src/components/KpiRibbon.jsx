import { motion } from "framer-motion";
import { SHOW_ANALYTICS } from "../config";
import AnimatedNumber from "./AnimatedNumber";

const HARD = [0.7, 0, 0.2, 1];
const list = { hidden: {}, show: { transition: { staggerChildren: 0.04 } } };
const tile = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0, transition: { duration: 0.22, ease: HARD } } };

const pct = (v) => `${v.toFixed(0)}%`;
const minutes = (v) => `${v.toFixed(1)}`;
const two = (v) => v.toFixed(2);
const whole = (v) => Math.round(v).toLocaleString("en-IN");
const pad2 = (n) => String(n).padStart(2, "0");

export default function KpiRibbon({ zones, summary, allocation, stale }) {
  const damaged = zones.filter((z) => z.damage_severity > 0);
  const m = allocation?.engine.metrics;
  const g = SHOW_ANALYTICS ? allocation?.greedy.metrics : null;
  const awaiting = "run allocation";

  const items = [
    { key: "need", label: "Zones in need", value: zones.length ? damaged.length : null, unit: zones.length ? `/ ${zones.length}` : "" },
    { key: "people", label: "People affected", value: zones.length ? damaged.reduce((s, z) => s + z.population, 0) : null, sub: "in damaged zones" },
    { key: "critical", label: "Critical zones", value: summary ? summary.Critical : null, tone: "critical" },
    { key: "depots", label: "Relief depots", value: allocation?.depots.length ?? null, sub: allocation ? `${allocation.zones.length} zones routed` : awaiting },
    { key: "coverage", label: "Weighted coverage", value: m?.coverage_pct ?? null, format: pct, sub: g ? `greedy ${g.coverage_pct.toFixed(0)}%` : m ? "priority-weighted" : awaiting },
    { key: "response", label: "Avg response", value: m?.avg_response_time_min ?? null, format: minutes, unit: m ? "min" : "", sub: g ? `greedy ${g.avg_response_time_min.toFixed(1)} min` : m ? "road travel from depot" : awaiting },
    { key: "gini", label: "Fairness (Gini)", value: m?.gini ?? null, format: two, sub: g ? `greedy ${g.gini.toFixed(2)} / lower = fairer` : m ? "lower = fairer" : awaiting },
  ];

  return (
    <motion.ul className={`kpis${stale ? " is-stale" : ""}`} variants={list} initial="hidden" animate="show" aria-label="Key figures">
      {items.map(({ key, label, value, format, unit, sub, tone }, i) => (
        <motion.li key={key} className={`kpi${tone ? ` kpi--${tone}` : ""}`} variants={tile}>
          <span className="kpi-label">
            <span className="kpi-no">{pad2(i + 1)}</span>
            {label}
          </span>
          <span className="kpi-value">
            <AnimatedNumber value={value} format={format ?? whole} />
            {unit && <small>{unit}</small>}
          </span>
          {sub && <span className="kpi-sub">{sub}</span>}
        </motion.li>
      ))}
    </motion.ul>
  );
}
