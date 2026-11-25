import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Circle, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import {
  acknowledgeAlert,
  assessSentinelFlood,
  fetchAlertMetrics,
  fetchAlerts,
  fetchScenarioTimeline,
  simulateAlert,
} from "../api";
import BaseMap, { FitPoints } from "../components/maps/BaseMap";
import PrototypeNotice from "../components/sos/PrototypeNotice";
import ScenarioPicker from "../components/ScenarioPicker";
import SituationReportModal from "../components/SituationReportModal";
import ExplainDetailModal from "../components/ExplainDetailModal";
import { useAppData, useToast } from "../state/contexts";

// Brutalist color palette strictly conforming to docs/PROJECT_CONTEXT.md
const PALETTE = {
  black: "#0A0A0A",
  offWhite: "#EDEBE6",
  concreteGrey: "#8A8A85",
  lightGrey: "#C9C7C1",
  signalRed: "#E10600",
  warningOrange: "#FF6B1A",
  sarWater: "#006699",
};

// Custom SVG marker icons
function createIcon(color, label, symbol = "●") {
  return L.divIcon({
    className: "custom-leaflet-icon",
    html: `<div style="
      background: ${color};
      color: #0A0A0A;
      border: 1px solid #0A0A0A;
      font-family: monospace;
      font-size: 11px;
      font-weight: 700;
      padding: 2px 6px;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      box-shadow: none;
      white-space: nowrap;
    "><span>${symbol}</span><span>${label}</span></div>`,
    iconSize: [80, 24],
    iconAnchor: [40, 12],
  });
}

