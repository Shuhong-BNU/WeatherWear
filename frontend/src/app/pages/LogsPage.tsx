import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { fetchLogSources, fetchLogTail } from "../../shared/api";

export default function LogsPage() {
  const { t, i18n } = useTranslation();
  const [source, setSource] = useState("app.events.jsonl");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [requestIdFilter, setRequestIdFilter] = useState("");
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [successFilter, setSuccessFilter] = useState<"all" | "success" | "error">("all");
  const [llmFilter, setLlmFilter] = useState<"all" | "llm" | "non_llm">("all");
  const [fallbackOnly, setFallbackOnly] = useState(false);
  const zh = i18n.language.startsWith("zh");

  const sourcesQuery = useQuery({
    queryKey: ["log-sources"],
    queryFn: fetchLogSources,
    staleTime: 10_000,
  });

  useEffect(() => {
    if (!sourcesQuery.data?.length) {
      return;
    }
    if (!sourcesQuery.data.some((item) => item.source === source)) {
      setSource(sourcesQuery.data[0].source);
    }
  }, [source, sourcesQuery.data]);

  const tailQuery = useQuery({
    queryKey: ["log-tail", source],
    queryFn: () => fetchLogTail(source, 240),
    enabled: Boolean(source),
    refetchInterval: autoRefresh ? 3000 : false,
  });

  const filteredStructuredEvents = useMemo(() => {
    const events = tailQuery.data?.kind === "structured" ? tailQuery.data.events : [];
    return events.filter((item) => {
      const event = item as Record<string, unknown>;
      const payload = (event.payload as Record<string, unknown> | undefined) || {};
      const tags = Array.isArray(payload.tags) ? payload.tags.map((tag) => String(tag)) : [];
      const requestId = String(payload.request_id || "");
      const type = String(event.type || "");
      const success = payload.success;
      const usedLlm = Boolean(payload.used_llm);
      const fallbackUsed = Boolean(payload.fallback_used);
      if (requestIdFilter && !requestId.includes(requestIdFilter.trim())) {
        return false;
      }
      if (eventTypeFilter && !type.includes(eventTypeFilter.trim())) {
        return false;
      }
      if (tagFilter && !tags.some((tag) => tag.includes(tagFilter.trim()))) {
        return false;
      }
      if (successFilter === "success" && success !== true) {
        return false;
      }
      if (successFilter === "error" && success !== false) {
        return false;
      }
      if (llmFilter === "llm" && !usedLlm) {
        return false;
      }
      if (llmFilter === "non_llm" && usedLlm) {
        return false;
      }
      if (fallbackOnly && !fallbackUsed) {
        return false;
      }
      return true;
    });
  }, [eventTypeFilter, fallbackOnly, llmFilter, requestIdFilter, successFilter, tagFilter, tailQuery.data]);

  const renderedLines = useMemo(() => {
    if (!tailQuery.data) {
      return "";
    }
    if (tailQuery.data.kind === "structured" && filteredStructuredEvents.length) {
      return filteredStructuredEvents.map((item) => JSON.stringify(item, null, 2)).join("\n\n");
    }
    if (tailQuery.data.kind === "structured") {
      return "";
    }
    return tailQuery.data.lines.join("\n");
  }, [filteredStructuredEvents, tailQuery.data]);

  return (
    <section className="grid gap-5">
      <div className="panel flex flex-col gap-4 p-6 xl:flex-row xl:items-center xl:justify-between">
        <div>
          <div className="section-title">{t("logs.runtimeLogs")}</div>
          <div className="muted-copy mt-2">{t("logs.intro")}</div>
        </div>

        <div className="flex flex-wrap gap-3">
          <button type="button" className="secondary-button" onClick={() => sourcesQuery.refetch()}>
            {t("logs.refreshSources")}
          </button>
          <button type="button" className="secondary-button" onClick={() => tailQuery.refetch()} disabled={!source}>
            {t("logs.refreshCurrent")}
          </button>
          <button
            type="button"
            className={autoRefresh ? "primary-button" : "secondary-button"}
            onClick={() => setAutoRefresh((value) => !value)}
          >
            {autoRefresh ? t("logs.autoRefreshOn") : t("logs.autoRefreshOff")}
          </button>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[320px_minmax(0,1fr)]">
        <section className="panel p-6">
          <div className="field-label">{t("logs.sourcesTitle")}</div>
          <div className="mt-4 grid gap-2">
            {(sourcesQuery.data || []).map((item) => (
              <button
                key={item.source}
                type="button"
                className={
                  source === item.source
                    ? "rounded-2xl bg-slate-950 px-4 py-3 text-left text-sm font-semibold text-white"
                    : "rounded-2xl border border-slate-200 px-4 py-3 text-left text-sm text-slate-600"
                }
                onClick={() => setSource(item.source)}
              >
                <div>{item.label}</div>
                <div className={`mt-1 text-xs ${source === item.source ? "text-white/70" : "text-slate-400"}`}>
                  {item.source}
                </div>
              </button>
            ))}
          </div>
        </section>

        <section className="panel p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="section-title">{source || t("common.noData")}</div>
              <div className="muted-copy mt-2">{t("logs.sourceHint")}</div>
            </div>
            <button
              type="button"
              className="secondary-button"
              onClick={() => void navigator.clipboard?.writeText(renderedLines)}
              disabled={!renderedLines}
            >
              {t("logs.copyLogs")}
            </button>
          </div>
          {tailQuery.data?.kind === "structured" ? (
            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <label className="grid gap-2">
                <span className="field-label">{zh ? "请求 ID" : "Request ID"}</span>
                <input className="input" value={requestIdFilter} onChange={(e) => setRequestIdFilter(e.target.value)} />
              </label>
              <label className="grid gap-2">
                <span className="field-label">{zh ? "事件类型" : "Event type"}</span>
                <input className="input" value={eventTypeFilter} onChange={(e) => setEventTypeFilter(e.target.value)} />
              </label>
              <label className="grid gap-2">
                <span className="field-label">{zh ? "标签" : "Tag"}</span>
                <input className="input" value={tagFilter} onChange={(e) => setTagFilter(e.target.value)} />
              </label>
              <label className="grid gap-2">
                <span className="field-label">{zh ? "成功状态" : "Success"}</span>
                <select className="input" value={successFilter} onChange={(e) => setSuccessFilter(e.target.value as typeof successFilter)}>
                  <option value="all">{zh ? "全部" : "All"}</option>
                  <option value="success">{zh ? "仅成功" : "Success only"}</option>
                  <option value="error">{zh ? "仅失败" : "Error only"}</option>
                </select>
              </label>
              <label className="grid gap-2">
                <span className="field-label">{zh ? "LLM" : "LLM"}</span>
                <select className="input" value={llmFilter} onChange={(e) => setLlmFilter(e.target.value as typeof llmFilter)}>
                  <option value="all">{zh ? "全部" : "All"}</option>
                  <option value="llm">{zh ? "仅 LLM" : "LLM only"}</option>
                  <option value="non_llm">{zh ? "仅非 LLM" : "Non-LLM only"}</option>
                </select>
              </label>
              <label className="flex items-center gap-3 rounded-2xl border border-slate-200 px-4 py-3 text-sm text-slate-700">
                <input type="checkbox" checked={fallbackOnly} onChange={(e) => setFallbackOnly(e.target.checked)} />
                <span>{zh ? "仅看触发兜底" : "Fallback only"}</span>
              </label>
            </div>
          ) : null}
          {tailQuery.data?.kind === "structured" ? (
            <div className="mt-4 text-sm text-slate-500">
              {zh ? "筛选后事件数" : "Filtered events"}: {filteredStructuredEvents.length}
            </div>
          ) : null}

          <pre className="mt-4 max-h-[620px] overflow-auto rounded-3xl bg-slate-950 p-4 text-xs leading-6 text-slate-100">
            {tailQuery.isLoading ? t("common.loading") : renderedLines || t("logs.empty")}
          </pre>
        </section>
      </div>
    </section>
  );
}
