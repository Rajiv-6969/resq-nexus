import { motion } from "framer-motion";
import { Link, NavLink } from "react-router";
import { SCENARIO_PAGES } from "../constants";
import { useAppData } from "../state/contexts";
import { LogoMark, MapIcon, SparkIcon } from "./icons";

const LINKS = [
  { to: "/command", label: "Command Centre", icon: MapIcon },
];

export default function NavBar() {
  const { scenarioId, health, geminiConfigured } = useAppData();
  const query = scenarioId ? `?scenario=${encodeURIComponent(scenarioId)}` : "";
  const apiState = health.status; // checking | online | offline

  return (
    <header className="nav">
      <Link to="/" className="brand" aria-label="ResQ Nexus home">
        <LogoMark size={34} />
        <span className="brand-name">ResQ Nexus</span>
      </Link>

      <nav className="nav-links" aria-label="Main">
        {LINKS.map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={SCENARIO_PAGES.includes(to) ? `${to}${query}` : to} className="nav-link">
            {({ isActive }) => (
              <>
                <Icon size={16} />
                <span>{label}</span>
                {isActive && <motion.span layoutId="nav-active" className="nav-active" transition={{ type: "spring", stiffness: 420, damping: 34 }} />}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="nav-status">
        <span className={`status-pill status-pill--${apiState}`} title={`Backend API: ${apiState}`}>
          <span className="status-dot" aria-hidden="true" />
          API {apiState === "online" ? "online" : apiState === "offline" ? "offline" : "…"}
        </span>
        <span
          className={`status-pill ${geminiConfigured ? "status-pill--ai" : "status-pill--muted"}`}
          title={geminiConfigured ? "Explanations are written by Google Gemini" : "No GEMINI_API_KEY: template explanations"}
        >
          <SparkIcon size={13} />
          {geminiConfigured ? "Gemini" : "Templates"}
        </span>
      </div>
    </header>
  );
}
