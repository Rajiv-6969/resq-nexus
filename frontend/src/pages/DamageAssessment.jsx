import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import AnimatedNumber from "../components/AnimatedNumber";
import DamageGlyph from "../components/DamageGlyph";
import ScenarioPicker from "../components/ScenarioPicker";
import { SEVERITY_LABELS, accessLabel, formatNumber, vulnerabilityLabel } from "../constants";
import { fetchDamageMetrics, fetchDamageStatus, fetchScenarioBuildings, postAssessDamage } from "../api";
import { useAppData, useToast } from "../state/contexts";

const pad2 = (n) => String(n).padStart(2, "0");

const DAMAGE_COLORS = {
  0: "#8A8A85", // Concrete grey
  1: "#C9C7C1", // Light concrete
  2: "#FF6B1A", // Warning orange
  3: "#E10600", // Signal red
};

export default function DamageAssessment() {
  const { scenarios, scenarioId, scenario, selectScenario, listState, detailError } = useAppData();
  const { showToast } = useToast();

  const [modelStatus, setModelStatus] = useState(null);
  const [modelMetrics, setModelMetrics] = useState(null);
  const [scenarioBuildings, setScenarioBuildings] = useState([]);
  const [activeTab, setActiveTab] = useState("scenario"); // "scenario" | "model"
  const [assessing, setAssessing] = useState(false);
  const [satelliteAssessment, setSatelliteAssessment] = useState(null);

  useEffect(() => {
    fetchDamageStatus()
      .then((st) => setModelStatus(st))
      .catch(() => {});

    fetchDamageMetrics()
      .then((m) => setModelMetrics(m))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (scenarioId) {
      fetchScenarioBuildings(scenarioId)
        .then((data) => {
          if (data?.buildings) setScenarioBuildings(data.buildings);
        })
        .catch(() => setScenarioBuildings([]));
    }
  }, [scenarioId]);

  const zones = useMemo(
    () => [...(scenario?.zones ?? [])].sort((a, b) => b.damage_severity - a.damage_severity || b.population - a.population),
    [scenario],
  );

  const people = zones.reduce((sum, z) => sum + z.population, 0);
  const bySeverity = [3, 2, 1, 0].map((s) => {
    const list = zones.filter((z) => z.damage_severity === s);
    return { severity: s, count: list.length, people: list.reduce((sum, z) => sum + z.population, 0) };
  });

  const handleRunTileAssessment = async () => {
    setAssessing(true);
    try {
      const data = await postAssessDamage({
        tile_id: "palu-tsunami_0000001",
        bounds: { south: -0.92, west: 119.83, north: -0.88, east: 119.87 },
      });
      setSatelliteAssessment(data);
      showToast(`Assessed ${data.buildings?.length ?? 0} building footprints`, "success");
    } catch (err) {
      showToast(err.message || "Assessment failed", "error");
    } finally {
      setAssessing(false);
    }
  };

  const votedMetrics = modelMetrics?.test_results?.test_voted;

  return (
    <div className="damage brutalist-view">
      <section className="sec sec--black page-hero" aria-labelledby="damage-title">
        <p className="sec-bar mono">
          <span>(02) ASSESS</span>
          <span>STAGE 01 OF 04</span>
        </p>
        <div className="page-hero-row">
          <h1 id="damage-title" className="page-title mono">
            Damage Assessment
          </h1>
          <p className="page-sub">
            Satellite building damage footprints & H3 zone aggregation using DisasterReliefGPT ResNet34 FPN with object-level majority voting.
          </p>
        </div>
      </section>

      {/* Model Status Bar */}
      <div className="damage-status-strip mono text-xs">
        <div className="status-item">
          <span>DAMAGE MODEL:</span>
          <strong className={modelStatus?.model_installed ? "signal-green" : "signal-red"}>
            {modelStatus?.model_installed ? "ONNX ACTIVE (512x512 TILED)" : "WEIGHTS PENDING"}
          </strong>
        </div>
        <div className="status-item">
          <span>BASE PAPER:</span>
          <span>DisasterReliefGPT (Technologies 2026, 14, 179)</span>
        </div>
        <div className="status-item">
          <span>LOCALISATION F1:</span>
          <strong>{votedMetrics?.localisation_f1 ?? "0.8305"}</strong>
        </div>
        <div className="status-item">
          <span>xVIEW2 SCORE:</span>
          <strong>{votedMetrics?.xview2_score ?? "0.6618"}</strong>
        </div>
      </div>

      {/* View Switcher */}
      <div className="brutalist-tabs mono">
        <button
          type="button"
          className={`tab-btn ${activeTab === "scenario" ? "active" : ""}`}
          onClick={() => setActiveTab("scenario")}
        >
          01 / Scenario Zones & Building Footprints
        </button>
        <button
          type="button"
          className={`tab-btn ${activeTab === "model" ? "active" : ""}`}
          onClick={() => setActiveTab("model")}
        >
          02 / Live Satellite ONNX Assessment
        </button>
      </div>

      {activeTab === "scenario" && (
        <div className="scenario-damage-pane">
          <div className="toolbar">
            <p className="toolbar-label mono">01 / Scenario</p>
            <ScenarioPicker scenarios={scenarios} scenarioId={scenarioId} onSelect={selectScenario} failed={listState.status === "error"} />
            <p className="toolbar-note mono">
              {scenario ? `${zones.length} zones / ${formatNumber(people)} people / ${scenarioBuildings.length} buildings` : "Loading..."}
            </p>
          </div>

          {(listState.error || detailError) && <p className="notice notice--warn">{listState.error || detailError}</p>}

          {/* Severity Breakdown */}
          <section className="severity-summary mono" aria-label="Zones by damage severity">
            {bySeverity.map(({ severity, count, people: affected }) => (
              <div key={severity} className={`severity-tile severity-tile--s${severity}`}>
                <span className="severity-name">
                  {pad2(severity)} / {SEVERITY_LABELS[severity]}
                </span>
                <span className="severity-count">
                  <AnimatedNumber value={scenario ? count : null} />
                </span>
                <span className="severity-people">{scenario ? `${formatNumber(affected)} people` : ""}</span>
              </div>
            ))}
          </section>

          {/* Building Footprint Samples Banner */}
          {scenarioBuildings.length > 0 && (
            <div className="building-chip-bar mono text-xs mt-4">
              <span className="chip-label">Footprints ({scenarioBuildings.length}):</span>
              <span className="chip-dot" style={{ background: DAMAGE_COLORS[0] }}>No Damage</span>
              <span className="chip-dot" style={{ background: DAMAGE_COLORS[1] }}>Minor</span>
              <span className="chip-dot" style={{ background: DAMAGE_COLORS[2] }}>Major</span>
              <span className="chip-dot" style={{ background: DAMAGE_COLORS[3] }}>Destroyed</span>
            </div>
          )}

          {/* Zones Grid */}
          <ul className="damage-grid mono">
            {zones.map((z) => (
              <li key={z.id} className={`damage-card damage-card--s${z.damage_severity}`}>
                <div className="damage-top">
                  <DamageGlyph type={z.disaster_type} severity={z.damage_severity} />
                  <span className="damage-id">{z.id}</span>
                </div>
                <div className="damage-body">
                  <h3>{z.name}</h3>
                  <p className="damage-severity">
                    <span className="severity-dot" style={{ background: DAMAGE_COLORS[z.damage_severity] }} />
                    {SEVERITY_LABELS[z.damage_severity]} <span className="muted">({z.damage_severity}/3)</span>
                  </p>
                  <dl>
                    <div>
                      <dt>Population</dt>
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
              </li>
            ))}
          </ul>
        </div>
      )}

      {activeTab === "model" && (
        <div className="model-damage-pane mono text-xs">
          <div className="eval-metrics-box">
            <h2 className="text-sm font-bold uppercase mb-2">DisasterReliefGPT xBD Model Evaluation Metrics</h2>
            <div className="metrics-columns">
              <div className="metric-col">
                <span className="col-title font-bold">Primary: Object Majority Voted</span>
                <p>Localisation F1: <strong>0.8305</strong></p>
                <p>Damage F1 Harmonic: <strong>0.5895</strong></p>
                <p>Damage F1 Macro: <strong>0.6394</strong></p>
                <p>xView2 Score: <strong>0.6618</strong></p>
              </div>
              <div className="metric-col">
                <span className="col-title font-bold">Secondary: Known Footprints (Unmasked)</span>
                <p>Damage F1 Macro: <strong>0.6910</strong></p>
                <p>xView2 Score: <strong>0.7004</strong></p>
              </div>
            </div>
          </div>

          <div className="action-strip mt-4">
            <button
              type="button"
              className="brutalist-btn btn--primary"
              onClick={handleRunTileAssessment}
              disabled={assessing}
            >
              {assessing ? "Processing ONNX Tiles..." : "Run Assessment on Palu Tsunami Tile"}
            </button>
            <Link to="/admin/incidents/new" className="brutalist-btn btn--action ml-2">
              + Upload Custom GeoTIFF / Vantor STAC
            </Link>
          </div>

          {satelliteAssessment && (
            <div className="satellite-result-box mt-4">
              <h3 className="text-sm font-bold">Assessment ID: {satelliteAssessment.assessment_id}</h3>
              <p>Buildings Assessed: <strong>{satelliteAssessment.buildings?.length ?? 0}</strong></p>
              <p>H3 Zones Produced: <strong>{satelliteAssessment.zones?.length ?? 0}</strong></p>
              <p>Peak RAM: <strong>{satelliteAssessment.timing?.peak_mb ?? 180} MB</strong></p>
              <Link to="/command" className="brutalist-btn btn--dispatch mt-2 inline-block">
                Allocate Relief for Assessment &rarr;
              </Link>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
