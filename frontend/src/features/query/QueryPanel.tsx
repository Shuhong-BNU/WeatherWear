import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import type {
  ConfirmationMode,
  GenderMode,
  LocationPin,
  QueryCoords,
  QueryProgressState,
  ResultViewModel,
} from "../../shared/types";
import CandidateConfirmCard from "../candidates/CandidateConfirmCard";
import LocationMapCard from "../map/LocationMapCard";
import ModeToggle from "./ModeToggle";
import QueryStatusCard from "./QueryStatusCard";

interface QueryPanelProps {
  queryText: string;
  gender: GenderMode;
  occasionText: string;
  targetDate: string;
  confirmationMode: ConfirmationMode;
  progressState: QueryProgressState;
  draftCoords: QueryCoords | null;
  locationPin: LocationPin | null;
  searchLocationLabel: string;
  resultVm: ResultViewModel | null;
  examples: Array<{ label: string; query_text: string }>;
  recentQueries: string[];
  selectedCandidateId: string;
  showAllCandidates: boolean;
  isPending: boolean;
  onQueryTextChange: (value: string) => void;
  onGenderChange: (value: GenderMode) => void;
  onOccasionTextChange: (value: string) => void;
  onTargetDateChange: (value: string) => void;
  onConfirmationModeChange: (value: ConfirmationMode) => void;
  onSubmit: () => void;
  onPause: () => void;
  onClear: () => void;
  onSelectMapCoords: (coords: QueryCoords) => void;
  onClearMapCoords: () => void;
  onUseMapCoords: () => void;
  onPickQuickQuery: (query: string, run: boolean) => void;
  onSelectCandidate: (candidateId: string) => void;
  onConfirmCandidate: (candidateId?: string) => void;
  onToggleShowAllCandidates: () => void;
  onReselectLocation: () => void;
}

