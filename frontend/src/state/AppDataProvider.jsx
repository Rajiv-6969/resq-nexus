import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useSearchParams } from "react-router";
import { fetchHealth, fetchPriority, fetchScenario, fetchScenarios, postAllocate, postExplain } from "../api";
import { DEFAULT_WEIGHTS, SCENARIO_PAGES, weightsKey } from "../constants";
import { useDebouncedValue, withMinimum } from "../lib/hooks";
import { AppDataContext, useAuth, useToast } from "./contexts";

const STORAGE_KEY = "resq.scenario";

function readStoredScenario() {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export default function AppDataProvider({ children }) {
  const toast = useToast();
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN"; // the Command Centre data is admin-only
  const { pathname } = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const [attempt, setAttempt] = useState(0);

  const [health, setHealth] = useState({ status: "checking" });
  const [scenarios, setScenarios] = useState([]);
  const [listState, setListState] = useState({ status: "loading", error: null });
  const [storedId, setStoredId] = useState(readStoredScenario);
  const [details, setDetails] = useState({});
  const [detailError, setDetailError] = useState(null);

  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const liveWeights = useDebouncedValue(weights, 160);
  const [ranking, setRanking] = useState(null); // { scenarioId, key, data }
  const [rankingError, setRankingError] = useState(null);

  const [runs, setRuns] = useState({}); // scenarioId -> { weightsKey, weights, result, explanations, explainError }
  const [pipeline, setPipeline] = useState({ status: "idle", step: -1, scenarioId: null, error: null });
  const runCounter = useRef(0);

  // A different account (or a logout) starts with no Command Centre data in memory.
  const userId = user?.id ?? null;
  const [dataOwner, setDataOwner] = useState(userId);
  if (dataOwner !== userId) {
    setDataOwner(userId);
    setDetails({});
    setDetailError(null);
    setRanking(null);
    setRankingError(null);
    setRuns({});
    setPipeline({ status: "idle", step: -1, scenarioId: null, error: null });
  }
  useEffect(() => {
    runCounter.current += 1; // a run still in flight for the previous account no longer reports back
  }, [userId]);

  // Which scenario is on screen: the URL wins, then the last choice, then the first scenario.
  const urlId = searchParams.get("scenario");
  const scenarioId = useMemo(() => {
    const ids = scenarios.map((s) => s.id);
    return [urlId, storedId, ids[0]].find((id) => id && ids.includes(id)) ?? null;
  }, [scenarios, urlId, storedId]);
  const onScenarioPage = SCENARIO_PAGES.includes(pathname);

  // API health (also tells us whether a Gemini key is configured).
  useEffect(() => {
    const controller = new AbortController();
    fetchHealth({ signal: controller.signal })
      .then((data) => setHealth({ ...data, status: "online" }))
      .catch((err) => err.name !== "AbortError" && setHealth({ status: "offline" }));
    return () => controller.abort();
  }, [attempt]);

  // Scenario list.
  useEffect(() => {
    const controller = new AbortController();
    setListState({ status: "loading", error: null });
    fetchScenarios({ signal: controller.signal })
      .then((list) => {
        setScenarios(list);
        setListState(list.length ? { status: "ready", error: null } : { status: "error", error: "No scenarios found in backend/data/scenarios." });
      })
      .catch((err) => err.name !== "AbortError" && setListState({ status: "error", error: err.message }));
    return () => controller.abort();
  }, [attempt]);

  // Full scenario (cached per id).
  const haveDetail = Boolean(scenarioId && details[scenarioId]);
  useEffect(() => {
    if (!isAdmin || !scenarioId || haveDetail) return;
    const controller = new AbortController();
    setDetailError(null);
    fetchScenario(scenarioId, { signal: controller.signal })
      .then((data) => setDetails((all) => ({ ...all, [scenarioId]: data })))
      .catch((err) => err.name !== "AbortError" && setDetailError(err.message));
    return () => controller.abort();
  }, [isAdmin, scenarioId, haveDetail, attempt]);

  // Priority ranking: re-scored live (debounced) whenever the weights move.
  useEffect(() => {
    if (!isAdmin || !scenarioId) return;
    const controller = new AbortController();
    const key = weightsKey(liveWeights);
    fetchPriority(scenarioId, liveWeights, { signal: controller.signal })
      .then((data) => {
        setRanking({ scenarioId, key, data });
        setRankingError(null);
      })
      .catch((err) => err.name !== "AbortError" && setRankingError(err.message));
    return () => controller.abort();
  }, [isAdmin, scenarioId, liveWeights, attempt]);

  // Keep ?scenario=<id> in the address bar on scenario pages (refresh / shared links).
  useEffect(() => {
    if (!onScenarioPage || !scenarioId || urlId === scenarioId) return;
    setSearchParams(
      (params) => {
        const next = new URLSearchParams(params);
        next.set("scenario", scenarioId);
        return next;
      },
      { replace: true },
    );
  }, [onScenarioPage, scenarioId, urlId, setSearchParams]);

  const selectScenario = useCallback(
    (id) => {
      setStoredId(id);
      try {
        window.localStorage.setItem(STORAGE_KEY, id);
      } catch {
        // private mode: the choice just isn't remembered
      }
      if (onScenarioPage) {
        setSearchParams(
          (params) => {
            const next = new URLSearchParams(params);
            next.set("scenario", id);
            next.delete("zone");
            return next;
          },
          { replace: true },
        );
      }
    },
    [onScenarioPage, setSearchParams],
  );

  const setWeight = useCallback((key, value) => setWeights((w) => ({ ...w, [key]: value })), []);
  const resetWeights = useCallback(() => setWeights(DEFAULT_WEIGHTS), []);
  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  // Assess -> Prioritise -> Allocate -> Explain, one visible step at a time.
  const runPipeline = useCallback(async () => {
    if (!scenarioId) return;
    runCounter.current += 1;
    const runId = runCounter.current;
    const id = scenarioId;
    const w = weights;
    const key = weightsKey(w);
    const current = () => runCounter.current === runId;
    const setStep = (step) => current() && setPipeline({ status: "running", step, scenarioId: id, error: null });

    setStep(0);
    try {
      const scenario = await withMinimum(details[id] ?? fetchScenario(id), 550);
      if (!current()) return;
      setDetails((all) => ({ ...all, [id]: scenario }));

      setStep(1);
      const scored = await withMinimum(fetchPriority(id, w), 550);
      if (!current()) return;
      setRanking({ scenarioId: id, key, data: scored });

      setStep(2);
      const result = await withMinimum(postAllocate(id, w, false), 900);
      if (!current()) return;
      setRuns((all) => ({ ...all, [id]: { weightsKey: key, weights: w, result, explanations: null, explainError: null } }));
      const m = result.engine.metrics;
      toast.success(
        "Allocation complete",
        `${result.depots.length} depots · ${m.coverage_pct?.toFixed(0) ?? "—"}% priority-weighted coverage · ${(m.computation_ms / 1000).toFixed(2)} s`,
      );

      setStep(3);
      try {
        const explained = await withMinimum(postExplain(id, w, false), 600);
        if (!current()) return;
        setRuns((all) => ({ ...all, [id]: { ...all[id], explanations: explained } }));
        if (explained.source === "gemini") toast.info("Explanations ready", `Written by Gemini (${explained.model}).`);
        else toast.warning(explained.source === "mixed" ? "Partly template explanations" : "Template explanations", explained.notice);
      } catch (err) {
        if (!current()) return;
        setRuns((all) => ({ ...all, [id]: { ...all[id], explainError: err.message } }));
        toast.error("Explanations unavailable", err.message);
      }
      if (current()) setPipeline({ status: "done", step: 4, scenarioId: id, error: null });
    } catch (err) {
      if (!current()) return;
      setPipeline((p) => ({ ...p, status: "error", error: err.message }));
      toast.error("Pipeline stopped", err.message);
    }
  }, [scenarioId, weights, details, toast]);

  const run = scenarioId ? (runs[scenarioId] ?? null) : null;
  const value = useMemo(
    () => ({
      health,
      apiOnline: health.status === "online",
      geminiConfigured: Boolean(health.gemini_configured),
      scenarios,
      listState,
      scenarioId,
      scenarioSummary: scenarios.find((s) => s.id === scenarioId) ?? null,
      scenario: scenarioId ? (details[scenarioId] ?? null) : null,
      detailError,
      selectScenario,
      weights,
      setWeight,
      resetWeights,
      ranking: ranking?.scenarioId === scenarioId ? ranking.data : null,
      rankingSettled: ranking?.scenarioId === scenarioId && ranking.key === weightsKey(weights),
      rankingError,
      run,
      runStale: Boolean(run && run.weightsKey !== weightsKey(weights)),
      pipeline: pipeline.scenarioId === scenarioId ? pipeline : { status: "idle", step: -1, scenarioId, error: null },
      runPipeline,
      retry,
    }),
    [health, scenarios, listState, scenarioId, details, detailError, selectScenario, weights, setWeight, resetWeights,
      ranking, rankingError, run, pipeline, runPipeline, retry],
  );

  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>;
}
