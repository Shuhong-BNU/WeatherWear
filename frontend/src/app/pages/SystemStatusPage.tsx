import { useTranslation } from "react-i18next";
import { useWeatherWearSession } from "../state/WeatherWearSession";
import type { RuntimeModuleStatus } from "../../shared/types";

export default function SystemStatusPage() {
  const { t } = useTranslation();
  const { runtimeHealth, runtimeHealthLoading } = useWeatherWearSession();
  const modules = Object.entries((runtimeHealth?.modules as Record<string, RuntimeModuleStatus>) || {});
  const issues = ((runtimeHealth?.web_stack as { issues?: string[] } | undefined)?.issues || []) as string[];
  const suggestions = (runtimeHealth?.suggestions || []) as string[];

  return (
    <div className="grid gap-5">
      <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        <div className="panel p-5">
          <div className="field-label">{t("systemStatus.llmConfigured")}</div>
          <div className="mt-3 text-lg font-semibold text-slate-950">
            {runtimeHealthLoading
              ? t("common.loading")
              : runtimeHealth?.llm_configured
                ? t("common.configured")
                : t("common.notConfigured")}
          </div>
        </div>
        <div className="panel p-5">
          <div className="field-label">{t("systemStatus.openWeatherConfigured")}</div>
          <div className="mt-3 text-lg font-semibold text-slate-950">
            {runtimeHealthLoading
              ? t("common.loading")
              : runtimeHealth?.openweather_configured
                ? t("common.configured")
                : t("common.notConfigured")}
          </div>
        </div>
        <div className="panel p-5">
          <div className="field-label">Provider</div>
          <div className="mt-3 text-lg font-semibold text-slate-950">{String(runtimeHealth?.llm_provider || t("common.noData"))}</div>
        </div>
        <div className="panel p-5">
          <div className="field-label">Model</div>
          <div className="mt-3 text-lg font-semibold text-slate-950">{String(runtimeHealth?.llm_model || t("common.noData"))}</div>
        </div>
      </section>

      <section className="panel p-6">
        <div className="section-title">{t("systemStatus.modulesTitle")}</div>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {modules.map(([name, status]) => (
            <div key={name} className="panel-muted p-4">
              <div className="text-sm font-semibold text-slate-900">{name}</div>
              <div className="mt-2 text-sm text-slate-600">
                {status.available ? t("common.enabled") : t("common.disabled")}
              </div>
              <div className="mt-2 text-sm text-slate-500">{status.version || t("common.noData")}</div>
              {status.error ? <div className="mt-2 text-sm text-rose-600">{status.error}</div> : null}
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <div className="panel p-6">
          <div className="section-title">{t("systemStatus.issuesTitle")}</div>
          <div className="mt-4 grid gap-3">
            {issues.length ? (
              issues.map((item) => (
                <div key={item} className="panel-muted px-4 py-3 text-sm leading-7 text-slate-700">
                  {item}
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-500">{t("common.noData")}</div>
            )}
          </div>
        </div>

        <div className="panel p-6">
          <div className="section-title">{t("systemStatus.suggestionsTitle")}</div>
          <div className="mt-4 grid gap-3">
            {suggestions.length ? (
              suggestions.map((item) => (
                <div key={item} className="panel-muted px-4 py-3 text-sm leading-7 text-slate-700">
                  {item}
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-500">{t("common.noData")}</div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
