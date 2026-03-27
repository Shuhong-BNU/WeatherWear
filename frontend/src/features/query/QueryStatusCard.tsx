import { useTranslation } from "react-i18next";
import type { QueryProgressState } from "../../shared/types";

interface QueryStatusCardProps {
  progressState: QueryProgressState;
}

function toneClasses(tone: QueryProgressState["tone"]) {
  if (tone === "success") return "bg-emerald-50 text-emerald-700";
  if (tone === "warning") return "bg-amber-50 text-amber-700";
  if (tone === "paused") return "bg-slate-100 text-slate-700";
  if (tone === "error") return "bg-rose-50 text-rose-700";
  if (tone === "running") return "bg-blue-50 text-blue-700";
  return "bg-slate-100 text-slate-600";
}

export default function QueryStatusCard(props: QueryStatusCardProps) {
  const { t } = useTranslation();
  const { progressState } = props;

  if (!progressState.visible) {
    return (
      <section className="panel-muted p-4">
        <div className="field-label">{t("status.title")}</div>
        <div className="mt-2 text-sm leading-7 text-slate-600">{t("status.idleHint")}</div>
      </section>
    );
  }

  return (
    <section className="panel-muted p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="field-label">{t("status.title")}</div>
          <div className="mt-2 text-base font-semibold text-slate-900">{progressState.title}</div>
          <div className="mt-1 text-sm leading-7 text-slate-600">{progressState.detail}</div>
        </div>
        <span className={`rounded-full px-3 py-1 text-xs font-semibold ${toneClasses(progressState.tone)}`}>
          {progressState.elapsedSeconds.toFixed(1)}s
        </span>
      </div>

      <div className="mt-4">
        <div className="status-track">
          <div className="status-fill" style={{ width: `${progressState.progress}%` }} />
        </div>
      </div>

      <div className="mt-4 grid gap-2">
        {progressState.steps.map((step, index) => (
          <div key={`${step.label}-${index}`} className="flex items-center gap-3 text-sm">
            <span
              className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${
                step.state === "complete"
                  ? "bg-emerald-500 text-white"
                  : step.state === "current"
                    ? "bg-brand-500 text-white"
                    : "bg-slate-200 text-slate-500"
              }`}
            >
              {index + 1}
            </span>
            <span
              className={
                step.state === "upcoming"
                  ? "text-slate-500"
                  : step.state === "current"
                    ? "font-semibold text-slate-900"
                    : "text-slate-700"
              }
            >
              {step.label}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}
