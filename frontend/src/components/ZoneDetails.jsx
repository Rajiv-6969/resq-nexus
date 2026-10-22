import { CloseIcon } from "./icons";
import LevelBadge from "./LevelBadge";
import {
  BREAKDOWN,
  DISASTER_LABELS,
  SEVERITY_LABELS,
  accessLabel,
  formatNumber,
  formatScore,
  levelClass,
  vulnerabilityLabel,
} from "../constants";

function levelRule(level, levels) {
  if (level === "Low") return `Score below ${levels.Medium.toFixed(2)}`;
  return `Score ≥ ${levels[level].toFixed(2)}`;
}

export default function ZoneDetails({ zone, total, settings, onClose, ref }) {
  if (!zone) {
    return (
      <section ref={ref} className="card zone-empty" aria-live="polite">
        <h2 className="card-title">Zone details</h2>
        <p>Select a zone on the map or in the ranking to see its details and priority score.</p>
      </section>
    );
  }

  const weights = settings.weights;
  const equity = zone.contributions.equity_adjustment;

  return (
    <section
      ref={ref}
      className={`card zone-card ${levelClass(zone.priority_level)}`}
      aria-live="polite"
      aria-label={`Zone details: ${zone.name}`}
    >
      <div className="zone-head">
        <div>
          <h2 className="zone-name">{zone.name}</h2>
          <p className="zone-sub">
            Rank #{zone.rank} of {total} · {zone.id} · {zone.latitude.toFixed(3)}°N, {zone.longitude.toFixed(3)}°E
          </p>
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close zone details">
          <CloseIcon size={16} />
        </button>
      </div>

      <div className="score-row">
        <span className="score-big">{formatScore(zone.priority_score)}</span>
        <LevelBadge level={zone.priority_level} />
        <span className="score-rule">{levelRule(zone.priority_level, settings.levels)}</span>
      </div>
      <div className="gauge" role="presentation">
        <span className={levelClass(zone.priority_level)} style={{ width: `${Math.min(zone.priority_score, 1) * 100}%` }} />
      </div>

      <dl className="facts">
        <div>
          <dt>Damage</dt>
          <dd>
            {SEVERITY_LABELS[zone.damage_severity]} <span className="muted">({zone.damage_severity}/3)</span>
          </dd>
        </div>
        <div>
          <dt>Population</dt>
          <dd>{formatNumber(zone.population)}</dd>
        </div>
        <div>
          <dt>Vulnerability</dt>
          <dd>
            {zone.vulnerability_index.toFixed(2)} <span className="muted">({vulnerabilityLabel(zone.vulnerability_index)})</span>
          </dd>
        </div>
        <div>
          <dt>Road access</dt>
          <dd>
            {zone.accessibility.toFixed(2)} <span className="muted">({accessLabel(zone.accessibility)})</span>
          </dd>
        </div>
        <div>
          <dt>Disaster</dt>
          <dd>{DISASTER_LABELS[zone.disaster_type] ?? zone.disaster_type}</dd>
        </div>
      </dl>

      <h3 className="subhead">Score breakdown</h3>
      <ul className="breakdown">
        {BREAKDOWN.map((row) => {
          const weight = weights[row.weight];
          const value = zone.contributions[row.key];
          const share = weight > 0 ? value / weight : 0; // the normalised factor, 0-1
          return (
            <li key={row.key}>
              <span className="breakdown-label">
                {row.label} <span className="muted">×{weight.toFixed(2)}</span>
              </span>
              <span className="breakdown-bar" aria-hidden="true">
                <span style={{ width: `${Math.max(0, Math.min(share, 1)) * 100}%` }} />
              </span>
              <span className="breakdown-value">+{value.toFixed(3)}</span>
            </li>
          );
        })}
        <li className={equity > 0 ? "equity on" : "equity"}>
          <span className="breakdown-label">Equity boost</span>
          <span className="breakdown-bar" aria-hidden="true">
            <span style={{ width: `${(equity / settings.equity.max_boost) * 100}%` }} />
          </span>
          <span className="breakdown-value">+{equity.toFixed(3)}</span>
        </li>
      </ul>
      <p className="footnote">
        {equity > 0
          ? "Remote zone: road access is below the equity threshold, so it gets a small boost to avoid being deprioritised."
          : `Equity boost applies to damaged zones with road access below ${settings.equity.accessibility_threshold.toFixed(2)}.`}
      </p>
    </section>
  );
}
