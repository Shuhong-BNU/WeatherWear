import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { Suspense, lazy, useEffect } from "react";
import { useTranslation } from "react-i18next";
import AppFrame from "./layout/AppFrame";
import { useWeatherWearSession } from "./state/WeatherWearSession";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const FavoritesPage = lazy(() => import("./pages/FavoritesPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));
const LogsPage = lazy(() => import("./pages/LogsPage"));
const MapConfigPage = lazy(() => import("./pages/MapConfigPage"));
const ModelConfigPage = lazy(() => import("./pages/ModelConfigPage"));
const PlaygroundPage = lazy(() => import("./pages/PlaygroundPage"));
const PreferencesPage = lazy(() => import("./pages/PreferencesPage"));
const QueryPage = lazy(() => import("./pages/QueryPage"));
const SystemStatusPage = lazy(() => import("./pages/SystemStatusPage"));
const TracePage = lazy(() => import("./pages/TracePage"));

function DeveloperOnlyOutlet() {
  const { t } = useTranslation();
  const { developerSession, developerSessionLoading, viewMode, setNotice } = useWeatherWearSession();
  const locked = developerSession?.required && !developerSession.unlocked;

  useEffect(() => {
    if (viewMode !== "developer" || locked) {
      setNotice({
        tone: "warning",
        message: locked ? t("shell.devUnlockRequired") : t("shell.devOnlyNotice"),
      });
    }
  }, [locked, setNotice, t, viewMode]);

  if (developerSessionLoading) {
    return null;
  }

  if (viewMode !== "developer" || locked) {
    return <Navigate to="/query" replace />;
  }
  return <Outlet />;
}

function RouteFallback() {
  const { t } = useTranslation();
  return (
    <section className="panel p-6">
      <div className="section-title">{t("common.loading")}</div>
      <div className="muted-copy mt-2">{t("shell.runtimeLoading")}</div>
    </section>
  );
}

export default function AppRouter() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route element={<AppFrame />}>
            <Route path="/" element={<Navigate to="/query" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/query" element={<QueryPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/favorites" element={<FavoritesPage />} />
            <Route path="/preferences" element={<PreferencesPage />} />

            <Route element={<DeveloperOnlyOutlet />}>
              <Route path="/dev/playground" element={<PlaygroundPage />} />
              <Route path="/dev/trace" element={<TracePage />} />
              <Route path="/dev/model-config" element={<ModelConfigPage />} />
              <Route path="/dev/map-config" element={<MapConfigPage />} />
              <Route path="/dev/system-status" element={<SystemStatusPage />} />
              <Route path="/dev/logs" element={<LogsPage />} />
            </Route>

            <Route path="*" element={<Navigate to="/query" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
