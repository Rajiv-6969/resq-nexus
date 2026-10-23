// Shared labels, colours and formatting helpers for the whole UI.

export const PRIORITY_LEVELS = ["Critical", "High", "Medium", "Low"];

// Priority colours (red / orange / yellow / green) tuned for the dark theme.
export const LEVEL_COLORS = {
  Critical: { fill: "#E63946", stroke: "#ff9aa2", glow: "rgba(230, 57, 70, 0.55)" },
  High: { fill: "#F4A261", stroke: "#ffd2ad", glow: "rgba(244, 162, 97, 0.45)" },
  Medium: { fill: "#E9C46A", stroke: "#f7e3ae", glow: "rgba(233, 196, 106, 0.4)" },
  Low: { fill: "#52B788", stroke: "#a4e3c2", glow: "rgba(82, 183, 136, 0.4)" },
};

// Depot / cluster colours: kept apart from the priority colours on purpose.
export const CLUSTER_COLORS = ["#4CC9F0", "#B388FF", "#FF7EB6", "#7AE7C7", "#FFD6A5"];
export const clusterColor = (index) => CLUSTER_COLORS[index % CLUSTER_COLORS.length];

export const SEVERITY_LABELS = ["None", "Minor", "Major", "Destroyed"];
export const SEVERITY_COLORS = ["#52B788", "#E9C46A", "#F4A261", "#E63946"];

export const DISASTER_META = {
  flood: { label: "Flood", color: "#4CC9F0", verb: "Flooding" },
  earthquake: { label: "Earthquake", color: "#F4A261", verb: "Ground shaking" },
  wildfire: { label: "Wildfire", color: "#FF6B35", verb: "Fire spread" },
};
export const disasterLabel = (type) => DISASTER_META[type]?.label ?? type;

export const RESOURCES = [
  { key: "rescue_teams", label: "Rescue teams", short: "Rescue", hint: "search & rescue teams", color: "#E63946" },
  { key: "medical_kits", label: "Medical kits", short: "Medical", hint: "first-aid / medical kits", color: "#FF7EB6" },
  { key: "food_packets", label: "Food packets", short: "Food", hint: "one-day ration packets", color: "#FFD166" },
  { key: "shelters", label: "Shelters", short: "Shelter", hint: "units, ~100 people each", color: "#2EC4B6" },
  { key: "vehicles", label: "Vehicles", short: "Vehicles", hint: "trucks, boats, ambulances", color: "#B388FF" },
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
export const SCENARIO_PAGES = ["/command", "/analytics", "/damage"];
