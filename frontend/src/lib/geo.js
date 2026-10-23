// Small geometry helpers for the map.

// Convex hull (Andrew's monotone chain) of [lat, lon] points; returns the hull in order.
export function convexHull(points) {
  const pts = [...points].sort((a, b) => a[1] - b[1] || a[0] - b[0]);
  if (pts.length < 3) return pts;
  const cross = (o, a, b) => (a[1] - o[1]) * (b[0] - o[0]) - (a[0] - o[0]) * (b[1] - o[1]);
  const lower = [];
  for (const p of pts) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop();
    lower.push(p);
  }
  const upper = [];
  for (let i = pts.length - 1; i >= 0; i -= 1) {
    const p = pts[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop();
    upper.push(p);
  }
  return lower.slice(0, -1).concat(upper.slice(0, -1));
}

// Push hull vertices outwards from their centroid so the outline does not cut through markers.
export function padHull(hull, factor = 0.12, minDegrees = 0.012) {
  if (hull.length < 3) return hull;
  const lat = hull.reduce((s, p) => s + p[0], 0) / hull.length;
  const lon = hull.reduce((s, p) => s + p[1], 0) / hull.length;
  return hull.map(([a, b]) => {
    const dLat = a - lat;
    const dLon = b - lon;
    const length = Math.hypot(dLat, dLon) || 1;
    const push = Math.max(length * factor, minDegrees);
    return [a + (dLat / length) * push, b + (dLon / length) * push];
  });
}
