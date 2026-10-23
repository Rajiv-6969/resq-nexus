import { useEffect, useMemo, useRef } from "react";
import { CircleMarker, MapContainer, Marker, Pane, Polygon, Polyline, TileLayer, Tooltip, useMap, ZoomControl } from "react-leaflet";
import L from "leaflet";
import { AnimatePresence, motion } from "framer-motion";
import { LEVEL_COLORS, PIPELINE_STEPS, PRIORITY_LEVELS, SEVERITY_LABELS, clusterColor, formatNumber, formatScore } from "../constants";
import { convexHull, padHull } from "../lib/geo";
import { prefersReducedMotion } from "../lib/hooks";
import { LayersIcon } from "./icons";

const INDIA_VIEW = { center: [22.5, 80.5], zoom: 5 };
const MIN_RADIUS = 6;
const MAX_EXTRA_RADIUS = 17;
const LAYER_LABELS = { routes: "Routes", clusters: "Depot areas", roads: "Road network", hazard: "Hazard" };

// Circle area grows with population (radius ~ sqrt), the usual proportional-symbol rule.
const radiusFor = (population, maxPopulation) =>
  MIN_RADIUS + MAX_EXTRA_RADIUS * Math.sqrt(population / Math.max(maxPopulation, 1));

const EPICENTRE_HTML =
  '<span class="hazard-glyph hazard-glyph--quake"><svg viewBox="0 0 24 24" width="26" height="26"><circle cx="12" cy="12" r="10" fill="rgba(11,16,32,.85)" stroke="#F4A261" stroke-width="1.6"/><circle cx="12" cy="12" r="5.5" fill="none" stroke="#F4A261" stroke-width="1.6"/><circle cx="12" cy="12" r="2" fill="#FFD166"/></svg></span>';
const HOTSPOT_HTML =
  '<span class="hazard-glyph hazard-glyph--fire"><svg viewBox="0 0 24 24" width="26" height="26"><circle cx="12" cy="12" r="11" fill="rgba(11,16,32,.85)" stroke="#FF6B35" stroke-width="1.4"/><path d="M12 4.5c.8 2.8 4 4.4 4 8.4a4 4 0 0 1-8 0c0-2 1-3.2 2-4.4.2 1.3.8 2.1 1.6 2.4.2-2.4-.4-4.4.4-6.4z" fill="#FF6B35" stroke="#FFD166" stroke-width=".8"/></svg></span>';

// Icons are cached so re-renders never restart their CSS animations.
const iconCache = new Map();
function cachedIcon(key, make) {
  if (!iconCache.has(key)) iconCache.set(key, make());
  return iconCache.get(key);
}
const hazardIcon = (html) =>
  cachedIcon(`hazard:${html}`, () => L.divIcon({ className: "hazard-icon", html, iconSize: [26, 26], iconAnchor: [13, 13] }));
const pulseIcon = (radius) =>
  cachedIcon(`pulse:${radius}`, () =>
    L.divIcon({
      className: "pulse-icon",
      html: '<span class="pulse-ring"></span><span class="pulse-ring pulse-ring--late"></span>',
      iconSize: [radius * 2, radius * 2],
      iconAnchor: [radius, radius],
    }),
  );

function hazardMarkers(hazard) {
  if (!hazard) return [];
  if (hazard.epicentre) {
    return [{ key: "epicentre", position: hazard.epicentre, html: EPICENTRE_HTML, label: `Epicentre (M${hazard.magnitude})` }];
  }
  if (hazard.hotspots) {
    return hazard.hotspots.map((h, i) => ({ key: `hotspot-${i}`, position: h, html: HOTSPOT_HTML, label: "Fire ignition area" }));
  }
  return [];
}

function FitToZones({ zones, scenarioId }) {
  const map = useMap();
  const fitted = useRef(null);
  useEffect(() => {
    if (!zones.length || fitted.current === scenarioId) return;
    fitted.current = scenarioId;
    map.fitBounds(L.latLngBounds(zones.map((z) => [z.latitude, z.longitude])), { padding: [56, 56], maxZoom: 11 });
  }, [map, zones, scenarioId]);
  return null;
}

function PanToSelected({ zone }) {
  const map = useMap();
  useEffect(() => {
    if (!zone) return;
    const target = L.latLng(zone.latitude, zone.longitude);
    if (!map.getBounds().pad(-0.18).contains(target)) map.panTo(target, { animate: true });
  }, [map, zone]);
  return null;
}

