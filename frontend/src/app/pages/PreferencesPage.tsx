import { useTranslation } from "react-i18next";
import { useWeatherWearSession } from "../state/WeatherWearSession";
import type { ConfirmationMode, LocaleCode, ViewMode } from "../../shared/types";

function ToggleGroup<T extends string>(props: {
  value: T;
  options: Array<{ value: T; label: string }>;
  onChange: (value: T) => void;
}) {
  return (
    <div className="flex rounded-2xl bg-slate-100 p-1">
      {props.options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={
            props.value === option.value
              ? "rounded-xl bg-white px-4 py-2 text-sm font-semibold text-slate-950 shadow-sm"
              : "rounded-xl px-4 py-2 text-sm text-slate-500"
          }
          onClick={() => props.onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export default function PreferencesPage() {
  const { t } = useTranslation();
  const {
    locale,
    setLocale,
    confirmationMode,
    setConfirmationMode,
    viewMode,
    setViewMode,
  } = useWeatherWearSession();

  return (
    <div className="grid gap-5 lg:grid-cols-3">
      <section className="panel p-6">
        <div className="section-title">{t("preferences.localeTitle")}</div>
        <div className="muted-copy mt-2">{t("preferences.localeDescription")}</div>
        <div className="mt-4">
          <ToggleGroup<LocaleCode>
            value={locale}
            options={[
              { value: "zh-CN", label: "中文" },
              { value: "en-US", label: "English" },
            ]}
            onChange={setLocale}
          />
        </div>
      </section>

      <section className="panel p-6">
        <div className="section-title">{t("preferences.confirmationTitle")}</div>
        <div className="muted-copy mt-2">{t("preferences.confirmationDescription")}</div>
        <div className="mt-4">
          <ToggleGroup<ConfirmationMode>
            value={confirmationMode}
            options={[
              { value: "smart", label: t("mode.smartTitle") },
              { value: "strict", label: t("mode.strictTitle") },
            ]}
            onChange={setConfirmationMode}
          />
        </div>
      </section>

      <section className="panel p-6">
        <div className="section-title">{t("preferences.viewModeTitle")}</div>
        <div className="muted-copy mt-2">{t("preferences.viewModeDescription")}</div>
        <div className="mt-4">
          <ToggleGroup<ViewMode>
            value={viewMode}
            options={[
              { value: "user", label: t("shell.userMode") },
              { value: "developer", label: t("shell.developerMode") },
            ]}
            onChange={setViewMode}
          />
        </div>
      </section>
    </div>
  );
}
