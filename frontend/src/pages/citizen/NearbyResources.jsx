import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Circle, Marker, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import { fetchNearbyResources } from "../../api";
import CapacityBar from "../../components/CapacityBar";
import { ResourceGlyph } from "../../components/Glyphs";
import { AsteriskMark } from "../../components/icons";
import BaseMap from "../../components/maps/BaseMap";
import { ResourceStatusTag } from "../../components/Tags";
import { RESOURCE_META, RESOURCE_TYPES } from "../../constants";
import { getCurrentPosition, roundCoord } from "../../lib/geolocation";
import { useNow } from "../../lib/hooks";
import { DEFAULT_LOCATION, DEMO_LOCATIONS, toValidLatLng } from "../../lib/map";
import { resourceIcon, userIcon } from "../../lib/markers";
import { availabilityText } from "../../lib/resources";
import { timeAgo } from "../../lib/time";

const RADII = [2, 5, 10, 25, 50];
const BLACK = "#0A0A0A";

// Fit the search circle whenever the origin or radius changes.
function FitRadius({ origin, radiusKm }) {
  const map = useMap();
  const pos = toValidLatLng(origin);
  useEffect(() => {
    if (!pos) return;
    map.fitBounds(L.latLng(pos[0], pos[1]).toBounds(radiusKm * 2000), { padding: [16, 16], animate: false });
  }, [map, pos ? pos[0] : null, pos ? pos[1] : null, radiusKm]);
  return null;
}

function PanTo({ point }) {
  const map = useMap();
  const pos = toValidLatLng(point);
  useEffect(() => {
    if (pos) map.panTo(pos, { animate: true, duration: 0.35 });
  }, [map, pos ? pos[0] : null, pos ? pos[1] : null]);
  return null;
}

function PickOnClick({ enabled, onPick }) {
  useMapEvents({ click: (e) => enabled && onPick({ latitude: roundCoord(e.latlng.lat), longitude: roundCoord(e.latlng.lng) }) });
  return null;
}

const SOURCE_TEXT = { gps: "Your location", pin: "Chosen on the map", demo: "Demo location" };

