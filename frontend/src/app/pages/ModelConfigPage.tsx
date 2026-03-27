import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { fetchModelSettings, testModelSettings, updateModelSettings } from "../../shared/api";
import type { ModelProviderDraft, ModelSettingsResponse } from "../../shared/types";

type SlotKey = "default" | "alternate";
type TestKind = "chat" | "embedding";

interface EmbeddingDraft {
  enabled: boolean;
  inherit_from_chat_provider: boolean;
  provider: string;
  base_url: string;
  model: string;
  proxy_url: string;
  timeout_seconds: number;
  api_key: string;
}

function toProviderDraft(source: ModelSettingsResponse["providers"][SlotKey] | undefined): ModelProviderDraft {
  return {
    provider: source?.provider || "openai_compatible",
    name: source?.name || "",
    base_url: source?.base_url || "",
    model: source?.model || "",
    proxy_url: source?.proxy_url || "",
    temperature: source?.temperature ?? 0.2,
    timeout_seconds: source?.timeout_seconds ?? 60,
    api_key: "",
  };
}

function toEmbeddingDraft(source: ModelSettingsResponse["embedding"] | undefined): EmbeddingDraft {
  return {
    enabled: source?.enabled ?? false,
    inherit_from_chat_provider: source?.inherit_from_chat_provider ?? false,
    provider: source?.provider || "openai_compatible",
    base_url: source?.base_url || "",
    model: source?.model || "",
    proxy_url: source?.proxy_url || "",
    timeout_seconds: source?.timeout_seconds ?? 60,
    api_key: "",
  };
}

