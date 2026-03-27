import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteHistory } from "../../shared/api";
import { useWeatherWearSession } from "../state/WeatherWearSession";

export default function HistoryPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { historyItems, historyLoading, runHistoryQuery } = useWeatherWearSession();

  const deleteMutation = useMutation({
    mutationFn: deleteHistory,
    onSuccess() {
      void queryClient.invalidateQueries({ queryKey: ["history"] });
    },
  });

  if (historyLoading) {
    return <div className="panel p-6 text-sm leading-7 text-slate-500">{t("common.loading")}</div>;
  }

  return (
    <section className="grid gap-4">
      {historyItems.length ? (
        historyItems.map((item) => (
          <div key={item.id} className="panel flex flex-col gap-4 p-5 xl:flex-row xl:items-center xl:justify-between">
            <div className="grid gap-2">
              <div className="field-label">{t("history.queryText")}</div>
              <div className="text-lg font-semibold text-slate-950">
                {item.query_text || item.confirmed_location_label}
              </div>
              <div className="text-sm text-slate-500">{item.confirmed_location_label || t("common.noData")}</div>
              <div className="text-sm text-slate-500">
                {new Date(item.created_at).toLocaleString()} · {item.query_path || t("common.noData")}
              </div>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                className="primary-button"
                onClick={() => {
                  runHistoryQuery(item);
                  navigate("/query");
                }}
              >
                {t("history.runAgain")}
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => deleteMutation.mutate(item.id)}
                disabled={deleteMutation.isPending}
              >
                {t("common.remove")}
              </button>
            </div>
          </div>
        ))
      ) : (
        <div className="panel p-6 text-sm leading-7 text-slate-500">{t("history.empty")}</div>
      )}
    </section>
  );
}
