import { useTranslation } from "react-i18next";

interface ReasonListCardProps {
  reasons: string[];
}

export default function ReasonListCard(props: ReasonListCardProps) {
  const { t } = useTranslation();

  return (
    <section className="panel p-6">
      <div className="section-title">{t("reasons.title")}</div>
      <div className="muted-copy mt-2">{t("reasons.description")}</div>
      <div className="mt-4 grid gap-3">
        {props.reasons.length ? (
          props.reasons.map((reason) => (
            <div key={reason} className="panel-muted px-4 py-3 text-sm leading-7 text-slate-700">
              {reason}
            </div>
          ))
        ) : (
          <div className="text-sm text-slate-500">{t("reasons.empty")}</div>
        )}
      </div>
    </section>
  );
}
