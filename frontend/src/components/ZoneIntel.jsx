import { AnimatePresence, motion } from "framer-motion";
import { SHOW_ANALYTICS } from "../config";
import AnimatedNumber from "./AnimatedNumber";
import CoverageMeter from "./CoverageMeter";
import LevelBadge from "./LevelBadge";
import { CloseIcon } from "./icons";
import {
  BREAKDOWN,
  RESOURCES,
  SEVERITY_LABELS,
  accessLabel,
  disasterLabel,
  formatNumber,
  formatScore,
  levelClass,
  vulnerabilityLabel,
} from "../constants";

const HARD = [0.7, 0, 0.2, 1];
const reveal = { initial: { opacity: 0, x: 16 }, animate: { opacity: 1, x: 0 }, transition: { duration: 0.2, ease: HARD } };
const pad2 = (n) => String(n).padStart(2, "0");

function levelRule(level, levels) {
  if (level === "Low") return `Score below ${levels.Medium.toFixed(2)}`;
  return `Score ≥ ${levels[level].toFixed(2)}`;
}

function ScenarioBrief({ scenario, zones, onSelectZone, hasRun, onRun, canRun }) {
  if (!scenario) return <div className="intel-empty">Loading scenario…</div>;
  const top = zones.slice(0, 4);
  return (
    <motion.div className="brief" {...reveal}>
      <p className="label">
        {disasterLabel(scenario.disaster_type)} / {scenario.region}, {scenario.state}
      </p>
      <h2 className="brief-title">{scenario.name}</h2>
      {scenario.description && <p className="brief-text">{scenario.description}</p>}
      <div>
        <h3 className="subhead">Most urgent zones</h3>
        <ul className="brief-top">
          {top.map((z) => (
            <li key={z.id}>
              <button type="button" onClick={() => onSelectZone(z.id)}>
                <span className="brief-rank">{pad2(z.rank)}</span>
                <span className="brief-name">{z.name}</span>
                <LevelBadge level={z.priority_level} />
              </button>
            </li>
          ))}
        </ul>
      </div>
      {!hasRun && (
        <button type="button" className="btn btn--solid btn--lg btn--block" onClick={onRun} disabled={!canRun}>
          Run allocation <span className="arrow">&rarr;</span>
        </button>
      )}
      <p className="hint">Select any zone on the map or in the ranking for its full intel.</p>
      <p className="data-note">
        <span className="label">Data</span>
        <span>{scenario.data_note}</span>
      </p>
    </motion.div>
  );
}

function AllocationBlock({ zone, plan, depot, stale, hasRun, onRun, canRun, demand }) {
  if (!hasRun) {
    return (
      <div className="intel-cta">
        <p>Run the Allocation Engine to see this zone&apos;s resources, depot, route and travel time.</p>
        <button type="button" className="btn btn--solid" onClick={onRun} disabled={!canRun}>
          Run allocation <span className="arrow">&rarr;</span>
        </button>
      </div>
    );
  }
  if (!plan) return null;
  const noNeed = zone.damage_severity === 0 || plan.coverage_pct == null;
  return (
    <motion.section className={`intel-alloc${stale ? " is-stale" : ""}`} {...reveal}>
      <h3 className="subhead">Allocation {stale && <span className="stale-tag">previous weights</span>}</h3>
      <CoverageMeter value={noNeed ? 100 : plan.coverage_pct} label={noNeed ? "no need" : "of needs covered"} muted={noNeed} />
      <dl className="alloc-facts">
        <div>
          <dt className="label">Depot</dt>
          <dd>
            <span className="depot-chip">{depot?.label}</span>
            <span>{depot?.name}</span>
          </dd>
        </div>
        <div>
          <dt className="label">Travel time</dt>
          <dd>
            <AnimatedNumber value={plan.travel_time_min} format={(v) => v.toFixed(0)} /> min
          </dd>
        </div>
        <div>
          <dt className="label">Road distance</dt>
          <dd>
            {plan.distance_km.toFixed(1)} km / {Math.max(plan.route.length - 1, 0)} leg{plan.route.length === 2 ? "" : "s"}
          </dd>
        </div>
      </dl>
      {noNeed ? (
        <p className="footnote">No damage reported, so this zone needs no relief and its share goes to damaged zones.</p>
      ) : (
        <ul className="alloc-resources">
          {RESOURCES.map((r) => {
            const need = demand[r.key];
            const got = plan.allocated[r.key];
            const share = need > 0 ? Math.min(got / need, 1) : 0;
            return (
              <li key={r.key} className={need === 0 ? "is-none" : ""}>
                <span className="res-label">{r.label}</span>
                <span className="res-bar" aria-hidden="true">
                  <motion.span initial={{ width: 0 }} animate={{ width: `${share * 100}%` }} transition={{ duration: 0.45, ease: HARD }} />
                </span>
                <span className="res-value">{need === 0 ? "not needed" : `${formatNumber(got)} / ${formatNumber(need)}`}</span>
              </li>
            );
          })}
        </ul>
      )}
    </motion.section>
  );
}

