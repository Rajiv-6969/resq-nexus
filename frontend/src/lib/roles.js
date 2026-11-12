// Roles, where each one lands after login, and its navigation links.

export const ROLE_LABELS = { CITIZEN: "Citizen", SERVICE_PROVIDER: "Service provider", ADMIN: "Admin" };

// Each role's own dashboard.
export const ROLE_HOME = { CITIZEN: "/sos", SERVICE_PROVIDER: "/provider", ADMIN: "/admin" };

export const NAV_LINKS = {
  PUBLIC: [
    { to: "/", label: "Home", end: true },
    { to: "/about", label: "About" },
    { to: "/login", label: "Login" },
  ],
  CITIZEN: [
    { to: "/sos", label: "SOS" },
    { to: "/requests", label: "My Requests" },
    { to: "/resources", label: "Nearby Resources" },
  ],
  SERVICE_PROVIDER: [
    { to: "/provider", label: "Dashboard", end: true },
    { to: "/provider/requests", label: "Requests" },
    { to: "/provider/resources", label: "My Resources" },
  ],
  ADMIN: [
    { to: "/admin", label: "SOS Monitor", end: true },
    { to: "/command", label: "Command Centre" },
    { to: "/damage", label: "Damage" },
    { to: "/admin/incidents/new", label: "New Incident" },
    { to: "/admin/providers", label: "Providers" },
    { to: "/admin/resources", label: "Resources" },
    { to: "/admin/users", label: "Users" },
  ],
};

export const homeFor = (user) => (user ? ROLE_HOME[user.role] ?? "/" : "/");

// Only same-site paths, and never back to the account pages themselves.
export function safeNext(next) {
  if (!next || !next.startsWith("/") || next.startsWith("//")) return null;
  return /^\/(login|register|logout)\b/.test(next) ? null : next;
}

// Demo accounts for the login page's Demo Login buttons. The passwords are public on purpose
// (they are listed in the README); every seeded account of a role shares its password.
export const DEMO_ACCOUNTS = [
  { role: "CITIZEN", label: "Citizen", email: "citizen@resq.example", password: "Citizen#2026" },
  { role: "SERVICE_PROVIDER", label: "Service provider", email: "provider@resq.example", password: "Provider#2026" },
  { role: "ADMIN", label: "Admin", email: "admin@resq.example", password: "Admin#2026" },
];
