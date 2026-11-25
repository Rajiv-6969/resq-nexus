import { useEffect, useMemo, useRef } from "react";
import { CircleMarker, MapContainer, Marker, Pane, Polygon, Polyline, TileLayer, Tooltip, useMap, ZoomControl } from "react-leaflet";
import L from "leaflet";
import { AnimatePresence, motion } from "framer-motion";
import { LEVEL_COLORS, PIPELINE_STEPS, PRIORITY_LEVELS, SEVERITY_LABELS, formatNumber, formatScore } from "../constants";
import { convexHull, padHull } from "../lib/geo";
import { prefersReducedMotion } from "../lib/hooks";
import { TILE_ATTRIBUTION, TILE_URL, toValidLatLng } from "../lib/map";
import { AsteriskMark } from "./icons";

const INDIA_VIEW = { center: [22.5, 80.5], zoom: 5 };
const MIN_RADIUS = 6;
const MAX_EXTRA_RADIUS = 17;
const LAYER_LABELS = { hexes: "Zone hexagons", routes: "Routes", clusters: "Depot areas", roads: "Road network", hazard: "Hazard" };

// GeoJSON Polygon (lon, lat) -> Leaflet positions (lat, lon).
const ringPositions = (geometry) => {
  if (geometry?.type !== "Polygon" || !Array.isArray(geometry?.coordinates?.[0])) return null;
  const positions = geometry.coordinates[0].map(([lon, lat]) => toValidLatLng([lat, lon])).filter(Boolean);
  return positions.length >= 3 ? positions : null;
};
const BLACK = "#0A0A0A";
const RED = "#E10600";
const GRAPHITE = "#5A5A57";

// Circle area grows with population (radius ~ sqrt), the usual proportional-symbol rule.
const radiusFor = (population, maxPopulation) =>
  MIN_RADIUS + MAX_EXTRA_RADIUS * Math.sqrt(population / Math.max(maxPopulation, 1));

const EPICENTRE_SVG =
  '<svg viewBox="0 0 24 24" width="24" height="24"><rect x="2" y="2" width="20" height="20" fill="#0A0A0A" stroke="#E10600" stroke-width="2"/><path d="M12 5v14M5 12h14" stroke="#E10600" stroke-width="2"/></svg>';
const HOTSPOT_SVG =
  '<svg viewBox="0 0 24 24" width="24" height="24"><path d="M12 2.5 22.5 21h-21z" fill="#FF6B1A" stroke="#0A0A0A" stroke-width="1.5" stroke-linejoin="miter"/></svg>';

// Icons are cached so re-renders never restart their CSS animations.
const iconCache = new Map();
function cachedIcon(key, make) {
  if (!iconCache.has(key)) iconCache.set(key, make());
  return iconCache.get(key);
}
const hazardIcon = (svg) =>
  cachedIcon(`hazard:${svg}`, () => L.divIcon({ className: "hazard-icon", html: svg, iconSize: [24, 24], iconAnchor: [12, 12] }));

// Square corner brackets that blink around a Critical zone.
const beaconIcon = (radius) =>
  cachedIcon(`beacon:${radius}`, () => {
    const s = radius * 2 + 14;
    const c = 6;
    const d = `M1 ${c + 1}V1h${c} M${s - c - 1} 1h${c}v${c} M${s - 1} ${s - c - 1}v${c}h-${c} M${c + 1} ${s - 1}H1v-${c}`;
    return L.divIcon({
      className: "beacon-icon",
      html: `<svg class="beacon" width="${s}" height="${s}" viewBox="0 0 ${s} ${s}"><path d="${d}" fill="none" stroke="${RED}" stroke-width="2"/></svg>`,
      iconSize: [s, s],
      iconAnchor: [s / 2, s / 2],
    });
  });

