import { useEffect, useState } from "react";
import { fetchDetailedZoneExplanation } from "../api";
import { useToast } from "../state/contexts";

export default function ExplainDetailModal({ scenarioId, zoneId, onClose }) {
  const toast = useToast();
  const [lang, setLang] = useState("en");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!scenarioId || !zoneId) return;
    setLoading(true);
    fetchDetailedZoneExplanation(scenarioId, zoneId, lang)
      .then((res) => setData(res))
      .catch((err) => {
        toast.error("Explanation failed", err.message);
      })
      .finally(() => setLoading(false));
  }, [scenarioId, zoneId, lang, toast]);

  if (!scenarioId || !zoneId) return null;

  return (
    <div className="report-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="explain-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="report-modal-header mono">
          <div className="header-left">
            <span className="report-tag">DECISION AUDIT</span>
            <span className="report-id">[{zoneId}]</span>
          </div>

          <div className="header-right">
            <div className="report-lang-toggle" aria-label="Explanation Language">
              <button
                type="button"
                className={`lang-btn ${lang === "en" ? "active" : ""}`}
                onClick={() => setLang("en")}
              >
                EN
              </button>
              <span>/</span>
              <button
                type="button"
                className={`lang-btn ${lang === "hi" ? "active" : ""}`}
                onClick={() => setLang("hi")}
              >
                HI
              </button>
            </div>

            <button type="button" className="close-btn" onClick={onClose} aria-label="Close">
              ✕ CLOSE
            </button>
          </div>
        </div>

        <div className="explain-modal-body p-4">
          {loading ? (
            <div className="mono text-xs">Computing contextual road & fairness factors...</div>
          ) : data ? (
            <div className="explain-content">
              <div className="explain-meta-bar mono text-xs mb-3">
                <span className="chip">Rank #{data.metrics?.rank}</span>
                <span className="chip">Priority Score: {data.metrics?.priority_score}</span>
                <span className="chip">Coverage: {data.metrics?.coverage_pct}%</span>
                <span className="chip">Greedy Baseline: {data.metrics?.greedy_coverage_pct}%</span>
                <span className="chip">Route: {data.metrics?.distance_km} km ({data.metrics?.travel_time_min}m)</span>
              </div>

              <div className="explain-text-box mono text-xs p-3">
                <div className="explain-source-tag font-bold mb-2">
                  [{data.source === "gemini" ? "AI CONTEXTUAL REASONING: GEMINI" : "FAIRNESS-AWARE DECISION ENGINE AUDIT"}]
                </div>
                <p style={{ whiteSpace: "pre-line", lineHeight: 1.5 }}>{data.explanation}</p>
              </div>
            </div>
          ) : (
            <div className="mono text-xs">Explanation not available.</div>
          )}
        </div>
      </div>
    </div>
  );
}