// Leaflet needs to be told when its container changes size (panel toggles, window resize).
function KeepSized() {
  const map = useMap();
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize({ pan: false }));
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  return null;
}

// A route from depot to zone that draws itself in, then shows supplies flowing along it.
function AnimatedRoute({ positions, color, delay, dim, highlight }) {
  const lineRef = useRef(null);
  const flowRef = useRef(null);

  useEffect(() => {
    const line = lineRef.current?.getElement();
    const flow = flowRef.current?.getElement();
    if (!line || prefersReducedMotion() || typeof line.animate !== "function") return undefined;
    const length = line.getTotalLength();
    line.style.strokeDasharray = `${length}`;
    line.style.strokeDashoffset = `${length}`;
    const draw = line.animate([{ strokeDashoffset: length }, { strokeDashoffset: 0 }], {
      duration: 1100,
      delay,
      easing: "cubic-bezier(.2,.7,.2,1)",
      fill: "forwards",
    });
    const reveal = flow?.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 500, delay: delay + 900, fill: "both" });
    const reset = () => {
      line.style.strokeDasharray = "";
      line.style.strokeDashoffset = "";
    };
    draw.onfinish = () => {
      reset();
      draw.cancel();
    };
    return () => {
      draw.cancel();
      reveal?.cancel();
      reset();
    };
  }, [delay]);

  return (
    <>
      <Polyline
        ref={lineRef}
        pane="routes"
        positions={positions}
        interactive={false}
        pathOptions={{ color, weight: highlight ? 5 : 2.8, opacity: dim ? 0.2 : 0.92, lineCap: "round", lineJoin: "round", className: "route-line" }}
      />
      <Polyline
        ref={flowRef}
        pane="routes"
        positions={positions}
        interactive={false}
        pathOptions={{ color: "#ffffff", weight: highlight ? 2.2 : 1.3, opacity: dim ? 0.08 : 0.6, dashArray: "2 12", lineCap: "round", className: "route-flow" }}
      />
    </>
  );
}

// Zone circles can be reached with Tab and selected with Enter or Space.
function makeFocusable(layer, name) {
  const el = layer.getElement();
  if (!el) return;
  el.setAttribute("tabindex", "0");
  el.setAttribute("role", "button");
  el.setAttribute("aria-label", name);
}

function MapLegend({ allocation, hazard }) {
  return (
    <div className="map-legend glass-dense" aria-label="Map legend">
      <p className="legend-title">Priority</p>
      <ul className="legend-levels">
        {PRIORITY_LEVELS.map((level) => (
          <li key={level}>
            <span className="legend-dot" style={{ background: LEVEL_COLORS[level].fill, boxShadow: `0 0 8px ${LEVEL_COLORS[level].glow}` }} />
            {level}
          </li>
        ))}
      </ul>
      <p className="legend-row">
        <span className="legend-sizes" aria-hidden="true">
          <span />
          <span />
          <span />
        </span>
        Size = population
      </p>
      {allocation && (
        <>
          <p className="legend-row">
            <span className="legend-depot" aria-hidden="true">A</span> Relief depot
          </p>
          <p className="legend-row">
            <span className="legend-route" aria-hidden="true" /> Route · ring = depot area
          </p>
        </>
      )}
      {hazard?.epicentre && <p className="legend-row legend-row--hazard">◎ Epicentre</p>}
      {hazard?.hotspots && <p className="legend-row legend-row--hazard">▲ Ignition area</p>}
    </div>
  );
}

function LayerToggles({ layers, onToggle, allocation, hazard }) {
  const available = { routes: Boolean(allocation), clusters: Boolean(allocation), roads: Boolean(allocation), hazard: Boolean(hazard?.epicentre || hazard?.hotspots) };
  return (
    <fieldset className="layer-toggles glass-dense">
      <legend>
        <LayersIcon size={14} /> Layers
      </legend>
      {Object.keys(LAYER_LABELS).map((key) => (
        <label key={key} className={available[key] ? "" : "is-disabled"}>
          <input type="checkbox" checked={layers[key] && available[key]} disabled={!available[key]} onChange={() => onToggle(key)} />
          <span className="toggle-track" aria-hidden="true" />
          {LAYER_LABELS[key]}
        </label>
      ))}
    </fieldset>
  );
}