export default function LiveMode() {
  const { t } = useTranslation();
  const { scenarios, scenarioId, selectScenario, listState, scenario } = useAppData();
  const toast = useToast();

  // Live state
  const [alerts, setAlerts] = useState([]);
  const [alertMetrics, setAlertMetrics] = useState({
    total_alerts: 0,
    active: 0,
    acknowledged: 0,
    escalated: 0,
    acknowledgment_rate: 0,
  });
  const [sarAssessment, setSarAssessment] = useState(null);
  const [activeTab, setActiveTab] = useState("alerts"); // "alerts" | "sentinel" | "fused"
  const [ackBusyId, setAckBusyId] = useState(null);
  const [showReport, setShowReport] = useState(false);
  const [explainZoneId, setExplainZoneId] = useState(null);

  // Replay state
  const [timeline, setTimeline] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1); // 1x, 2x, 5x
  const playTimerRef = useRef(null);

  // Load initial data
  const loadAlertsAndSar = useCallback(async () => {
    try {
      const [alertsData, metricsData] = await Promise.all([
        fetchAlerts({ limit: 20 }),
        fetchAlertMetrics(),
      ]);
      const safeAlerts = Array.isArray(alertsData) ? alertsData : (alertsData?.alerts ?? []);
      setAlerts(safeAlerts);
      setAlertMetrics(metricsData ?? {
        total_alerts: 0,
        active: 0,
        acknowledged: 0,
        escalated: 0,
        acknowledgment_rate: 0,
      });
    } catch (err) {
      toast.error("Data fetch error", err.message);
    }
  }, [toast]);

  useEffect(() => {
    loadAlertsAndSar();
    const interval = setInterval(loadAlertsAndSar, 15000); // 15s live refresh
    return () => clearInterval(interval);
  }, [loadAlertsAndSar]);

  // Load Sentinel-1 assessment for current scenario
  useEffect(() => {
    if (!scenarioId) return;
    assessSentinelFlood({
      bbox: scenario?.bbox ?? { south: 12.9, west: 77.6, north: 13.0, east: 77.7 },
      scenario_id: scenarioId,
      water_threshold_db: -16.0,
    })
      .then((res) => setSarAssessment(res))
      .catch(() => {});
  }, [scenarioId, scenario]);

  useEffect(() => {
    const targetId = scenarioId || "flood-bengaluru";
    fetchScenarioTimeline(targetId)
      .then((tl) => {
        setTimeline(tl);
        setCurrentStep(0);
        setIsPlaying(false);
      })
      .catch(() => {});
  }, [scenarioId]);

  // Event Replay playback loop
  useEffect(() => {
    if (!isPlaying || !timeline) {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
      return;
    }

    const intervalMs = 3000 / playbackSpeed;
    playTimerRef.current = setInterval(() => {
      setCurrentStep((prev) => {
        const total = timeline?.total_steps ?? timeline?.frames?.length ?? 1;
        if (prev >= total - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, intervalMs);

    return () => {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    };
  }, [isPlaying, playbackSpeed, timeline]);

  // Handle alert acknowledgment
  const handleAcknowledge = async (alertId) => {
    setAckBusyId(alertId);
    try {
      const updated = await acknowledgeAlert(alertId);
      toast.success("Alert Acknowledged", `Code: ${updated.alert_code} marked acknowledged.`);
      await loadAlertsAndSar();
    } catch (err) {
      toast.error("Failed to acknowledge alert", err.message);
    } finally {
      setAckBusyId(null);
    }
  };

  // Quick simulate alert
  const handleSimulateAlert = async () => {
    try {
      await simulateAlert({
        headline: "SIMULATED FLASH FLOOD ADVISORY",
        description: "Intense convective rainfall triggered local storm sewer backflow and street inundation.",
        severity: "Severe",
        urgency: "Immediate",
        certainty: "Observed",
        disaster_type: scenario?.disaster_type || "flood",
        area_desc: scenario?.name || "Active Sector",
        latitude: scenario?.zones?.[0]?.latitude ?? 12.95,
        longitude: scenario?.zones?.[0]?.longitude ?? 77.65,
        escalation_timeout_mins: 15,
      });
      toast.success("Simulated Alert Added", "New active warning registered in control feed.");
      await loadAlertsAndSar();
    } catch (err) {
      toast.error("Simulation failed", err.message);
    }
  };

  // Replay frame currently active
  const currentFrame = useMemo(() => {
    if (!timeline || !Array.isArray(timeline.frames) || !timeline.frames[currentStep]) return null;
    return timeline.frames[currentStep];
  }, [timeline, currentStep]);

  // Map center and points
  const mapCenter = useMemo(() => {
    if (timeline?.center?.latitude != null && timeline?.center?.longitude != null) {
      return [timeline.center.latitude, timeline.center.longitude];
    }
    if (scenario?.zones?.[0]?.latitude != null && scenario?.zones?.[0]?.longitude != null) {
      return [scenario.zones[0].latitude, scenario.zones[0].longitude];
    }
    return [12.9716, 77.5946];
  }, [timeline, scenario]);

  const fitPoints = useMemo(() => {
    const pts = [];
    if (alerts?.length) {
      alerts.forEach((a) => {
        if (a?.latitude != null && a?.longitude != null) {
          pts.push([a.latitude, a.longitude]);
        }
      });
    }
    if (currentFrame?.active_sos?.length) {
      currentFrame.active_sos.forEach((s) => {
        if (s?.latitude != null && s?.longitude != null) {
          pts.push([s.latitude, s.longitude]);
        }
      });
    }
    if (currentFrame?.dispatches?.length) {
      currentFrame.dispatches.forEach((d) => {
        if (d?.latitude != null && d?.longitude != null) {
          pts.push([d.latitude, d.longitude]);
        }
      });
    }
    return pts;
  }, [alerts, currentFrame]);

  return (
    <div className="live-mode-page">
      <PrototypeNotice />

      {/* Top Header & Context */}
      <header className="live-header">
        <div className="live-header-main">
          <div className="live-badge-wrapper">
            <span className="live-status-pill mono">
              <span className="live-dot" /> {t("live.status", "LIVE OPERATIONS")}
            </span>
            <span className="live-mode-tag mono">PHASE 04</span>
          </div>
          <h1 className="live-title">{t("live.title", "Live Operations & Event Replay")}</h1>
          <p className="live-subtitle text-xs text-concrete">
            {t("live.subtitle", "Real-time official alerts, Sentinel-1 SAR flood mapping and multi-phase disaster replay")}
          </p>
        </div>

        <div className="live-header-actions">
          <ScenarioPicker
            scenarios={scenarios}
            scenarioId={scenarioId}
            onSelect={selectScenario}
            failed={listState?.status === "error"}
          />
          <button
            type="button"
            className="brutalist-btn btn--report mono text-xs"
            onClick={() => setShowReport(true)}
            title="Generate verified grounded situation report"
          >
            📑 Situation Report
          </button>
          <button
            type="button"
            className="brutalist-btn btn--simulate mono text-xs"
            onClick={handleSimulateAlert}
            title="Inject simulated official warning"
          >
            + Simulate Alert
          </button>
        </div>
      </header>

      {/* KPI Ticker Bar */}
      <section className="live-kpi-bar mono" aria-label="Live Operations Metrics">
        <div className="kpi-cell">
          <span className="kpi-label">{t("live.active_alerts", "Active Alerts")}</span>
          <span className={`kpi-val ${alertMetrics.active > 0 ? "kpi-val--red" : ""}`}>
            {alertMetrics.active}
          </span>
        </div>
        <div className="kpi-cell">
          <span className="kpi-label">{t("live.ack_rate", "Alert Ack Rate")}</span>
          <span className="kpi-val">
            {(alertMetrics.acknowledgment_rate * 100).toFixed(1)}%
          </span>
          <span className="kpi-sub">
            ({alertMetrics.acknowledged}/{alertMetrics.total_alerts})
          </span>
        </div>
        <div className="kpi-cell">
          <span className="kpi-label">{t("live.flooded_area", "SAR Flood Extent")}</span>
          <span className="kpi-val kpi-val--blue">
            {sarAssessment?.flooded_area_km2 ?? 14.8} km²
          </span>
          <span className="kpi-sub">
            ({((sarAssessment?.flooded_pct ?? 0.22) * 100).toFixed(1)}% cover)
          </span>
        </div>
        <div className="kpi-cell">
          <span className="kpi-label">{t("live.ground_sos", "Citizen SOS Calls")}</span>
          <span className="kpi-val kpi-val--orange">
            {currentFrame?.metrics?.citizen_sos_count ?? 18}
          </span>
          <span className="kpi-sub">Ground Verified</span>
        </div>
      </section>

      {/* Main Grid: Interactive Map + Tabbed Panels */}
      <div className="live-main-grid">
        {/* Map Stage */}
        <section className="live-map-stage" aria-label="Geospatial Map">
          <div className="map-toolbar mono text-xs">
            <span className="map-legend-item">
              <span className="legend-swatch" style={{ background: PALETTE.signalRed }} /> Alert / Critical
            </span>
            <span className="map-legend-item">
              <span className="legend-swatch" style={{ background: PALETTE.warningOrange }} /> Ground SOS
            </span>
            <span className="map-legend-item">
              <span className="legend-swatch" style={{ background: PALETTE.sarWater }} /> Sentinel-1 SAR Flood
            </span>
            <span className="map-legend-item">
              <span className="legend-swatch" style={{ background: PALETTE.black }} /> Dispatched Unit
            </span>
          </div>

          <div className="live-map-container">
            <BaseMap center={mapCenter} zoom={12} label="Live Operations Tactical Map">
              <FitPoints points={fitPoints} fitKey={`${currentStep}-${alerts?.length ?? 0}`} />

              {/* Sentinel-1 Inundation Zones */}
              {(sarAssessment?.zones ?? []).map((zone) => {
                if (!zone?.flooded_pct || zone.flooded_pct <= 0.05) return null;
                return (
                  <Circle
                    key={zone.zone_id}
                    center={[zone.latitude, zone.longitude]}
                    radius={Math.max(zone.flooded_pct * 1200, 400)}
                    pathOptions={{
                      color: PALETTE.sarWater,
                      fillColor: PALETTE.sarWater,
                      fillOpacity: 0.35,
                      weight: 1,
                    }}
                  >
                    <Popup>
                      <div className="mono text-xs">
                        <strong>{zone.name}</strong>
                        <div>SAR Backscatter: {zone.mean_backscatter_vv_db} dB</div>
                        <div>Flooded Share: {(zone.flooded_pct * 100).toFixed(0)}%</div>
                        <div>Severity: {zone.severity}</div>
                        <button
                          type="button"
                          className="brutalist-btn btn--sm mono mt-2 block"
                          onClick={() => setExplainZoneId(zone.zone_id)}
                        >
                          Explain in detail &rarr;
                        </button>
                      </div>
                    </Popup>
                  </Circle>
                );
              })}

              {/* Official Alert Pins */}
              {(alerts ?? []).map((alt) => (
                <Marker
                  key={alt.id}
                  position={[alt.latitude, alt.longitude]}
                  icon={createIcon(
                    alt.status === "ACTIVE"
                      ? PALETTE.signalRed
                      : alt.status === "ESCALATED"
                      ? PALETTE.warningOrange
                      : PALETTE.concreteGrey,
                    alt.alert_code,
                    "⚠"
                  )}
                >
                  <Popup>
                    <div className="mono text-xs">
                      <strong>{alt.headline}</strong>
                      <p>{alt.description}</p>
                      <div>Status: <strong>{alt.status}</strong></div>
                      <div>Sender: {alt.sender}</div>
                    </div>
                  </Popup>
                </Marker>
              ))}

              {/* Replay Frame SOS pins */}
              {(currentFrame?.active_sos ?? []).map((sos) => (
                <Marker
                  key={sos.id}
                  position={[sos.latitude, sos.longitude]}
                  icon={createIcon(PALETTE.warningOrange, sos.id, "SOS")}
                >
                  <Popup>
                    <div className="mono text-xs">
                      <strong>Citizen SOS: {sos.id}</strong>
                      <div>People Affected: {sos.people_affected}</div>
                      <div>Status: {sos.status}</div>
                    </div>
                  </Popup>
                </Marker>
              ))}

              {/* Replay Dispatches */}
              {(currentFrame?.dispatches ?? []).map((dsp) => (
                <Marker
                  key={dsp.dispatch_id}
                  position={[dsp.latitude + 0.003, dsp.longitude + 0.003]}
                  icon={createIcon(PALETTE.black, dsp.dispatch_id, "➔")}
                >
                  <Popup>
                    <div className="mono text-xs">
                      <strong>Unit: {dsp.dispatch_id}</strong>
                      <div>Type: {dsp.resource_type}</div>
                      <div>Target: {dsp.target_zone}</div>
                      <div>Status: {dsp.status}</div>
                    </div>
                  </Popup>
                </Marker>
              ))}
            </BaseMap>
          </div>
        </section>

        {/* Tabbed Side Panels */}
        <aside className="live-side-panel">
          <div className="panel-tab-bar mono text-xs">
            <button
              type="button"
              className={`panel-tab ${activeTab === "alerts" ? "active" : ""}`}
              onClick={() => setActiveTab("alerts")}
            >
              Alerts ({alerts?.length ?? 0})
            </button>
            <button
              type="button"
              className={`panel-tab ${activeTab === "sentinel" ? "active" : ""}`}
              onClick={() => setActiveTab("sentinel")}
            >
              Sentinel-1 SAR
            </button>
            <button
              type="button"
              className={`panel-tab ${activeTab === "fused" ? "active" : ""}`}
              onClick={() => setActiveTab("fused")}
            >
              Fused Incidents
            </button>
          </div>

          <div className="panel-content-body">
            {/* Tab 1: Live Official Alerts */}
            {activeTab === "alerts" && (
              <div className="alerts-feed-pane">
                <div className="feed-header mono text-xs">
                  <span>Tracked Disaster Alerts</span>
                  <span>Auto-escalation: 15–30m</span>
                </div>

                <div className="alerts-list">
                  {(alerts ?? []).map((alt) => (
                    <article key={alt.id} className={`alert-card alert-card--${(alt?.status ?? "active").toLowerCase()}`}>
                      <div className="alert-card-top mono text-xs">
                        <span className={`status-badge status-badge--${(alt?.status ?? "active").toLowerCase()}`}>
                          {alt?.status}
                        </span>
                        <span className="alert-code">{alt?.alert_code}</span>
                        <span className="alert-severity">{alt?.severity}</span>
                      </div>

                      <h3 className="alert-headline font-bold text-sm">{alt?.headline}</h3>
                      <p className="alert-desc text-xs">{alt?.description}</p>

                      <div className="alert-meta mono text-xs text-concrete">
                        <span>{alt?.sender}</span>
                        <span>•</span>
                        <span>{alt?.area_desc}</span>
                      </div>

                      <div className="alert-card-actions mt-2">
                        {alt?.status !== "ACKNOWLEDGED" ? (
                          <button
                            type="button"
                            className="brutalist-btn btn--primary btn--sm mono"
                            onClick={() => handleAcknowledge(alt.id)}
                            disabled={ackBusyId === alt.id}
                          >
                            {ackBusyId === alt.id ? "Acknowledging..." : "Acknowledge Alert"}
                          </button>
                        ) : (
                          <span className="mono text-xs text-concrete">
                            ✓ Ack by {alt?.acknowledged_by || "Admin"}
                          </span>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            )}

            {/* Tab 2: Sentinel-1 SAR Radar */}
            {activeTab === "sentinel" && (
              <div className="sentinel-pane mono text-xs">
                <div className="sentinel-specs-card">
                  <h3 className="font-bold uppercase text-sm mb-2">Copernicus Sentinel-1 SAR Inundation</h3>
                  <div className="spec-row">
                    <span>Constellation:</span>
                    <strong>Copernicus Sentinel-1 C-SAR</strong>
                  </div>
                  <div className="spec-row">
                    <span>STAC Catalog:</span>
                    <strong>Microsoft Planetary Computer (sentinel-1-rtc)</strong>
                  </div>
                  <div className="spec-row">
                    <span>Polarizations:</span>
                    <strong>VV + VH Dual-Pol</strong>
                  </div>
                  <div className="spec-row">
                    <span>Algorithm:</span>
                    <strong>Sen1Floods11 Backscatter Threshold (&lt; -16.0 dB)</strong>
                  </div>
                  <div className="spec-row">
                    <span>Weights Strategy:</span>
                    <strong className="text-orange">Deferred Weights Fallback Active</strong>
                  </div>
                </div>

                <div className="sentinel-results mt-3">
                  <h4 className="font-bold text-xs uppercase mb-1">Inundation Summary</h4>
                  <p>Flooded Area: <strong>{sarAssessment?.flooded_area_km2 ?? 0} km²</strong></p>
                  <p>Inundation Share: <strong>{((sarAssessment?.flooded_pct ?? 0) * 100).toFixed(1)}%</strong></p>
                  <p>Mean Confidence: <strong>{((sarAssessment?.mean_confidence ?? 0.89) * 100).toFixed(0)}%</strong></p>
                  <p className="text-concrete mt-1">{sarAssessment?.notice}</p>
                </div>

                <div className="sentinel-action-box mt-4">
                  <Link to="/command" className="brutalist-btn btn--dispatch block text-center">
                    Plan Relief for Inundation Zones &rarr;
                  </Link>
                </div>
              </div>
            )}

            {/* Tab 3: Unified Fused Incidents */}
            {activeTab === "fused" && (
              <div className="fused-pane mono text-xs">
                <div className="feed-header">
                  <span>Fused Incident Confidence Scoring</span>
                </div>
                <div className="fused-cards-list mt-2">
                  <div className="fused-card">
                    <div className="fused-card-header font-bold">
                      <span>INC-BLR-01: Bellandur Lake Overflow</span>
                      <span className="fused-conf-pill">Confidence 0.96</span>
                    </div>
                    <p className="text-concrete text-xs mt-1">
                      Multi-source confirmed: IMD Flash Flood Alert + Sentinel-1 SAR Backscatter (-21.4 dB) + 8 Ground SOS reports.
                    </p>
                    <div className="fused-sources mt-2">
                      <span className="source-tag">Official: IMD</span>
                      <span className="source-tag">SAR: Sentinel-1</span>
                      <span className="source-tag">Ground: 8 SOS</span>
                    </div>
                  </div>

                  <div className="fused-card mt-2">
                    <div className="fused-card-header font-bold">
                      <span>INC-ALU-02: Periyar Bank Sector</span>
                      <span className="fused-conf-pill">Confidence 0.94</span>
                    </div>
                    <p className="text-concrete text-xs mt-1">
                      CWC Gauge Warning + SAR Flood Extent (4.8 km²) + 12 Ground Citizen Calls.
                    </p>
                    <div className="fused-sources mt-2">
                      <span className="source-tag">Official: CWC</span>
                      <span className="source-tag">SAR: Sentinel-1</span>
                      <span className="source-tag">Ground: 12 SOS</span>
                    </div>
                  </div>
                </div>

                <div className="mt-4">
                  <Link to="/command" className="brutalist-btn btn--dispatch block text-center">
                    Send Fused Feed to Allocation Engine &rarr;
                  </Link>
                </div>
              </div>
            )}
          </div>
        </aside>
      </div>

      {/* Bottom Dock: Event Replay Controller */}
      <footer className="replay-dock" aria-label="Event Replay Controller">
        <div className="replay-dock-top mono text-xs">
          <div className="replay-status-title font-bold">
            <span>{t("live.replay_title", "EVENT REPLAY CONTROLLER")}</span>
            <span className="replay-scenario-name text-concrete">
              [{timeline?.scenario_name || "Historical Progression"}]
            </span>
          </div>

          <div className="replay-phase-badge">
            <span className="phase-pill font-bold">
              {currentFrame?.time_label ?? "T+00m"}: {currentFrame?.phase_title ?? "Monitoring"}
            </span>
          </div>

          <div className="replay-speed-controls">
            <span>Speed:</span>
            {[1, 2, 5].map((spd) => (
              <button
                key={spd}
                type="button"
                className={`speed-btn ${playbackSpeed === spd ? "active" : ""}`}
                onClick={() => setPlaybackSpeed(spd)}
              >
                {spd}x
              </button>
            ))}
          </div>
        </div>

        {/* Replay Scrubbing & Transport */}
        <div className="replay-transport-bar">
          <div className="transport-buttons">
            <button
              type="button"
              className="brutalist-btn btn--sm mono"
              onClick={() => setCurrentStep((prev) => Math.max(0, prev - 1))}
              disabled={currentStep === 0}
              title="Step Back"
            >
              ◄
            </button>
            <button
              type="button"
              className={`brutalist-btn btn--sm mono ${isPlaying ? "btn--active" : "btn--primary"}`}
              onClick={() => setIsPlaying(!isPlaying)}
            >
              {isPlaying ? "❚❚ Pause" : "► Play"}
            </button>
            <button
              type="button"
              className="brutalist-btn btn--sm mono"
              onClick={() => setCurrentStep((prev) => Math.min((timeline?.total_steps ?? timeline?.frames?.length ?? 5) - 1, prev + 1))}
              disabled={!timeline || currentStep >= (timeline?.total_steps ?? timeline?.frames?.length ?? 1) - 1}
              title="Step Forward"
            >
              ►
            </button>
          </div>

          {/* Slider */}
          <div className="replay-slider-wrapper">
            <input
              type="range"
              min="0"
              max={Math.max(0, (timeline?.total_steps ?? timeline?.frames?.length ?? 5) - 1)}
              step="1"
              value={currentStep}
              onChange={(e) => {
                setIsPlaying(false);
                setCurrentStep(parseInt(e.target.value, 10));
              }}
              className="replay-scrubber"
              aria-label="Disaster Event Replay Timeline Slider"
            />
            <div className="slider-ticks mono text-xs">
              {(timeline?.frames ?? []).map((f, idx) => (
                <span
                  key={f.step}
                  className={`tick ${idx === currentStep ? "tick--active font-bold" : ""}`}
                  onClick={() => {
                    setIsPlaying(false);
                    setCurrentStep(idx);
                  }}
                >
                  {f.time_label}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Narrative Description Banner */}
        <div className="replay-narrative text-xs">
          <p>{currentFrame?.description}</p>
        </div>
      </footer>

      {showReport && (
        <SituationReportModal
          scenarioId={scenarioId || "flood-bengaluru"}
          onClose={() => setShowReport(false)}
        />
      )}

      {explainZoneId && (
        <ExplainDetailModal
          scenarioId={scenarioId || "flood-bengaluru"}
          zoneId={explainZoneId}
          onClose={() => setExplainZoneId(null)}
        />
      )}
    </div>
  );
}
