import { createContext, lazy, Suspense, useContext, useEffect, useMemo, useState } from "react";
import { NavLink, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Activity, BarChart3, Database, Droplets, FileUp, FlaskConical,
  Gauge, LayoutDashboard, Waves, Wind, Workflow,
} from "lucide-react";
import { api } from "./api";

const OverviewPage = lazy(() => import("./pages/ObservationPages").then((module) => ({ default: module.OverviewPage })));
const DatasetExplorerPage = lazy(() => import("./pages/ObservationPages").then((module) => ({ default: module.DatasetExplorerPage })));
const ObservationPage = lazy(() => import("./pages/ObservationPages").then((module) => ({ default: module.ObservationPage })));
const SSTPage = lazy(() => import("./pages/ObservationPages").then((module) => ({ default: module.SSTPage })));
const ChlorophyllPage = lazy(() => import("./pages/ObservationPages").then((module) => ({ default: module.ChlorophyllPage })));
const NPZDPage = lazy(() => import("./pages/ModelPages").then((module) => ({ default: module.NPZDPage })));
const BayesianPage = lazy(() => import("./pages/ModelPages").then((module) => ({ default: module.BayesianPage })));
const PredictionPage = lazy(() => import("./pages/ModelPages").then((module) => ({ default: module.PredictionPage })));
const LimitationsPage = lazy(() => import("./pages/ModelPages").then((module) => ({ default: module.LimitationsPage })));
const UploadPage = lazy(() => import("./pages/UploadPages").then((module) => ({ default: module.UploadPage })));
const InteractivePredictionPage = lazy(() => import("./pages/UploadPages").then((module) => ({ default: module.InteractivePredictionPage })));

const UploadContext = createContext(null);

const navigation = [
  { group: "Workspace", items: [
    { title: "Overview", path: "/overview", icon: LayoutDashboard },
    { title: "Dataset Explorer", path: "/dataset", icon: Database },
    { title: "Ocean Observations", path: "/observations", icon: Activity },
  ] },
  { group: "Analysis", items: [
    { title: "Sea Surface Temperature", path: "/sst", icon: Gauge },
    { title: "Chlorophyll-a", path: "/chlorophyll", icon: Droplets },
    { title: "NPZD Model", path: "/npzd", icon: Workflow },
    { title: "Bayesian Estimation", path: "/bayesian", icon: BarChart3 },
  ] },
  { group: "Forecasting", items: [
    { title: "Dataset Upload", path: "/upload", icon: FileUp },
    { title: "Interactive Prediction", path: "/interactive-prediction", icon: Wind },
    { title: "Prediction Uncertainty", path: "/uncertainty", icon: Activity },
  ] },
  { group: "Reference", items: [
    { title: "Results & Limitations", path: "/limitations", icon: FlaskConical },
  ] },
];

const routeTitles = Object.fromEntries(
  navigation.flatMap((group) => group.items.map((item) => [item.path, item.title])),
);

function Shell() {
  const location = useLocation();
  const [serviceOnline, setServiceOnline] = useState(false);
  const [upload, setUpload] = useState(() => {
    try {
      return JSON.parse(sessionStorage.getItem("oceansense-upload") || "null");
    } catch {
      return null;
    }
  });

  useEffect(() => {
    let active = true;
    api("/health").then(() => active && setServiceOnline(true))
      .catch(() => active && setServiceOnline(false));
    const timer = window.setInterval(() => {
      api("/health").then(() => active && setServiceOnline(true))
        .catch(() => active && setServiceOnline(false));
    }, 15000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (upload) sessionStorage.setItem("oceansense-upload", JSON.stringify(upload));
    else sessionStorage.removeItem("oceansense-upload");
  }, [upload]);

  const uploadContext = useMemo(() => ({ upload, setUpload }), [upload]);
  const currentTitle = routeTitles[location.pathname] || "Overview";

  return (
    <UploadContext.Provider value={uploadContext}>
      <div className="app-shell">
        <aside className="sidebar">
          <NavLink to="/overview" className="brand">
            <span className="brand-icon"><Waves size={21} strokeWidth={1.8} /></span>
            <span><strong>OceanSense <em>AI</em></strong><small>MARINE ANALYTICS</small></span>
          </NavLink>
          <div className="sidebar-rule" />
          <nav aria-label="Main navigation">
            {navigation.map((group) => (
              <div className="nav-group" key={group.group}>
                <div className="nav-label">{group.group}</div>
                {group.items.map(({ title, path, icon: Icon }) => (
                  <NavLink key={path} to={path} title={title} aria-label={title} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
                    <Icon size={16} strokeWidth={1.8} />
                    <span>{title}</span>
                    {path === "/upload" && upload && <span className="nav-dot" title="Dataset uploaded" />}
                  </NavLink>
                ))}
              </div>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <div className="offline-mark"><span /> LOCAL WORKSPACE</div>
            <p>Bundled observations · Black Sea</p>
            <p>11 paired dates · 2003</p>
          </div>
        </aside>
        <div className="main-column">
          <header className="topbar">
            <div className="breadcrumbs"><span>OCEANSENSE</span><span className="crumb-slash">/</span>{currentTitle}</div>
            <div className="service-state">
              <span className={`service-dot${serviceOnline ? " online" : ""}`} />
              {serviceOnline ? "Local API connected" : "API unavailable"}
            </div>
          </header>
          <main className="main-content">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.18 }}
            >
              <Suspense fallback={<div className="state-box">Loading analysis page…</div>}>
                <Outlet context={uploadContext} />
              </Suspense>
            </motion.div>
          </main>
          <footer className="app-footer">
            <span>OceanSense AI <span className="footer-sep">/</span> Research prototype</span>
            <span>Observations and model output are distinguished throughout</span>
          </footer>
        </div>
      </div>
    </UploadContext.Provider>
  );
}

export function useUploadedDataset() {
  return useContext(UploadContext);
}

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="dataset" element={<DatasetExplorerPage />} />
        <Route path="observations" element={<ObservationPage />} />
        <Route path="sst" element={<SSTPage />} />
        <Route path="chlorophyll" element={<ChlorophyllPage />} />
        <Route path="npzd" element={<NPZDPage />} />
        <Route path="bayesian" element={<BayesianPage />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="interactive-prediction" element={<InteractivePredictionPage />} />
        <Route path="uncertainty" element={<PredictionPage />} />
        <Route path="limitations" element={<LimitationsPage />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Route>
    </Routes>
  );
}
