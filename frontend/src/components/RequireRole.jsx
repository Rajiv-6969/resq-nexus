import { useEffect, useRef } from "react";
import { Navigate, useLocation } from "react-router";
import { homeFor } from "../lib/roles";
import { useAuth, useToast } from "../state/contexts";
import PageLoader from "./PageLoader";

function WrongRole({ to }) {
  const toast = useToast();
  const shown = useRef(false);
  useEffect(() => {
    if (shown.current) return;
    shown.current = true;
    toast.warning("Not available", "That page belongs to another kind of account.");
  }, [toast]);
  return <Navigate to={to} replace />;
}

// Protected route: visitors go to the login page (and come back after), other roles go to their own dashboard.
export default function RequireRole({ roles, children }) {
  const { user, ready } = useAuth();
  const location = useLocation();
  if (!ready) return <PageLoader label="Checking your session" />;
  if (!user) {
    const next = encodeURIComponent(`${location.pathname}${location.search}`);
    return <Navigate to={`/login?next=${next}`} replace state={{ message: "Log in to continue." }} />;
  }
  if (!roles.includes(user.role)) return <WrongRole to={homeFor(user)} />;
  return children;
}
