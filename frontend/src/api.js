// Thin client for the ResQ Nexus FastAPI backend.
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request(path, { method = "GET", body, signal } = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      signal,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ApiError(`Cannot reach the ResQ Nexus API at ${API_BASE_URL}.`, 0);
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail ?? detail);
    } catch {
      // body was not JSON; keep the status text
    }
    throw new ApiError(`API error ${response.status}: ${detail}`, response.status);
  }
  return response.json();
}

const scenarioPath = (id) => `/scenarios/${encodeURIComponent(id)}`;

export const fetchHealth = (options) => request("/health", options);
export const fetchScenarios = (options) => request("/scenarios", options);
export const fetchScenario = (id, options) => request(scenarioPath(id), options);

export function fetchPriority(id, weights, options) {
  const query = weights ? `?${new URLSearchParams(Object.entries(weights).map(([k, v]) => [k, String(v)]))}` : "";
  return request(`${scenarioPath(id)}/priority${query}`, options);
}

export const postAllocate = (id, weights, options) =>
  request(`${scenarioPath(id)}/allocate`, { ...options, method: "POST", body: weights ? { weights } : {} });

export const postExplain = (id, weights, options) =>
  request(`${scenarioPath(id)}/explain`, { ...options, method: "POST", body: weights ? { weights } : {} });
