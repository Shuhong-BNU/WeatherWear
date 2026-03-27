import { useTranslation } from "react-i18next";
import type { ConfirmationMode } from "../../shared/types";

interface ModeToggleProps {
  value: ConfirmationMode;
  onChange: (value: ConfirmationMode) => void;
}

export default function ModeToggle(props: ModeToggleProps) {
  const { t } = useTranslation();
  const { value, onChange } = props;
  const options: Array<{
    value: ConfirmationMode;
    title: string;
    description: string;
  }> = [
    {
      value: "smart",
      title: t("mode.smartTitle"),
      description: t("mode.smartDescription"),
    },
    {
      value: "strict",
      title: t("mode.strictTitle"),
      description: t("mode.strictDescription"),
    },
  ];

  return (
    <section className="panel p-5">
      <div className="section-title">{t("mode.title")}</div>
      <div className="muted-copy mt-2">{t("mode.description")}</div>
      <div className="mt-4 rounded-2xl bg-slate-100 p-1">
        <div className="grid grid-cols-2 gap-1">
          {options.map((option) => {
            const active = option.value === value;
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => onChange(option.value)}
                className={
                  active
                    ? "rounded-xl bg-white px-4 py-3 text-left shadow-sm"
                    : "rounded-xl px-4 py-3 text-left text-slate-500 transition hover:bg-white/60"
                }
              >
                <div className={`text-sm font-semibold ${active ? "text-slate-900" : "text-slate-700"}`}>
                  {option.title}
                </div>
              </button>
            );
          })}
        </div>
      </div>
      <div className="panel-muted mt-4 p-4 text-sm leading-7 text-slate-600">
        {options.find((item) => item.value === value)?.description}
      </div>
    </section>
  );
}
