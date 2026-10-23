import { motion } from "framer-motion";
import { SHOW_ANALYTICS } from "../config";
import AnimatedNumber from "./AnimatedNumber";
import { AlertIcon, ClockIcon, DepotIcon, ScaleIcon, ShieldIcon, TargetIcon, UsersIcon } from "./icons";

const list = { hidden: {}, show: { transition: { staggerChildren: 0.05 } } };
const tile = { hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0, transition: { duration: 0.4 } } };

const pct = (v) => `${v.toFixed(0)}%`;
const minutes = (v) => `${v.toFixed(1)}`;
const two = (v) => v.toFixed(2);
const whole = (v) => Math.round(v).toLocaleString("en-IN");

export default function KpiRibbon({ zones, summary, allocation, stale }) {
  const damaged = zones.filter((z) => z.damage_severity > 0);
  const m = allocation?.engine.metrics;
  const g = SHOW_ANALYTICS ? allocation?.greedy.metrics : null;
  const awaiting = "run allocation";

  const items = [
    { key: "need", icon: TargetIcon, label: "Zones in need", value: zones.length ? damaged.length : null, unit: zones.length ? `/ ${zones.length}` : "", tone: "neutral" },
    { key: "people", icon: UsersIcon, label: "People affected", value: zones.length ? damaged.reduce((s, z) => s + z.population, 0) : null, sub: "in damaged zones", tone: "neutral" },
    { key: "critical", icon: AlertIcon, label: "Critical zones", value: summary ? summary.Critical : null, tone: "critical" },
    { key: "depots", icon: DepotIcon, label: "Relief depots", value: allocation?.depots.length ?? null, sub: allocation ? `${allocation.zones.length} zones routed` : awaiting, tone: "violet" },
    { key: "coverage", icon: ShieldIcon, label: "Weighted coverage", value: m?.coverage_pct ?? null, format: pct, sub: g ? `greedy ${g.coverage_pct.toFixed(0)}%` : m ? "priority-weighted" : awaiting, tone: "gold" },
    { key: "response", icon: ClockIcon, label: "Avg response", value: m?.avg_response_time_min ?? null, format: minutes, unit: m ? "min" : "", sub: g ? `greedy ${g.avg_response_time_min.toFixed(1)} min` : m ? "road travel from depot" : awaiting, tone: "teal" },
    { key: "gini", icon: ScaleIcon, label: "Fairness (Gini)", value: m?.gini ?? null, format: two, sub: g ? `greedy ${g.gini.toFixed(2)} · lower = fairer` : m ? "lower = fairer" : awaiting, tone: "violet" },
  ];

  return (
    <motion.ul className={`kpis${stale ? " is-stale" : ""}`} variants={list} initial="hidden" animate="show" aria-label="Key figures">
      {items.map(({ key, icon: Icon, label, value, format, unit, sub, tone }) => (
        <motion.li key={key} className={`kpi kpi--${tone}`} variants={tile}>
          <span className="kpi-icon">
            <Icon size={17} />
          </span>
          <span className="kpi-body">
            <span className="kpi-label">{label}</span>
            <span className="kpi-value">
              <AnimatedNumber value={value} format={format ?? whole} />
              {unit && <small>{unit}</small>}
            </span>
            {sub && <span className="kpi-sub">{sub}</span>}
          </span>
        </motion.li>
      ))}
    </motion.ul>
  );
}
