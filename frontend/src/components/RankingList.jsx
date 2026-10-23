import { motion } from "framer-motion";
import LevelBadge from "./LevelBadge";
import { LEVEL_COLORS, clusterColor, formatScore } from "../constants";

// Zones ranked by priority; rows glide into their new order when the weights change.
export default function RankingList({ zones, result, selectedZoneId, onSelectZone }) {
  const plans = Object.fromEntries((result?.zones ?? []).map((z) => [z.id, z.engine]));
  const depotIndex = Object.fromEntries((result?.depots ?? []).map((d, i) => [d.id, i]));

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
            <motion.li key={z.id} layout="position" transition={{ type: "spring", stiffness: 520, damping: 42 }}>
              <button type="button" className={`rank-row${selected ? " is-selected" : ""}`} onClick={() => onSelectZone(z.id)} aria-pressed={selected}>
                <span className="rank-num">{z.rank}</span>
                <span className="rank-main">
                  <strong>{z.name}</strong>
                  <span className="rank-bar" aria-hidden="true">
                    <motion.span
                      initial={false}
                      animate={{ width: `${Math.min(z.priority_score, 1) * 100}%` }}
                      style={{ background: LEVEL_COLORS[z.priority_level].fill, boxShadow: `0 0 8px ${LEVEL_COLORS[z.priority_level].glow}` }}
                    />
                  </span>
                </span>
                <span className="rank-score">{formatScore(z.priority_score)}</span>
                {plan ? (
                  <span className="rank-cov" title={plan.coverage_pct == null ? "No relief needed" : `${plan.coverage_pct}% of needs covered`}>
                    <span className="rank-depot" style={{ background: clusterColor(depotIndex[plan.depot_id] ?? 0) }} aria-hidden="true" />
                    {plan.coverage_pct == null ? "—" : `${plan.coverage_pct.toFixed(0)}%`}
                  </span>
                ) : (
                  <LevelBadge level={z.priority_level} size="sm" />
                )}
              </button>
            </motion.li>
          );
        })}
      </ol>
    </section>
  );
}
