// Thin client for the ResQ Nexus FastAPI backend.
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(message, status, fieldErrors = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors; // { field: "message" } for 422 validation errors
  }
}

// The access token of the logged-in user (set by AuthProvider) and what to do when it stops working.
let authToken = null;
let unauthorizedHandler = null;
export const setAuthToken = (token) => {
  authToken = token;
};
export const setUnauthorizedHandler = (handler) => {
  unauthorizedHandler = handler;
};

const FIELD_LABELS = {
  full_name: "Name",
  email: "Email",
  password: "Password",
  phone: "Phone",
  organisation_name: "Organisation",
  organisation_type: "Organisation type",
  latitude: "Location",
  longitude: "Location",
  address: "Address",
  emergency_type: "Emergency type",
  people_affected: "People affected",
  injuries: "Injuries",
  needs: "Needs",
  vulnerable: "Vulnerable people",
  description: "Description",
  contact_phone: "Contact phone",
  capacity_total: "Total",
  capacity_available: "Available",
  status: "Status",
  name: "Name",
  resource_type: "Type",
  area: "Area",
  region: "Region",
  provider_id: "Owner",
  note: "Note",
};

const cleanMessage = (msg) => String(msg ?? "").replace(/^Value error, /, "");

// FastAPI validation errors ([{ loc: ["body", "email"], msg }]) -> { email: msg } plus one readable sentence.
function parseDetail(detail) {
  if (typeof detail === "string") return { message: detail, fieldErrors: {} };
  if (Array.isArray(detail)) {
    const fieldErrors = {};
    for (const item of detail) {
      const loc = (item.loc ?? []).filter((part) => part !== "body" && part !== "query" && part !== "path");
      const field = loc.length ? String(loc[0]) : "_form";
      if (!fieldErrors[field]) fieldErrors[field] = cleanMessage(item.msg);
    }
    const [field, message] = Object.entries(fieldErrors)[0] ?? ["_form", "Some fields are not valid."];
    return { message: field === "_form" ? message : `${FIELD_LABELS[field] ?? field}: ${message}`, fieldErrors };
  }
  return { message: "The request failed.", fieldErrors: {} };
}

async function request(path, { method = "GET", body, signal, auth = true, notifyUnauthorized = true } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const sentToken = auth ? authToken : null;
  if (sentToken) headers.Authorization = `Bearer ${sentToken}`;
  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      signal,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ApiError(`Cannot reach the ResQ Nexus API at ${API_BASE_URL}.`, 0);
  }
  if (response.status === 204) return null;
  if (!response.ok) {
    let parsed = { message: `Request failed (${response.status}).`, fieldErrors: {} };
    try {
      const data = await response.json();
      if (data?.detail !== undefined) parsed = parseDetail(data.detail);
    } catch {
      // body was not JSON; keep the generic message
    }
    // A token that stops working (expired, account deactivated) ends the session.
    if (response.status === 401 && notifyUnauthorized && sentToken && sentToken === authToken) unauthorizedHandler?.(parsed.message);
    throw new ApiError(parsed.message, response.status, parsed.fieldErrors);
  }
  return response.json();
}

const get = (path, options) => request(path, options);
const send = (method, path, body, options) => request(path, { ...options, method, body });
const query = (params) => {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  return entries.length ? `?${new URLSearchParams(entries.map(([k, v]) => [k, String(v)]))}` : "";
};

// ------------------------------------------------------------------ public + Command Centre (admin)
const scenarioPath = (id) => `/scenarios/${encodeURIComponent(id)}`;

export const fetchHealth = (options) => get("/health", { ...options, auth: false });
export const fetchScenarios = (options) => get("/scenarios", { ...options, auth: false });
export const fetchScenario = (id, options) => get(scenarioPath(id), options);
export const fetchPriority = (id, weights, options) => get(`${scenarioPath(id)}/priority${weights ? query(weights) : ""}`, options);

const runBody = (weights, includeSos) => ({ ...(weights ? { weights } : {}), ...(includeSos ? { include_sos: true } : {}) });
export const postAllocate = (id, weights, includeSos, options) =>
  send("POST", `${scenarioPath(id)}/allocate`, runBody(weights, includeSos), options);
export const postExplain = (id, weights, includeSos, options) =>
  send("POST", `${scenarioPath(id)}/explain`, runBody(weights, includeSos), options);

// ------------------------------------------------------------------ damage assessment & imagery
export const fetchDamageStatus = (options) => get("/damage/status", options);
export const fetchDamageSamples = (options) => get("/damage/samples", options);
export const fetchDamageMetrics = (options) => get("/damage/metrics", options);
export const postAssessDamage = (body, options) => send("POST", "/damage/assess", body, options);
export const postAllocateDamage = (body, options) => send("POST", "/damage/allocate", body, options);
export const fetchScenarioBuildings = (id, options) => get(`/scenarios/${encodeURIComponent(id)}/buildings`, options);
export const fetchVantorEvents = (limit = 10, options) => get(`/damage/vantor/events?limit=${limit}`, options);
export const postSearchVantor = (body, options) => send("POST", "/damage/vantor/search", body, options);

