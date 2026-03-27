import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { fetchMapSettings, testMapSettings, updateMapSettings } from "../../shared/api";
import type { MapProvider, MapSettingsResponse } from "../../shared/types";

function toDraft(source: MapSettingsResponse | undefined): MapSettingsResponse {
  return {
    provider: source?.provider || "osm",
    baidu_ak: source?.baidu_ak || "",
    baidu_ak_configured: source?.baidu_ak_configured || false,
    osm_tile_url: source?.osm_tile_url || "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    osm_attribution: source?.osm_attribution || "&copy; OpenStreetMap contributors",
    default_center_lat: source?.default_center_lat ?? 39.9042,
    default_center_lon: source?.default_center_lon ?? 116.4074,
    default_zoom: source?.default_zoom ?? 9,
  };
}

export default function MapConfigPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<MapSettingsResponse>(toDraft(undefined));
  const [saveMessage, setSaveMessage] = useState("");

  const settingsQuery = useQuery({
    queryKey: ["map-settings"],
    queryFn: fetchMapSettings,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (settingsQuery.data) {
      setDraft(toDraft(settingsQuery.data));
    }
  }, [settingsQuery.data]);

  const saveMutation = useMutation({
    mutationFn: updateMapSettings,
    onSuccess(data) {
      queryClient.setQueryData(["map-settings"], data);
      setDraft(toDraft(data));
      setSaveMessage(t("mapConfig.saveSuccess"));
    },
  });

  const testMutation = useMutation({
    mutationFn: testMapSettings,
  });

  return (
    <div className="grid gap-5 xl:grid-cols-[0.34fr_0.66fr]">
      <section className="panel p-6">
        <div className="field-label">{t("mapConfig.providerLabel")}</div>
        <div className="mt-4 grid gap-2">
          {(["osm", "baidu"] as MapProvider[]).map((item) => (
            <button
              key={item}
              type="button"
              className={
                draft.provider === item
                  ? "rounded-2xl bg-slate-950 px-4 py-3 text-left text-sm font-semibold text-white"
                  : "rounded-2xl border border-slate-200 px-4 py-3 text-left text-sm text-slate-600"
              }
              onClick={() => setDraft((current) => ({ ...current, provider: item }))}
            >
              {item === "osm" ? t("mapConfig.providers.osm") : t("mapConfig.providers.baidu")}
            </button>
          ))}
        </div>

        <div className="panel-muted mt-6 p-4">
          <div className="field-label">{t("mapConfig.statusTitle")}</div>
          <div className="mt-3 text-sm text-slate-700">
            {draft.provider === "baidu"
              ? draft.baidu_ak_configured || draft.baidu_ak
                ? t("common.configured")
                : t("common.notConfigured")
              : t("common.enabled")}
          </div>
          <div className="mt-2 text-sm text-slate-500">{t("mapConfig.runtimeHint")}</div>
        </div>
      </section>

      <section className="panel p-6">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="grid gap-2 md:col-span-2">
            <span className="field-label">{t("mapConfig.fields.baiduAk")}</span>
            <input
              className="input"
              value={draft.baidu_ak}
              onChange={(event) => setDraft((current) => ({ ...current, baidu_ak: event.target.value }))}
            />
          </label>

          <label className="grid gap-2 md:col-span-2">
            <span className="field-label">{t("mapConfig.fields.osmTileUrl")}</span>
            <input
              className="input"
              value={draft.osm_tile_url}
              onChange={(event) => setDraft((current) => ({ ...current, osm_tile_url: event.target.value }))}
            />
          </label>

          <label className="grid gap-2 md:col-span-2">
            <span className="field-label">{t("mapConfig.fields.osmAttribution")}</span>
            <input
              className="input"
              value={draft.osm_attribution}
              onChange={(event) => setDraft((current) => ({ ...current, osm_attribution: event.target.value }))}
            />
          </label>

          <label className="grid gap-2">
            <span className="field-label">{t("mapConfig.fields.defaultLat")}</span>
            <input
              className="input"
              type="number"
              step="0.0001"
              value={draft.default_center_lat}
              onChange={(event) =>
                setDraft((current) => ({ ...current, default_center_lat: Number(event.target.value) }))
              }
            />
          </label>

          <label className="grid gap-2">
            <span className="field-label">{t("mapConfig.fields.defaultLon")}</span>
            <input
              className="input"
              type="number"
              step="0.0001"
              value={draft.default_center_lon}
              onChange={(event) =>
                setDraft((current) => ({ ...current, default_center_lon: Number(event.target.value) }))
              }
            />
          </label>

          <label className="grid gap-2">
            <span className="field-label">{t("mapConfig.fields.defaultZoom")}</span>
            <input
              className="input"
              type="number"
              min="1"
              max="18"
              value={draft.default_zoom}
              onChange={(event) => setDraft((current) => ({ ...current, default_zoom: Number(event.target.value) }))}
            />
          </label>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <button type="button" className="secondary-button" onClick={() => testMutation.mutate(draft)}>
            {testMutation.isPending ? t("common.testing") : t("common.testConnection")}
          </button>
          <button type="button" className="primary-button" onClick={() => saveMutation.mutate(draft)}>
            {saveMutation.isPending ? t("common.saving") : t("common.save")}
          </button>
        </div>

        {saveMessage ? <div className="mt-4 text-sm text-emerald-700">{saveMessage}</div> : null}

        {testMutation.data ? (
          <div className="panel-muted mt-5 p-4">
            <div className="field-label">{t("mapConfig.connectionResult")}</div>
            <div className="mt-3 text-sm text-slate-700">{testMutation.data.message}</div>
          </div>
        ) : null}

        {settingsQuery.isLoading ? <div className="mt-4 text-sm text-slate-500">{t("common.loading")}</div> : null}
      </section>
    </div>
  );
}
