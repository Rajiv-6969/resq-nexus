import L from "leaflet";

// Square, geometric map markers drawn as inline SVG (Leaflet divIcons), cached so
// re-renders never rebuild them (and never restart their CSS animations).
const cache = new Map();
function cached(key, make) {
  if (!cache.has(key)) cache.set(key, make());
  return cache.get(key);
}

const BLACK = "#0A0A0A";
const RED = "#E10600";
const ORANGE = "#FF6B1A";
const PAPER = "#EDEBE6";
const CONCRETE = "#8A8A85";
const WHITE = "#FFFFFF";

// ------------------------------------------------------------------ resources
// One silhouette per type, so the map reads without colour: square + cross, diamond, triangle,
// barred square, circle, inverted triangle, shield.
const SHAPES = {
  HOSPITAL: (f, s, i) =>
    `<rect x="2" y="2" width="20" height="20" fill="${f}" stroke="${s}" stroke-width="1.5"/><path d="M12 6.5v11M6.5 12h11" stroke="${i}" stroke-width="3"/>`,
  AMBULANCE: (f, s, i) =>
    `<path d="M12 1 23 12 12 23 1 12z" fill="${f}" stroke="${s}" stroke-width="1.5" stroke-linejoin="miter"/><rect x="9" y="9" width="6" height="6" fill="${i}"/>`,
  SHELTER: (f, s, i) =>
    `<path d="M12 1.5 23 22H1z" fill="${f}" stroke="${s}" stroke-width="1.5" stroke-linejoin="miter"/><rect x="9.5" y="14" width="5" height="8" fill="${i}"/>`,
  FOOD: (f, s, i) =>
    `<rect x="2" y="2" width="20" height="20" fill="${f}" stroke="${s}" stroke-width="1.5"/><path d="M6 7.5h12M6 12h12M6 16.5h12" stroke="${i}" stroke-width="2"/>`,
  WATER: (f, s, i) => `<circle cx="12" cy="12" r="10.5" fill="${f}" stroke="${s}" stroke-width="1.5"/><circle cx="12" cy="12" r="4" fill="${i}"/>`,
  FIRE_STATION: (f, s, i) =>
    `<path d="M1 2.5h22L12 22.5z" fill="${f}" stroke="${s}" stroke-width="1.5" stroke-linejoin="miter"/><path d="M12 6.5v7" stroke="${i}" stroke-width="3"/>`,
  POLICE: (f, s, i) =>
    `<path d="M2.5 2h19v11.5L12 22.5 2.5 13.5z" fill="${f}" stroke="${s}" stroke-width="1.5" stroke-linejoin="miter"/><path d="M7 8h10M7 12h10" stroke="${i}" stroke-width="2"/>`,
};

// OPEN: solid black. FULL: orange. CLOSED: pale and grey.
const STATUS_COLOURS = {
  OPEN: [BLACK, BLACK, WHITE],
  FULL: [ORANGE, BLACK, BLACK],
  CLOSED: [PAPER, CONCRETE, CONCRETE],
};

export function resourceSvg(type, status = "OPEN", size = 24) {
  const [fill, stroke, ink] = STATUS_COLOURS[status] ?? STATUS_COLOURS.OPEN;
  const shape = (SHAPES[type] ?? SHAPES.HOSPITAL)(fill, stroke, ink);
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" aria-hidden="true">${shape}</svg>`;
}

// The same shape as an outline in the text colour (for chips and legends on any background).
export function glyphSvg(type, size = 14) {
  const shape = (SHAPES[type] ?? SHAPES.HOSPITAL)("none", "currentColor", "currentColor");
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" aria-hidden="true">${shape}</svg>`;
}

const frame = (size, colour) =>
  `<rect x="1" y="1" width="${size - 2}" height="${size - 2}" fill="none" stroke="${colour}" stroke-width="2"/>`;

export const resourceIcon = (type, status, selected = false) =>
  cached(`res:${type}:${status}:${selected}`, () => {
    const box = selected ? 40 : 26;
    const inner = resourceSvg(type, status, 24).replace("<svg ", `<svg x="${(box - 24) / 2}" y="${(box - 24) / 2}" `);
    return L.divIcon({
      className: `map-glyph${selected ? " is-selected" : ""}`,
      html: `<svg width="${box}" height="${box}" viewBox="0 0 ${box} ${box}" aria-hidden="true">${selected ? frame(box, RED) : ""}${inner}</svg>`,
      iconSize: [box, box],
      iconAnchor: [box / 2, box / 2],
    });
  });