function hazardMarkers(hazard) {
  if (!hazard) return [];
  if (hazard.epicentre) {
    const pos = toValidLatLng(hazard.epicentre);
    if (pos) {
      return [{ key: "epicentre", position: pos, svg: EPICENTRE_SVG, label: `Epicentre (M${hazard.magnitude})` }];
    }
  }
  if (hazard.hotspots && Array.isArray(hazard.hotspots)) {
    return hazard.hotspots
      .map((h, i) => {
        const pos = toValidLatLng(h);
        return pos ? { key: `hotspot-${i}`, position: pos, svg: HOTSPOT_SVG, label: "Fire ignition area" } : null;
      })
      .filter(Boolean);
  }
  return [];
}

function FitToZones({ zones, scenarioId }) {
  const map = useMap();
  const fitted = useRef(null);
  useEffect(() => {
    if (!zones?.length || fitted.current === scenarioId) return;
    const validCoords = zones.map((z) => toValidLatLng([z.latitude, z.longitude])).filter(Boolean);
    if (!validCoords.length) return;
    fitted.current = scenarioId;
    if (validCoords.length === 1) {
      map.setView(validCoords[0], 11, { animate: false });
    } else {
      map.fitBounds(L.latLngBounds(validCoords), { padding: [56, 56], maxZoom: 11 });
    }
  }, [map, zones, scenarioId]);
  return null;
}

