import { motion } from "framer-motion";
import { Wipe } from "../components/Reveal";
import ScenarioPicker from "../components/ScenarioPicker";
import PipelineStepper from "../components/PipelineStepper";
import {
  DepotDistributionChart,
  FairnessChart,
  FitnessChart,
  MetricCard,
  ZoneCoverageChart,
  ZoneDistributionChart,
} from "../components/charts";
import { AlertIcon, AsteriskMark, ClockIcon, CpuIcon, ScaleIcon, ShieldIcon, TargetIcon, UsersIcon } from "../components/icons";
import { RESOURCE_ICONS } from "../components/iconMaps";
import { RESOURCES, disasterLabel, formatNumber } from "../constants";
import { stepperStates } from "../lib/pipeline";
import { useAppData } from "../state/contexts";

const one = (v) => v.toFixed(1);
const zero = (v) => v.toFixed(0);
const two = (v) => v.toFixed(2);

function ChartPanel({ title, sub, wide, children, delay = 0 }) {
  return (
    <motion.section
      className={`chart-panel${wide ? " chart-panel--wide" : ""}`}
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.15 }}
      transition={{ duration: 0.3, ease: [0.7, 0, 0.2, 1], delay }}
    >
      <header>
        <h2 className="panel-title">{title}</h2>
        {sub && <p className="panel-sub">{sub}</p>}
      </header>
      {children}
    </motion.section>
  );
}

function EmptyState({ onRun, canRun, running, states, scenario }) {
  return (
    <motion.div className="empty-state" initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25, ease: [0.7, 0, 0.2, 1] }}>
      <p className="label">No plan</p>
      <h2 className="empty-title">No allocation yet{scenario ? ` for the ${disasterLabel(scenario.disaster_type).toLowerCase()} scenario` : ""}</h2>
      <p>
        Run the pipeline to compare the Allocation Engine with the greedy baseline on response time, coverage, unmet demand,
        fairness and computation time.
      </p>
      <PipelineStepper states={states} />
      <button type="button" className="btn btn--solid btn--lg" onClick={onRun} disabled={!canRun}>
        {running ? "Running" : "Run allocation"}
        {running ? <AsteriskMark size={16} className="asterisk loader" /> : <span className="arrow">&rarr;</span>}
      </button>
    </motion.div>
  );
}

