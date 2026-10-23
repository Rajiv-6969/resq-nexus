import { AnimatePresence, motion } from "framer-motion";
import { SHOW_ANALYTICS } from "../config";
import AnimatedNumber from "./AnimatedNumber";
import CoverageRing from "./CoverageRing";
import LevelBadge from "./LevelBadge";
import { BrainIcon, ClockIcon, CloseIcon, DepotIcon, InfoIcon, PlayIcon, RouteIcon, SparkIcon } from "./icons";
import { DISASTER_ICONS, RESOURCE_ICONS } from "./iconMaps";
import {
  BREAKDOWN,
  LEVEL_COLORS,
  RESOURCES,
  SEVERITY_LABELS,
  accessLabel,
  clusterColor,
  disasterLabel,
  formatNumber,
  formatScore,
  levelClass,
  vulnerabilityLabel,
} from "../constants";

const reveal = { initial: { opacity: 0, y: 8 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.35 } };

function levelRule(level, levels) {
  if (level === "Low") return `Score below ${levels.Medium.toFixed(2)}`;
  return `Score ≥ ${levels[level].toFixed(2)}`;
}

function ScenarioBrief({ scenario, zones, onSelectZone, hasRun, onRun, canRun }) {
  if (!scenario) return <div className="intel-empty">Loading scenario…</div>;
  const Icon = DISASTER_ICONS[scenario.disaster_type];
  const top = zones.slice(0, 4);
  return (
    <motion.div className="brief" {...reveal}>
      <p className="kicker">
        {Icon && <Icon size={14} />} {disasterLabel(scenario.disaster_type)} · {scenario.region}, {scenario.state}
      </p>
      <h2 className="brief-title">{scenario.name}</h2>
      {scenario.description && <p className="brief-text">{scenario.description}</p>}
      <h3 className="subhead">Most urgent zones</h3>
      <ul className="brief-top">
        {top.map((z) => (
          <li key={z.id}>
            <button type="button" onClick={() => onSelectZone(z.id)}>
              <span className="brief-rank">#{z.rank}</span>
              <span className="brief-name">{z.name}</span>
              <LevelBadge level={z.priority_level} size="sm" />
            </button>
          </li>
        ))}
      </ul>
      {!hasRun && (
        <button type="button" className="btn btn-primary btn-block" onClick={onRun} disabled={!canRun}>
          <PlayIcon size={14} /> Run allocation
        </button>
      )}
      <p className="hint">Select any zone on the map or in the ranking for its full intel.</p>
      <p className="data-note">
        <InfoIcon size={15} />
        <span>{scenario.data_note}</span>
      </p>
    </motion.div>
  );
}

