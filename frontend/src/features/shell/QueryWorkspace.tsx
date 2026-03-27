import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import AdvancedPanel from "../advanced/AdvancedPanel";
import QueryPanel from "../query/QueryPanel";
import AdviceSectionsCard from "../results/AdviceSectionsCard";
import KnowledgeBasisCard from "../results/KnowledgeBasisCard";
import MetricGrid from "../results/MetricGrid";
import ReasonListCard from "../results/ReasonListCard";
import ResultSummaryCard from "../results/ResultSummaryCard";
import { useWeatherWearSession } from "../../app/state/WeatherWearSession";
import type { ViewMode } from "../../shared/types";

interface QueryWorkspaceProps {
  mode: ViewMode;
  showAdvanced?: boolean;
}

export default function QueryWorkspace(props: QueryWorkspaceProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const {
    queryText,
    setQueryText,
    gender,
    setGender,
    occasionText,
    setOccasionText,
    targetDate,
    setTargetDate,
    confirmationMode,
    setConfirmationMode,
    draftCoords,
    setDraftCoords,
    resultVm,
    selectedCandidateId,
    setSelectedCandidateId,
    showAllCandidates,
    setShowAllCandidates,
    examples,
    recentQueries,
    runtimeHealth,
    runtimeHealthLoading,
    queryError,
    isPending,
    progressState,
    activeAdvancedTab,
    setActiveAdvancedTab,
    clearWorkspace,
    pauseActiveQuery,
    submitTextQuery,
    submitMapQuery,
    confirmCandidate,
    rerunStrictSelection,
    runRecentQuery,
    saveCurrentFavorite,
    isCurrentFavorite,
    mapRuntimeDiagnostics,
  } = useWeatherWearSession();

  const detailItems =
    props.mode === "developer"
      ? [
          [t("query.weatherSummaryFinalLocation"), resultVm?.summary.confirmed_location_label || resultVm?.summary.selected_city || t("common.noData")],
          [t("query.weatherSummaryTargetDate"), resultVm?.summary.query_context.target_date || t("common.noData")],
          [t("query.weatherSummaryWeatherTime"), resultVm?.weather.observed_at_local || t("common.noData")],
          [t("query.weatherSummaryLocalTime"), resultVm?.weather.city_local_time || t("common.noData")],
          [t("query.weatherSummarySource"), resultVm?.weather.source || t("common.noData")],
          [t("query.weatherSummaryPath"), resultVm?.hero_summary.query_path || t("common.noData")],
        ]
      : [
          [t("query.weatherSummaryFinalLocation"), resultVm?.summary.confirmed_location_label || resultVm?.summary.selected_city || t("common.noData")],
          [t("query.weatherSummaryTargetDate"), resultVm?.summary.query_context.target_date || t("common.noData")],
          [t("query.weatherSummaryWeatherTime"), resultVm?.weather.observed_at_local || t("common.noData")],
          [t("query.weatherSummaryLocalTime"), resultVm?.weather.city_local_time || t("common.noData")],
        ];

  const handleSubmit = useCallback(() => {
    if (queryText.trim()) {
      submitTextQuery();
      return;
    }
    submitMapQuery();
  }, [queryText, submitMapQuery, submitTextQuery]);

  const handleMapSelect = useCallback(
    (coords: { lat: number; lon: number }) => {
      setDraftCoords(coords);
    },
    [setDraftCoords],
  );

  const handleClearMapCoords = useCallback(() => {
    setDraftCoords(null);
  }, [setDraftCoords]);

  const handleUseMapCoords = useCallback(() => {
    submitMapQuery();
  }, [submitMapQuery]);

  const handleToggleShowAllCandidates = useCallback(() => {
    setShowAllCandidates(!showAllCandidates);
  }, [setShowAllCandidates, showAllCandidates]);

  const sidebar = (
    <QueryPanel
      queryText={queryText}
      gender={gender}
      occasionText={occasionText}
      targetDate={targetDate}
      confirmationMode={confirmationMode}
      progressState={progressState}
      draftCoords={draftCoords}
      locationPin={resultVm?.location_pin || null}
      searchLocationLabel={
        resultVm?.summary.confirmed_location_label ||
        (resultVm?.summary.resolution_status === "resolved" ? resultVm.summary.selected_city : "") ||
        queryText.trim()
      }
      resultVm={resultVm}
      examples={examples}
      recentQueries={recentQueries}
      selectedCandidateId={selectedCandidateId}
      showAllCandidates={showAllCandidates}
      isPending={isPending}
      onQueryTextChange={setQueryText}
      onGenderChange={setGender}
      onOccasionTextChange={setOccasionText}
      onTargetDateChange={setTargetDate}
      onConfirmationModeChange={setConfirmationMode}
      onSubmit={handleSubmit}
      onPause={pauseActiveQuery}
      onClear={clearWorkspace}
      onSelectMapCoords={handleMapSelect}
      onClearMapCoords={handleClearMapCoords}
      onUseMapCoords={handleUseMapCoords}
      onPickQuickQuery={(query, run) => {
        setQueryText(query);
        if (run) {
          runRecentQuery(query);
        }
      }}
      onSelectCandidate={setSelectedCandidateId}
      onConfirmCandidate={confirmCandidate}
      onToggleShowAllCandidates={handleToggleShowAllCandidates}
      onReselectLocation={rerunStrictSelection}
    />
  );

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(320px,0.39fr)_minmax(0,0.61fr)]">
      <aside className="flex flex-col gap-5">{sidebar}</aside>

      <section className="flex flex-col gap-5">
        {queryError ? (
          <section className="panel border-rose-200 bg-rose-50 p-5 text-sm leading-7 text-rose-700">
            <div className="field-label text-rose-500">{t("query.requestFailed")}</div>
            <div className="mt-2">{queryError.message}</div>
          </section>
        ) : null}

        <ResultSummaryCard resultVm={resultVm} viewMode={props.mode} />
        <MetricGrid metrics={resultVm?.weather_metrics || []} />

        {props.mode === "developer" ? (
          <div className="grid gap-5 xl:grid-cols-2">
            <ReasonListCard reasons={resultVm?.decision_factors || resultVm?.explanation_reasons || []} />
            <KnowledgeBasisCard knowledge={resultVm?.knowledge_basis || { status: "no_match", summary: "", items: [] }} />
          </div>
        ) : null}

        <AdviceSectionsCard sections={resultVm?.fashion_sections || []} />

        <section className="panel p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <div className="section-title">{t("query.weatherSummaryTitle")}</div>
              <div className="muted-copy mt-2">{t("query.weatherSummaryDescription")}</div>
            </div>

            {resultVm ? (
              <div className="flex flex-wrap gap-2">
                <button type="button" className="secondary-button !px-4 !py-2.5" onClick={saveCurrentFavorite}>
                  {isCurrentFavorite ? t("query.removeFavoriteCurrent") : t("query.favoriteCurrent")}
                </button>
                {props.mode === "developer" ? (
                  <>
                    <button
                      type="button"
                      className="secondary-button !px-4 !py-2.5"
                      onClick={() => navigate("/dev/trace")}
                    >
                      {t("query.openTrace")}
                    </button>
                    <button
                      type="button"
                      className="secondary-button !px-4 !py-2.5"
                      onClick={() => navigate("/dev/playground")}
                    >
                      {t("query.openPlayground")}
                    </button>
                  </>
                ) : null}
              </div>
            ) : null}
          </div>

          <div className={`mt-4 grid gap-4 ${detailItems.length > 2 ? "sm:grid-cols-2" : "md:grid-cols-2"}`}>
            {detailItems.map(([label, value]) => (
              <div key={label} className="panel-muted p-4">
                <div className="field-label">{label}</div>
                <div className="mt-2 text-sm leading-7 text-slate-700">{value}</div>
              </div>
            ))}
            {props.mode === "developer" ? (
              <div className="panel-muted p-4">
                <div className="field-label">{t("map.diagnostics.title")}</div>
                <div className="mt-2 text-sm leading-7 text-slate-700">
                  {mapRuntimeDiagnostics.provider} · {mapRuntimeDiagnostics.errorMessage || t("common.none")}
                </div>
              </div>
            ) : null}
          </div>
        </section>

        {props.showAdvanced ? (
          <AdvancedPanel
            resultVm={resultVm}
            viewMode={props.mode}
            isOpen
            activeTab={activeAdvancedTab}
            health={runtimeHealth}
            healthLoading={runtimeHealthLoading}
            mapRuntimeDiagnostics={mapRuntimeDiagnostics}
            onToggleOpen={() => undefined}
            onTabChange={setActiveAdvancedTab}
            forceExpanded
          />
        ) : null}
      </section>
    </div>
  );
}
