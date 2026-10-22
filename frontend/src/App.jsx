import { useEffect, useRef, useState } from "react";
import { API_BASE_URL, fetchPriority, fetchScenario, fetchScenarios } from "./api";
import AllocationPanel from "./components/AllocationPanel";
import PriorityList from "./components/PriorityList";
import ResourceSummary from "./components/ResourceSummary";
import ScenarioSummary from "./components/ScenarioSummary";
import TopBar from "./components/TopBar";
import ZoneDetails from "./components/ZoneDetails";
import ZoneMap from "./components/ZoneMap";
import { AlertIcon, InfoIcon } from "./components/icons";

const NO_ZONES = [];

const scenarioFromUrl = () => new URLSearchParams(window.location.search).get("scenario");

export default function App() {
  const [scenarios, setScenarios] = useState([]);
  const [scenarioId, setScenarioId] = useState(scenarioFromUrl);
  const [data, setData] = useState(null); // { scenario, ranking } of the loaded scenario
  const [selectedZoneId, setSelectedZoneId] = useState(null);
  const [allocationRequested, setAllocationRequested] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [attempt, setAttempt] = useState(0); // bump to retry after an error
  const detailsRef = useRef(null);

  // Scenario list for the dropdown.
  useEffect(() => {
    const controller = new AbortController();
    fetchScenarios({ signal: controller.signal })
      .then((list) => {
        setScenarios(list);
        setScenarioId((current) => (list.some((s) => s.id === current) ? current : (list[0]?.id ?? null)));
        if (list.length === 0) {
          setError("No scenarios found in backend/data/scenarios.");
          setLoading(false);
        }
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
        setError(err.message);
        setLoading(false);
      });
    return () => controller.abort();
  }, [attempt]);

  // Selected scenario and its priority ranking.
  useEffect(() => {
    if (!scenarioId) return;
    const controller = new AbortController();
    const options = { signal: controller.signal };
    setLoading(true);
    setError(null);
    Promise.all([fetchScenario(scenarioId, options), fetchPriority(scenarioId, options)])
      .then(([scenario, ranking]) => {
        setData({ scenario, ranking });
        setSelectedZoneId(null);
        setAllocationRequested(false);
        setLoading(false);
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
        setError(err.message);
        setLoading(false);
      });
    return () => controller.abort();
  }, [scenarioId, attempt]);

  // Keep ?scenario=<id> in the address bar so a refresh or shared link opens the same scenario.
  useEffect(() => {
    if (!scenarioId) return;
    const url = new URL(window.location.href);
    url.searchParams.set("scenario", scenarioId);
    window.history.replaceState(null, "", url);
  }, [scenarioId]);

  // Bring the details card into view when a zone is picked; Escape closes it.
  useEffect(() => {
    if (!selectedZoneId) return;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    detailsRef.current?.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "nearest" });
    const onKey = (e) => e.key === "Escape" && setSelectedZoneId(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedZoneId]);

  const zones = data?.ranking.zones ?? NO_ZONES;
  const selectedZone = zones.find((z) => z.id === selectedZoneId) ?? null;

  return (
    <div className="app">
      <TopBar scenarios={scenarios} scenarioId={scenarioId} onScenarioChange={setScenarioId} failed={Boolean(error)} />
      <ScenarioSummary scenario={data?.scenario} summary={data?.ranking.summary} failed={Boolean(error)} />

      {error && (
        <div className="error-banner" role="alert">
          <AlertIcon size={20} />
          <div>
            <strong>{error}</strong>
            <p>
              Is the backend running? In another terminal: <code>cd backend</code>, activate the virtual
              environment, then <code>uvicorn main:app --reload</code>. It should answer at{" "}
              <code>{API_BASE_URL}/health</code>.
            </p>
          </div>
          <button type="button" className="btn-secondary" onClick={() => setAttempt((n) => n + 1)}>
            Retry
          </button>
        </div>
      )}

      <main className="workspace">
        <ZoneMap
          zones={zones}
          hazard={data?.scenario.hazard}
          selectedZoneId={selectedZoneId}
          onSelectZone={setSelectedZoneId}
          loading={loading}
        />

        <aside className="side-panel" aria-label="Zone details, ranking and resources">
          {data ? (
            <>
              <ZoneDetails
                ref={detailsRef}
                zone={selectedZone}
                total={zones.length}
                settings={data.ranking.settings}
                onClose={() => setSelectedZoneId(null)}
              />
              <PriorityList zones={zones} selectedZoneId={selectedZoneId} onSelectZone={setSelectedZoneId} />
              <ResourceSummary resources={data.scenario.resources} />
              <AllocationPanel requested={allocationRequested} onAllocate={() => setAllocationRequested(true)} />
              <p className="data-note">
                <InfoIcon size={16} />
                <span>{data.scenario.data_note}</span>
              </p>
            </>
          ) : (
            <div className="panel-placeholder">{error ? "No scenario loaded." : "Loading scenario…"}</div>
          )}
        </aside>
      </main>
    </div>
  );
}
