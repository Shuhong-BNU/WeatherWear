import { useTranslation } from "react-i18next";
import type { TimelineStep } from "../../shared/types";

interface TimelinePanelProps {
  steps: TimelineStep[];
}

export default function TimelinePanel(props: TimelinePanelProps) {
  const { t } = useTranslation();

  if (!props.steps.length) {
    return <div className="text-sm text-slate-500">{t("timeline.empty")}</div>;
  }

  return (
    <div className="grid gap-3">
      {props.steps.map((step) => {
        const ok = step.status === "success";
        return (
          <details key={`${step.id}-${step.title}`} className="rounded-2xl border border-slate-200 bg-white p-4">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <span className={`h-3 w-3 rounded-full ${ok ? "bg-emerald-500" : "bg-rose-500"}`} />
                <div>
                  <div className="text-sm font-semibold text-slate-900">{step.title}</div>
                  <div className="mt-1 text-xs text-slate-500">{step.role}</div>
                </div>
              </div>
              <div className="flex flex-wrap gap-2 text-xs">
                <span className="chip chip-info">{step.elapsed_ms}ms</span>
                <span className="chip chip-info">Σ {step.cumulative_ms}ms</span>
                {step.used_llm ? (
                  <span className="chip chip-warning">{t("timeline.llm")}</span>
                ) : (
                  <span className="chip chip-info">{t("timeline.rules")}</span>
                )}
                {step.fallback_used ? <span className="chip chip-warning">{t("timeline.fallback")}</span> : null}
              </div>
            </summary>

            <div className="mt-4 grid gap-3 border-t border-slate-200 pt-4 text-sm text-slate-700">
              <div><span className="field-label">{t("timeline.provider")}</span><div className="mt-1">{step.provider || t("common.none")}</div></div>
              <div><span className="field-label">Step kind</span><div className="mt-1">{step.step_kind || t("common.none")}</div></div>
              <div><span className="field-label">{t("timeline.model")}</span><div className="mt-1">{step.model || t("common.none")}</div></div>
              <div><span className="field-label">{t("timeline.decision")}</span><div className="mt-1">{step.decision_reason || t("common.none")}</div></div>
              <div><span className="field-label">{t("timeline.input")}</span><div className="mt-1 whitespace-pre-wrap">{step.input_summary || t("common.none")}</div></div>
              <div><span className="field-label">{t("timeline.output")}</span><div className="mt-1 whitespace-pre-wrap">{step.output_summary || t("common.none")}</div></div>
              {Object.keys(step.metadata || {}).length ? (
                <div>
                  <span className="field-label">{t("timeline.metadata")}</span>
                  <pre className="mt-1 overflow-x-auto rounded-2xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">
                    {JSON.stringify(step.metadata, null, 2)}
                  </pre>
                </div>
              ) : null}
              {step.error ? (
                <div><span className="field-label">{t("timeline.error")}</span><div className="mt-1 whitespace-pre-wrap text-rose-600">{step.error}</div></div>
              ) : null}
            </div>
          </details>
        );
      })}
    </div>
  );
}
