import { Link, NavLink } from "react-router";
import { SHOW_ANALYTICS } from "../config";
import { SCENARIO_PAGES } from "../constants";
import { useAppData } from "../state/contexts";
import { AsteriskMark } from "./icons";

const LINKS = [
  { to: "/command", label: "Command Centre" },
  { to: "/analytics", label: "Analytics" },
  { to: "/damage", label: "Damage Assessment" },
  { to: "/about", label: "About" },
].filter((link) => SHOW_ANALYTICS || link.to !== "/analytics");

const API_TEXT = { checking: "API …", online: "API online", offline: "API offline" };

export default function NavBar() {
  const { scenarioId, health, geminiConfigured } = useAppData();
  const query = scenarioId ? `?scenario=${encodeURIComponent(scenarioId)}` : "";
  const apiState = health.status; // checking | online | offline

  return (
    <header className="nav">
      <Link to="/" className="wordmark" aria-label="ResQ Nexus home">
        <AsteriskMark size={17} />
        <span>ResQ Nexus</span>
      </Link>

      <nav className="nav-links" aria-label="Main">
        {LINKS.map(({ to, label }) => (
          <NavLink key={to} to={SCENARIO_PAGES.includes(to) ? `${to}${query}` : to} className="nav-link">
            {label}
          </NavLink>
        ))}
      </nav>

      <p
        className="nav-status mono"
        title={geminiConfigured ? "Explanations are written by Google Gemini" : "No GEMINI_API_KEY: template explanations"}
      >
        <span className={`status-sq is-${apiState}`} aria-hidden="true" />
        {API_TEXT[apiState] ?? "API"} / {geminiConfigured ? "Gemini" : "Templates"}
      </p>
    </header>
  );
}