function ExplanationBlock({ zone, run, onExplainDeep }) {
  const explanation = run?.explanations?.explanations.find((e) => e.zone_id === zone.id);
  if (!run) return null;
  return (
    <section className="intel-explain">
      <header>
        <h3 className="subhead">Why this allocation</h3>
        {explanation && (
          <span className={`source-badge source-badge--${explanation.source}`}>{explanation.source === "gemini" ? "Gemini" : "Template"}</span>
        )}
      </header>
      <AnimatePresence mode="wait">
        {explanation ? (
          <div>
            <motion.p
              key={zone.id}
              className="explain-text"
              initial={{ clipPath: "inset(0% 100% 0% 0%)" }}
              animate={{ clipPath: "inset(0% 0% 0% 0%)" }}
              exit={{ opacity: 0, transition: { duration: 0.08 } }}
              transition={{ duration: 0.5, ease: HARD }}
            >
              {explanation.text}
            </motion.p>
            {onExplainDeep && (
              <button
                type="button"
                className="brutalist-btn btn--sm mono mt-2"
                onClick={() => onExplainDeep(zone.id)}
              >
                Explain in detail &rarr;
              </button>
            )}
          </div>
        ) : run.explainError ? (
          <p className="explain-text muted">Explanations could not be loaded: {run.explainError}</p>
        ) : (
          <div className="skeleton-lines" aria-label="Writing explanation">
            <span />
            <span />
            <span />
          </div>
        )}
      </AnimatePresence>
    </section>
  );
}

export default function ZoneIntel({ zone, zones, total, settings, scenario, run, stale, onClose, onSelectZone, onRun, canRun, onExplainDeep }) {
  if (!zone) {
    return <ScenarioBrief scenario={scenario} zones={zones} onSelectZone={onSelectZone} hasRun={Boolean(run)} onRun={onRun} canRun={canRun} />;
  }

  const result = run?.result;
  const resultZone = result?.zones.find((z) => z.id === zone.id);
  const plan = resultZone?.engine;
  const depot = result?.depots.find((d) => d.id === plan?.depot_id) ?? null;
  const greedyCoverage = resultZone?.greedy.coverage_pct;
  const weights = settings.weights;
  const equity = zone.contributions.equity_adjustment;

  return (
    <motion.article key={zone.id} className={`intel intel--${levelClass(zone.priority_level)}`} {...reveal} aria-label={`Zone details: ${zone.name}`}>
      <header className="intel-head">
        <div>
          <p className="label">
            Rank {pad2(zone.rank)} / {pad2(total)} &middot; {zone.id}
          </p>
          <h2 className="intel-name">{zone.name}</h2>
          <p className="intel-coords">
            {zone.latitude.toFixed(3)}&deg; N &nbsp;{zone.longitude.toFixed(3)}&deg; E
          </p>
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close zone details">
          <CloseIcon size={16} />
        </button>
      </header>

      <div className="intel-score">
        <span className="score-big">
          <AnimatedNumber value={zone.priority_score} format={(v) => v.toFixed(3)} duration={0.6} />
        </span>
        <div className="score-side">
          <LevelBadge level={zone.priority_level} size="lg" />
          <span className="score-rule">{levelRule(zone.priority_level, settings.levels)}</span>
        </div>
      </div>
      <div className="gauge" role="presentation">
        <motion.span
          className={levelClass(zone.priority_level)}
          initial={false}
          animate={{ width: `${Math.min(zone.priority_score, 1) * 100}%` }}
          transition={{ duration: 0.4, ease: HARD }}
        />
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
      </dl>

      <AllocationBlock
        zone={zone}
        plan={plan}
        depot={depot}
        stale={stale}
        hasRun={Boolean(run)}
        onRun={onRun}
        canRun={canRun}
        demand={resultZone?.demand ?? {}}
      />
      {SHOW_ANALYTICS && plan && greedyCoverage != null && plan.coverage_pct != null && (
        <p className="compare-chip">
          Greedy baseline would cover <strong>{greedyCoverage.toFixed(0)}%</strong> of this zone&apos;s needs
          {greedyCoverage === 0 ? ": nothing at all." : "."}
        </p>
      )}

      <ExplanationBlock zone={zone} run={run} onExplainDeep={onExplainDeep} />

      <section className="intel-breakdown">
        <h3 className="subhead">Score breakdown</h3>
        <ul className="breakdown">
          {BREAKDOWN.map((row) => {
            const weight = weights[row.weight];
            const value = zone.contributions[row.key];
            const share = weight > 0 ? value / weight : 0;
            return (
              <li key={row.key}>
                <span className="breakdown-label">
                  {row.label} <span className="muted">&times;{weight.toFixed(2)}</span>
                </span>
                <span className="breakdown-bar" aria-hidden="true">
                  <motion.span initial={false} animate={{ width: `${Math.max(0, Math.min(share, 1)) * 100}%` }} transition={{ duration: 0.35, ease: HARD }} />
                </span>
                <span className="breakdown-value">+{value.toFixed(3)}</span>
              </li>
            );
          })}
          <li className={equity > 0 ? "equity on" : "equity"}>
            <span className="breakdown-label">Equity boost</span>
            <span className="breakdown-bar" aria-hidden="true">
              <motion.span initial={false} animate={{ width: `${(equity / settings.equity.max_boost) * 100}%` }} transition={{ duration: 0.35, ease: HARD }} />
            </span>
            <span className="breakdown-value">+{equity.toFixed(3)}</span>
          </li>
        </ul>
        <p className="footnote">
          {equity > 0
            ? "Remote zone: road access is below the equity threshold, so it gets a small boost to avoid being deprioritised."
            : `Equity boost applies to damaged zones with road access below ${settings.equity.accessibility_threshold.toFixed(2)}.`}{" "}
          Total {formatScore(zone.priority_score)}.
        </p>
      </section>
    </motion.article>
  );
}
