import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import type { ResultViewModel } from "../../shared/types";

interface CandidateConfirmCardProps {
  resultVm: ResultViewModel | null;
  selectedCandidateId: string;
  showAllCandidates: boolean;
  isPending: boolean;
  onSelect: (candidateId: string) => void;
  onConfirm: (candidateId?: string) => void;
  onToggleShowAll: () => void;
  onReselect: () => void;
}

function CandidateCard(props: {
  label: string;
  meta: string;
  description: string;
  selected: boolean;
  recommendedLabel?: string;
  onClick: () => void;
}) {
  const { label, meta, description, selected, recommendedLabel, onClick } = props;
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-2xl border p-4 text-left transition ${
        selected ? "border-brand-500 bg-brand-50 ring-4 ring-brand-100" : "border-slate-200 bg-white hover:border-brand-200"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-slate-900">{label}</div>
          <div className="mt-1 text-xs text-slate-500">{meta}</div>
        </div>
        {recommendedLabel ? <span className="chip chip-success">{recommendedLabel}</span> : null}
      </div>
      <div className="mt-3 text-sm leading-7 text-slate-700">{description}</div>
    </button>
  );
}

export default function CandidateConfirmCard(props: CandidateConfirmCardProps) {
  const { t } = useTranslation();
  const {
    resultVm,
    selectedCandidateId,
    showAllCandidates,
    isPending,
    onSelect,
    onConfirm,
    onToggleShowAll,
    onReselect,
  } = props;

  const options = resultVm?.clarification.options || [];
  const recommended = options[0];
  const secondary = useMemo(() => (showAllCandidates ? options.slice(1) : options.slice(1, 3)), [options, showAllCandidates]);

  if (resultVm?.clarification.needed && recommended) {
    return (
      <section className="panel p-5">
        <div className="section-title">{t("candidate.title")}</div>
        <div className="muted-copy mt-2">{resultVm.clarification.message || t("candidate.subtitleFallback")}</div>

        <div className="mt-4">
          <CandidateCard
            label={recommended.label}
            meta={t("candidate.confidenceMeta", { value: recommended.confidence.toFixed(2), source: recommended.source })}
            description={recommended.reason}
            selected={selectedCandidateId === recommended.candidate_id}
            recommendedLabel={t("candidate.recommended")}
            onClick={() => onSelect(recommended.candidate_id)}
          />
        </div>

        {secondary.length ? (
          <div className="mt-4 grid gap-3">
            {secondary.map((option) => (
              <CandidateCard
                key={option.candidate_id}
                label={option.label}
                meta={t("candidate.confidenceMeta", { value: option.confidence.toFixed(2), source: option.source })}
                description={option.reason}
                selected={selectedCandidateId === option.candidate_id}
                onClick={() => onSelect(option.candidate_id)}
              />
            ))}
          </div>
        ) : null}

        <div className="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            className="primary-button"
            disabled={isPending}
            onClick={() => onConfirm(selectedCandidateId || recommended.candidate_id)}
          >
            {t("candidate.confirm")}
          </button>
          {options.length > 3 ? (
            <button type="button" className="secondary-button" onClick={onToggleShowAll}>
              {showAllCandidates ? t("candidate.showLess") : t("candidate.showMore")}
            </button>
          ) : null}
          <button type="button" className="ghost-button" onClick={onReselect}>
            {t("candidate.reselect")}
          </button>
        </div>
      </section>
    );
  }

  return null;
}
