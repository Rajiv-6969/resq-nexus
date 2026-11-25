import { useEffect, useLayoutEffect, useRef } from "react";
import { MapContainer, TileLayer, ZoomControl, useMap } from "react-leaflet";
import L from "leaflet";
import { DEFAULT_CENTER, TILE_ATTRIBUTION, TILE_URL, toValidLatLng } from "../../lib/map";

// Leaflet only measures its box once; re-measure whenever the layout changes its size.
function KeepSized() {
  const map = useMap();
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize({ pan: false }));
    observer.observe(map.getContainer());
    return () => observer.disconnect();
  }, [map]);
  return null;
}

// Hands the Leaflet map to a parent (for buttons outside the map, e.g. "pin the map centre").
function ExposeMap({ mapRef }) {
  const map = useMap();
  useEffect(() => {
    if (!mapRef) return undefined;
    mapRef.current = map;
    return () => {
      mapRef.current = null;
    };
  }, [map, mapRef]);
  return null;
}

// Moves the view when `point` (or `zoom`) changes, e.g. after "use my location".
export function FlyTo({ point, zoom }) {
  const map = useMap();
  const valid = toValidLatLng(point);
  useEffect(() => {
    if (!valid) return;
    map.setView(valid, zoom ?? map.getZoom(), { animate: false });
  }, [map, valid ? valid[0] : null, valid ? valid[1] : null, zoom]);
  return null;
}

// Fits every point in view whenever `fitKey` changes (not on every data refresh).
export function FitPoints({ points = [], fitKey, maxZoom = 13 }) {
  const map = useMap();
  const latest = useRef(points);
  useLayoutEffect(() => {
    latest.current = points;
  });
  useEffect(() => {
    const current = (latest.current || []).map(toValidLatLng).filter(Boolean);
    if (!current?.length) return;
    if (current.length === 1) map.setView(current[0], Math.min(maxZoom, 14), { animate: false });
    else map.fitBounds(L.latLngBounds(current), { padding: [48, 48], maxZoom, animate: false });
  }, [map, fitKey, maxZoom]);
  return null;
}

// OpenStreetMap base map in the site's flat, square chrome.
export default function BaseMap({ center, zoom = 12, label, mapRef, children }) {
  const centerPos = toValidLatLng(center) ?? DEFAULT_CENTER;

  return (
    <MapContainer
      className="map"
      center={centerPos}
      zoom={zoom}
      scrollWheelZoom
      zoomControl={false}
      aria-label={label}
    >
      <TileLayer attribution={TILE_ATTRIBUTION} url={TILE_URL} maxZoom={19} />
      <ZoomControl position="bottomright" />
      <KeepSized />
      <ExposeMap mapRef={mapRef} />
      {children}
    </MapContainer>
  );
}
