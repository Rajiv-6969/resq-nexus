import { LEVEL_COLORS, SEVERITY_LABELS, formatNumber, formatScore } from "../constants";
import LevelBadge from "./LevelBadge";

export default function PriorityList({ zones, selectedZoneId, onSelectZone }) {
  return (
    <section className="card">
      <h2 className="card-title">
        Priority ranking <span className="card-count">{zones.length} zones</span>
      </h2>
      <ol className="rank-list">
        {zones.map((zone) => (
          <li key={zone.id}>
            <button
              type="button"
              className="rank-item"
              aria-pressed={zone.id === selectedZoneId}
              onClick={() => onSelectZone(zone.id)}
            >
              <span className="rank-num">{zone.rank}</span>
              <span className="rank-main">
                <span className="rank-name">{zone.name}</span>
                <span className="rank-sub">
                  {SEVERITY_LABELS[zone.damage_severity]} · {formatNumber(zone.population)} people
                </span>
              </span>
              <span className="rank-score">
                <LevelBadge level={zone.priority_level} />
                <span className="rank-score-line">
                  <span className="score-bar" aria-hidden="true">
                    <span
                      style={{
                        width: `${Math.min(zone.priority_score, 1) * 100}%`,
                        background: LEVEL_COLORS[zone.priority_level].fill,
                      }}
                    />
                  </span>
                  <span className="score-num">{formatScore(zone.priority_score)}</span>
                </span>
              </span>
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}