// ------------------------------------------------------------------ SOS requests
// Squares coloured by severity; the inner mark shows the status. PENDING ones get blinking
// corner brackets; RESOLVED ones are hollow. A request without details yet is black with a red "!".
const SEVERITY_FILL = { Critical: RED, High: ORANGE, Medium: "#C9C7C1", Low: "#5A5A57" };
const MARK_INK = { Critical: WHITE, High: BLACK, Medium: BLACK, Low: WHITE };

function sosSquare(level, status) {
  if (status === "RESOLVED") {
    return `<rect x="5" y="5" width="18" height="18" fill="${PAPER}" fill-opacity="0.85" stroke="${CONCRETE}" stroke-width="2" stroke-dasharray="3 2"/><path d="M9.5 14l3 3 6-6" fill="none" stroke="${CONCRETE}" stroke-width="2"/>`;
  }
  if (!level) {
    return `<rect x="4" y="4" width="20" height="20" fill="${BLACK}" stroke="${RED}" stroke-width="2"/><path d="M14 8v8" stroke="${RED}" stroke-width="3"/><rect x="12.5" y="18" width="3" height="3" fill="${RED}"/>`;
  }
  const ink = MARK_INK[level];
  const mark =
    status === "ACKNOWLEDGED"
      ? `<rect x="11" y="11" width="6" height="6" fill="${ink}"/>`
      : status === "DISPATCHED"
        ? `<path d="M9 14h9M14.5 10l4 4-4 4" fill="none" stroke="${ink}" stroke-width="2.2"/>`
        : "";
  return `<rect x="4" y="4" width="20" height="20" fill="${SEVERITY_FILL[level]}" stroke="${BLACK}" stroke-width="2"/>${mark}`;
}

const BRACKETS =
  '<path class="sos-brackets" d="M1 8V1h7M20 1h7v7M27 20v7h-7M8 27H1v-7" fill="none" stroke="#E10600" stroke-width="2"/>';

export const sosIcon = (level, status, selected = false) =>
  cached(`sos:${level}:${status}:${selected}`, () => {
    const box = 28;
    const ring = selected ? `<rect x="0.5" y="0.5" width="27" height="27" fill="none" stroke="${BLACK}" stroke-width="1"/>` : "";
    return L.divIcon({
      className: `map-sos${selected ? " is-selected" : ""}${status === "PENDING" ? " is-pending" : ""}`,
      html: `<svg width="${box}" height="${box}" viewBox="0 0 28 28" aria-hidden="true">${status === "PENDING" || selected ? BRACKETS : ""}${ring}${sosSquare(level, status)}</svg>`,
      iconSize: [box, box],
      iconAnchor: [box / 2, box / 2],
    });
  });

export function sosSvg(level, status, size = 20) {
  return `<svg width="${size}" height="${size}" viewBox="4 4 20 20" aria-hidden="true">${sosSquare(level, status)}</svg>`;
}

// ------------------------------------------------------------------ people and places
// "You are here": a red square crosshair.
export const userIcon = () =>
  cached("user", () =>
    L.divIcon({
      className: "map-user",
      html: `<svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true"><rect x="7" y="7" width="20" height="20" fill="none" stroke="${RED}" stroke-width="2"/><rect x="13" y="13" width="8" height="8" fill="${RED}"/><path d="M17 0v7M17 27v7M0 17h7M27 17h7" stroke="${RED}" stroke-width="2"/></svg>`,
      iconSize: [34, 34],
      iconAnchor: [17, 17],
    }),
  );

// A dropped pin: a red square with a white cross, on a short black stem.
export const pinIcon = () =>
  cached("pin", () =>
    L.divIcon({
      className: "pin-icon",
      html: `<svg width="28" height="38" viewBox="0 0 28 38" aria-hidden="true"><rect x="13" y="24" width="2" height="13" fill="${BLACK}"/><rect x="1" y="1" width="26" height="26" fill="${RED}" stroke="${BLACK}" stroke-width="2"/><path d="M14 7v14M7 14h14" stroke="${WHITE}" stroke-width="3"/></svg>`,
      iconSize: [28, 38],
      iconAnchor: [14, 37],
    }),
  );

// A service provider's base: its type's glyph inside a heavy black frame.
export const baseIcon = (type) =>
  cached(`base:${type}`, () => {
    const inner = resourceSvg(type, "OPEN", 22).replace("<svg ", '<svg x="7" y="7" ');
    return L.divIcon({
      className: "map-base",
      html: `<svg width="36" height="36" viewBox="0 0 36 36" aria-hidden="true"><rect x="1.5" y="1.5" width="33" height="33" fill="${PAPER}" stroke="${BLACK}" stroke-width="3"/>${inner}</svg>`,
      iconSize: [36, 36],
      iconAnchor: [18, 18],
    });
  });
