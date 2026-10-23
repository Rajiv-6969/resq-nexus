import { useMemo } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router";
import DamageGlyph from "../components/DamageGlyph";
import ScenarioPicker from "../components/ScenarioPicker";
import { ArrowRightIcon, BrainIcon } from "../components/icons";
import { SEVERITY_COLORS, SEVERITY_LABELS, accessLabel, disasterLabel, formatNumber, vulnerabilityLabel } from "../constants";
import { useAppData } from "../state/contexts";

const grid = { hidden: {}, show: { transition: { staggerChildren: 0.035 } } };
const card = { hidden: { opacity: 0, y: 14, scale: 0.98 }, show: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.4 } } };

export default function DamageAssessment() {
  const { scenarios, scenarioId, scenario, selectScenario, listState, detailError } = useAppData();

  const zones = useMemo(
    () => [...(scenario?.zones ?? [])].sort((a, b) => b.damage_severity - a.damage_severity || b.population - a.population),
    [scenario],
  );
  const bySeverity = [3, 2, 1, 0].map((s) => {
    const list = zones.filter((z) => z.damage_severity === s);
    return { severity: s, count: list.length, people: list.reduce((sum, z) => sum + z.population, 0) };
  });

  return (
    <div className="damage">
      <header className="page-head">
        <div>
          <p className="kicker">Assess</p>
          <h1 className="page-title">Damage Assessment</h1>
          <p className="page-sub">
            Damage severity for every zone{scenario ? ` in the ${disasterLabel(scenario.disaster_type).toLowerCase()} scenario (${scenario.region}, ${scenario.state})` : ""}.
          </p>
        </div>
        <div className="page-head-tools">
          <ScenarioPicker scenarios={scenarios} scenarioId={scenarioId} onSelect={selectScenario} failed={listState.status === "error"} layoutGroup="damage-picker" />
        </div>
      </header>

      <motion.div className="ai-banner" role="status" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}>
        <span className="ai-banner-icon">
          <BrainIcon size={22} />
        </span>
        <div>
          <strong>AI damage model integration in progress</strong>
          <p>
            Severity levels currently come from the scenario data. An AI damage-assessment model will feed this stage in a later
            release; until then the values below are synthetic.
          </p>
        </div>
        <span className="ai-banner-tag">In progress</span>
      </motion.div>

      {(listState.error || detailError) && <p className="notice notice--warn">{listState.error || detailError}</p>}

      <section className="severity-summary" aria-label="Zones by damage severity">
        {bySeverity.map(({ severity, count, people }) => (
          <div key={severity} className="severity-tile" style={{ "--accent": SEVERITY_COLORS[severity] }}>
            <span className="severity-name">{SEVERITY_LABELS[severity]}</span>
            <span className="severity-count">{scenario ? count : "—"}</span>
            <span className="severity-people">{scenario ? `${formatNumber(people)} people` : ""}</span>
            <span className="severity-meter" aria-hidden="true">
              {[1, 2, 3].map((i) => (
                <span key={i} className={i <= severity ? "on" : ""} />
              ))}
            </span>
          </div>
        ))}
      </section>

      <motion.ul className="damage-grid" variants={grid} initial="hidden" animate={scenario ? "show" : "hidden"} key={scenarioId ?? "none"}>
        {zones.map((z) => (
          <motion.li key={z.id} className={`damage-card damage-card--s${z.damage_severity}`} variants={card} style={{ "--accent": SEVERITY_COLORS[z.damage_severity] }}>
            <DamageGlyph type={z.disaster_type} severity={z.damage_severity} />
            <div className="damage-body">
              <h3>{z.name}</h3>
              <p className="damage-severity">
                <span className="severity-dot" aria-hidden="true" />
                {SEVERITY_LABELS[z.damage_severity]} <span className="muted">({z.damage_severity}/3)</span>
              </p>
              <span className="severity-meter" aria-hidden="true">
                {[1, 2, 3].map((i) => (
                  <span key={i} className={i <= z.damage_severity ? "on" : ""} />
                ))}
              </span>
              <dl>
                <div>
                  <dt>People</dt>
                  <dd>{formatNumber(z.population)}</dd>
                </div>
                <div>
                  <dt>Vulnerability</dt>
                  <dd>{vulnerabilityLabel(z.vulnerability_index)}</dd>
                </div>
                <div>
                  <dt>Access</dt>
                  <dd>{accessLabel(z.accessibility)}</dd>
                </div>
              </dl>
              <Link className="damage-link" to={`/command?scenario=${encodeURIComponent(scenarioId)}&zone=${encodeURIComponent(z.id)}`}>
                View on map <ArrowRightIcon size={13} />
              </Link>
            </div>
          </motion.li>
        ))}
      </motion.ul>
      {!scenario && !listState.error && <div className="page-loader">Loading scenario…</div>}
    </div>
  );
}
