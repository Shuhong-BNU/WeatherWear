import { useTranslation } from "react-i18next";
import type { KnowledgeBasisViewModel } from "../../shared/types";

interface KnowledgeBasisCardProps {
  knowledge: KnowledgeBasisViewModel;
}

export default function KnowledgeBasisCard(props: KnowledgeBasisCardProps) {
  const { t } = useTranslation();
  const toneClass =
    props.knowledge.status === "merged"
      ? "chip chip-success"
      : props.knowledge.status === "matched"
        ? "chip chip-info"
        : "chip chip-warning";

  return (
    <section className="panel p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="section-title">{t("knowledge.title")}</div>
          <div className="muted-copy mt-2">{t("knowledge.description")}</div>
        </div>
        <span className={toneClass}>{t(`knowledge.status.${props.knowledge.status}`)}</span>
      </div>
      <div className="mt-4 text-sm leading-7 text-slate-600">{props.knowledge.summary}</div>
      <div className="mt-4 grid gap-3">
        {props.knowledge.items.length ? (
          props.knowledge.items.map((item) => (
            <div key={item.id} className="panel-muted px-4 py-4">
              <div className="text-sm font-semibold text-slate-900">{item.label}</div>
              <div className="mt-2 text-sm leading-7 text-slate-700">{item.short_reason}</div>
            </div>
          ))
        ) : (
          <div className="text-sm text-slate-500">{t("knowledge.empty")}</div>
        )}
      </div>
    </section>
  );
}
