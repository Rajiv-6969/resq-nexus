import { lazy, Suspense, useEffect } from "react";
import { AnimatePresence, MotionConfig } from "framer-motion";
import { Navigate, Route, Routes, useLocation } from "react-router";
import Backdrop from "./components/Backdrop";
import NavBar from "./components/NavBar";
import PageTransition from "./components/PageTransition";
import { SHOW_ANALYTICS } from "./config";
import Landing from "./pages/Landing";
import AppDataProvider from "./state/AppDataProvider";
import ToastProvider from "./state/ToastProvider";

const loadCommandCentre = () => import("./pages/CommandCentre");
const loadAnalytics = SHOW_ANALYTICS ? () => import("./pages/Analytics") : null;
const loadDamage = () => import("./pages/DamageAssessment");
const loadAbout = () => import("./pages/About");
const CommandCentre = lazy(loadCommandCentre);
const Analytics = SHOW_ANALYTICS ? lazy(loadAnalytics) : null;
const DamageAssessment = lazy(loadDamage);
const About = lazy(loadAbout);

function PageLoader() {
  return (
    <div className="page-loader" role="status">
      <span className="spinner" aria-hidden="true" />
      Loading…
    </div>
  );
}

const page = (element) => <PageTransition>{element}</PageTransition>;

export default function App() {
  const location = useLocation();

  // Fetch the other pages in the background so navigating never waits on a download.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      [loadCommandCentre, loadAnalytics, loadDamage, loadAbout].forEach((load) => load?.().catch(() => {}));
    }, 900);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <MotionConfig reducedMotion="user">
      <ToastProvider>
        <AppDataProvider>
          <Backdrop />
          <div className="shell">
            <a className="skip-link" href="#main">
              Skip to content
            </a>
            <NavBar />
            <Suspense fallback={<PageLoader />}>
              <AnimatePresence mode="wait">
                <Routes location={location} key={location.pathname}>
                  <Route path="/" element={page(<Landing />)} />
                  <Route path="/command" element={page(<CommandCentre />)} />
                  {SHOW_ANALYTICS && <Route path="/analytics" element={page(<Analytics />)} />}
                  <Route path="/damage" element={page(<DamageAssessment />)} />
                  <Route path="/about" element={page(<About />)} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </AnimatePresence>
            </Suspense>
          </div>
        </AppDataProvider>
      </ToastProvider>
    </MotionConfig>
  );
}
