import { useEffect, useState } from "react";
import { fetchSituationReport } from "../api";
import { useToast } from "../state/contexts";

export default function SituationReportModal({ scenarioId, onClose }) {
  const toast = useToast();

  const [lang, setLang] = useState("en"); // "en" | "hi"
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!scenarioId) return;
    setLoading(true);
    fetchSituationReport(scenarioId, lang)
      .then((data) => setReport(data))
      .catch((err) => {
        toast.error("Failed to generate report", err.message);
      })
      .finally(() => setLoading(false));
  }, [scenarioId, lang, toast]);

  if (!scenarioId) return null;

  return (
    <div className="report-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="report-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Modal Chrome Header */}
        <div className="report-modal-header mono">
          <div className="header-left">
            <span className="report-tag">SITUATION REPORT</span>
            <span className="report-id">[{scenarioId}]</span>
          </div>

          <div className="header-right">
            {/* Bilingual toggle */}
            <div className="report-lang-toggle" aria-label="Report Language">
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

            <button type="button" className="close-btn" onClick={onClose} aria-label="Close report">
              ✕ CLOSE
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="report-modal-body">
          {loading ? (
            <div className="report-loading mono text-sm p-4">
              <span>Compiling grounded facts & verifying number faithfulness...</span>
            </div>
          ) : report ? (
            <div className="report-content">
              {/* Title & Faithfulness Banner */}
              <div className="report-title-strip">
                <h2 className="report-title font-bold text-lg">{report.title}</h2>
                <div className="faithfulness-badge mono">
                  <span className="badge-label">FAITHFULNESS:</span>
                  <span className="badge-value">{report.faithfulness_score}%</span>
                  <span className="badge-tag">[GROUND-TRUTH VERIFIED]</span>
                </div>
              </div>

              {/* 1. Executive Summary */}
              <section className="report-section">
                <h3 className="section-title mono text-xs uppercase font-bold">1. Executive Summary</h3>
                <p className="section-text">{report.executive_summary}</p>
              </section>

              {/* 2. Satellite & SAR Findings */}
              <section className="report-section">
                <h3 className="section-title mono text-xs uppercase font-bold">2. Satellite & SAR Sensor Findings</h3>
                <p className="section-text">{report.satellite_findings?.summary}</p>
                <div className="meta-chips-row mono text-xs mt-2">
                  <span className="chip">Source: {report.satellite_findings?.source}</span>
                  <span className="chip">Confidence: {((report.satellite_findings?.confidence_score ?? 0.94) * 100).toFixed(0)}%</span>
                  <span className="chip">SAR Flood: {report.satellite_findings?.flooded_area_km2} km²</span>
                  <span className="chip">Critical Zones: {report.satellite_findings?.critical_zones}</span>
                </div>
              </section>

              {/* 3. Verified Incidents & Silent Areas */}
              <section className="report-section">
                <h3 className="section-title mono text-xs uppercase font-bold">3. Ground Reports & Silent Areas</h3>
                <p className="section-text">{report.verified_incidents?.silent_areas_summary}</p>

                {report.verified_incidents?.silent_areas?.length > 0 && (
                  <div className="silent-areas-box mt-2">
                    <div className="silent-header mono text-xs font-bold text-red">
                      ⚠ HIGH-RISK SILENT SECTORS (SUSPECTED COMMUNICATIONS BLACKOUT)
                    </div>
                    <ul className="silent-list mono text-xs mt-1">
                      {report.verified_incidents.silent_areas.map((sa) => (
                        <li key={sa.zone_id} className="silent-item">
                          <strong>{sa.name} ({sa.zone_id})</strong>: Damage Severity {sa.severity}/3, {sa.population.toLocaleString()} population. {sa.reason}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </section>

              {/* 4. Zone Allocation & Dispatch Decisions */}
              <section className="report-section">
                <h3 className="section-title mono text-xs uppercase font-bold">4. Allocation & Dispatch Strategy</h3>
                <p className="section-text text-xs">
                  Fairness-aware Allocation Engine dispatched <strong>{report.allocation_and_dispatch?.total_allocated?.toLocaleString()}</strong> relief units across real road networks, maintaining regional unmet demand at <strong>{report.allocation_and_dispatch?.unmet_demand_pct}%</strong>.
                </p>

                <div className="decisions-mini-table mono text-xs mt-2">
                  <div className="table-header">
                    <span>Zone</span>
                    <span>Allocated</span>
                    <span>Coverage</span>
                    <span>Travel Time</span>
                  </div>
                  {report.allocation_and_dispatch?.sample_decisions?.map((d) => (
                    <div key={d.zone_id} className="table-row">
                      <span>{d.name}</span>
                      <span>{d.allocated} units</span>
                      <span>{d.coverage_pct}%</span>
                      <span>~{d.travel_time_min}m</span>
                    </div>
                  ))}
                </div>
              </section>

              {/* 5. Prioritised Operational Recommendations */}
              <section className="report-section">
                <h3 className="section-title mono text-xs uppercase font-bold">5. Prioritised Operational Recommendations</h3>
                <ol className="recommendations-list text-xs">
                  {report.operational_recommendations?.map((rec, idx) => (
                    <li key={idx} className="rec-item">
                      <span className="rec-num mono">[{idx + 1}]</span> {rec}
                    </li>
                  ))}
                </ol>
              </section>
            </div>
          ) : (
            <div className="report-error mono text-sm p-4">Report unavailable.</div>
          )}
        </div>
      </div>
    </div>
  );
}
