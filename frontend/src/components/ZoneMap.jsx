import { useEffect, useMemo } from "react";
import { CircleMarker, MapContainer, Marker, TileLayer, Tooltip, useMap } from "react-leaflet";
import L from "leaflet";
import { LEVEL_COLORS, PRIORITY_LEVELS, SEVERITY_LABELS, formatNumber, formatScore } from "../constants";

const INDIA_VIEW = { center: [22.5, 80.5], zoom: 5 };
const MIN_RADIUS = 6;
const MAX_EXTRA_RADIUS = 18;

// Circle area grows with population (radius ~ sqrt), the usual proportional-symbol rule.
const radiusFor = (population, maxPopulation) =>
  MIN_RADIUS + MAX_EXTRA_RADIUS * Math.sqrt(population / Math.max(maxPopulation, 1));

const EPICENTRE_SVG =
  '<svg viewBox="0 0 24 24" width="24" height="24"><circle cx="12" cy="12" r="10" fill="rgba(255,255,255,.85)" stroke="#0f172a" stroke-width="2"/><circle cx="12" cy="12" r="5.5" fill="none" stroke="#0f172a" stroke-width="2"/><circle cx="12" cy="12" r="2" fill="#0f172a"/></svg>';
const HOTSPOT_SVG =
  '<svg viewBox="0 0 24 24" width="24" height="24"><circle cx="12" cy="12" r="11" fill="rgba(255,255,255,.9)" stroke="#7c2d12" stroke-width="1.5"/><path d="M12 4.5c.8 2.8 4 4.4 4 8.4a4 4 0 0 1-8 0c0-2 1-3.2 2-4.4.2 1.3.8 2.1 1.6 2.4.2-2.4-.4-4.4.4-6.4z" fill="#ea580c" stroke="#7c2d12" stroke-width="1"/></svg>';

const hazardIcon = (svg) =>
  L.divIcon({ className: "hazard-icon", html: svg, iconSize: [24, 24], iconAnchor: [12, 12] });

function FitToZones({ zones }) {
  const map = useMap();
  useEffect(() => {
    if (!zones.length) return;
    const bounds = L.latLngBounds(zones.map((z) => [z.latitude, z.longitude]));
    map.fitBounds(bounds, { padding: [56, 56], maxZoom: 11 });
  }, [map, zones]);
  return null;
}

function PanToSelected({ zone }) {
  const map = useMap();
  useEffect(() => {
    if (!zone) return;
    const target = L.latLng(zone.latitude, zone.longitude);
    if (!map.getBounds().pad(-0.15).contains(target)) map.panTo(target, { animate: true });
  }, [map, zone]);
  return null;
}

function hazardMarkers(hazard) {
  if (!hazard) return [];
  if (hazard.epicentre) {
    return [{ key: "epicentre", position: hazard.epicentre, icon: EPICENTRE_SVG, label: `Epicentre (M${hazard.magnitude})` }];
  }
  if (hazard.hotspots) {
    return hazard.hotspots.map((h, i) => ({ key: `hotspot-${i}`, position: h, icon: HOTSPOT_SVG, label: "Fire ignition area" }));
  }
  return [];
}

function MapLegend({ hasEpicentre, hasHotspots }) {
  return (
    <div className="map-legend" aria-label="Map legend">
      <p className="legend-title">Priority level</p>
      <ul>
        {PRIORITY_LEVELS.map((level) => (
          <li key={level}>
            <span className="legend-dot" style={{ background: LEVEL_COLORS[level].fill, borderColor: LEVEL_COLORS[level].stroke }} />
            {level}
          </li>
        ))}
      </ul>
      <p className="legend-note">
        <span className="legend-sizes" aria-hidden="true">
          <span />
          <span />
          <span />
        </span>
        Circle size = population
      </p>
      {hasEpicentre && (
        <p className="legend-note">
          <span className="legend-glyph" dangerouslySetInnerHTML={{ __html: EPICENTRE_SVG }} /> Epicentre
        </p>
      )}
      {hasHotspots && (
        <p className="legend-note">
          <span className="legend-glyph" dangerouslySetInnerHTML={{ __html: HOTSPOT_SVG }} /> Ignition area
        </p>
      )}
    </div>
  );
}

export default function ZoneMap({ zones, hazard, selectedZoneId, onSelectZone, loading }) {
  const maxPopulation = useMemo(() => Math.max(0, ...zones.map((z) => z.population)), [zones]);
  const selectedZone = zones.find((z) => z.id === selectedZoneId) ?? null;
  const markers = hazardMarkers(hazard);

  // Draw big circles first so small ones stay clickable; the selected zone goes on top.
  const drawOrder = useMemo(
    () => [...zones].sort((a, b) => b.population - a.population),
    [zones],
  );

  return (
    <div className="map-pane">
      <MapContainer
        className="map"
        center={INDIA_VIEW.center}
        zoom={INDIA_VIEW.zoom}
        scrollWheelZoom
        aria-label="Map of affected zones"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />
        <FitToZones zones={zones} />
        <PanToSelected zone={selectedZone} />

        {markers.map((m) => (
          <Marker
            key={m.key}
            position={[m.position.latitude, m.position.longitude]}
            icon={hazardIcon(m.icon)}
            keyboard={false}
            interactive
          >
            <Tooltip direction="top" offset={[0, -12]}>
              {m.label}
            </Tooltip>
          </Marker>
        ))}

        {drawOrder.map((zone) => {
          const colors = LEVEL_COLORS[zone.priority_level];
          const radius = radiusFor(zone.population, maxPopulation);
          return (
            <CircleMarker
              key={zone.id}
              center={[zone.latitude, zone.longitude]}
              radius={radius}
              pathOptions={{ color: colors.stroke, weight: 1.5, fillColor: colors.fill, fillOpacity: 0.72 }}
              eventHandlers={{ click: () => onSelectZone(zone.id) }}
            >
              <Tooltip direction="top" offset={[0, -radius]}>
                <strong>{zone.name}</strong> · {zone.priority_level} ({formatScore(zone.priority_score)})
                <br />
                {SEVERITY_LABELS[zone.damage_severity]} damage · {formatNumber(zone.population)} people
              </Tooltip>
            </CircleMarker>
          );
        })}

        {selectedZone && (
          <CircleMarker
            key={`selected-${selectedZone.id}`}
            center={[selectedZone.latitude, selectedZone.longitude]}
            radius={radiusFor(selectedZone.population, maxPopulation) + 5}
            pathOptions={{ color: "#0d9488", weight: 3.5, fill: false, dashArray: "6 4" }}
            interactive={false}
          />
        )}
      </MapContainer>

      <MapLegend hasEpicentre={Boolean(hazard?.epicentre)} hasHotspots={Boolean(hazard?.hotspots)} />

      {loading && (
        <div className="map-loading" role="status">
          <span className="spinner" aria-hidden="true" />
          Loading scenario…
        </div>
      )}
    </div>
  );
}
