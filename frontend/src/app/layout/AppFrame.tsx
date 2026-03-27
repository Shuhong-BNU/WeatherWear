import { NavLink, Outlet, matchPath, useLocation, useNavigate } from "react-router-dom";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { APP_ROUTE_META } from "../routes";
import { useWeatherWearSession } from "../state/WeatherWearSession";

function isRuntimeHealthy(health: Record<string, unknown> | undefined) {
  const webStack = (health?.web_stack as { compatible?: boolean } | undefined)?.compatible;
  const suggestions = health?.suggestions as unknown[] | undefined;
  return webStack !== false && !(suggestions && suggestions.length);
}

export default function AppFrame() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const [showDevUnlock, setShowDevUnlock] = useState(false);
  const [pinInput, setPinInput] = useState("");
  const {
    developerSession,
    developerSessionLoading,
    lockDeveloperMode,
    locale,
    setLocale,
    unlockDeveloperMode,
    viewMode,
    setViewMode,
    runtimeHealth,
    runtimeHealthLoading,
    notice,
    dismissNotice,
  } = useWeatherWearSession();

  const currentRoute = useMemo(
    () =>
      APP_ROUTE_META.find((route) => matchPath({ path: route.path, end: true }, location.pathname)) ||
      APP_ROUTE_META[0],
    [location.pathname],
  );

  const visibleRoutes = APP_ROUTE_META.filter((route) => !route.devOnly || viewMode === "developer");
  const userRoutes = visibleRoutes.filter((route) => route.group === "user");
  const developerRoutes = visibleRoutes.filter((route) => route.group === "developer");
  const runtimeHealthy = isRuntimeHealthy(runtimeHealth);
  const developerUnlocked = Boolean(developerSession?.unlocked);
  const hideNewQueryButton = location.pathname === "/query";

  async function handleViewModeChange(nextMode: "user" | "developer") {
    if (nextMode === "user") {
      setViewMode("user");
      return;
    }
    if (developerSessionLoading) {
      return;
    }
    if (developerSession?.required && !developerSession.unlocked) {
      setShowDevUnlock(true);
      return;
    }
    setViewMode("developer");
  }

  async function handleUnlockSubmit() {
    const ok = await unlockDeveloperMode(pinInput);
    if (!ok) {
      return;
    }
    setPinInput("");
    setShowDevUnlock(false);
    setViewMode("developer");
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(96,165,250,0.15),transparent_28%),radial-gradient(circle_at_80%_10%,rgba(59,130,246,0.1),transparent_24%),#f6f9fc] p-4 md:p-5">
      <div className="mx-auto grid min-h-[calc(100vh-2rem)] max-w-[1600px] gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="panel flex h-full flex-col overflow-hidden px-5 py-5">
          <button
            type="button"
            className="text-left"
            onClick={() => navigate("/dashboard")}
          >
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-950 text-lg font-semibold text-white">
                W
              </div>
              <div>
                <div className="text-sm font-semibold text-slate-950">{t("common.appName")}</div>
                <div className="text-xs text-slate-500">{t("common.assistantName")}</div>
              </div>
            </div>
          </button>

          <nav className="mt-8 flex-1 space-y-6">
            <div>
              <div className="field-label">{t("nav.groupUser")}</div>
              <div className="mt-3 grid gap-1.5">
                {userRoutes.map((route) => (
                  <NavLink
                    key={route.path}
                    to={route.path}
                    className={({ isActive }: { isActive: boolean }) =>
                      isActive
                        ? "rounded-2xl bg-slate-950 px-4 py-3 text-sm font-semibold text-white"
                        : "rounded-2xl px-4 py-3 text-sm text-slate-600 transition hover:bg-slate-100 hover:text-slate-950"
                    }
                  >
                    {t(route.navKey)}
                  </NavLink>
                ))}
              </div>
            </div>

            {developerRoutes.length ? (
              <div>
                <div className="field-label">{t("nav.groupDeveloper")}</div>
                <div className="mt-3 grid gap-1.5">
                  {developerRoutes.map((route) => (
                    <NavLink
                      key={route.path}
                      to={route.path}
                      className={({ isActive }: { isActive: boolean }) =>
                        isActive
                          ? "rounded-2xl bg-brand-500 px-4 py-3 text-sm font-semibold text-white"
                          : "rounded-2xl px-4 py-3 text-sm text-slate-600 transition hover:bg-slate-100 hover:text-slate-950"
                      }
                    >
                      {t(route.navKey)}
                    </NavLink>
                  ))}
                </div>
              </div>
            ) : null}
          </nav>

          <div className="panel-muted mt-4 p-4">
            <div className="field-label">{t("pages.systemStatusTitle")}</div>
            <div className="mt-3 flex items-center gap-2 text-sm">
              <span className={`h-2.5 w-2.5 rounded-full ${runtimeHealthy ? "bg-emerald-500" : "bg-amber-500"}`} />
              <span className="font-medium text-slate-800">
                {runtimeHealthLoading
                  ? t("shell.runtimeLoading")
                  : runtimeHealthy
                    ? t("shell.runtimeHealthy")
                    : t("shell.runtimeWarning")}
              </span>
            </div>
          </div>
        </aside>

        <div className="flex min-h-0 flex-col gap-4">
          <header className="panel px-5 py-4 md:px-6">
            <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
              <div>
                <div className="field-label">{t("common.appName")}</div>
                <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950 md:text-3xl">
                  {t(currentRoute.titleKey)}
                </h1>
                <p className="mt-2 max-w-3xl text-sm leading-7 text-slate-600 md:text-base">
                  {t(currentRoute.descriptionKey)}
                </p>
              </div>

              <div className="grid gap-3 md:min-w-[340px]">
                <div className="flex flex-wrap items-center justify-end gap-2">
                  <div className="flex rounded-2xl bg-slate-100 p-1">
                    {(["zh-CN", "en-US"] as const).map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => setLocale(item)}
                        className={
                          locale === item
                            ? "rounded-xl bg-white px-3 py-2 text-sm font-semibold text-slate-950 shadow-sm"
                            : "rounded-xl px-3 py-2 text-sm text-slate-500"
                        }
                      >
                        {item === "zh-CN" ? "中文" : "English"}
                      </button>
                    ))}
                  </div>

                  <div className="flex rounded-2xl bg-slate-100 p-1">
                    {(["user", "developer"] as const).map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => void handleViewModeChange(item)}
                        className={
                          viewMode === item
                            ? "rounded-xl bg-slate-950 px-3 py-2 text-sm font-semibold text-white"
                            : "rounded-xl px-3 py-2 text-sm text-slate-500"
                        }
                      >
                        {item === "user" ? t("shell.userMode") : t("shell.developerMode")}
                      </button>
                    ))}
                  </div>

                  {!hideNewQueryButton ? (
                    <button type="button" className="primary-button !px-4 !py-2.5" onClick={() => navigate("/query")}>
                      {t("shell.newQuery")}
                    </button>
                  ) : null}

                  {developerUnlocked ? (
                    <button type="button" className="secondary-button !px-4 !py-2.5" onClick={() => void lockDeveloperMode()}>
                      {t("shell.lockDeveloper")}
                    </button>
                  ) : null}
                </div>

                <div className="flex justify-end">
                  <span
                    className={`chip ${
                      runtimeHealthy ? "chip-success" : "chip-warning"
                    }`}
                  >
                    {runtimeHealthLoading
                      ? t("shell.runtimeLoading")
                      : runtimeHealthy
                        ? t("shell.runtimeHealthy")
                        : t("shell.runtimeWarning")}
                  </span>
                </div>
              </div>
            </div>

            {notice ? (
              <div className="mt-4 flex items-start justify-between gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                <span>{notice.message}</span>
                <button type="button" className="text-amber-700 underline-offset-2 hover:underline" onClick={dismissNotice}>
                  {t("common.close")}
                </button>
              </div>
            ) : null}

            {showDevUnlock ? (
              <div className="mt-4 rounded-3xl border border-slate-200 bg-slate-50 p-4">
                <div className="section-title">{t("shell.devUnlockTitle")}</div>
                <div className="muted-copy mt-2">{t("shell.devUnlockDescription")}</div>
                <div className="mt-4 flex flex-col gap-3 md:flex-row">
                  <input
                    className="input md:flex-1"
                    type="password"
                    value={pinInput}
                    onChange={(event) => setPinInput(event.target.value)}
                    placeholder={t("shell.devUnlockPlaceholder")}
                  />
                  <button type="button" className="primary-button" onClick={() => void handleUnlockSubmit()}>
                    {t("shell.devUnlockAction")}
                  </button>
                  <button type="button" className="secondary-button" onClick={() => setShowDevUnlock(false)}>
                    {t("common.cancel")}
                  </button>
                </div>
              </div>
            ) : null}
          </header>

          <main className="min-h-0">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