function AllocationBlock({ zone, plan, depot, depotColor, stale, hasRun, onRun, canRun, demand }) {
  if (!hasRun) {
    return (
      <div className="intel-cta">
        <p>Run the Allocation Engine to see this zone&apos;s resources, depot, route and travel time.</p>
        <button type="button" className="btn btn-primary btn-sm" onClick={onRun} disabled={!canRun}>
          <PlayIcon size={13} /> Run allocation
        </button>
      </div>
    );
  }
  if (!plan) return null;
  const noNeed = zone.damage_severity === 0 || plan.coverage_pct == null;
  return (
    <motion.section className={`intel-alloc${stale ? " is-stale" : ""}`} {...reveal}>
      <h3 className="subhead">Allocation {stale && <span className="stale-tag">previous weights</span>}</h3>
      <div className="alloc-head">
        <CoverageRing value={noNeed ? 100 : plan.coverage_pct} label={noNeed ? "no need" : "covered"} color={noNeed ? "#52B788" : "#FFD166"} />
        <dl className="alloc-facts">
          <div>
            <dt>
              <DepotIcon size={14} /> Depot
            </dt>
            <dd>
              <span className="depot-chip" style={{ "--c": depotColor }}>
                {depot?.label}
              </span>
              {depot?.name}
            </dd>
          </div>
          <div>
            <dt>
              <ClockIcon size={14} /> Travel time
            </dt>
            <dd>
              <AnimatedNumber value={plan.travel_time_min} format={(v) => v.toFixed(0)} /> min
            </dd>
          </div>
          <div>
            <dt>
              <RouteIcon size={14} /> Road distance
            </dt>
            <dd>
              {plan.distance_km.toFixed(1)} km · {Math.max(plan.route.length - 1, 0)} leg{plan.route.length === 2 ? "" : "s"}
            </dd>
          </div>
        </dl>
      </div>
      {noNeed ? (
        <p className="footnote">No damage reported, so this zone needs no relief and its share goes to damaged zones.</p>
      ) : (
        <ul className="alloc-resources">
          {RESOURCES.map((r) => {
            const Icon = RESOURCE_ICONS[r.key];
            const need = demand[r.key];
            const got = plan.allocated[r.key];
            const share = need > 0 ? Math.min(got / need, 1) : 0;
            return (
              <li key={r.key} className={need === 0 ? "is-none" : ""}>
                <span className="res-label">
                  <Icon size={15} /> {r.label}
                </span>
                <span className="res-bar" aria-hidden="true">
                  <motion.span initial={{ width: 0 }} animate={{ width: `${share * 100}%` }} transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }} style={{ background: r.color }} />
                </span>
                <span className="res-value">
                  {need === 0 ? "not needed" : `${formatNumber(got)} / ${formatNumber(need)}`}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </motion.section>
  );
}

function ExplanationBlock({ zone, run }) {
  const explanation = run?.explanations?.explanations.find((e) => e.zone_id === zone.id);
  if (!run) return null;
  return (
    <section className="intel-explain">
      <header>
        <h3 className="subhead">
          <BrainIcon size={15} /> Why this allocation
        </h3>
        {explanation && (
          <span className={`source-badge source-badge--${explanation.source}`}>
            <SparkIcon size={12} /> {explanation.source === "gemini" ? "Gemini" : "Template"}
          </span>
        )}
      </header>
      <AnimatePresence mode="wait">
        {explanation ? (
          <motion.p key={zone.id} className="explain-text" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            {explanation.text}
          </motion.p>
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

export default function ZoneIntel({ zone, zones, total, settings, scenario, run, stale, onClose, onSelectZone, onRun, canRun }) {
  if (!zone) {
    return <ScenarioBrief scenario={scenario} zones={zones} onSelectZone={onSelectZone} hasRun={Boolean(run)} onRun={onRun} canRun={canRun} />;
  }

  const result = run?.result;
  const resultZone = result?.zones.find((z) => z.id === zone.id);
  const plan = resultZone?.engine;
  const depotIndex = result ? result.depots.findIndex((d) => d.id === plan?.depot_id) : -1;
  const depot = depotIndex >= 0 ? result.depots[depotIndex] : null;
  const greedyCoverage = resultZone?.greedy.coverage_pct;
  const weights = settings.weights;
  const equity = zone.contributions.equity_adjustment;
  const color = LEVEL_COLORS[zone.priority_level];

  return (
    <motion.article key={zone.id} className={`intel intel--${levelClass(zone.priority_level)}`} {...reveal} aria-label={`Zone details: ${zone.name}`}>
      <header className="intel-head">
        <div>
          <p className="kicker">
            Rank #{zone.rank} of {total} · {zone.id}
          </p>
          <h2 className="intel-name">{zone.name}</h2>
          <p className="intel-coords">
            {zone.latitude.toFixed(3)}°N, {zone.longitude.toFixed(3)}°E
          </p>
        </div>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close zone details">
          <CloseIcon size={16} />
        </button>
      </header>

      <div className="intel-score">
        <span className="score-big" style={{ textShadow: `0 0 22px ${color.glow}` }}>
          <AnimatedNumber value={zone.priority_score} format={(v) => v.toFixed(3)} duration={0.8} />
        </span>
        <div className="score-side">
          <LevelBadge level={zone.priority_level} />
          <span className="score-rule">{levelRule(zone.priority_level, settings.levels)}</span>
        </div>
      </div>
      <div className="gauge" role="presentation">
        <motion.span
          className={levelClass(zone.priority_level)}
          initial={false}
          animate={{ width: `${Math.min(zone.priority_score, 1) * 100}%` }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
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
        depotColor={depotIndex >= 0 ? clusterColor(depotIndex) : undefined}
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

      <ExplanationBlock zone={zone} run={run} />

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
                  {row.label} <span className="muted">×{weight.toFixed(2)}</span>
                </span>
                <span className="breakdown-bar" aria-hidden="true">
                  <motion.span initial={false} animate={{ width: `${Math.max(0, Math.min(share, 1)) * 100}%` }} />
                </span>
                <span className="breakdown-value">+{value.toFixed(3)}</span>
              </li>
            );
          })}
          <li className={equity > 0 ? "equity on" : "equity"}>
            <span className="breakdown-label">Equity boost</span>
            <span className="breakdown-bar" aria-hidden="true">
              <motion.span initial={false} animate={{ width: `${(equity / settings.equity.max_boost) * 100}%` }} />
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