function PanToSelected({ zone }) {
  const map = useMap();
  useEffect(() => {
    if (!zone) return;
    const pos = toValidLatLng([zone.latitude, zone.longitude]);
    if (!pos) return;
    const target = L.latLng(pos[0], pos[1]);
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

// A solid route from depot to zone that draws itself in once.
function AnimatedRoute({ positions, delay, dim, highlight }) {
  const lineRef = useRef(null);
  const validPositions = (positions ?? []).map(toValidLatLng).filter(Boolean);

  useEffect(() => {
    const line = lineRef.current?.getElement();
    if (!line || prefersReducedMotion() || typeof line.animate !== "function") return undefined;
    const length = line.getTotalLength();
    line.style.strokeDasharray = `${length}`;
    line.style.strokeDashoffset = `${length}`;
    const draw = line.animate([{ strokeDashoffset: length }, { strokeDashoffset: 0 }], {
      duration: 650,
      delay,
      easing: "cubic-bezier(.7,0,.2,1)",
      fill: "forwards",
    });
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
      reset();
    };
  }, [delay]);

  if (validPositions.length < 2) return null;

  return (
    <Polyline
      ref={lineRef}
      pane="routes"
      positions={validPositions}
      interactive={false}
      pathOptions={{
        color: highlight ? RED : BLACK,
        weight: highlight ? 4 : 2.5,
        opacity: dim ? 0.25 : 0.9,
        lineCap: "butt",
        lineJoin: "miter",
        className: "route-line",
      }}
    />
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
    <div className="map-legend" aria-label="Map legend">
      <p className="legend-title">Priority</p>
      <ul className="legend-levels">
        {PRIORITY_LEVELS.map((level) => (
          <li key={level}>
            <span className="legend-swatch" style={{ background: LEVEL_COLORS[level].fill }} />
            {level}
          </li>
        ))}
      </ul>
      <p className="legend-row">
        <svg className="legend-sizes" width="30" height="16" viewBox="0 0 30 16" aria-hidden="true">
          <circle cx="4" cy="12" r="3" />
          <circle cx="12" cy="10.5" r="4.5" />
          <circle cx="23" cy="8.5" r="6.5" />
        </svg>
        Size = population
      </p>
      {allocation && (
        <>
          <p className="legend-row">
            <span className="legend-depot" aria-hidden="true">
              A
            </span>
            Relief depot
          </p>
          <p className="legend-row">
            <span className="legend-route" aria-hidden="true" />
            Route
          </p>
          <p className="legend-row">
            <span className="legend-hull" aria-hidden="true" />
            Depot area
          </p>
        </>
      )}
      {hazard?.epicentre && (
        <p className="legend-row">
          <span className="legend-glyph" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="14" height="14">
              <rect x="2" y="2" width="20" height="20" fill="#0A0A0A" stroke={RED} strokeWidth="2.5" />
              <path d="M12 5v14M5 12h14" stroke={RED} strokeWidth="2.5" />
            </svg>
          </span>
          Epicentre
        </p>
      )}
      {hazard?.hotspots && (
        <p className="legend-row">
          <span className="legend-glyph" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="14" height="14">
              <path d="M12 2.5 22.5 21h-21z" fill="#FF6B1A" />
            </svg>
          </span>
          Ignition area
        </p>
      )}
    </div>
  );
}

function LayerToggles({ layers, onToggle, allocation, hazard, hexes }) {
  const available = { hexes: Boolean(hexes), routes: Boolean(allocation), clusters: Boolean(allocation), roads: Boolean(allocation), hazard: Boolean(hazard?.epicentre || hazard?.hotspots) };
  return (
    <fieldset className="layer-toggles">
      <legend>Layers</legend>
      {Object.keys(LAYER_LABELS).map((key) => (
        <label key={key} className={available[key] ? "" : "is-disabled"}>
          <input type="checkbox" checked={layers[key] && available[key]} disabled={!available[key]} onChange={() => onToggle(key)} />
          <span className="toggle-box" aria-hidden="true" />
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
  const step = Math.min(pipeline.step ?? 0, PIPELINE_STEPS.length - 1);

  const depotById = useMemo(() => Object.fromEntries((allocation?.depots ?? []).map((d) => [d.id, d])), [allocation]);
  const plans = useMemo(() => Object.fromEntries((allocation?.zones ?? []).map((z) => [z.id, z.engine])), [allocation]);
  const nodes = useMemo(() => {
    const out = {};
    (allocation?.zones ?? []).forEach((z) => {
      const pos = toValidLatLng([z.latitude, z.longitude]);
      if (pos) out[z.id] = pos;
    });
    (allocation?.depots ?? []).forEach((d) => {
      const pos = toValidLatLng([d.latitude, d.longitude]);
      if (pos) out[d.id] = pos;
    });
    return out;
  }, [allocation]);

  const hulls = useMemo(() => {
    if (!allocation) return [];
    return (allocation.depots ?? []).map((d) => {
      const dPos = toValidLatLng([d.latitude, d.longitude]);
      const zonePoints = (d.zone_ids ?? []).map((id) => nodes[id]).filter(Boolean);
      const points = dPos ? zonePoints.concat([dPos]) : zonePoints;
      const validPoints = points.map(toValidLatLng).filter(Boolean);
      return { id: d.id, points: validPoints.length >= 3 ? padHull(convexHull(validPoints)) : [] };
    });
  }, [allocation, nodes]);

  // Routes to zones that receive relief, drawn outward from the depots (shortest trips first).
  const routes = useMemo(() => {
    if (!allocation) return [];
    return (allocation.zones ?? [])
      .filter((z) => z.engine && Object.values(z.engine.allocated ?? {}).some((v) => v > 0))
      .sort((a, b) => (a.engine.travel_time_min ?? 0) - (b.engine.travel_time_min ?? 0))
      .map((z, i) => {
        const positions = (z.engine.route_coords ?? []).map(toValidLatLng).filter(Boolean);
        return { id: z.id, positions, delay: 100 + i * 60 };
      })
      .filter((r) => r.positions.length >= 2);
  }, [allocation]);

  const depotIcons = useMemo(
    () =>
      (allocation?.depots ?? []).map((d) =>
        L.divIcon({
          className: "depot-icon",
          html: `<span class="depot-pin"><span>${d.label}</span></span>`,
          iconSize: [26, 26],
          iconAnchor: [13, 13],
        }),
      ),
    [allocation],
  );

  // Draw big circles first so small ones stay clickable.
  const drawOrder = useMemo(() => [...zones].sort((a, b) => b.population - a.population), [zones]);
  const runKey = allocation ? `${allocation.scenario_id}-${allocation.weights ? Object.values(allocation.weights).join("-") : ""}` : "none";

  const mapCenter = useMemo(() => toValidLatLng(INDIA_VIEW.center) ?? [22.5, 80.5], []);

  return (
    <div className={`map-pane${stale ? " is-stale" : ""}`}>
      <MapContainer className="map" center={mapCenter} zoom={INDIA_VIEW.zoom} scrollWheelZoom zoomControl={false} aria-label="Map of affected zones">
        <TileLayer attribution={TILE_ATTRIBUTION} url={TILE_URL} maxZoom={19} />
        <ZoomControl position="bottomright" />
        <FitToZones zones={zones} scenarioId={scenarioId} />
        <PanToSelected zone={selectedZone} />
        <KeepSized />

        <Pane name="hexes" style={{ zIndex: 340 }} />
        <Pane name="hulls" style={{ zIndex: 350 }} />
        <Pane name="roads" style={{ zIndex: 360 }} />
        <Pane name="routes" style={{ zIndex: 380 }} />
        <Pane name="beacons" style={{ zIndex: 390 }} />

        {layers.hexes &&
          zones.map((zone) => {
            const ring = ringPositions(zone.geometry);
            if (!ring) return null;
            const selected = zone.id === selectedZoneId;
            return (
              <Polygon
                key={`hex-${zone.id}`}
                pane="hexes"
                positions={ring}
                pathOptions={{
                  color: selected ? RED : BLACK,
                  weight: selected ? 2 : 0.6,
                  opacity: selected ? 1 : 0.5,
                  fillColor: (LEVEL_COLORS[zone.priority_level] ?? LEVEL_COLORS.Low).fill,
                  fillOpacity: stale ? 0.15 : 0.35,
                  lineJoin: "miter",
                  className: "zone-hex",
                }}
                eventHandlers={{ click: () => onSelectZone(zone.id) }}
              />
            );
          })}

        {allocation &&
          layers.clusters &&
          hulls.map((h) => {
            const validPoints = (h.points ?? []).map(toValidLatLng).filter(Boolean);
            return validPoints.length >= 3 ? (
              <Polygon
                key={`hull-${runKey}-${h.id}`}
                pane="hulls"
                positions={validPoints}
                interactive={false}
                pathOptions={{ color: BLACK, weight: 1.2, opacity: 0.75, dashArray: "4 6", lineJoin: "miter", fillColor: BLACK, fillOpacity: 0.05, className: "hull" }}
              />
            ) : null;
          })}

        {allocation &&
          layers.roads &&
          (allocation.roads ?? []).map((r) => {
            const positions = r.coords ? r.coords.map(toValidLatLng).filter(Boolean) : [nodes[r.from], nodes[r.to]].filter(Boolean);
            return positions.length >= 2 ? (
              <Polyline
                key={`road-${runKey}-${r.from}-${r.to}`}
                pane="roads"
                positions={positions}
                interactive={false}
                pathOptions={{ color: GRAPHITE, weight: 1, opacity: 0.5, lineCap: "butt", className: "road" }}
              />
            ) : null;
          })}

        {allocation &&
          layers.routes &&
          routes.map((r) => (
            <AnimatedRoute
              key={`route-${runKey}-${r.id}`}
              positions={r.positions}
              delay={r.delay}
              dim={Boolean(selectedZoneId && selectedZoneId !== r.id) || stale}
              highlight={selectedZoneId === r.id}
            />
          ))}

        {zones
          .filter((z) => z.priority_level === "Critical")
          .map((z) => {
            const pos = toValidLatLng([z.latitude, z.longitude]);
            if (!pos) return null;
            return (
              <Marker
                key={`beacon-${z.id}`}
                pane="beacons"
                position={pos}
                interactive={false}
                keyboard={false}
                icon={beaconIcon(Math.round(radiusFor(z.population, maxPopulation)))}
              />
            );
          })}

        {drawOrder.map((zone) => {
          const pos = toValidLatLng([zone.latitude, zone.longitude]);
          if (!pos) return null;
          const colors = LEVEL_COLORS[zone.priority_level] ?? LEVEL_COLORS.Low;
          const radius = radiusFor(zone.population, maxPopulation);
          const plan = plans[zone.id];
          return (
            <CircleMarker
              key={zone.id}
              center={pos}
              radius={radius}
              pathOptions={{ color: BLACK, weight: 1.2, fillColor: colors.fill, fillOpacity: 0.95, className: `zone-dot zone-dot--${(zone.priority_level || "low").toLowerCase()}` }}
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
                <span className={`tt-level tt-level--${(zone.priority_level || "low").toLowerCase()}`}>
                  {zone.priority_level} / {formatScore(zone.priority_score)}
                </span>
                <span>
                  {SEVERITY_LABELS[zone.damage_severity] ?? zone.damage_severity} damage / {formatNumber(zone.population)} people
                </span>
                {plan && plan.coverage_pct != null && (
                  <span>
                    {plan.coverage_pct.toFixed(0)}% covered / {Math.round(plan.travel_time_min)} min from {depotById[plan.depot_id]?.name}
                  </span>
                )}
              </Tooltip>
            </CircleMarker>
          );
        })}

        {selectedZone && (() => {
          const pos = toValidLatLng([selectedZone.latitude, selectedZone.longitude]);
          if (!pos) return null;
          return (
            <CircleMarker
              key={`selected-${selectedZone.id}`}
              center={pos}
              radius={radiusFor(selectedZone.population, maxPopulation) + 5}
              interactive={false}
              pathOptions={{ color: BLACK, weight: 2.5, fill: false, className: "selected-ring" }}
            />
          );
        })()}

        {allocation &&
          (allocation.depots ?? []).map((d, i) => {
            const pos = toValidLatLng([d.latitude, d.longitude]);
            if (!pos) return null;
            return (
              <Marker key={`depot-${runKey}-${d.id}`} position={pos} icon={depotIcons[i]} keyboard={false}>
                <Tooltip direction="top" offset={[0, -14]} className="zone-tooltip">
                  <strong>{d.name}</strong>
                  <span>
                    Serves {d.zone_ids.length} zone{d.zone_ids.length === 1 ? "" : "s"} / near {d.nearest_zone}
                  </span>
                </Tooltip>
              </Marker>
            );
          })}

        {layers.hazard &&
          hazardList.map((m) => {
            const pos = toValidLatLng(m.position);
            if (!pos) return null;
            return (
              <Marker key={m.key} position={pos} icon={hazardIcon(m.svg)} keyboard={false}>
                <Tooltip direction="top" offset={[0, -12]} className="zone-tooltip">
                  {m.label}
                </Tooltip>
              </Marker>
            );
          })}
      </MapContainer>

      <p className="map-corner map-corner--tl mono" aria-hidden="true">
        Map / {zones.length ? `${zones.length} zones` : "no scenario"}
      </p>

      <LayerToggles layers={layers} onToggle={onToggleLayer} allocation={allocation} hazard={hazard} hexes={zones.some((z) => z.geometry)} />
      <MapLegend allocation={allocation} hazard={hazard} />

      {stale && (
        <div className="map-stale" role="status">
          Weights changed since this plan was made: run the allocation again to update it.
        </div>
      )}

      <AnimatePresence>
        {running && (
          <motion.div
            className="map-running"
            role="status"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 16 }}
            transition={{ duration: 0.16, ease: [0.7, 0, 0.2, 1] }}
          >
            <p className="map-running-title">
              <AsteriskMark size={18} className="asterisk loader" />
              Allocation Engine running
            </p>
            <p className="map-running-step">
              Step {step + 1} of {PIPELINE_STEPS.length} / {PIPELINE_STEPS[step]?.name}
            </p>
            <span className="map-running-bar" aria-hidden="true">
              {PIPELINE_STEPS.map((s, i) => (
                <span key={s.key} className={i <= step ? "on" : undefined} />
              ))}
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {loading && (
        <div className="map-loading" role="status">
          <AsteriskMark size={20} className="asterisk loader" />
          Loading scenario
        </div>
      )}
    </div>
  );
}
