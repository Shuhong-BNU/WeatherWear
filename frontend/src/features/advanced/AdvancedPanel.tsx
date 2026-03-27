import { useTranslation } from "react-i18next";
import type { AdvancedTab, MapRuntimeDiagnostics, ResultViewModel, ViewMode } from "../../shared/types";
import DebugPanel from "./DebugPanel";
import TimelinePanel from "./TimelinePanel";

interface AdvancedPanelProps {
  resultVm: ResultViewModel | null;
  viewMode: ViewMode;
  isOpen: boolean;
  activeTab: AdvancedTab;
  health: Record<string, unknown> | undefined;
  healthLoading: boolean;
  mapRuntimeDiagnostics: MapRuntimeDiagnostics;
  onToggleOpen: () => void;
  onTabChange: (tab: AdvancedTab) => void;
  forceExpanded?: boolean;
}

export default function AdvancedPanel(props: AdvancedPanelProps) {
  const { t } = useTranslation();
  const {
    resultVm,
    viewMode,
    isOpen,
    activeTab,
    health,
    healthLoading,
    mapRuntimeDiagnostics,
    onToggleOpen,
    onTabChange,
    forceExpanded = false,
  } = props;

  const tabs: Array<{ key: AdvancedTab; label: string }> = [
    { key: "location", label: t("advanced.locationTab") },
    { key: "timeline", label: t("advanced.timelineTab") },
    { key: "debug", label: t("advanced.debugTab") },
  ];
  const expanded = forceExpanded || isOpen;

  return (
    <section className="panel p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="section-title">{t("advanced.title")}</div>
          <div className="muted-copy mt-2">
            {viewMode === "developer" ? t("advanced.developerDescription") : t("advanced.userDescription")}
          </div>
        </div>
        {!forceExpanded ? (
          <button type="button" className="secondary-button" onClick={onToggleOpen}>
            {isOpen ? t("advanced.collapse") : t("advanced.expand")}
          </button>
        ) : null}
      </div>

      {expanded ? (
        <>
          <div className="mt-5 flex flex-wrap gap-2 rounded-2xl bg-slate-100 p-1">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                type="button"
                className={
                  activeTab === tab.key
                    ? "rounded-xl bg-white px-4 py-2 text-sm font-semibold text-slate-900 shadow-sm"
                    : "rounded-xl px-4 py-2 text-sm text-slate-500 hover:bg-white/70"
                }
                onClick={() => onTabChange(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="mt-5">
            {activeTab === "location" ? (
              <div className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <div className="field-label">{t("advanced.currentLocation")}</div>
                  <div className="mt-2 text-lg font-semibold text-slate-900">
                    {resultVm?.summary.confirmed_location_label || resultVm?.summary.selected_city || t("common.noData")}
                  </div>
                  <div className="mt-3 text-sm leading-7 text-slate-600">
                    {t("advanced.resolutionStatus")}：{resultVm?.summary.resolution_status || "idle"}
                    <br />
                    {t("advanced.locationSource")}：{resultVm?.summary.location_source_label || t("common.noData")}
                    <br />
                    {t("advanced.confidence")}：{resultVm?.summary.resolution_confidence?.toFixed?.(2) || "0.00"}
                  </div>
                  {resultVm?.location_pin?.lat != null && resultVm.location_pin.lon != null ? (
                    <div className="mt-4 text-sm text-slate-600">
                      {t("advanced.coords")}：{resultVm.location_pin.lat}, {resultVm.location_pin.lon}
                    </div>
                  ) : null}
                </div>

                <div className="grid gap-3">
                  {(resultVm?.clarification.options || []).length ? (
                    resultVm?.clarification.options.map((option) => (
                      <div key={option.candidate_id} className="rounded-2xl border border-slate-200 bg-white p-4">
                        <div className="flex items-center justify-between gap-3">
                          <div className="text-sm font-semibold text-slate-900">{option.label}</div>
                          {option.recommended ? <span className="chip chip-success">{t("advanced.recommended")}</span> : null}
                        </div>
                        <div className="mt-2 text-xs text-slate-500">
                          {t("advanced.confidence")} {option.confidence.toFixed(2)} · {option.source}
                        </div>
                        <div className="mt-3 text-sm leading-7 text-slate-700">{option.reason}</div>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-slate-500">{t("advanced.noCandidates")}</div>
                  )}
                </div>
              </div>
            ) : null}

            {activeTab === "timeline" ? <TimelinePanel steps={resultVm?.timeline_steps || []} /> : null}
            {activeTab === "debug" ? (
              <DebugPanel
                resultVm={resultVm}
                health={health}
                isLoading={healthLoading}
                mapRuntimeDiagnostics={mapRuntimeDiagnostics}
              />
            ) : null}
          </div>
        </>
      ) : null}
    </section>
  );
}
