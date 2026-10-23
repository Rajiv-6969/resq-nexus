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
export const SEVERITY_COLORS = ["#5A5A57", "#C9C7C1", "#FF6B1A", "#E10600"];

export const DISASTER_META = {
  flood: { label: "Flood", verb: "Flooding" },
  earthquake: { label: "Earthquake", verb: "Ground shaking" },
  wildfire: { label: "Wildfire", verb: "Fire spread" },
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
