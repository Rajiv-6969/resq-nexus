import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useSearchParams } from "react-router";
import CommandMap from "../components/CommandMap";
import ErrorBanner from "../components/ErrorBanner";
import KpiRibbon from "../components/KpiRibbon";
import PipelineStepper from "../components/PipelineStepper";
import RankingList from "../components/RankingList";
import ScenarioPicker from "../components/ScenarioPicker";
import StockSummary from "../components/StockSummary";
import WeightControls from "../components/WeightControls";
import ZoneIntel from "../components/ZoneIntel";
import { ListIcon, PlayIcon, RefreshIcon, SlidersIcon, TargetIcon } from "../components/icons";
import { stepperStates } from "../lib/pipeline";
import { useAppData } from "../state/contexts";

const NO_ZONES = [];
const TABS = [
  { key: "zone", label: "Zone intel", icon: TargetIcon },
  { key: "ranking", label: "Ranking", icon: ListIcon },
  { key: "controls", label: "Controls", icon: SlidersIcon },
];

function RunButton({ running, hasRun, stale, disabled, onRun }) {
  const label = running ? "Engine running…" : stale ? "Re-run allocation" : hasRun ? "Run again" : "Run Allocation";
  return (
    <motion.button
      type="button"
      className={`run-button${running ? " is-running" : ""}${stale ? " is-stale" : ""}`}
      onClick={onRun}
      disabled={disabled}
      whileHover={disabled ? undefined : { scale: 1.03 }}
      whileTap={disabled ? undefined : { scale: 0.97 }}
    >
      <span className="run-glow" aria-hidden="true" />
      {running ? <span className="spinner spinner--sm" aria-hidden="true" /> : hasRun ? <RefreshIcon size={16} /> : <PlayIcon size={16} />}
      <span>{label}</span>
    </motion.button>
  );
}

export default function CommandCentre() {
  const {
    scenarios,
    listState,
    scenarioId,
    scenario,
    detailError,
    selectScenario,
    ranking,
    rankingSettled,
    rankingError,
    weights,
    setWeight,
    resetWeights,
    run,
    runStale,
    pipeline,
    runPipeline,
    retry,
  } = useAppData();
  const [searchParams, setSearchParams] = useSearchParams();
  const [tab, setTab] = useState("zone");
  const [layers, setLayers] = useState({ routes: true, clusters: true, roads: true, hazard: true });
  const sideBodyRef = useRef(null);

  const zones = ranking?.zones ?? NO_ZONES;
  const selectedZoneId = searchParams.get("zone");
  const selectedZone = zones.find((z) => z.id === selectedZoneId) ?? null;
  const running = pipeline.status === "running";
  const error = listState.error || detailError || rankingError;
  const states = stepperStates(pipeline, { ready: Boolean(ranking), run, stale: runStale });
  const allocation = run?.result ?? null;

  const setSelectedZone = useCallback(
    (id) =>
      setSearchParams(
        (params) => {
          const next = new URLSearchParams(params);
          if (id) next.set("zone", id);
          else next.delete("zone");
          return next;
        },
        { replace: true },
      ),
    [setSearchParams],
  );
  const selectZone = useCallback(
    (id) => {
      setSelectedZone(id);
      setTab("zone");
    },
    [setSelectedZone],
  );

  // Escape closes the selected zone.
  useEffect(() => {
    if (!selectedZoneId) return undefined;
    const onKey = (e) => e.key === "Escape" && setSelectedZone(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedZoneId, setSelectedZone]);

  // A new tab or zone starts at the top of the side panel.
  useEffect(() => {
    if (sideBodyRef.current) sideBodyRef.current.scrollTop = 0;
  }, [tab, selectedZoneId]);

  const toggleLayer = useCallback((key) => setLayers((l) => ({ ...l, [key]: !l[key] })), []);
  const canRun = Boolean(ranking) && !running;
  const summary = useMemo(() => ranking?.summary ?? null, [ranking]);

  return (
    <div className="cc">
      <section className="cc-bar glass" aria-label="Scenario and pipeline">
        <ScenarioPicker scenarios={scenarios} scenarioId={scenarioId} onSelect={selectScenario} failed={listState.status === "error"} />
        <PipelineStepper states={states} />
        <RunButton running={running} hasRun={Boolean(run)} stale={runStale} disabled={!canRun} onRun={runPipeline} />
      </section>

      {error && <ErrorBanner message={error} onRetry={retry} />}

      <KpiRibbon zones={zones} summary={summary} allocation={allocation} stale={runStale} />

      <section className="cc-main">
        <div className="cc-map glass">
          <CommandMap
            scenarioId={scenarioId}
            zones={zones}
            hazard={scenario?.hazard}
            allocation={allocation}
            stale={runStale}
            selectedZoneId={selectedZoneId}
            onSelectZone={selectZone}
            layers={layers}
            onToggleLayer={toggleLayer}
            loading={!ranking && !error}
            pipeline={pipeline}
          />
        </div>

        <aside className="cc-side glass" aria-label="Zone intel, ranking and controls">
          <div className="tabs" role="tablist" aria-label="Side panel">
            {TABS.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                type="button"
                role="tab"
                id={`tab-${key}`}
                aria-selected={tab === key}
                aria-controls="side-panel-body"
                className={`tab${tab === key ? " is-active" : ""}`}
                onClick={() => setTab(key)}
              >
                <Icon size={15} />
                <span>{label}</span>
                {tab === key && <motion.span layoutId="tab-active" className="tab-active" transition={{ type: "spring", stiffness: 460, damping: 36 }} />}
              </button>
            ))}
          </div>
          <div className="cc-side-body" id="side-panel-body" role="tabpanel" aria-labelledby={`tab-${tab}`} ref={sideBodyRef}>
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={tab}
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -12 }}
                transition={{ duration: 0.2 }}
              >
                {!ranking ? (
                  <div className="intel-empty">{error ? "No scenario loaded." : "Loading scenario…"}</div>
                ) : tab === "zone" ? (
                  <ZoneIntel
                    zone={selectedZone}
                    zones={zones}
                    total={zones.length}
                    settings={ranking.settings}
                    scenario={scenario}
                    run={run}
                    stale={runStale}
                    onClose={() => setSelectedZone(null)}
                    onSelectZone={selectZone}
                    onRun={runPipeline}
                    canRun={canRun}
                  />
                ) : tab === "ranking" ? (
                  <RankingList zones={zones} result={allocation} selectedZoneId={selectedZoneId} onSelectZone={selectZone} />
                ) : (
                  <>
                    <WeightControls weights={weights} onChange={setWeight} onReset={resetWeights} settled={rankingSettled} hasRun={Boolean(run)} />
                    {scenario && <StockSummary resources={scenario.resources} result={allocation} />}
                  </>
                )}
              </motion.div>
            </AnimatePresence>
          </div>
        </aside>
      </section>
    </div>
  );
}
