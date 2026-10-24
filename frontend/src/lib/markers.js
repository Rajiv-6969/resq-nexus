import L from "leaflet";

// Square, geometric map markers drawn as inline SVG (Leaflet divIcons), cached so
// re-renders never rebuild them.
const cache = new Map();
function cached(key, make) {
  if (!cache.has(key)) cache.set(key, make());
  return cache.get(key);
}

const BLACK = "#0A0A0A";
const RED = "#E10600";
const WHITE = "#FFFFFF";

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
