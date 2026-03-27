export type AppNavGroup = "user" | "developer";

export interface AppRouteMeta {
  path: string;
  titleKey: string;
  descriptionKey: string;
  navKey: string;
  group: AppNavGroup;
  devOnly?: boolean;
}

export const APP_ROUTE_META: AppRouteMeta[] = [
  {
    path: "/dashboard",
    titleKey: "pages.dashboardTitle",
    descriptionKey: "pages.dashboardDescription",
    navKey: "nav.dashboard",
    group: "user",
  },
  {
    path: "/query",
    titleKey: "pages.queryTitle",
    descriptionKey: "pages.queryDescription",
    navKey: "nav.query",
    group: "user",
  },
  {
    path: "/history",
    titleKey: "pages.historyTitle",
    descriptionKey: "pages.historyDescription",
    navKey: "nav.history",
    group: "user",
  },
  {
    path: "/favorites",
    titleKey: "pages.favoritesTitle",
    descriptionKey: "pages.favoritesDescription",
    navKey: "nav.favorites",
    group: "user",
  },
  {
    path: "/preferences",
    titleKey: "pages.preferencesTitle",
    descriptionKey: "pages.preferencesDescription",
    navKey: "nav.preferences",
    group: "user",
  },
  {
    path: "/dev/playground",
    titleKey: "pages.playgroundTitle",
    descriptionKey: "pages.playgroundDescription",
    navKey: "nav.playground",
    group: "developer",
    devOnly: true,
  },
  {
    path: "/dev/trace",
    titleKey: "pages.traceTitle",
    descriptionKey: "pages.traceDescription",
    navKey: "nav.trace",
    group: "developer",
    devOnly: true,
  },
  {
    path: "/dev/model-config",
    titleKey: "pages.modelConfigTitle",
    descriptionKey: "pages.modelConfigDescription",
    navKey: "nav.modelConfig",
    group: "developer",
    devOnly: true,
  },
  {
    path: "/dev/map-config",
    titleKey: "pages.mapConfigTitle",
    descriptionKey: "pages.mapConfigDescription",
    navKey: "nav.mapConfig",
    group: "developer",
    devOnly: true,
  },
  {
    path: "/dev/system-status",
    titleKey: "pages.systemStatusTitle",
    descriptionKey: "pages.systemStatusDescription",
    navKey: "nav.systemStatus",
    group: "developer",
    devOnly: true,
  },
  {
    path: "/dev/logs",
    titleKey: "pages.logsTitle",
    descriptionKey: "pages.logsDescription",
    navKey: "nav.logs",
    group: "developer",
    devOnly: true,
  },
];
