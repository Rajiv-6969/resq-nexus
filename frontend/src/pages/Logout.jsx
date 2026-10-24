import { useEffect } from "react";
import PageLoader from "../components/PageLoader";
import { useAuth } from "../state/contexts";

// Ends the session and returns to the login page.
export default function Logout() {
  const { logout } = useAuth();
  useEffect(() => {
    logout("You have logged out.");
  }, [logout]);
  return <PageLoader label="Logging out" />;
}
