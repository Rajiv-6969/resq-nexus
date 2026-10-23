import { motion } from "framer-motion";
import LevelBadge from "./LevelBadge";
import { LEVEL_COLORS, formatScore } from "../constants";

const HARD = [0.7, 0, 0.2, 1];

// Zones ranked by priority; rows slide straight into their new order when the weights change.
export default function RankingList({ zones, result, selectedZoneId, onSelectZone }) {
  const plans = Object.fromEntries((result?.zones ?? []).map((z) => [z.id, z.engine]));
  const depotLabels = Object.fromEntries((result?.depots ?? []).map((d) => [d.id, d.label]));

  return (
    <section className="ranking" aria-label="Zones ranked by priority">
      <header className="ranking-head">
        <span>#</span>
        <span>Zone</span>
        <span>Score</span>
        <span>{result ? "Covered" : "Level"}</span>
      </header>
      <ol className="rank-list">
        {zones.map((z) => {
          const plan = plans[z.id];
          const selected = z.id === selectedZoneId;
          return (
            <motion.li key={z.id} layout="position" transition={{ duration: 0.25, ease: HARD }}>
              <button type="button" className={`rank-row${selected ? " is-selected" : ""}`} onClick={() => onSelectZone(z.id)} aria-pressed={selected}>
                <span className="rank-num">{String(z.rank).padStart(2, "0")}</span>
                <span className="rank-main">
                  <strong>{z.name}</strong>
                  <span className="rank-bar" aria-hidden="true">
                    <motion.span
                      initial={false}
                      animate={{ width: `${Math.min(z.priority_score, 1) * 100}%` }}
                      transition={{ duration: 0.3, ease: HARD }}
                      style={{ background: LEVEL_COLORS[z.priority_level].fill }}
                    />
                  </span>
                </span>
                <span className="rank-score">{formatScore(z.priority_score)}</span>
                {plan ? (
                  <span className="rank-cov" title={plan.coverage_pct == null ? "No relief needed" : `${plan.coverage_pct}% of needs covered`}>
                    <span className="rank-depot" aria-hidden="true">
                      {depotLabels[plan.depot_id]}
                    </span>
                    {plan.coverage_pct == null ? "—" : `${plan.coverage_pct.toFixed(0)}%`}
                  </span>
                ) : (
                  <LevelBadge level={z.priority_level} />
                )}
              </button>
            </motion.li>
          );
        })}
      </ol>
    </section>
  );
}
