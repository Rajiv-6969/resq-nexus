// Shared labels, colours and formatting helpers for the dashboard.

export const PRIORITY_LEVELS = ["Critical", "High", "Medium", "Low"];

// Marker fill / outline per priority level (red, orange, yellow, green).
export const LEVEL_COLORS = {
  Critical: { fill: "#dc2626", stroke: "#991b1b" },
  High: { fill: "#f97316", stroke: "#c2410c" },
  Medium: { fill: "#eab308", stroke: "#a16207" },
  Low: { fill: "#16a34a", stroke: "#166534" },
};

export const SEVERITY_LABELS = ["None", "Minor", "Major", "Destroyed"];

export const DISASTER_LABELS = { flood: "Flood", earthquake: "Earthquake", wildfire: "Wildfire" };

export const RESOURCES = [
  { key: "rescue_teams", label: "Rescue teams", hint: "search & rescue teams" },
  { key: "medical_kits", label: "Medical kits", hint: "first-aid / medical kits" },
  { key: "food_packets", label: "Food packets", hint: "one-day ration packets" },
  { key: "shelters", label: "Shelters", hint: "units, ~100 people each" },
  { key: "vehicles", label: "Vehicles", hint: "trucks, boats, ambulances" },
];

// Score breakdown rows: contribution key -> label and the weight it uses.
export const BREAKDOWN = [
  { key: "severity", label: "Damage severity", weight: "severity" },
  { key: "population", label: "Population", weight: "population" },
  { key: "vulnerability", label: "Vulnerability", weight: "vulnerability" },
  { key: "accessibility", label: "Poor road access", weight: "accessibility" },
];

export const PIPELINE = [
  { name: "Assess", status: "done" },
  { name: "Prioritise", status: "current" },
  { name: "Allocate", status: "next" },
  { name: "Explain", status: "next" },
];

const numberFormat = new Intl.NumberFormat("en-IN");
export const formatNumber = (value) => numberFormat.format(value);

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
