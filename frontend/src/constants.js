// Shared labels, colours and formatting helpers for the whole UI.

export const PRIORITY_LEVELS = ["Critical", "High", "Medium", "Low"];

// Priority colours: signal red, orange, light concrete, dark concrete.
export const LEVEL_COLORS = {
  Critical: { fill: "#E10600", text: "#FFFFFF" },
  High: { fill: "#FF6B1A", text: "#0A0A0A" },
  Medium: { fill: "#C9C7C1", text: "#0A0A0A" },
  Low: { fill: "#5A5A57", text: "#EDEBE6" },
};

// Depot series colours (charts only; the map labels depots A, B, C ...).
export const CLUSTER_COLORS = ["#0A0A0A", "#E10600", "#8A8A85", "#FF6B1A", "#C9C7C1"];
export const clusterColor = (index) => CLUSTER_COLORS[index % CLUSTER_COLORS.length];

export const SEVERITY_LABELS = ["None", "Minor", "Major", "Destroyed"];
export const DISASTER_META = {
  flood: { label: "Flood", verb: "Flooding" },
  earthquake: { label: "Earthquake", verb: "Ground shaking" },
  wildfire: { label: "Wildfire", verb: "Fire spread" },
  cyclone: { label: "Cyclone", verb: "Wind and storm surge" },
};
export const disasterLabel = (type) => DISASTER_META[type]?.label ?? type;

export const RESOURCES = [
  { key: "rescue_teams", label: "Rescue teams", short: "Rescue", hint: "search & rescue teams", color: "#E10600" },
  { key: "medical_kits", label: "Medical kits", short: "Medical", hint: "first-aid / medical kits", color: "#0A0A0A" },
  { key: "food_packets", label: "Food packets", short: "Food", hint: "one-day ration packets", color: "#8A8A85" },
  { key: "shelters", label: "Shelters", short: "Shelter", hint: "units, ~100 people each", color: "#C9C7C1" },
  { key: "vehicles", label: "Vehicles", short: "Vehicles", hint: "trucks, boats, ambulances", color: "#FF6B1A" },
];

// Score breakdown rows: contribution key -> label and the weight it uses.
export const BREAKDOWN = [
  { key: "severity", label: "Damage severity", weight: "severity" },
  { key: "population", label: "Population", weight: "population" },
  { key: "vulnerability", label: "Vulnerability", weight: "vulnerability" },
  { key: "accessibility", label: "Poor road access", weight: "accessibility" },
];

// Priority weight sliders (w1..w4). Values are relative; the API rescales them to sum to 1.
export const WEIGHT_FIELDS = [
  { key: "severity", label: "Damage severity", symbol: "w1" },
  { key: "population", label: "Population", symbol: "w2" },
  { key: "vulnerability", label: "Vulnerability", symbol: "w3" },
  { key: "accessibility", label: "Poor road access", symbol: "w4" },
];
export const DEFAULT_WEIGHTS = { severity: 40, population: 25, vulnerability: 20, accessibility: 15 };
export const weightsKey = (w) => WEIGHT_FIELDS.map((f) => w[f.key]).join("-");
export const isDefaultWeights = (w) => weightsKey(w) === weightsKey(DEFAULT_WEIGHTS);

export const PIPELINE_STEPS = [
  { key: "assess", name: "Assess", detail: "Damage & exposure" },
  { key: "prioritise", name: "Prioritise", detail: "Score every zone" },
  { key: "allocate", name: "Allocate", detail: "Allocation Engine" },
  { key: "explain", name: "Explain", detail: "Plain-language reasons" },
];

const numberFormat = new Intl.NumberFormat("en-IN");
export const formatNumber = (value) => numberFormat.format(Math.round(value));

// Resource and service-provider organisation types, with the unit their capacity counts.
export const RESOURCE_TYPES = ["HOSPITAL", "AMBULANCE", "SHELTER", "FOOD", "WATER", "FIRE_STATION", "POLICE"];
export const RESOURCE_META = {
  HOSPITAL: { label: "Hospital", plural: "Hospitals", org: "Hospital", unit: "beds" },
  AMBULANCE: { label: "Ambulance", plural: "Ambulances", org: "Ambulance service", unit: "ambulances" },
  SHELTER: { label: "Shelter", plural: "Shelters", org: "Shelter / relief camp", unit: "places" },
  FOOD: { label: "Food point", plural: "Food points", org: "Food distribution", unit: "food packets" },
  WATER: { label: "Water point", plural: "Water points", org: "Water supply", unit: "litres" },
  FIRE_STATION: { label: "Fire station", plural: "Fire stations", org: "Fire and rescue", unit: "fire engines" },
  POLICE: { label: "Police station", plural: "Police", org: "Police", unit: "patrol units" },
};
export const RESOURCE_STATUSES = ["OPEN", "FULL", "CLOSED"];

// SOS requests: the emergency details form and the status tracker.
export const EMERGENCY_TYPES = [
  { value: "flood", label: "Flood" },
  { value: "earthquake", label: "Earthquake" },
  { value: "wildfire", label: "Wildfire" },
  { value: "cyclone", label: "Cyclone" },
  { value: "fire", label: "Fire" },
  { value: "medical", label: "Medical" },
  { value: "other", label: "Other" },
];
export const INJURY_LEVELS = [
  { value: "none", label: "None" },
  { value: "minor", label: "Minor" },
  { value: "serious", label: "Serious" },
  { value: "critical", label: "Critical" },
];
export const NEEDS = [
  { value: "rescue", label: "Rescue" },
  { value: "medical", label: "Medical" },
  { value: "ambulance", label: "Ambulance" },
  { value: "food", label: "Food" },
  { value: "water", label: "Water" },
  { value: "shelter", label: "Shelter" },
];
export const VULNERABLE_GROUPS = [
  { value: "children", label: "Children" },
  { value: "elderly", label: "Elderly" },
  { value: "disabled", label: "Disabled" },
  { value: "pregnant", label: "Pregnant" },
];
export const SOS_STATUSES = ["PENDING", "ACKNOWLEDGED", "DISPATCHED", "RESOLVED"];
export const SOS_STEPS = {
  PENDING: { label: "Pending", detail: "Alert received, waiting for a responder" },
  ACKNOWLEDGED: { label: "Acknowledged", detail: "A responder has accepted your request" },
  DISPATCHED: { label: "Dispatched", detail: "Help is on the way" },
  RESOLVED: { label: "Resolved", detail: "The request is closed" },
};
export const labelFor = (list, value) => list.find((item) => item.value === value)?.label ?? value;
export const formatScore = (value) => value.toFixed(3);

export function accessLabel(accessibility) {
  if (accessibility < 0.3) return "Poor";
  if (accessibility < 0.6) return "Limited";
  return "Good";
}

export function vulnerabilityLabel(index) {
  if (index >= 0.66) return "High";
  if (index >= 0.33) return "Moderate";
  return "Low";
}

export const levelClass = (level) => level.toLowerCase();

// Pages whose URL carries ?scenario=<id>.
export const SCENARIO_PAGES = ["/command", "/damage", "/analytics"];
