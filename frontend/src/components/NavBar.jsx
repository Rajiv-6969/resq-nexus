import { useTranslation } from "react-i18next";
import { Link, NavLink } from "react-router";
import { SCENARIO_PAGES } from "../constants";
import { NAV_LINKS, ROLE_LABELS } from "../lib/roles";
import { useAppData, useAuth } from "../state/contexts";
import { AsteriskMark } from "./icons";

// Thin bordered bar: wordmark on the left, the role's links and the logged-in user on the right.
export default function NavBar() {
  const { i18n } = useTranslation();
  const { user } = useAuth();
  const { scenarioId } = useAppData();
  const query = scenarioId ? `?scenario=${encodeURIComponent(scenarioId)}` : "";
  const links = NAV_LINKS[user?.role ?? "PUBLIC"];

  return (
    <header className="nav">
      <Link to="/" className="wordmark" aria-label="ResQ Nexus home">
        <AsteriskMark size={17} />
        <span>ResQ Nexus</span>
      </Link>

      <nav className="nav-links" aria-label="Main">
        {links.map(({ to, label, end }) => (
          <NavLink key={to} to={SCENARIO_PAGES.includes(to) ? `${to}${query}` : to} end={end} className="nav-link">
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="nav-lang mono" aria-label="Language selector">
        <button
          type="button"
          className={`nav-lang-btn ${i18n.language === "en" ? "active" : ""}`}
          onClick={() => i18n.changeLanguage("en")}
          aria-label="English"
        >
          EN
        </button>
        <span className="nav-lang-sep">/</span>
        <button
          type="button"
          className={`nav-lang-btn ${i18n.language === "hi" ? "active" : ""}`}
          onClick={() => i18n.changeLanguage("hi")}
          aria-label="Hindi"
        >
          HI
        </button>
      </div>

      {user && (
        <div className="nav-user">
          <p className="nav-who mono" title={user.email}>
            <span className="nav-name">{user.full_name}</span>
            <span className={`nav-role nav-role--${user.role.toLowerCase()}`}>{ROLE_LABELS[user.role]}</span>
          </p>
          <Link to="/logout" className="nav-logout mono">
            Logout
          </Link>
        </div>
      )}
    </header>
  );
}
