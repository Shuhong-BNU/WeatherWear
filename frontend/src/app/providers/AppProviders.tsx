import type { PropsWithChildren } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import i18n from "../../i18n";
import BrowserRuntimeLogger from "./BrowserRuntimeLogger";
import { WeatherWearSessionProvider } from "../state/WeatherWearSession";

const queryClient = new QueryClient();

export default function AppProviders(props: PropsWithChildren) {
  return (
    <I18nextProvider i18n={i18n}>
      <QueryClientProvider client={queryClient}>
        <WeatherWearSessionProvider>
          <BrowserRuntimeLogger />
          {props.children}
        </WeatherWearSessionProvider>
      </QueryClientProvider>
    </I18nextProvider>
  );
}