export default function ModelConfigPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const zh = i18n.language.startsWith("zh");
  const [slot, setSlot] = useState<SlotKey>("default");
  const [defaultProvider, setDefaultProvider] = useState<SlotKey>("default");
  const [providerDraft, setProviderDraft] = useState<ModelProviderDraft>(toProviderDraft(undefined));
  const [embeddingDraft, setEmbeddingDraft] = useState<EmbeddingDraft>(toEmbeddingDraft(undefined));
  const [showProviderAdvanced, setShowProviderAdvanced] = useState(false);
  const [showEmbeddingAdvanced, setShowEmbeddingAdvanced] = useState(false);
  const [clearApiKey, setClearApiKey] = useState(false);
  const [clearEmbeddingApiKey, setClearEmbeddingApiKey] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const [lastTestKind, setLastTestKind] = useState<TestKind>("chat");

  const settingsQuery = useQuery({
    queryKey: ["model-settings"],
    queryFn: fetchModelSettings,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (!settingsQuery.data) {
      return;
    }
    setDefaultProvider(settingsQuery.data.default_provider);
    setProviderDraft(toProviderDraft(settingsQuery.data.providers[slot]));
    setEmbeddingDraft(toEmbeddingDraft(settingsQuery.data.embedding));
    setClearApiKey(false);
    setClearEmbeddingApiKey(false);
  }, [settingsQuery.data, slot]);

  const activeProvider = settingsQuery.data?.providers[slot];
  const activeEmbedding = settingsQuery.data?.embedding;
  const activeProviderSlot = settingsQuery.data?.active_provider || settingsQuery.data?.default_provider || "default";

  const saveMutation = useMutation({
    mutationFn: () =>
      updateModelSettings({
        slot,
        provider: providerDraft,
        embedding: embeddingDraft,
        clear_api_key: clearApiKey,
        clear_embedding_api_key: clearEmbeddingApiKey,
        default_provider: defaultProvider,
      }),
    onSuccess(data) {
      queryClient.setQueryData(["model-settings"], data);
      setSaveMessage(t("modelConfig.saveSuccess"));
      setDefaultProvider(data.default_provider);
      setProviderDraft(toProviderDraft(data.providers[slot]));
      setEmbeddingDraft(toEmbeddingDraft(data.embedding));
      setClearApiKey(false);
      setClearEmbeddingApiKey(false);
    },
  });

  const testMutation = useMutation({
    mutationFn: (kind: TestKind) => {
      setLastTestKind(kind);
      if (kind === "embedding") {
        return testModelSettings({
          slot,
          embedding: embeddingDraft,
        });
      }
      return testModelSettings({
        slot,
        provider: providerDraft,
      });
    },
  });

  const missingFieldsText = useMemo(() => {
    const missing = activeProvider?.missing_fields || [];
    return missing.length ? missing.join(", ") : "";
  }, [activeProvider?.missing_fields]);

  const embeddingMissingFieldsText = useMemo(() => {
    const missing = activeEmbedding?.missing_fields || [];
    return missing.length ? missing.join(", ") : "";
  }, [activeEmbedding?.missing_fields]);

  return (
    <div className="grid gap-5 xl:grid-cols-[0.32fr_0.68fr]">
      <section className="panel p-6">
        <div className="field-label">{t("modelConfig.slotLabel")}</div>
        <div className="mt-4 grid gap-2">
          {(["default", "alternate"] as SlotKey[]).map((item) => (
            <button
              key={item}
              type="button"
              className={
                slot === item
                  ? "rounded-2xl bg-slate-950 px-4 py-3 text-left text-sm font-semibold text-white"
                  : "rounded-2xl border border-slate-200 px-4 py-3 text-left text-sm text-slate-600"
              }
              onClick={() => setSlot(item)}
            >
              {item === "default" ? t("modelConfig.defaultSlot") : t("modelConfig.alternateSlot")}
            </button>
          ))}
        </div>

        <div className="mt-6">
          <div className="field-label">{t("modelConfig.activeSlot")}</div>
          <div className="mt-3 flex rounded-2xl bg-slate-100 p-1">
            {(["default", "alternate"] as SlotKey[]).map((item) => (
              <button
                key={item}
                type="button"
                className={
                  defaultProvider === item
                    ? "rounded-xl bg-white px-4 py-2 text-sm font-semibold text-slate-950 shadow-sm"
                    : "rounded-xl px-4 py-2 text-sm text-slate-500"
                }
                onClick={() => setDefaultProvider(item)}
              >
                {item === "default" ? t("modelConfig.defaultSlot") : t("modelConfig.alternateSlot")}
              </button>
            ))}
          </div>
        </div>

        <div className="panel-muted mt-4 p-4">
          <div className="field-label">{t("modelConfig.activeSlot")}</div>
          <div className="mt-3 text-sm font-semibold text-slate-900">
            {activeProviderSlot === "default" ? t("modelConfig.defaultSlot") : t("modelConfig.alternateSlot")}
          </div>
          <div className="mt-2 text-sm text-slate-500">
            {activeProviderSlot === slot
              ? (settingsQuery.data?.providers[slot]?.model || t("common.noData"))
              : `${settingsQuery.data?.providers[activeProviderSlot]?.name || activeProviderSlot} / ${
                  settingsQuery.data?.providers[activeProviderSlot]?.model || t("common.noData")
                }`}
          </div>
        </div>

        <div className="panel-muted mt-6 p-4">
          <div className="field-label">{t("modelConfig.statusTitle")}</div>
          <div className="mt-3 text-sm text-slate-700">
            {activeProvider?.enabled ? t("common.enabled") : t("common.disabled")}
          </div>
          <div className="mt-2 text-sm text-slate-500">
            {activeProvider?.has_api_key ? t("modelConfig.storedKeyHint") : t("common.notConfigured")}
          </div>
          {missingFieldsText ? (
            <div className="mt-3 text-sm text-amber-700">
              {t("modelConfig.missingFields", { value: missingFieldsText })}
            </div>
          ) : null}
        </div>

        <div className="panel-muted mt-4 p-4">
          <div className="field-label">{t("modelConfig.embeddingStatusTitle")}</div>
          <div className="mt-3 text-sm text-slate-700">
            {activeEmbedding?.enabled ? t("common.enabled") : t("common.disabled")}
          </div>
          <div className="mt-2 text-sm text-slate-500">
            {activeEmbedding?.has_api_key ? t("modelConfig.storedKeyHint") : t("common.notConfigured")}
          </div>
          {embeddingMissingFieldsText ? (
            <div className="mt-3 text-sm text-amber-700">
              {t("modelConfig.missingFields", { value: embeddingMissingFieldsText })}
            </div>
          ) : null}
          <div className="mt-3 space-y-1 text-sm text-slate-500">
            <div>{`${zh ? "运行时提供方" : "Runtime provider"}: ${activeEmbedding?.runtime_provider || t("common.noData")}`}</div>
            <div>{`${zh ? "运行时 API 地址" : "Runtime base URL"}: ${activeEmbedding?.runtime_base_url || t("common.noData")}`}</div>
            <div>{`${zh ? "健康状态" : "Health"}: ${String(activeEmbedding?.health?.status || t("common.noData"))}`}</div>
            <div>{`${zh ? "索引是否兼容" : "Index compatible"}: ${
              activeEmbedding?.health?.index_compatible == null
                ? t("common.noData")
                : activeEmbedding?.health?.index_compatible
                  ? t("common.yes")
                  : t("common.no")
            }`}</div>
          </div>
        </div>
      </section>

      <section className="panel p-6">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="grid gap-2">
            <span className="field-label">{t("modelConfig.fields.name")}</span>
            <input
              className="input"
              value={providerDraft.name || ""}
              onChange={(event) => setProviderDraft((current) => ({ ...current, name: event.target.value }))}
            />
          </label>
          <label className="grid gap-2 md:col-span-2">
            <span className="field-label">{t("modelConfig.fields.baseUrl")}</span>
            <input
              className="input"
              value={providerDraft.base_url || ""}
              onChange={(event) => setProviderDraft((current) => ({ ...current, base_url: event.target.value }))}
            />
          </label>
          <label className="grid gap-2">
            <span className="field-label">{t("modelConfig.fields.model")}</span>
            <input
              className="input"
              value={providerDraft.model || ""}
              onChange={(event) => setProviderDraft((current) => ({ ...current, model: event.target.value }))}
            />
          </label>
          <label className="grid gap-2 md:col-span-2">
            <span className="field-label">{t("modelConfig.fields.apiKey")}</span>
            <input
              className="input"
              type="password"
              value={providerDraft.api_key || ""}
              onChange={(event) => {
                setClearApiKey(false);
                setProviderDraft((current) => ({ ...current, api_key: event.target.value }));
              }}
            />
            <div className="text-sm text-slate-500">{t("modelConfig.apiKeyHint")}</div>
          </label>
        </div>

        <div className="mt-5 rounded-2xl border border-slate-200 p-4">
          <button
            type="button"
            className="flex w-full items-center justify-between text-left text-sm font-semibold text-slate-900"
            onClick={() => setShowProviderAdvanced((value) => !value)}
          >
            <span>{t("modelConfig.advancedTitle")}</span>
            <span className="text-slate-500">
              {showProviderAdvanced ? t("common.close") : t("modelConfig.advancedOpen")}
            </span>
          </button>

          {showProviderAdvanced ? (
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <label className="grid gap-2">
                <span className="field-label">{t("modelConfig.fields.provider")}</span>
                <input
                  className="input"
                  value={providerDraft.provider || ""}
                  onChange={(event) => setProviderDraft((current) => ({ ...current, provider: event.target.value }))}
                />
              </label>
              <label className="grid gap-2">
                <span className="field-label">{t("modelConfig.fields.proxyUrl")}</span>
                <input
                  className="input"
                  value={providerDraft.proxy_url || ""}
                  onChange={(event) => setProviderDraft((current) => ({ ...current, proxy_url: event.target.value }))}
                />
              </label>
              <label className="grid gap-2">
                <span className="field-label">{t("modelConfig.fields.temperature")}</span>
                <input
                  className="input"
                  type="number"
                  step="0.1"
                  value={providerDraft.temperature ?? 0.2}
                  onChange={(event) =>
                    setProviderDraft((current) => ({ ...current, temperature: Number(event.target.value) }))
                  }
                />
              </label>
              <label className="grid gap-2">
                <span className="field-label">{t("modelConfig.fields.timeoutSeconds")}</span>
                <input
                  className="input"
                  type="number"
                  min="1"
                  value={providerDraft.timeout_seconds ?? 60}
                  onChange={(event) =>
                    setProviderDraft((current) => ({ ...current, timeout_seconds: Number(event.target.value) }))
                  }
                />
              </label>
            </div>
          ) : null}
        </div>

        <div className="mt-5 rounded-2xl border border-slate-200 p-4">
          <div className="section-title !text-lg">{t("modelConfig.embeddingTitle")}</div>
          <div className="mt-2 text-sm text-slate-500">{t("modelConfig.embeddingDescription")}</div>

          <div className="mt-4 grid gap-4">
            <label className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 px-4 py-3">
              <div>
                <div className="text-sm font-semibold text-slate-900">{t("modelConfig.embeddingEnabled")}</div>
                <div className="text-sm text-slate-500">
                  {embeddingDraft.enabled ? t("common.enabled") : t("common.disabled")}
                </div>
              </div>
              <input
                type="checkbox"
                checked={embeddingDraft.enabled}
                onChange={(event) =>
                  setEmbeddingDraft((current) => ({ ...current, enabled: event.target.checked }))
                }
              />
            </label>

            <label className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200 px-4 py-3">
              <div>
                <div className="text-sm font-semibold text-slate-900">{t("modelConfig.embeddingInherit")}</div>
                <div className="text-sm text-slate-500">
                  {embeddingDraft.inherit_from_chat_provider ? t("common.yes") : t("common.no")}
                </div>
              </div>
              <input
                type="checkbox"
                checked={embeddingDraft.inherit_from_chat_provider}
                onChange={(event) =>
                  setEmbeddingDraft((current) => ({
                    ...current,
                    inherit_from_chat_provider: event.target.checked,
                  }))
                }
              />
            </label>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="grid gap-2">
                <span className="field-label">{t("modelConfig.fields.model")}</span>
                <input
                  className="input"
                  value={embeddingDraft.model}
                  onChange={(event) =>
                    setEmbeddingDraft((current) => ({ ...current, model: event.target.value }))
                  }
                />
              </label>
              <label className="grid gap-2 md:col-span-2">
                <span className="field-label">{t("modelConfig.fields.apiKey")}</span>
                <input
                  className="input"
                  type="password"
                  value={embeddingDraft.api_key}
                  onChange={(event) => {
                    setClearEmbeddingApiKey(false);
                    setEmbeddingDraft((current) => ({ ...current, api_key: event.target.value }));
                  }}
                />
                <div className="text-sm text-slate-500">{t("modelConfig.apiKeyHint")}</div>
              </label>
            </div>

            <div className="rounded-2xl border border-slate-200 p-4">
              <button
                type="button"
                className="flex w-full items-center justify-between text-left text-sm font-semibold text-slate-900"
                onClick={() => setShowEmbeddingAdvanced((value) => !value)}
              >
                <span>{t("modelConfig.embeddingAdvancedTitle")}</span>
                <span className="text-slate-500">
                  {showEmbeddingAdvanced ? t("common.close") : t("modelConfig.advancedOpen")}
                </span>
              </button>

              {showEmbeddingAdvanced ? (
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <label className="grid gap-2">
                    <span className="field-label">{t("modelConfig.fields.provider")}</span>
                    <input
                      className="input"
                      value={embeddingDraft.provider}
                      disabled={embeddingDraft.inherit_from_chat_provider}
                      onChange={(event) =>
                        setEmbeddingDraft((current) => ({ ...current, provider: event.target.value }))
                      }
                    />
                  </label>
                  <label className="grid gap-2 md:col-span-2">
                    <span className="field-label">{t("modelConfig.fields.baseUrl")}</span>
                    <input
                      className="input"
                      value={embeddingDraft.base_url}
                      disabled={embeddingDraft.inherit_from_chat_provider}
                      onChange={(event) =>
                        setEmbeddingDraft((current) => ({ ...current, base_url: event.target.value }))
                      }
                    />
                  </label>
                  <label className="grid gap-2">
                    <span className="field-label">{t("modelConfig.fields.proxyUrl")}</span>
                    <input
                      className="input"
                      value={embeddingDraft.proxy_url}
                      disabled={embeddingDraft.inherit_from_chat_provider}
                      onChange={(event) =>
                        setEmbeddingDraft((current) => ({ ...current, proxy_url: event.target.value }))
                      }
                    />
                  </label>
                  <label className="grid gap-2">
                    <span className="field-label">{t("modelConfig.fields.timeoutSeconds")}</span>
                    <input
                      className="input"
                      type="number"
                      min="1"
                      value={embeddingDraft.timeout_seconds}
                      onChange={(event) =>
                        setEmbeddingDraft((current) => ({
                          ...current,
                          timeout_seconds: Number(event.target.value),
                        }))
                      }
                    />
                  </label>
                </div>
              ) : null}
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setClearApiKey(true);
              setProviderDraft((current) => ({ ...current, api_key: "" }));
            }}
          >
            {t("modelConfig.clearKey")}
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setClearEmbeddingApiKey(true);
              setEmbeddingDraft((current) => ({ ...current, api_key: "" }));
            }}
          >
            {t("modelConfig.embeddingClearKey")}
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={() => testMutation.mutate("chat")}
            disabled={testMutation.isPending}
          >
            {testMutation.isPending && lastTestKind === "chat" ? t("common.testing") : t("common.testConnection")}
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={() => testMutation.mutate("embedding")}
            disabled={testMutation.isPending}
          >
            {testMutation.isPending && lastTestKind === "embedding"
              ? t("common.testing")
              : t("modelConfig.embeddingTest")}
          </button>
          <button
            type="button"
            className="primary-button"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
          >
            {saveMutation.isPending ? t("common.saving") : t("common.save")}
          </button>
        </div>

        {saveMessage ? <div className="mt-4 text-sm text-emerald-700">{saveMessage}</div> : null}

        {testMutation.data ? (
          <div className="panel-muted mt-5 p-4">
            <div className="field-label">
              {lastTestKind === "embedding" ? t("modelConfig.embeddingConnectionResult") : t("modelConfig.connectionResult")}
            </div>
            <div className="mt-3 text-sm text-slate-700">{testMutation.data.message}</div>
            <div className="mt-2 text-sm text-slate-500">
              {testMutation.data.provider} / {testMutation.data.model} / {testMutation.data.latency_ms}ms
            </div>
            {lastTestKind === "embedding" ? (
              <div className="mt-3 space-y-1 text-sm text-slate-500">
                <div>{`${zh ? "向量维度" : "Dimensions"}: ${testMutation.data.dimensions || 0}`}</div>
                <div>{`${zh ? "索引是否兼容" : "Index compatible"}: ${
                  testMutation.data.index_compatible == null
                    ? t("common.noData")
                    : testMutation.data.index_compatible
                      ? t("common.yes")
                      : t("common.no")
                }`}</div>
                <div>{`${zh ? "降级原因" : "Degrade reason"}: ${testMutation.data.degrade_reason || t("common.none")}`}</div>
                <div>{`${zh ? "Embedding 指纹" : "Embedding fingerprint"}: ${testMutation.data.embedding_fingerprint || t("common.noData")}`}</div>
              </div>
            ) : null}
          </div>
        ) : null}

        {settingsQuery.isLoading ? <div className="mt-4 text-sm text-slate-500">{t("common.loading")}</div> : null}
      </section>
    </div>
  );
}
