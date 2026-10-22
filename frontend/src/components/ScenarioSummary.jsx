import { DISASTER_ICONS } from "./iconMaps";
import { DISASTER_LABELS, PRIORITY_LEVELS, formatNumber, levelClass } from "../constants";

export default function ScenarioSummary({ scenario, summary, failed }) {
  if (!scenario) {
    if (failed) return null;
    return (
      <section className="scenario-bar" aria-busy="true">
        <p className="muted">Loading scenario…</p>
      </section>
    );
  }

  const Icon = DISASTER_ICONS[scenario.disaster_type];
  const population = scenario.zones.reduce((sum, z) => sum + z.population, 0);
  const damaged = scenario.zones.filter((z) => z.damage_severity > 0).length;

  return (
    <section className="scenario-bar" aria-label="Scenario summary">
      <div className="scenario-heading">
        <span className={`disaster-chip ${scenario.disaster_type}`}>
          {Icon && <Icon size={16} />}
          {DISASTER_LABELS[scenario.disaster_type]}
        </span>
        <div className="scenario-text">
          <h1>{scenario.name}</h1>
          <p title={scenario.description}>
            {scenario.region}, {scenario.state} · {scenario.description}
          </p>
        </div>
      </div>

      <div className="kpis">
        <dl className="kpi-group">
          <div className="kpi">
            <dt>Zones</dt>
            <dd>{scenario.zones.length}</dd>
          </div>
          <div className="kpi">
            <dt>Population</dt>
            <dd>{formatNumber(population)}</dd>
          </div>
          <div className="kpi">
            <dt>Damaged zones</dt>
            <dd>{damaged}</dd>
          </div>
        </dl>
        {summary && (
          <dl className="kpi-group kpi-group--levels" aria-label="Zones per priority level">
            {PRIORITY_LEVELS.map((level) => (
              <div key={level} className={`kpi kpi-level ${levelClass(level)}`}>
                <dt>{level}</dt>
                <dd>{summary[level] ?? 0}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </section>
  );
}