export default function CommandMap({ scenarioId, zones, hazard, allocation, stale, selectedZoneId, onSelectZone, layers, onToggleLayer, loading, pipeline }) {
  const maxPopulation = useMemo(() => Math.max(0, ...zones.map((z) => z.population)), [zones]);
  const selectedZone = zones.find((z) => z.id === selectedZoneId) ?? null;
  const hazardList = hazardMarkers(hazard);
  const running = pipeline.status === "running";

  const depotIndex = useMemo(() => Object.fromEntries((allocation?.depots ?? []).map((d, i) => [d.id, i])), [allocation]);
  const plans = useMemo(() => Object.fromEntries((allocation?.zones ?? []).map((z) => [z.id, z.engine])), [allocation]);
  const nodes = useMemo(() => {
    const out = {};
    (allocation?.zones ?? []).forEach((z) => (out[z.id] = [z.latitude, z.longitude]));
    (allocation?.depots ?? []).forEach((d) => (out[d.id] = [d.latitude, d.longitude]));
    return out;
  }, [allocation]);

  const hulls = useMemo(() => {
    if (!allocation) return [];
    return allocation.depots.map((d, i) => {
      const points = d.zone_ids.map((id) => nodes[id]).filter(Boolean).concat([[d.latitude, d.longitude]]);
      return { id: d.id, color: clusterColor(i), points: padHull(convexHull(points)) };
    });
  }, [allocation, nodes]);

  // Routes to zones that receive relief, drawn outward from the depots (shortest trips first).
  const routes = useMemo(() => {
    if (!allocation) return [];
    return allocation.zones
      .filter((z) => Object.values(z.engine.allocated).some((v) => v > 0))
      .sort((a, b) => a.engine.travel_time_min - b.engine.travel_time_min)
      .map((z, i) => ({ id: z.id, positions: z.engine.route_coords, color: clusterColor(depotIndex[z.engine.depot_id] ?? 0), delay: 150 + i * 90 }));
  }, [allocation, depotIndex]);

  const depotIcons = useMemo(
    () =>
      (allocation?.depots ?? []).map((d, i) =>
        L.divIcon({
          className: "depot-icon",
          html: `<span class="depot-pin" style="--c:${clusterColor(i)}"><span>${d.label}</span></span>`,
          iconSize: [36, 36],
          iconAnchor: [18, 18],
        }),
      ),
    [allocation],
  );

  // Draw big circles first so small ones stay clickable.
  const drawOrder = useMemo(() => [...zones].sort((a, b) => b.population - a.population), [zones]);
  const runKey = allocation ? `${allocation.scenario_id}-${allocation.weights ? Object.values(allocation.weights).join("-") : ""}` : "none";

  return (
    <div className={`map-pane${stale ? " is-stale" : ""}`}>
      <MapContainer className="map" center={INDIA_VIEW.center} zoom={INDIA_VIEW.zoom} scrollWheelZoom zoomControl={false} aria-label="Map of affected zones">
        <TileLayer
          className="tiles-dark"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        <ZoomControl position="bottomright" />
        <FitToZones zones={zones} scenarioId={scenarioId} />
        <PanToSelected zone={selectedZone} />
        <KeepSized />

        <Pane name="hulls" style={{ zIndex: 350 }} />
        <Pane name="roads" style={{ zIndex: 360 }} />
        <Pane name="routes" style={{ zIndex: 380 }} />
        <Pane name="pulses" style={{ zIndex: 390 }} />

        {allocation && layers.clusters &&
          hulls.map((h) =>
            h.points.length >= 3 ? (
              <Polygon key={`hull-${runKey}-${h.id}`} pane="hulls" positions={h.points} interactive={false}
                pathOptions={{ color: h.color, weight: 1.4, opacity: 0.75, dashArray: "6 7", fillColor: h.color, fillOpacity: 0.07, className: "hull" }} />
            ) : null,
          )}

        {allocation && layers.roads &&
          allocation.roads.map((r) =>
            nodes[r.from] && nodes[r.to] ? (
              <Polyline key={`road-${runKey}-${r.from}-${r.to}`} pane="roads" positions={[nodes[r.from], nodes[r.to]]} interactive={false}
                pathOptions={{ color: "#8ea2d8", weight: 1, opacity: 0.28, dashArray: "1 5", className: "road" }} />
            ) : null,
          )}

        {allocation && layers.routes &&
          routes.map((r) => (
            <AnimatedRoute
              key={`route-${runKey}-${r.id}`}
              positions={r.positions}
              color={r.color}
              delay={r.delay}
              dim={Boolean(selectedZoneId && selectedZoneId !== r.id) || stale}
              highlight={selectedZoneId === r.id}
            />
          ))}

        {zones
          .filter((z) => z.priority_level === "Critical")
          .map((z) => {
            const r = Math.round(radiusFor(z.population, maxPopulation));
            return (
              <Marker key={`pulse-${z.id}`} pane="pulses" position={[z.latitude, z.longitude]} interactive={false} keyboard={false} icon={pulseIcon(r)} />
            );
          })}

        {drawOrder.map((zone) => {
          const colors = LEVEL_COLORS[zone.priority_level];
          const radius = radiusFor(zone.population, maxPopulation);
          const plan = plans[zone.id];
          const ring = plan && layers.clusters ? clusterColor(depotIndex[plan.depot_id] ?? 0) : colors.stroke;
          return (
            <CircleMarker
              key={zone.id}
              center={[zone.latitude, zone.longitude]}
              radius={radius}
              pathOptions={{ color: ring, weight: plan ? 2.4 : 1.4, fillColor: colors.fill, fillOpacity: 0.84, className: `zone-dot zone-dot--${zone.priority_level.toLowerCase()}` }}
              eventHandlers={{
                click: () => onSelectZone(zone.id),
                keypress: (e) => {
                  if (e.originalEvent.key === "Enter" || e.originalEvent.key === " ") {
                    e.originalEvent.preventDefault();
                    onSelectZone(zone.id);
                  }
                },
                add: (e) => makeFocusable(e.target, zone.name),
              }}
            >
              <Tooltip direction="top" offset={[0, -radius]} className="zone-tooltip">
                <strong>{zone.name}</strong>
                <span className="tt-level" style={{ color: colors.fill }}>
                  {zone.priority_level} · {formatScore(zone.priority_score)}
                </span>
                <span>
                  {SEVERITY_LABELS[zone.damage_severity]} damage · {formatNumber(zone.population)} people
                </span>
                {plan && plan.coverage_pct != null && (
                  <span>
                    {plan.coverage_pct.toFixed(0)}% covered · {Math.round(plan.travel_time_min)} min from {allocation.depots[depotIndex[plan.depot_id]]?.name}
                  </span>
                )}
              </Tooltip>
            </CircleMarker>
          );
        })}

        {selectedZone && (
          <CircleMarker
            key={`selected-${selectedZone.id}`}
            center={[selectedZone.latitude, selectedZone.longitude]}
            radius={radiusFor(selectedZone.population, maxPopulation) + 6}
            interactive={false}
            pathOptions={{ color: "#2EC4B6", weight: 3, fill: false, dashArray: "5 5", className: "selected-ring" }}
          />
        )}

        {allocation &&
          allocation.depots.map((d, i) => (
            <Marker key={`depot-${runKey}-${d.id}`} position={[d.latitude, d.longitude]} icon={depotIcons[i]} keyboard={false}>
              <Tooltip direction="top" offset={[0, -16]} className="zone-tooltip">
                <strong>{d.name}</strong>
                <span>
                  Serves {d.zone_ids.length} zone{d.zone_ids.length === 1 ? "" : "s"} · near {d.nearest_zone}
                </span>
              </Tooltip>
            </Marker>
          ))}

        {layers.hazard &&
          hazardList.map((m) => (
            <Marker key={m.key} position={[m.position.latitude, m.position.longitude]} icon={hazardIcon(m.html)} keyboard={false}>
              <Tooltip direction="top" offset={[0, -12]} className="zone-tooltip">
                {m.label}
              </Tooltip>
            </Marker>
          ))}
      </MapContainer>

      <LayerToggles layers={layers} onToggle={onToggleLayer} allocation={allocation} hazard={hazard} />
      <MapLegend allocation={allocation} hazard={hazard} />

      {stale && (
        <div className="map-stale" role="status">
          Weights changed since this plan was made: run the allocation again to update it.
        </div>
      )}

      <AnimatePresence>
        {running && (
          <motion.div className="map-running" role="status" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <div className="radar" aria-hidden="true">
              <span className="radar-sweep" />
              <span className="radar-ring" />
              <span className="radar-ring radar-ring--inner" />
            </div>
            <p className="map-running-title">Allocation Engine running</p>
            <p className="map-running-step">
              Step {Math.min(pipeline.step + 1, PIPELINE_STEPS.length)} of {PIPELINE_STEPS.length} · {PIPELINE_STEPS[Math.min(pipeline.step, 3)]?.name}
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {loading && (
        <div className="map-loading" role="status">
          <span className="spinner" aria-hidden="true" />
          Loading scenario…
        </div>
      )}
    </div>
  );
}