export default function NearbyResources() {
  const [origin, setOrigin] = useState(null); // { latitude, longitude, source, label?, accuracy? }
  const [locating, setLocating] = useState(true);
  const [geoProblem, setGeoProblem] = useState(null);
  const [types, setTypes] = useState([]); // empty = every type
  const [radiusKm, setRadiusKm] = useState(10);
  const [picking, setPicking] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [result, setResult] = useState({ status: "idle", data: null, error: null });
  const listRef = useRef(null);
  const now = useNow(30000);

  const locate = useCallback(async () => {
    setLocating(true);
    setGeoProblem(null);
    try {
      const point = await getCurrentPosition();
      setOrigin({ ...point, source: "gps" });
    } catch (err) {
      setGeoProblem(err.message);
      setOrigin((current) => current ?? { ...DEFAULT_LOCATION, source: "demo", label: `Demo / ${DEFAULT_LOCATION.label}, ${DEFAULT_LOCATION.detail}` });
    } finally {
      setLocating(false);
    }
  }, []);

  useEffect(() => {
    locate();
  }, [locate]);

  const lat = origin?.latitude;
  const lon = origin?.longitude;
  const typeKey = types.join(",");
  useEffect(() => {
    if (lat == null) return undefined;
    const controller = new AbortController();
    setResult((r) => ({ ...r, status: "loading", error: null }));
    fetchNearbyResources({ lat, lon, radiusKm, types: typeKey ? typeKey.split(",") : [] }, { signal: controller.signal })
      .then((data) => setResult({ status: "ready", data, error: null }))
      .catch((err) => err.name !== "AbortError" && setResult({ status: "error", data: null, error: err.message }));
    return () => controller.abort();
  }, [lat, lon, radiusKm, typeKey]);

  const resources = useMemo(() => result.data?.resources ?? [], [result.data]);
  const selected = resources.find((r) => r.id === selectedId) ?? null;
  const selectedPoint = useMemo(() => (selected ? [selected.latitude, selected.longitude] : null), [selected]);

  const toggleType = (type) => setTypes((current) => (current.includes(type) ? current.filter((t) => t !== type) : [...current, type]));

  const selectFromMap = (id) => {
    setSelectedId(id);
    const row = listRef.current?.querySelector(`[data-id="${id}"]`);
    row?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  };

  const pick = (point) => {
    setOrigin({ ...point, source: "pin" });
    setPicking(false);
    setSelectedId(null);
  };
  const chooseDemo = (place) => {
    setOrigin({ latitude: place.latitude, longitude: place.longitude, source: "demo", label: `Demo / ${place.label}, ${place.detail}` });
    setSelectedId(null);
  };

  return (
    <section className="sec resources-page" aria-labelledby="resources-title">
      <p className="sec-bar mono">
        <span>(04) Nearby resources</span>
        <span>
          {origin && Number.isFinite(origin.latitude) && Number.isFinite(origin.longitude)
            ? `${origin.label ?? SOURCE_TEXT[origin.source]}${origin.accuracy ? ` ±${origin.accuracy} m` : ""} / ${origin.latitude.toFixed(4)}, ${origin.longitude.toFixed(4)}`
            : "Finding your location…"}
        </span>
      </p>

      <div className="res-controls">
        <h1 id="resources-title" className="res-title">
          Nearby resources
        </h1>
        <div className="res-filter">
          <p className="label">Type</p>
          <div className="chips" role="group" aria-label="Resource types">
            <button type="button" className={`chip${types.length === 0 ? " is-on" : ""}`} aria-pressed={types.length === 0} onClick={() => setTypes([])}>
              All
            </button>
            {RESOURCE_TYPES.map((type) => (
              <button key={type} type="button" className={`chip${types.includes(type) ? " is-on" : ""}`} aria-pressed={types.includes(type)} onClick={() => toggleType(type)}>
                <ResourceGlyph type={type} outline size={14} />
                {RESOURCE_META[type].plural}
              </button>
            ))}
          </div>
        </div>
        <div className="res-filter res-filter--radius">
          <p className="label">Within</p>
          <div className="chips" role="radiogroup" aria-label="Distance radius">
            {RADII.map((km) => (
              <button key={km} type="button" role="radio" aria-checked={radiusKm === km} className={`chip${radiusKm === km ? " is-on" : ""}`} onClick={() => setRadiusKm(km)}>
                {km} km
              </button>
            ))}
          </div>
        </div>
        <div className="res-filter res-filter--where">
          <p className="label">From</p>
          <div className="chips">
            <button type="button" className={`chip${origin?.source === "gps" ? " is-on" : ""}`} onClick={locate} disabled={locating}>
              {locating ? "Locating…" : "My location"}
            </button>
            <button type="button" className={`chip${picking ? " is-on" : ""}`} aria-pressed={picking} onClick={() => setPicking((p) => !p)}>
              {picking ? "Tap the map…" : "Pick on map"}
            </button>
            {DEMO_LOCATIONS.map((place) => (
              <button
                key={place.key}
                type="button"
                className={`chip chip--demo${origin?.source === "demo" && origin.latitude === place.latitude ? " is-on" : ""}`}
                onClick={() => chooseDemo(place)}
                title={`Demo location: ${place.label}, ${place.detail}`}
              >
                {place.label}
              </button>
            ))}
          </div>
        </div>
        {geoProblem && origin?.source !== "gps" && (
          <p className="form-notice res-geo" role="status">
            {geoProblem} Showing a demo location; pick your position on the map or choose a demo area.
          </p>
        )}
      </div>

      <div className="res-body">
        <div className={`map-pane res-map${picking ? " is-picking" : ""}`}>
          {toValidLatLng(origin) ? (() => {
            const originPos = toValidLatLng(origin);
            return (
              <BaseMap center={originPos} zoom={13} label="Map of nearby resources">
                <FitRadius origin={originPos} radiusKm={radiusKm} />
                <PanTo point={selectedPoint} />
                <PickOnClick enabled={picking} onPick={pick} />
                <Circle
                  center={originPos}
                  radius={radiusKm * 1000}
                  pathOptions={{ color: BLACK, weight: 1.5, dashArray: "6 6", fill: false, interactive: false }}
                />
                <Marker position={originPos} icon={userIcon()} keyboard={false} interactive={false} zIndexOffset={2000} />
                {resources.map((r) => {
                  const pos = toValidLatLng(r);
                  if (!pos) return null;
                  return (
                    <Marker
                      key={r.id}
                      position={pos}
                      icon={resourceIcon(r.resource_type, r.status, r.id === selectedId)}
                      zIndexOffset={r.id === selectedId ? 1000 : 0}
                      title={`${r.name} (${r.type_label}, ${r.distance_km} km)`}
                      eventHandlers={{ click: () => selectFromMap(r.id) }}
                    />
                  );
                })}
              </BaseMap>
            );
          })() : (
            <div className="map-wait mono">
              <AsteriskMark size={18} className="asterisk loader" /> Finding your location
            </div>
          )}
          {picking && <p className="map-corner map-corner--tl mono">Tap the map to search from there</p>}
        </div>

        <div className="res-list" ref={listRef} aria-live="polite" aria-busy={result.status === "loading"}>
          <p className="res-count mono">
            {result.status === "loading" && !result.data
              ? "Searching…"
              : result.status === "error"
                ? `Could not load resources: ${result.error}`
                : `${resources.length} within ${radiusKm} km / nearest first`}
          </p>
          {result.status === "ready" && resources.length === 0 && (
            <div className="res-empty">
              <p>Nothing within {radiusKm} km of this point.</p>
              <p className="mono">The demo data covers Bengaluru, Kutch, Assam and Kumaon. Try a larger radius or a demo area above.</p>
            </div>
          )}
          <ol className="res-items">
            {resources.map((r) => (
              <li key={r.id} data-id={r.id}>
                <article className={`res-item${r.id === selectedId ? " is-selected" : ""}${r.status === "CLOSED" ? " is-closed" : ""}`}>
                  <button type="button" className="res-item-hit" onClick={() => setSelectedId(r.id)} aria-label={`Show ${r.name} on the map`} />
                  <ResourceGlyph type={r.resource_type} status={r.status} size={26} />
                  <div className="res-item-main">
                    <h2 className="res-item-name">{r.name}</h2>
                    <p className="res-item-type mono">
                      {r.type_label}
                      {r.area ? ` / ${r.area}` : ""}
                    </p>
                  </div>
                  <p className="res-item-dist mono">
                    {r.distance_km < 10 ? r.distance_km.toFixed(2) : r.distance_km.toFixed(1)}
                    <span> km</span>
                  </p>
                  <div className="res-item-avail">
                    <CapacityBar available={r.capacity_available} total={r.capacity_total} />
                    <p className="mono">{availabilityText(r)}</p>
                  </div>
                  <div className="res-item-foot">
                    <ResourceStatusTag status={r.status} />
                    {r.contact_phone && (
                      <a className="res-item-call mono" href={`tel:${r.contact_phone.replace(/[^+\d]/g, "")}`}>
                        {r.contact_phone}
                      </a>
                    )}
                    <span className="res-item-updated mono" title={new Date(r.updated_at).toLocaleString("en-IN")}>
                      Updated {timeAgo(r.updated_at, now)}
                    </span>
                  </div>
                </article>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
