import { render, screen, waitFor } from "@testing-library/react";

const sessionMock = vi.hoisted(() => ({
  state: {
    developerSession: { required: true, unlocked: false },
    developerSessionLoading: false,
    viewMode: "user",
    setNotice: vi.fn(),
  },
}));

vi.mock("../app/state/WeatherWearSession", () => ({
  useWeatherWearSession: () => sessionMock.state,
}));

vi.mock("../app/layout/AppFrame", async () => {
  const { Outlet } = await import("react-router-dom");
  return {
    default: function MockAppFrame() {
      return <Outlet />;
    },
  };
});

vi.mock("../app/pages/DashboardPage", () => ({ default: () => <div>dashboard-page</div> }));
vi.mock("../app/pages/FavoritesPage", () => ({ default: () => <div>favorites-page</div> }));
vi.mock("../app/pages/HistoryPage", () => ({ default: () => <div>history-page</div> }));
vi.mock("../app/pages/LogsPage", () => ({ default: () => <div>logs-page</div> }));
vi.mock("../app/pages/MapConfigPage", () => ({ default: () => <div>map-config-page</div> }));
vi.mock("../app/pages/ModelConfigPage", () => ({ default: () => <div>model-config-page</div> }));
vi.mock("../app/pages/PlaygroundPage", () => ({ default: () => <div>playground-page</div> }));
vi.mock("../app/pages/PreferencesPage", () => ({ default: () => <div>preferences-page</div> }));
vi.mock("../app/pages/QueryPage", () => ({ default: () => <div>query-page</div> }));
vi.mock("../app/pages/SystemStatusPage", () => ({ default: () => <div>system-status-page</div> }));
vi.mock("../app/pages/TracePage", () => ({ default: () => <div>trace-page</div> }));

import AppRouter from "../app/AppRouter";

describe("AppRouter", () => {
  beforeEach(() => {
    sessionMock.state.developerSession = { required: true, unlocked: false };
    sessionMock.state.developerSessionLoading = false;
    sessionMock.state.viewMode = "user";
    sessionMock.state.setNotice = vi.fn();
    window.history.replaceState({}, "", "/");
  });

  it("redirects the root route to the query page", async () => {
    render(<AppRouter />);

    expect(await screen.findByText("query-page")).toBeInTheDocument();
    await waitFor(() => expect(window.location.pathname).toBe("/query"));
  });

  it("redirects locked developer routes back to the query page", async () => {
    sessionMock.state.viewMode = "developer";
    window.history.replaceState({}, "", "/dev/logs");

    render(<AppRouter />);

    expect(await screen.findByText("query-page")).toBeInTheDocument();
    await waitFor(() => expect(window.location.pathname).toBe("/query"));
    expect(sessionMock.state.setNotice).toHaveBeenCalled();
  });

  it("allows unlocked developer routes to render", async () => {
    sessionMock.state.viewMode = "developer";
    sessionMock.state.developerSession = { required: true, unlocked: true };
    window.history.replaceState({}, "", "/dev/logs");

    render(<AppRouter />);

    expect(await screen.findByText("logs-page")).toBeInTheDocument();
    await waitFor(() => expect(window.location.pathname).toBe("/dev/logs"));
  });
});
