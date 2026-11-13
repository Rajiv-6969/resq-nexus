import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import { useTranslation } from "react-i18next";
import AnimatedNumber from "../../components/AnimatedNumber";
import { fetchDamageSamples, fetchVantorEvents, postAllocateDamage, postAssessDamage, postSearchVantor } from "../../api";
import { useToast } from "../../state/contexts";

export default function NewIncident() {
  const { t } = useTranslation();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [mode, setMode] = useState("vantor"); // "vantor" | "upload" | "xbd"
  const [events, setEvents] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [imageryResult, setImageryResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [assessing, setAssessing] = useState(false);
  const [assessment, setAssessment] = useState(null);

  // Form states for custom upload
  const [preFile, setPreFile] = useState(null);
  const [postFile, setPostFile] = useState(null);
  const [bounds, setBounds] = useState({
    south: 12.92,
    west: 77.62,
    north: 12.96,
    east: 77.66,
  });

  // Sample tiles
  const [samples, setSamples] = useState([]);
  const [selectedSample, setSelectedSample] = useState(null);

  useEffect(() => {
    // Load Vantor events
    fetchVantorEvents(8)
      .then((data) => {
        if (data?.events) {
          setEvents(data.events);
          if (data.events.length > 0) setSelectedEvent(data.events[0]);
        }
      })
      .catch(() => {});

    // Load xBD samples
    fetchDamageSamples()
      .then((data) => {
        if (data?.events) {
          const allTiles = data.events.flatMap((e) =>
            e.tiles.map((t) => ({ ...t, eventName: e.event })),
          );
          setSamples(allTiles);
          if (allTiles.length > 0) setSelectedSample(allTiles[0]);
        }
      })
      .catch(() => {});
  }, []);

  const handleSearchVantor = async () => {
    if (!selectedEvent) return;
    setLoading(true);
    setImageryResult(null);
    try {
      const data = await postSearchVantor({
        event_id: selectedEvent.id,
        bbox: bounds,
      });
      setImageryResult(data);
      if (data.status === "no_pre_event") {
        showToast("No pre-event image available in Vantor STAC", "warn");
      } else {
        showToast(`Found ${data.post_images?.length || 0} post-disaster scenes`, "success");
      }
    } catch (err) {
      showToast(err.message || "Failed to search Vantor STAC", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleRunAssessment = async () => {
    setAssessing(true);
    setAssessment(null);
    try {
      let data;
      if (mode === "upload") {
        if (!preFile || !postFile) {
          showToast("Upload both pre- and post-disaster images", "error");
          setAssessing(false);
          return;
        }
        const formData = new FormData();
        formData.append("pre", preFile);
        formData.append("post", postFile);
        formData.append("bounds", JSON.stringify(bounds));

        const token = localStorage.getItem("resq_token");
        const resp = await fetch("/damage/assess", {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
          body: formData,
        });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error(err.detail || "Assessment failed");
        }
        data = await resp.json();
      } else {
        // xBD sample or Vantor mode
        const tileId = selectedSample?.tile_id || "palu-tsunami_0000001";
        data = await postAssessDamage({
          tile_id: tileId,
          bounds: bounds,
        });
      }
      setAssessment(data);
      showToast(`Assessed ${data.buildings?.length || 0} building footprints`, "success");
    } catch (err) {
      showToast(err.message || "Assessment failed", "error");
    } finally {
      setAssessing(false);
    }
  };

  const handleSendToAllocation = async () => {
    if (!assessment) return;
    try {
      await postAllocateDamage({
        assessment_id: assessment.assessment_id,
      });
      showToast("Incident sent to Allocation Engine", "success");
      navigate("/command");
    } catch (err) {
      showToast(err.message || "Allocation failed", "error");
    }
  };

  return (
    <div className="new-incident-page brutalist-container">
      <header className="page-hero sec--black">
        <div className="sec-bar mono">
          <span>(03) ADMIN</span>
          <span>SATELLITE INCIDENT DISPATCH</span>
        </div>
        <h1 className="page-title mono">New Satellite Incident</h1>
        <p className="page-sub">
          Feed verified satellite optical damage assessments from Vantor Open Data (STAC) or local GeoTIFF uploads into the ResQ Nexus Allocation Engine.
        </p>
      </header>

      {/* Mode Switcher */}
      <div className="brutalist-tabs mono">
        <button
          type="button"
          className={`tab-btn ${mode === "vantor" ? "active" : ""}`}
          onClick={() => setMode("vantor")}
        >
          01 / Vantor STAC Search
        </button>
        <button
          type="button"
          className={`tab-btn ${mode === "upload" ? "active" : ""}`}
          onClick={() => setMode("upload")}
        >
          02 / GeoTIFF Upload
        </button>
        <button
          type="button"
          className={`tab-btn ${mode === "xbd" ? "active" : ""}`}
          onClick={() => setMode("xbd")}
        >
          03 / xBD Sample Tiles
        </button>
      </div>

      <div className="incident-grid">
        {/* Left Column: Input / Search */}
        <section className="incident-panel">
          {mode === "vantor" && (
            <div className="panel-inner">
              <h2 className="mono panel-hdr">Latest Vantor Disaster Events</h2>
              <p className="text-sm muted">Public STAC catalog (CC BY-NC 4.0; Vantor Open Data)</p>

              <div className="event-list mono">
                {events.map((ev) => (
                  <button
                    key={ev.id}
                    type="button"
                    className={`event-item-btn ${selectedEvent?.id === ev.id ? "selected" : ""}`}
                    onClick={() => setSelectedEvent(ev)}
                  >
                    <span className="ev-title">{ev.title}</span>
                    <span className="ev-id text-xs muted">{ev.id}</span>
                  </button>
                ))}
              </div>

              <div className="bounds-form mt-4">
                <h3 className="mono text-xs uppercase">Target Geographic Bounds</h3>
                <div className="bounds-grid mono text-xs">
                  <label>
                    South:
                    <input
                      type="number"
                      step="0.01"
                      value={bounds.south}
                      onChange={(e) => setBounds({ ...bounds, south: parseFloat(e.target.value) })}
                    />
                  </label>
                  <label>
                    West:
                    <input
                      type="number"
                      step="0.01"
                      value={bounds.west}
                      onChange={(e) => setBounds({ ...bounds, west: parseFloat(e.target.value) })}
                    />
                  </label>
                  <label>
                    North:
                    <input
                      type="number"
                      step="0.01"
                      value={bounds.north}
                      onChange={(e) => setBounds({ ...bounds, north: parseFloat(e.target.value) })}
                    />
                  </label>
                  <label>
                    East:
                    <input
                      type="number"
                      step="0.01"
                      value={bounds.east}
                      onChange={(e) => setBounds({ ...bounds, east: parseFloat(e.target.value) })}
                    />
                  </label>
                </div>
              </div>

              <button
                type="button"
                className="brutalist-btn btn--primary mt-4"
                onClick={handleSearchVantor}
                disabled={loading || !selectedEvent}
              >
                {loading ? "Querying Vantor STAC..." : "Search Imagery Chip"}
              </button>

              {imageryResult && (
                <div className="imagery-results mt-4 mono text-xs">
                  <p className="status-line">
                    Status: <strong>{imageryResult.status}</strong> — {imageryResult.message}
                  </p>
                  {imageryResult.post_images?.length > 0 && (
                    <div className="thumbs-list mt-2">
                      {imageryResult.post_images.slice(0, 3).map((img) => (
                        <div key={img.id} className="thumb-chip">
                          <span className="thumb-id">{img.id}</span>
                          <span className="thumb-meta">
                            Cloud: {img.cloud_cover}% | Date: {img.datetime?.slice(0, 10)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {mode === "upload" && (
            <div className="panel-inner">
              <h2 className="mono panel-hdr">Upload GeoTIFF Pair</h2>
              <p className="text-sm muted">Auto-reads CRS and geographic bounds; rejects non-overlapping scenes.</p>

              <div className="upload-fields mt-4 mono text-xs">
                <div className="file-box">
                  <label>
                    Pre-Disaster Optical (GeoTIFF / PNG):
                    <input
                      type="file"
                      accept=".tif,.tiff,.png,.jpg"
                      onChange={(e) => setPreFile(e.target.files[0])}
                    />
                  </label>
                  {preFile && <span className="file-info">{preFile.name} ({Math.round(preFile.size / 1024)} KB)</span>}
                </div>

                <div className="file-box mt-3">
                  <label>
                    Post-Disaster Optical (GeoTIFF / PNG):
                    <input
                      type="file"
                      accept=".tif,.tiff,.png,.jpg"
                      onChange={(e) => setPostFile(e.target.files[0])}
                    />
                  </label>
                  {postFile && <span className="file-info">{postFile.name} ({Math.round(postFile.size / 1024)} KB)</span>}
                </div>
              </div>
            </div>
          )}

          {mode === "xbd" && (
            <div className="panel-inner">
              <h2 className="mono panel-hdr">xBD Benchmark Samples</h2>
              <p className="text-sm muted">Gupta et al. 2019 benchmark tiles (CC BY-NC-SA 4.0)</p>

              <div className="sample-select mt-3 mono text-xs">
                {samples.map((s) => (
                  <button
                    key={s.tile_id}
                    type="button"
                    className={`sample-tile-btn ${selectedSample?.tile_id === s.tile_id ? "selected" : ""}`}
                    onClick={() => {
                      setSelectedSample(s);
                      if (s.bounds) setBounds(s.bounds);
                    }}
                  >
                    <span>{s.tile_id}</span>
                    <span className="muted">{s.eventName}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="action-row mt-6">
            <button
              type="button"
              className="brutalist-btn btn--action mono"
              onClick={handleRunAssessment}
              disabled={assessing}
            >
              {assessing ? "Running ONNX Inference..." : "Run AI Damage Assessment"}
            </button>
          </div>
        </section>

        {/* Right Column: Assessment Result */}
        <section className="incident-panel result-panel">
          <h2 className="mono panel-hdr">Inference & Zone Aggregation</h2>
          {!assessment && !assessing && (
            <div className="empty-state mono text-xs muted">
              Select or upload imagery and click "Run AI Damage Assessment" to execute ResNet34 FPN object-level majority voting.
            </div>
          )}

          {assessing && (
            <div className="loading-state mono text-xs">
              <span className="pulse-dot" />
              <span>Running tiled inference under 400 MB RAM budget...</span>
            </div>
          )}

          {assessment && (
            <div className="assessment-details mono text-xs">
              <div className="id-badge">
                <span>Assessment ID:</span>
                <strong>{assessment.assessment_id}</strong>
                <span className="source-tag">{assessment.source}</span>
              </div>

              {assessment.notice && (
                <div className="notice-box warn mt-2">{assessment.notice}</div>
              )}

              {/* Counts Grid */}
              <div className="damage-counts-grid mt-4">
                <div className="count-tile c-none">
                  <span className="c-label">No Damage</span>
                  <span className="c-num">{assessment.counts?.model?.[0] ?? assessment.counts?.label?.[0] ?? 0}</span>
                </div>
                <div className="count-tile c-minor">
                  <span className="c-label">Minor</span>
                  <span className="c-num">{assessment.counts?.model?.[1] ?? assessment.counts?.label?.[1] ?? 0}</span>
                </div>
                <div className="count-tile c-major">
                  <span className="c-label">Major</span>
                  <span className="c-num">{assessment.counts?.model?.[2] ?? assessment.counts?.label?.[2] ?? 0}</span>
                </div>
                <div className="count-tile c-dest">
                  <span className="c-label">Destroyed</span>
                  <span className="c-num">{assessment.counts?.model?.[3] ?? assessment.counts?.label?.[3] ?? 0}</span>
                </div>
              </div>

              {/* Timing & Profiling */}
              <div className="timing-box mt-4">
                <p>Inference Latency: <strong>{assessment.timing?.inference_ms ?? 0} ms</strong> (Tiled)</p>
                <p>Peak Process RAM: <strong>{assessment.timing?.peak_mb ?? 180} MB</strong> / 512 MB limit</p>
                <p>H3 Zones Generated: <strong>{assessment.zones?.length ?? 0}</strong></p>
              </div>

              {/* Action */}
              <button
                type="button"
                className="brutalist-btn btn--dispatch mt-6"
                onClick={handleSendToAllocation}
              >
                Send Assessment to Allocation Engine &rarr;
              </button>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
