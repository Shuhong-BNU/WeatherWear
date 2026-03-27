import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useWeatherWearSession } from "../state/WeatherWearSession";

export default function DashboardPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { resultVm, runtimeHealth, runtimeHealthLoading } = useWeatherWearSession();

  return (
    <div className="grid gap-5">
      <section className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="hero-panel p-6 md:p-7">
          <div className="field-label !text-white/70">{t("dashboard.lastResult")}</div>
          {resultVm ? (
            <>
              <div className="mt-4 text-3xl font-semibold tracking-tight text-white md:text-4xl">
                {resultVm.hero_summary.condition_emoji} {resultVm.hero_summary.title}
              </div>
              <div className="mt-3 max-w-3xl text-base leading-8 text-white/85">
                {resultVm.fashion.headline_advice || resultVm.hero_summary.one_line_advice}
              </div>
              <div className="mt-5 flex flex-wrap gap-2">
                {resultVm.weather.temperature ? <span className="hero-chip">{resultVm.weather.temperature}</span> : null}
                {resultVm.weather.daily_range_text ? (
                  <span className="hero-chip">{resultVm.weather.daily_range_text}</span>
                ) : null}
                {resultVm.weather.city_local_time ? (
                  <span className="hero-chip">{resultVm.weather.city_local_time}</span>
                ) : null}
              </div>
            </>
          ) : (
            <div className="mt-4 text-sm leading-7 text-white/80">{t("dashboard.noResult")}</div>
          )}
        </div>

        <section className="panel p-6">
          <div className="section-title">{t("dashboard.quickActions")}</div>
          <div className="mt-4 grid gap-3">
            <button type="button" className="primary-button" onClick={() => navigate("/query")}>
              {t("shell.newQuery")}
            </button>
            <button type="button" className="secondary-button" onClick={() => navigate("/history")}>
              {t("dashboard.openHistory")}
            </button>
            <button type="button" className="secondary-button" onClick={() => navigate("/favorites")}>
              {t("dashboard.openFavorites")}
            </button>
            <button type="button" className="secondary-button" onClick={() => navigate("/dev/trace")}>
              {t("dashboard.openTrace")}
            </button>
          </div>
        </section>
      </section>

      <section className="grid gap-5 lg:grid-cols-3">
        <div className="panel p-6">
          <div className="field-label">{t("dashboard.summaryCardTitle")}</div>
          <div className="mt-3 text-lg font-semibold text-slate-950">
            {resultVm?.summary.confirmed_location_label || resultVm?.summary.selected_city || t("common.noData")}
          </div>
        </div>
        <div className="panel p-6">
          <div className="field-label">{resultVm?.hero_summary.advice_label || t("dashboard.summaryCardAdvice")}</div>
          <div className="mt-3 text-sm leading-7 text-slate-700">
            {resultVm?.hero_summary.one_line_advice || t("dashboard.noResult")}
          </div>
        </div>
        <div className="panel p-6">
          <div className="field-label">{t("dashboard.summaryCardPath")}</div>
          <div className="mt-3 text-lg font-semibold text-slate-950">
            {resultVm?.hero_summary.query_path || t("common.noData")}
          </div>
        </div>
      </section>

      <section className="panel p-6">
        <div className="section-title">{t("dashboard.runtimeCardTitle")}</div>
        <div className="muted-copy mt-2">{t("dashboard.runtimeCardHint")}</div>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="panel-muted p-4">
            <div className="field-label">{t("systemStatus.llmConfigured")}</div>
            <div className="mt-2 text-base font-semibold text-slate-900">
              {runtimeHealthLoading
                ? t("common.loading")
                : runtimeHealth?.llm_configured
                  ? t("common.configured")
                  : t("common.notConfigured")}
            </div>
          </div>
          <div className="panel-muted p-4">
            <div className="field-label">{t("systemStatus.openWeatherConfigured")}</div>
            <div className="mt-2 text-base font-semibold text-slate-900">
              {runtimeHealthLoading
                ? t("common.loading")
                : runtimeHealth?.openweather_configured
                  ? t("common.configured")
                  : t("common.notConfigured")}
            </div>
          </div>
          <div className="panel-muted p-4">
            <div className="field-label">Python</div>
            <div className="mt-2 text-base font-semibold text-slate-900">
              {String(runtimeHealth?.python_version || t("common.noData"))}
            </div>
          </div>
          <div className="panel-muted p-4">
            <div className="field-label">Platform</div>
            <div className="mt-2 text-base font-semibold text-slate-900">
              {String(runtimeHealth?.platform || t("common.noData"))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
