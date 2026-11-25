// Shared map settings: OpenStreetMap tiles in their original colours, and demo starting points.
export const TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
export const TILE_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

// Demo locations: central Bengaluru and the three scenario regions (all demo data is placed around them).
export const DEMO_LOCATIONS = [
  { key: "bengaluru", label: "Bengaluru", detail: "MG Road", latitude: 12.97566, longitude: 77.60657 },
  { key: "kutch", label: "Kutch", detail: "Bhachau", latitude: 23.29781, longitude: 70.3461 },
  { key: "assam", label: "Assam", detail: "Barpeta", latitude: 26.32636, longitude: 91.00801 },
  { key: "kumaon", label: "Kumaon", detail: "Almora", latitude: 29.60207, longitude: 79.66298 },
];
export const DEFAULT_LOCATION = DEMO_LOCATIONS[0];
export const DEFAULT_CENTER = [12.9716, 77.5946];

/**
 * Converts a point in various representations to a strictly valid [lat, lon] tuple.
 * Accepts:
 *   - [lat, lon] or [lat, lng]
 *   - { lat, lon }
 *   - { lat, lng }
 *   - { latitude, longitude }
 * Verifies Number.isFinite(lat) && Number.isFinite(lon).
 * Returns [lat, lon] as finite numbers, or null if either value is missing, null, undefined, or NaN.
 */
export function toValidLatLng(point) {
  if (point == null) return null;

  let lat;
  let lon;

  if (Array.isArray(point)) {
    if (point.length < 2) return null;
    lat = typeof point[0] === "number" ? point[0] : parseFloat(point[0]);
    lon = typeof point[1] === "number" ? point[1] : parseFloat(point[1]);
  } else if (typeof point === "object") {
    const rawLat = point.lat ?? point.latitude;
    const rawLon = point.lng ?? point.lon ?? point.longitude;
    lat = typeof rawLat === "number" ? rawLat : parseFloat(rawLat);
    lon = typeof rawLon === "number" ? rawLon : parseFloat(rawLon);
  } else {
    return null;
  }

  if (Number.isFinite(lat) && Number.isFinite(lon)) {
    if (lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180) {
      return [lat, lon];
    }
  }

  return null;
}

/**
 * Filters and maps a list of points to valid [lat, lon] tuples.
 */
export function toValidLatLngList(points) {
  if (!Array.isArray(points)) return [];
  return points.map(toValidLatLng).filter(Boolean);
}
