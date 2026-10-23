import { useMemo } from "react";
import { motion } from "framer-motion";
import { Link } from "react-router";
import AnimatedNumber from "../components/AnimatedNumber";
import DamageGlyph from "../components/DamageGlyph";
import Figure from "../components/Figure";
import { Wipe } from "../components/Reveal";
import ScenarioPicker from "../components/ScenarioPicker";
import { SEVERITY_LABELS, accessLabel, disasterLabel, formatNumber, vulnerabilityLabel } from "../constants";
import { PHOTOS } from "../lib/photos";
import { useAppData } from "../state/contexts";

const HARD = [0.7, 0, 0.2, 1];
const grid = { hidden: {}, show: { transition: { staggerChildren: 0.03 } } };
const card = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0, transition: { duration: 0.25, ease: HARD } } };
const pad2 = (n) => String(n).padStart(2, "0");

function SeverityMeter({ severity }) {
  return (
    <span className="severity-meter" aria-hidden="true">
      {[1, 2, 3].map((i) => (
        <span key={i} className={i <= severity ? "on" : ""} />
      ))}
    </span>
  );
}

export default function DamageAssessment() {
  const { scenarios, scenarioId, scenario, selectScenario, listState, detailError } = useAppData();

  const zones = useMemo(
    () => [...(scenario?.zones ?? [])].sort((a, b) => b.damage_severity - a.damage_severity || b.population - a.population),
    [scenario],
  );
  const people = zones.reduce((sum, z) => sum + z.population, 0);
  const bySeverity = [3, 2, 1, 0].map((s) => {
    const list = zones.filter((z) => z.damage_severity === s);
    return { severity: s, count: list.length, people: list.reduce((sum, z) => sum + z.population, 0) };
  });

  return (
    <div className="damage">
      <section className="sec sec--black page-hero" aria-labelledby="damage-title">
        <p className="sec-bar mono">
          <span>(02) Assess</span>
          <span>Stage 01 of 04</span>
        </p>
        <div className="page-hero-row">
          <Wipe as="h1" id="damage-title" className="page-title">
            Damage Assessment
          </Wipe>
          <p className="page-sub">
            Damage severity for every zone
            {scenario ? ` in the ${disasterLabel(scenario.disaster_type).toLowerCase()} scenario (${scenario.region}, ${scenario.state})` : ""}.
          </p>
        </div>
      </section>

      <Figure photo={PHOTOS["damage-collapsed-building"]} index="01" className="page-figure" eager />

      <div className="toolbar">
        <p className="toolbar-label mono">01 / Scenario</p>
        <ScenarioPicker scenarios={scenarios} scenarioId={scenarioId} onSelect={selectScenario} failed={listState.status === "error"} />
        <p className="toolbar-note mono">{scenario ? `${zones.length} zones / ${formatNumber(people)} people` : "Loading scenario"}</p>
      </div>

      <div className="ai-banner" role="status">
        <span className="ai-banner-tag mono">In progress</span>
        <div>
          <strong>AI damage model integration in progress</strong>
          <p>
            Severity levels currently come from the scenario data. An AI damage-assessment model will feed this stage in a later
            release; until then the values below are synthetic.
          </p>
        </div>
      </div>

      {(listState.error || detailError) && <p className="notice notice--warn">{listState.error || detailError}</p>}

      <section className="severity-summary" aria-label="Zones by damage severity">
        {bySeverity.map(({ severity, count, people: affected }) => (
          <div key={severity} className={`severity-tile severity-tile--s${severity}`}>
            <span className="severity-name">
              {pad2(severity)} / {SEVERITY_LABELS[severity]}
            </span>
            <span className="severity-count">
              <AnimatedNumber value={scenario ? count : null} />
            </span>
            <span className="severity-people">{scenario ? `${formatNumber(affected)} people` : ""}</span>
            <SeverityMeter severity={severity} />
          </div>
        ))}
      </section>

      <motion.ul className="damage-grid" variants={grid} initial="hidden" animate={scenario ? "show" : "hidden"} key={scenarioId ?? "none"}>
        {zones.map((z) => (
          <motion.li key={z.id} className={`damage-card damage-card--s${z.damage_severity}`} variants={card}>
            <div className="damage-top">
              <DamageGlyph type={z.disaster_type} severity={z.damage_severity} />
              <span className="damage-id">{z.id}</span>
            </div>
            <div className="damage-body">
              <h3>{z.name}</h3>
              <p className="damage-severity">
                <span className="severity-dot" aria-hidden="true" />
                {SEVERITY_LABELS[z.damage_severity]} <span className="muted">({z.damage_severity}/3)</span>
              </p>
              <SeverityMeter severity={z.damage_severity} />
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
            </div>
            <Link className="damage-link" to={`/command?scenario=${encodeURIComponent(scenarioId)}&zone=${encodeURIComponent(z.id)}`}>
              View on map <span className="arrow">&rarr;</span>
            </Link>
          </motion.li>
        ))}
      </motion.ul>
      {!scenario && !listState.error && <div className="page-loader">Loading scenario</div>}
    </div>
  );
}
