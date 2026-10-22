// Thin client for the ResQ Nexus FastAPI backend.
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function getJson(path, { signal } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { signal });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ApiError(`Cannot reach the ResQ Nexus API at ${API_BASE_URL}.`, 0);
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = (await response.json()).detail ?? detail;
    } catch {
      // body was not JSON; keep the status text
    }
    throw new ApiError(`API error ${response.status}: ${detail}`, response.status);
  }
  return response.json();
}

export const fetchScenarios = (options) => getJson("/scenarios", options);
export const fetchScenario = (id, options) => getJson(`/scenarios/${encodeURIComponent(id)}`, options);
export const fetchPriority = (id, options) => getJson(`/scenarios/${encodeURIComponent(id)}/priority`, options);
