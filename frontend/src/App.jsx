import { lazy, Suspense, useEffect } from "react";
import { AnimatePresence, MotionConfig } from "framer-motion";
import { Navigate, Route, Routes, useLocation } from "react-router";
import DemoBar from "./components/DemoBar";
import Footer from "./components/Footer";
import NavBar from "./components/NavBar";
import PageLoader from "./components/PageLoader";
import PageTransition from "./components/PageTransition";
import RequireRole from "./components/RequireRole";
import { SHOW_ANALYTICS } from "./config";
import Landing from "./pages/Landing";
import AppDataProvider from "./state/AppDataProvider";
import AuthProvider from "./state/AuthProvider";
import ToastProvider from "./state/ToastProvider";

const loaders = {
  CommandCentre: () => import("./pages/CommandCentre"),
  Analytics: SHOW_ANALYTICS ? () => import("./pages/Analytics") : null,
  DamageAssessment: () => import("./pages/DamageAssessment"),
  About: () => import("./pages/About"),
  Login: () => import("./pages/Login"),
  Register: () => import("./pages/Register"),
  Logout: () => import("./pages/Logout"),
  SosHome: () => import("./pages/citizen/SosHome"),
  SosTrack: () => import("./pages/citizen/SosTrack"),
  MyRequests: () => import("./pages/citizen/MyRequests"),
  NearbyResources: () => import("./pages/citizen/NearbyResources"),
  ProviderDashboard: () => import("./pages/provider/ProviderDashboard"),
  ProviderRequests: () => import("./pages/provider/ProviderRequests"),
  ProviderResources: () => import("./pages/provider/ProviderResources"),
  SosMonitor: () => import("./pages/admin/SosMonitor"),
  AdminTables: () => import("./pages/admin/AdminTables"),
  NewIncident: () => import("./pages/admin/NewIncident"),
  LiveMode: () => import("./pages/LiveMode"),
};
const LiveMode = lazy(loaders.LiveMode);
const CommandCentre = lazy(loaders.CommandCentre);
const Analytics = SHOW_ANALYTICS ? lazy(loaders.Analytics) : null;
const DamageAssessment = lazy(loaders.DamageAssessment);
const About = lazy(loaders.About);
const Login = lazy(loaders.Login);
const Register = lazy(loaders.Register);
const Logout = lazy(loaders.Logout);
const SosHome = lazy(loaders.SosHome);
const SosTrack = lazy(loaders.SosTrack);
const MyRequests = lazy(loaders.MyRequests);
const NearbyResources = lazy(loaders.NearbyResources);
const ProviderDashboard = lazy(loaders.ProviderDashboard);
const ProviderRequests = lazy(loaders.ProviderRequests);
const ProviderResources = lazy(loaders.ProviderResources);
const SosMonitor = lazy(loaders.SosMonitor);
const NewIncident = lazy(loaders.NewIncident);
const AdminProviders = lazy(() => loaders.AdminTables().then((m) => ({ default: m.AdminProviders })));
const AdminResources = lazy(() => loaders.AdminTables().then((m) => ({ default: m.AdminResources })));
const AdminUsers = lazy(() => loaders.AdminTables().then((m) => ({ default: m.AdminUsers })));

const ADMIN = ["ADMIN"];
const CITIZEN = ["CITIZEN"];
const PROVIDER = ["SERVICE_PROVIDER"];

const page = (element) => <PageTransition>{element}</PageTransition>;
const guarded = (roles, element) => page(<RequireRole roles={roles}>{element}</RequireRole>);

export default function App() {
  const location = useLocation();

  // Fetch the other pages in the background so navigating never waits on a download.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      Object.values(loaders).forEach((load) => load?.().catch(() => {}));
    }, 900);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <MotionConfig reducedMotion="user">
      <ToastProvider>
        <AuthProvider>
          <AppDataProvider>
            <div className="shell">
              <a className="skip-link" href="#main">
                Skip to content
              </a>
              <DemoBar />
              <NavBar />
              <Suspense fallback={<PageLoader />}>
                <AnimatePresence mode="wait">
                  <Routes location={location} key={location.pathname}>
                    <Route path="/" element={page(<Landing />)} />
                    <Route path="/about" element={page(<About />)} />
                    <Route path="/login" element={page(<Login />)} />
                    <Route path="/register" element={page(<Register />)} />
                    <Route path="/logout" element={<Logout />} />

                    <Route path="/sos" element={guarded(CITIZEN, <SosHome />)} />
                    <Route path="/sos/:id" element={guarded(CITIZEN, <SosTrack />)} />
                    <Route path="/requests" element={guarded(CITIZEN, <MyRequests />)} />
                    <Route path="/resources" element={guarded(CITIZEN, <NearbyResources />)} />

                    <Route path="/provider" element={guarded(PROVIDER, <ProviderDashboard />)} />
                    <Route path="/provider/requests" element={guarded(PROVIDER, <ProviderRequests />)} />
                    <Route path="/provider/resources" element={guarded(PROVIDER, <ProviderResources />)} />

                    <Route path="/admin" element={guarded(ADMIN, <SosMonitor />)} />
                    <Route path="/live" element={guarded(ADMIN, <LiveMode />)} />
                    <Route path="/admin/incidents/new" element={guarded(ADMIN, <NewIncident />)} />
                    <Route path="/admin/providers" element={guarded(ADMIN, <AdminProviders />)} />
                    <Route path="/admin/resources" element={guarded(ADMIN, <AdminResources />)} />
                    <Route path="/admin/users" element={guarded(ADMIN, <AdminUsers />)} />
                    <Route path="/command" element={guarded(ADMIN, <CommandCentre />)} />
                    <Route path="/damage" element={guarded(ADMIN, <DamageAssessment />)} />
                    {SHOW_ANALYTICS && <Route path="/analytics" element={guarded(ADMIN, <Analytics />)} />}

                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </AnimatePresence>
              </Suspense>
              <Footer />
            </div>
          </AppDataProvider>
        </AuthProvider>
      </ToastProvider>
    </MotionConfig>
  );
}