function toDateInputValue(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export default function QueryPanel(props: QueryPanelProps) {
  const { t } = useTranslation();
  const {
    queryText,
    gender,
    occasionText,
    targetDate,
    confirmationMode,
    progressState,
    draftCoords,
    locationPin,
    searchLocationLabel,
    resultVm,
    examples,
    recentQueries,
    selectedCandidateId,
    showAllCandidates,
    isPending,
    onQueryTextChange,
    onGenderChange,
    onOccasionTextChange,
    onTargetDateChange,
    onConfirmationModeChange,
    onSubmit,
    onPause,
    onClear,
    onSelectMapCoords,
    onClearMapCoords,
    onUseMapCoords,
    onPickQuickQuery,
    onSelectCandidate,
    onConfirmCandidate,
    onToggleShowAllCandidates,
    onReselectLocation,
  } = props;

  const canSubmit = Boolean(queryText.trim() || draftCoords);
  const genderOptions = useMemo(
    () => [
      { value: "male" as const, label: t("query.genderMale"), icon: "♂" },
      { value: "female" as const, label: t("query.genderFemale"), icon: "♀" },
      { value: "neutral" as const, label: t("query.genderNeutral"), icon: "◌" },
    ],
    [t],
  );
  const occasionExamples = useMemo(
    () => [
      t("query.occasionExampleWork"),
      t("query.occasionExampleDate"),
      t("query.occasionExampleFriends"),
      t("query.occasionExampleHome"),
      t("query.occasionExampleExercise"),
    ],
    [t],
  );
  const minDate = useMemo(() => toDateInputValue(new Date()), []);
  const maxDate = useMemo(() => {
    const date = new Date();
    date.setDate(date.getDate() + 5);
    return toDateInputValue(date);
  }, []);

  return (
    <>
      <section className="panel p-5">
        <div className="section-title">{t("query.sectionTitle")}</div>
        <div className="muted-copy mt-2">{t("query.sectionDescription")}</div>

        <div className="mt-4 grid gap-4">
          <input
            className="input"
            value={queryText}
            onChange={(event) => onQueryTextChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                onSubmit();
              }
            }}
            placeholder={t("query.inputPlaceholder")}
          />

          <div className="panel-muted p-4">
            <div className="section-title !text-lg">{t("query.genderTitle")}</div>
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              {genderOptions.map((option) => {
                const active = option.value === gender;
                return (
                  <button
                    key={option.value}
                    type="button"
                    className={active ? "gender-card gender-card-active" : "gender-card"}
                    onClick={() => onGenderChange(option.value)}
                  >
                    <div className="text-lg">{option.icon}</div>
                    <div className="mt-2 text-base font-semibold">{option.label}</div>
                  </button>
                );
              })}
            </div>
            <div className="mt-3 text-sm text-slate-500">{t("query.genderHint")}</div>
          </div>

          <div className="grid gap-4 md:grid-cols-[1.5fr_0.9fr]">
            <label className="grid gap-2">
              <span className="field-label">{t("query.occasionTitle")}</span>
              <input
                className="input"
                value={occasionText}
                onChange={(event) => onOccasionTextChange(event.target.value)}
                placeholder={t("query.occasionPlaceholder")}
              />
              <div className="flex flex-wrap gap-2">
                {occasionExamples.map((item) => (
                  <button
                    key={item}
                    type="button"
                    className="ghost-button !rounded-full !px-3 !py-2 !text-sm"
                    onClick={() => onOccasionTextChange(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </label>

            <label className="grid gap-2">
              <span className="field-label">{t("query.targetDateTitle")}</span>
              <input
                className="input"
                type="date"
                min={minDate}
                max={maxDate}
                value={targetDate}
                onChange={(event) => onTargetDateChange(event.target.value)}
              />
              <div className="text-sm text-slate-500">{t("query.targetDateHint")}</div>
            </label>
          </div>

          <div className={`grid gap-3 ${isPending ? "grid-cols-3" : "grid-cols-2"}`}>
            <button className="primary-button" type="button" disabled={!canSubmit || isPending} onClick={onSubmit}>
              {t("query.submit")}
            </button>
            {isPending ? (
              <button className="ghost-button" type="button" onClick={onPause}>
                {t("query.pause")}
              </button>
            ) : null}
            <button className="secondary-button" type="button" onClick={onClear}>
              {t("common.clear")}
            </button>
          </div>
        </div>

        <div className="mt-4">
          <QueryStatusCard progressState={progressState} />
        </div>

        <div className="mt-5">
          <div className="field-label">{t("query.recentQueries")}</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {recentQueries.length ? (
              recentQueries.slice(0, 3).map((item) => (
                <button
                  key={item}
                  type="button"
                  className="secondary-button !rounded-full !px-3 !py-2 !text-sm"
                  onClick={() => onPickQuickQuery(item, true)}
                >
                  {item}
                </button>
              ))
            ) : (
              <div className="text-sm text-slate-500">{t("query.recentQueriesEmpty")}</div>
            )}
          </div>
        </div>

        <div className="mt-5">
          <div className="field-label">{t("query.quickPlaces")}</div>
          <div className="mt-3 flex flex-wrap gap-2">
            {examples.map((item) => (
              <button
                key={item.label}
                type="button"
                className="ghost-button !rounded-full !px-3 !py-2 !text-sm"
                onClick={() => onPickQuickQuery(item.query_text, false)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      <ModeToggle value={confirmationMode} onChange={onConfirmationModeChange} />

      <LocationMapCard
        draftCoords={draftCoords}
        locationPin={locationPin}
        searchLocationLabel={searchLocationLabel}
        isPending={isPending}
        onSelect={onSelectMapCoords}
        onClearDraft={onClearMapCoords}
        onUseDraft={onUseMapCoords}
        onReselectLocation={onReselectLocation}
      />

      <CandidateConfirmCard
        resultVm={resultVm}
        selectedCandidateId={selectedCandidateId}
        showAllCandidates={showAllCandidates}
        isPending={isPending}
        onSelect={onSelectCandidate}
        onConfirm={onConfirmCandidate}
        onToggleShowAll={onToggleShowAllCandidates}
        onReselect={onReselectLocation}
      />
    </>
  );
}
