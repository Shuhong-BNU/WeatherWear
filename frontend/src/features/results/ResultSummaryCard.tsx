import { useTranslation } from "react-i18next";
import type { ResultViewModel, ViewMode } from "../../shared/types";

interface ResultSummaryCardProps {
  resultVm: ResultViewModel | null;
  viewMode: ViewMode;
}

export default function ResultSummaryCard(props: ResultSummaryCardProps) {
  const { t } = useTranslation();
  const { resultVm, viewMode } = props;
  const hero = resultVm?.hero_summary;
  const weather = resultVm?.weather;
  const queryContext = resultVm?.summary.query_context;
  const headline = resultVm?.fashion.headline_advice || hero?.one_line_advice;
  const badges = resultVm?.badges || [];
  const adviceLabel = hero?.advice_label || t("hero.todayAdvice");

  return (
    <section className="hero-panel p-6 md:p-7">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div className="max-w-3xl">
          <div className="field-label !text-white/70">{t("hero.eyebrow")}</div>
          <div className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-4xl">
            {hero ? `${hero.condition_emoji} ${hero.title}` : t("hero.waitingTitle")}
          </div>
          <div className="mt-3 text-base text-white/85">{hero?.condition || t("hero.waitingCondition")}</div>
          <div className="mt-5 rounded-2xl bg-white/12 p-4 text-sm leading-8 text-white/95 md:text-base">
            <div className="text-xs uppercase tracking-[0.2em] text-white/70">{adviceLabel}</div>
            <div className="mt-2">{headline || t("hero.adviceFallback")}</div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2 text-xs text-white/80">
            {weather?.daily_range_text ? (
              <span className="hero-chip">{t("hero.rangeChip", { value: weather.daily_range_text })}</span>
            ) : null}
            {weather?.observed_at_local ? (
              <span className="hero-chip">{t("hero.weatherTimeChip", { value: weather.observed_at_local })}</span>
            ) : null}
            {weather?.city_local_time ? (
              <span className="hero-chip">{t("hero.timeChip", { value: weather.city_local_time })}</span>
            ) : null}
            {weather?.data_mode === "demo" ? <span className="hero-chip">{t("hero.demoWeatherChip")}</span> : null}
            {resultVm?.summary.confirmed_location_label ? (
              <span className="hero-chip">
                {t("hero.locationChip", { value: resultVm.summary.confirmed_location_label })}
              </span>
            ) : null}
            {queryContext?.target_date ? (
              <span className="hero-chip">{t("hero.targetDateChip", { value: queryContext.target_date })}</span>
            ) : null}
            {queryContext?.occasion_text ? (
              <span className="hero-chip">{t("hero.occasionChip", { value: queryContext.occasion_text })}</span>
            ) : null}
          </div>
        </div>

        {viewMode === "developer" ? (
          <div className="grid min-w-[260px] gap-2 rounded-3xl bg-white/10 p-4 backdrop-blur">
            {badges.map((badge) => (
              <div key={`${badge.key}-${badge.value}`} className="flex items-center justify-between gap-3 text-sm text-white/90">
                <span className="text-white/70">{badge.label}</span>
                <span className="font-medium">{badge.value}</span>
              </div>
            ))}
            <div className="flex items-center justify-between gap-3 text-sm text-white/90">
              <span className="text-white/70">{t("hero.modelLabel")}</span>
              <span className="font-medium">
                {resultVm?.summary.models_used.length ? resultVm.summary.models_used.join(" / ") : t("hero.noModel")}
              </span>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
