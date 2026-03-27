import { useTranslation } from "react-i18next";
import type { MapRuntimeDiagnostics, ResultViewModel } from "../../shared/types";

interface DebugPanelProps {
  resultVm: ResultViewModel | null;
  health: Record<string, unknown> | undefined;
  isLoading: boolean;
  mapRuntimeDiagnostics: MapRuntimeDiagnostics;
}

function JsonBlock(props: { value: unknown }) {
  return (
    <pre className="overflow-x-auto rounded-2xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">
      {JSON.stringify(props.value, null, 2)}
    </pre>
  );
}

export default function DebugPanel(props: DebugPanelProps) {
  const { t, i18n } = useTranslation();
  const { resultVm, health, isLoading, mapRuntimeDiagnostics } = props;
  const runtimeSummary = (resultVm?.debug_sections?.runtime_summary as Record<string, unknown> | undefined) || {};
  const retrievalSummary = (resultVm?.debug_sections?.retrieval_summary as Record<string, unknown> | undefined) || {};
  const zh = i18n.language.startsWith("zh");
  const summaryRows: Array<[string, string]> = [
    [zh ? "最终解析状态" : "Resolution final", runtimeSummary.resolution_final_status ?? resultVm?.summary.resolution_final_status ?? resultVm?.summary.resolution_status ?? t("common.noData")],
    [zh ? "缓存解析状态" : "Cached resolution", runtimeSummary.cached_resolution_status ?? resultVm?.summary.cached_resolution_status ?? t("common.noData")],
    [zh ? "天气数据模式" : "Weather mode", runtimeSummary.weather_data_mode ?? resultVm?.weather?.data_mode ?? t("common.noData")],
    [zh ? "检索模式" : "Retrieval mode", runtimeSummary.retrieval_mode ?? resultVm?.summary.retrieval_mode ?? t("common.noData")],
    [zh ? "向量腿状态" : "Vector leg", runtimeSummary.vector_leg_status ?? resultVm?.summary.vector_leg_status ?? t("common.noData")],
    [zh ? "生成模式" : "Fashion generation", runtimeSummary.fashion_generation_mode ?? resultVm?.summary.fashion_generation_mode ?? t("common.noData")],
  ].map(([label, value]) => [String(label), String(value || t("common.noData"))]);

  return (
    <div className="grid gap-4">
      <section className="rounded-2xl border border-slate-200 bg-white p-4">
        <div className="text-sm font-semibold text-slate-900">{zh ? "当前阶段摘要" : "Current stage summary"}</div>
        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {summaryRows.map(([label, value]) => (
            <div key={String(label)} className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <div className="text-[11px] uppercase tracking-[0.2em] text-slate-400">{label}</div>
              <div className="mt-2 text-sm font-semibold text-slate-900">{String(value || t("common.noData"))}</div>
            </div>
          ))}
        </div>
        <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
          {zh ? "召回构成" : "Retrieval composition"}:
          {" "}
          {`${zh ? "规则" : "rules"}=${String(retrievalSummary.rule_hits ?? 0)}, ${zh ? "向量" : "vector"}=${String(
            retrievalSummary.vector_hits ?? 0,
          )}, ${zh ? "跳过原因" : "skip reason"}=${String(
            retrievalSummary.vector_leg_skipped_reason || runtimeSummary.vector_leg_skipped_reason || t("common.none"),
          )}`}
        </div>
      </section>

      <details className="rounded-2xl border border-slate-200 bg-white p-4" open>
        <summary className="cursor-pointer text-sm font-semibold text-slate-900">{t("debug.requestSummary")}</summary>
        <div className="mt-4">
          <JsonBlock value={resultVm?.summary || {}} />
        </div>
      </details>

      <details className="rounded-2xl border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer text-sm font-semibold text-slate-900">{t("debug.warnings")}</summary>
        <div className="mt-4">
          <JsonBlock value={resultVm?.warnings || []} />
        </div>
      </details>

      <details className="rounded-2xl border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer text-sm font-semibold text-slate-900">{t("debug.runtime")}</summary>
        <div className="mt-4">
          <JsonBlock value={health || { loading: isLoading }} />
        </div>
      </details>

      <details className="rounded-2xl border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer text-sm font-semibold text-slate-900">{t("debug.mapRuntime")}</summary>
        <div className="mt-4">
          <JsonBlock value={mapRuntimeDiagnostics} />
        </div>
      </details>

      <details className="rounded-2xl border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer text-sm font-semibold text-slate-900">{t("debug.knowledge")}</summary>
        <div className="mt-4">
          <JsonBlock value={((resultVm?.debug_sections?.knowledge as unknown[]) || [])} />
        </div>
      </details>

      <details className="rounded-2xl border border-slate-200 bg-white p-4">
        <summary className="cursor-pointer text-sm font-semibold text-slate-900">{t("debug.rawTrace")}</summary>
        <div className="mt-4">
          <JsonBlock value={resultVm?.trace || []} />
        </div>
      </details>
    </div>
  );
}