// ------------------------------------------------------------------ accounts
export const postLogin = (email, password) => send("POST", "/auth/login", { email, password }, { auth: false });
export const postRegister = (body) => send("POST", "/auth/register", body, { auth: false });
export const postRegisterProvider = (body) => send("POST", "/auth/register/provider", body, { auth: false });
export const fetchMe = (options) => get("/auth/me", options);

// ------------------------------------------------------------------ citizens
export const sendSos = (location) => send("POST", "/sos", location);
export const addSosDetails = (id, details) => send("PATCH", `/sos/${id}/details`, details);
export const fetchMySos = (options) => get("/sos/mine", options);
export const fetchSos = (id, options) => get(`/sos/${id}`, options);
export const fetchNearbyResources = ({ lat, lon, radiusKm, types }, options) =>
  get(`/resources/nearby${query({ lat, lon, radius_km: radiusKm, types: types?.length ? types.join(",") : undefined })}`, options);

// ------------------------------------------------------------------ service providers
export const fetchProviderResources = (options) => get("/provider/resources", options);
export const updateProviderResource = (id, changes) => send("PATCH", `/provider/resources/${id}`, changes);
export const fetchProviderRequests = (radiusKm, options) => get(`/provider/requests${query({ radius_km: radiusKm })}`, options);
export const acceptRequest = (id) => send("POST", `/provider/requests/${id}/accept`);
export const setRequestStatus = (id, status) => send("POST", `/provider/requests/${id}/status`, { status });

// ------------------------------------------------------------------ admins
export const fetchAdminSummary = (options) => get("/admin/summary", options);
export const fetchAdminSos = (filters = {}, options) =>
  get(`/admin/sos${query({ status: filters.status?.join(","), type: filters.type?.join(",") })}`, options);
export const fetchSuggestions = (id, options) => get(`/admin/sos/${id}/suggestions`, options);
export const assignSos = (id, providerId) => send("POST", `/admin/sos/${id}/assign`, { provider_id: providerId });
export const adminSetSosStatus = (id, status) => send("POST", `/admin/sos/${id}/status`, { status });
export const fetchAdminProviders = (status, options) => get(`/admin/providers${query({ status })}`, options);
export const approveProvider = (id) => send("POST", `/admin/providers/${id}/approve`);
export const rejectProvider = (id, note) => send("POST", `/admin/providers/${id}/reject`, note ? { note } : {});
export const fetchAdminUsers = (role, options) => get(`/admin/users${query({ role })}`, options);
export const updateUser = (id, changes) => send("PATCH", `/admin/users/${id}`, changes);
export const fetchAdminResources = (filters = {}, options) =>
  get(`/admin/resources${query({ type: filters.type, region: filters.region, status: filters.status })}`, options);
export const createResource = (body) => send("POST", "/admin/resources", body);
export const updateResource = (id, changes) => send("PATCH", `/admin/resources/${id}`, changes);
export const deleteResource = (id) => send("DELETE", `/admin/resources/${id}`);

// ------------------------------------------------------------------ Phase 4: Live Alerts, Sentinel-1 & Replay
export const fetchAlerts = (filters = {}, options) =>
  get(`/alerts${query({ status: filters.status, disaster_type: filters.disasterType, limit: filters.limit })}`, options);
export const fetchAlertMetrics = (options) => get("/alerts/metrics", options);
export const acknowledgeAlert = (id) => send("POST", `/alerts/${id}/acknowledge`);
export const simulateAlert = (body) => send("POST", "/alerts/simulate", body);
export const fetchSentinelStatus = (options) => get("/sentinel/status", options);
export const searchSentinelImagery = (body, options) => send("POST", "/sentinel/search", body, options);
export const assessSentinelFlood = (body, options) => send("POST", "/sentinel/assess", body, options);
export const fetchReplayScenarios = (options) => get("/replay/scenarios", options);
export const fetchScenarioTimeline = (id, options) => get(`/replay/${encodeURIComponent(id)}`, options);

// ------------------------------------------------------------------ Phase 5: Situation Reports & Decision Explanations
export const fetchSituationReport = (scenarioId, lang = "en", options) =>
  get(`/reports/${encodeURIComponent(scenarioId)}${query({ lang })}`, options);
export const fetchDetailedZoneExplanation = (scenarioId, zoneId, lang = "en", options) =>
  get(`/reports/${encodeURIComponent(scenarioId)}/zones/${encodeURIComponent(zoneId)}/explain${query({ lang })}`, options);
export const runPollJob = (indiaOnly = true, options) =>
  send("POST", `/jobs/poll${query({ india_only: indiaOnly })}`, {}, options);