export default function Analytics() {
  const { scenarios, scenarioId, scenario, selectScenario, listState, ranking, run, runStale, pipeline, runPipeline } = useAppData();
  const result = run?.result;
  const running = pipeline.status === "running";
  const canRun = Boolean(ranking) && !running;
  const states = stepperStates(pipeline, { ready: Boolean(ranking), run, stale: runStale });
  const e = result?.engine.metrics;
  const g = result?.greedy.metrics;
  const ga = result?.settings.ga;
  const totalGenerations = result?.passes.reduce((s, p) => s + p.generations, 0);

  return (
    <div className="analytics">
      <section className="sec sec--black page-hero" aria-labelledby="analytics-title">
        <p className="sec-bar mono">
          <span>(04) Analytics</span>
          <span>Allocation Engine vs greedy baseline</span>
        </p>
        <div className="page-hero-row">
          <Wipe as="h1" id="analytics-title" className="page-title">
            Analytics
          </Wipe>
          <p className="page-sub">
            Same stock, same depots, same roads. The greedy baseline serves the highest-priority zone first from its nearest
            depot until the stock runs out.
          </p>
        </div>
      </section>
      <div className="toolbar">
        <p className="toolbar-label mono">01 / Scenario</p>
        <ScenarioPicker scenarios={scenarios} scenarioId={scenarioId} onSelect={selectScenario} failed={listState.status === "error"} />
        {result && (
          <button type="button" className={`btn btn--sm${runStale ? " btn--red" : ""} toolbar-action`} onClick={runPipeline} disabled={!canRun}>
            {running ? "Running" : runStale ? "Re-run (weights changed)" : "Re-run"}
          </button>
        )}
      </div>

      {!result ? (
        <EmptyState onRun={runPipeline} canRun={canRun} running={running} states={states} scenario={scenario} />
      ) : (
        <>
          {runStale && (
            <p className="notice notice--warn" role="status">
              The priority weights changed after this plan was made; these charts show the previous weights until you re-run.
            </p>
          )}
          <section className="metric-grid" aria-label="Metric comparison">
            <MetricCard index={0} title="Avg response time" icon={ClockIcon} engine={e.avg_response_time_min} greedy={g.avg_response_time_min} format={one} unit=" min" lowerIsBetter
              help="Road travel time from each zone's depot, averaged over the relief delivered." />
            <MetricCard index={1} title="Priority-weighted coverage" icon={ShieldIcon} engine={e.coverage_pct} greedy={g.coverage_pct} format={one} unit="%"
              help="Each zone's coverage %, weighted by its priority score." />
            <MetricCard index={2} title="Priority-weighted demand met" icon={TargetIcon} engine={e.demand_met_pct} greedy={g.demand_met_pct} format={one} unit="%"
              help="Share of all demand units met, weighted by zone priority. Greedy maximises this by design." />
            <MetricCard index={3} title="Total unmet demand" icon={AlertIcon} engine={e.unmet_demand_pct} greedy={g.unmet_demand_pct} format={one} unit="%" lowerIsBetter
              help="Demand left unmet, averaged over the five resource types. Both hand out all of the stock." />
            <MetricCard index={4} title="Fairness (Gini)" icon={ScaleIcon} engine={e.gini} greedy={g.gini} format={two} lowerIsBetter
              help="Inequality of coverage across zones in need: 0 means every zone is covered equally." />
            <MetricCard index={5} title="Zones reached" icon={UsersIcon} engine={e.zones_served} greedy={g.zones_served} format={zero} unit={` / ${e.zones_in_need}`} deltaUnit=" zones"
              help="Zones in need that receive at least some relief." />
            <MetricCard index={6} title="Computation time" icon={CpuIcon} engine={e.computation_ms} greedy={g.computation_ms} format={zero} unit=" ms" lowerIsBetter
              help="Wall-clock time to produce the plan on this machine." />
            <motion.article className="metric-card unmet-card" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25, ease: [0.7, 0, 0.2, 1], delay: 0.28 }}>
              <header>
                <span className="metric-icon">
                  <AlertIcon size={17} />
                </span>
                <h3>Unmet demand by resource</h3>
              </header>
              <table className="unmet-table">
                <thead>
                  <tr>
                    <th scope="col">Resource</th>
                    <th scope="col">Engine</th>
                    <th scope="col">Greedy</th>
                  </tr>
                </thead>
                <tbody>
                  {RESOURCES.map((r) => {
                    const Icon = RESOURCE_ICONS[r.key];
                    return (
                      <tr key={r.key}>
                        <th scope="row">
                          <Icon size={14} /> {r.label}
                        </th>
                        <td>{formatNumber(e.unmet_demand[r.key])}</td>
                        <td>{formatNumber(g.unmet_demand[r.key])}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <p className="metric-help">Units still needed after all stock is handed out.</p>
            </motion.article>
          </section>

          <div className="chart-grid">
            <ChartPanel
              wide
              title="GA fitness over generations"
              sub={`Population ${ga.population} · ${totalGenerations} generations over ${result.passes.length} pass${result.passes.length === 1 ? "" : "es"} · seed ${result.seed}. Elitism keeps the best plan, so the best line never drops within a pass.`}
            >
              <FitnessChart history={result.fitness_history} passes={result.passes} selectedPass={result.selected_pass} />
            </ChartPanel>
            <ChartPanel title="Coverage fairness" sub="Lorenz curve of zone coverage. The closer to the diagonal, the more evenly coverage is shared.">
              <FairnessChart result={result} />
            </ChartPanel>
            <ChartPanel title="Coverage by zone" sub="Zones in need, highest priority first.">
              <ZoneCoverageChart result={result} />
            </ChartPanel>
            <ChartPanel wide title="Resource distribution per zone" sub="Each bar is the zone's share of all relief stock, with the five resource types counted equally. Hover for unit counts.">
              <ZoneDistributionChart result={result} />
            </ChartPanel>
            <ChartPanel wide title="Resource distribution per depot" sub="How each resource's stock is split between the relief depots in the Allocation Engine plan.">
              <DepotDistributionChart result={result} />
            </ChartPanel>
          </div>
          <p className="analytics-note mono">Synthetic demo data: zones are real OpenStreetMap places; damage, needs and stock are generated.</p>
        </>
      )}
    </div>
  );
}
