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
