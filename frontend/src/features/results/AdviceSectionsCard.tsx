import { useTranslation } from "react-i18next";
import type { FashionSection } from "../../shared/types";

interface AdviceSectionsCardProps {
  sections: FashionSection[];
}

export default function AdviceSectionsCard(props: AdviceSectionsCardProps) {
  const { t } = useTranslation();

  return (
    <section className="grid gap-4 lg:grid-cols-2">
      {props.sections.length ? (
        props.sections.map((section) => (
          <div key={section.key} className="panel p-6">
            <div className="section-title">{section.title}</div>
            <div className="mt-4 whitespace-pre-wrap text-sm leading-8 text-slate-700">
              {section.content}
            </div>
          </div>
        ))
      ) : (
        <div className="panel p-6 text-sm text-slate-500">{t("advice.empty")}</div>
      )}
    </section>
  );
}
