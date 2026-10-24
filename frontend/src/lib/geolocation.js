// Browser geolocation as a promise, with messages people can act on.

const roundCoord = (value) => Math.round(value * 1e5) / 1e5;

export class GeoError extends Error {
  constructor(reason, message) {
    super(message);
    this.name = "GeoError";
    this.reason = reason; // unsupported | insecure | denied | unavailable | timeout
  }
}

const MESSAGES = {
  1: ["denied", "Location permission was denied."],
  2: ["unavailable", "Your location could not be found."],
  3: ["timeout", "Finding your location took too long."],
};

export function getCurrentPosition({ timeout = 12000 } = {}) {
  return new Promise((resolve, reject) => {
    if (!window.isSecureContext) {
      reject(new GeoError("insecure", "Location needs a secure (https) connection."));
      return;
    }
    if (!("geolocation" in navigator)) {
      reject(new GeoError("unsupported", "This browser cannot share its location."));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({
          latitude: roundCoord(position.coords.latitude),
          longitude: roundCoord(position.coords.longitude),
          accuracy: Math.round(position.coords.accuracy),
        }),
      (err) => reject(new GeoError(...(MESSAGES[err.code] ?? MESSAGES[2]))),
      { enableHighAccuracy: true, timeout, maximumAge: 30000 },
    );
  });
}

export { roundCoord };
