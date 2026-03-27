import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Circle, MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from "react-leaflet";
import { divIcon, type LeafletMouseEvent } from "leaflet";
import { useTranslation } from "react-i18next";
import { postClientLogEvent, updateMapSettings } from "../../shared/api";
import { useWeatherWearSession } from "../../app/state/WeatherWearSession";
import type { MapRuntimeDiagnostics, QueryCoords } from "../../shared/types";
import { useLocationPin } from "../../shared/hooks/useLocationPin";
import BaiduMapFrame from "./BaiduMapFrame";
import { bd09ToWgs84, wgs84ToBd09 } from "./coordinateTransforms";
import { loadBaiduMapSdk } from "./loadBaiduMapSdk";

interface LocationMapCardProps {
  draftCoords: QueryCoords | null;
  locationPin: {
    lat: number | null;
    lon: number | null;
    label: string;
    source: string;
    confirmed: boolean;
    zoom_hint: number;
  } | null;
  searchLocationLabel: string;
  isPending: boolean;
  onSelect: (coords: QueryCoords) => void;
  onClearDraft: () => void;
  onUseDraft: () => void;
  onReselectLocation?: () => void;
}

function boolLabel(t: (key: string) => string, value: boolean) {
  return value ? t("common.yes") : t("common.no");
}

function formatCenter(center: QueryCoords | null, t: (key: string) => string) {
  if (!center) {
    return t("common.noData");
  }
  return `${center.lat.toFixed(4)}, ${center.lon.toFixed(4)}`;
}

function toErrorMessage(error: unknown, t: (key: string) => string) {
  const code = error instanceof Error ? error.message : "";
  switch (code) {
    case "missing_baidu_ak":
      return t("map.baiduKeyMissing");
    case "baidu_sdk_timeout":
      return t("map.baiduLoadTimeout");
    case "baidu_runtime_missing":
      return t("map.baiduRuntimeMissing");
    case "baidu_map_init_failed":
      return t("map.baiduMapInitFailed");
    default:
      return t("map.baiduLoadFailed");
  }
}

function RuntimeDiagnosticsPanel(props: { diagnostics: MapRuntimeDiagnostics }) {
  const { t } = useTranslation();
  const { diagnostics } = props;
  const rows = [
    [t("map.diagnostics.provider"), diagnostics.provider],
    [t("map.diagnostics.scriptRequested"), boolLabel(t, diagnostics.scriptRequested)],
    [t("map.diagnostics.scriptLoaded"), boolLabel(t, diagnostics.scriptLoaded)],
    [t("map.diagnostics.readyResolved"), boolLabel(t, diagnostics.readyResolved)],
    [t("map.diagnostics.hasRuntime"), boolLabel(t, diagnostics.hasBMapGL)],
    [t("map.diagnostics.mapCreated"), boolLabel(t, diagnostics.mapCreated)],
    [t("map.diagnostics.center"), formatCenter(diagnostics.center, t)],
    [t("map.diagnostics.error"), diagnostics.errorMessage || t("common.none")],
  ];

  return (
    <div className="panel-muted mt-4 p-4">
      <div className="field-label">{t("map.diagnostics.title")}</div>
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="rounded-2xl border border-slate-200 bg-white px-4 py-3">
            <div className="field-label">{label}</div>
            <div className="mt-2 text-sm leading-7 text-slate-700">{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MapClickHandler(props: { onSelect: (coords: QueryCoords) => void }) {
  useMapEvents({
    click(event: LeafletMouseEvent) {
      props.onSelect({
        lat: Number(event.latlng.lat.toFixed(6)),
        lon: Number(event.latlng.lng.toFixed(6)),
      });
    },
  });
  return null;
}

function MapViewportController(props: { center: [number, number]; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo(props.center, props.zoom, { duration: 0.8 });
  }, [map, props.center, props.zoom]);
  return null;
}

function LeafletMapCanvas(props: {
  center: [number, number];
  zoom: number;
  hasMarker: boolean;
  confirmed: boolean;
  markerLabel: string;
  displayCoords: string;
  tileUrl: string;
  attribution: string;
  onSelect: (coords: QueryCoords) => void;
}) {
  const markerIcon = useMemo(
    () =>
      divIcon({
        className: "map-pin-wrapper",
        html: '<div class="map-pin-marker"><span></span></div>',
        iconSize: [28, 28],
        iconAnchor: [14, 28],
        popupAnchor: [0, -24],
      }),
    [],
  );

  return (
    <MapContainer center={props.center} zoom={props.zoom} scrollWheelZoom className="h-[320px] w-full md:h-[340px]">
      <TileLayer attribution={props.attribution} url={props.tileUrl} />
      <MapViewportController center={props.center} zoom={props.zoom} />
      <MapClickHandler onSelect={props.onSelect} />
      {props.hasMarker ? (
        <>
          <Circle
            center={props.center}
            radius={props.confirmed ? 2200 : 1600}
            pathOptions={{ color: "#4f7cff", fillColor: "#7ea5ff", fillOpacity: 0.18 }}
          />
          <Marker position={props.center} icon={markerIcon}>
            <Popup>
              <div className="text-sm font-semibold text-slate-900">{props.markerLabel}</div>
              <div className="mt-1 text-xs text-slate-500">{props.displayCoords}</div>
            </Popup>
          </Marker>
        </>
      ) : null}
    </MapContainer>
  );
}

function BaiduMapCanvas(props: {
  ak: string;
  center: [number, number];
  zoom: number;
  hasMarker: boolean;
  confirmed: boolean;
  markerLabel: string;
  onSelect: (coords: QueryCoords) => void;
  onDiagnosticsChange: (patch: Partial<MapRuntimeDiagnostics>) => void;
}) {
  const { t } = useTranslation();
  const { ak, center, confirmed, hasMarker, markerLabel, onDiagnosticsChange, onSelect, zoom } = props;
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const clickHandlerRef = useRef<((event: unknown) => void) | null>(null);
  const onSelectRef = useRef(props.onSelect);
  const [mapReady, setMapReady] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  useEffect(() => {
    let disposed = false;
    setMapReady(false);
    setErrorMessage("");
    onDiagnosticsChange({
      provider: "baidu",
      scriptRequested: true,
      scriptLoaded: false,
      readyResolved: false,
      hasBMapGL: Boolean(window.BMapGL),
      mapCreated: false,
      errorMessage: "",
    });

    loadBaiduMapSdk(ak, {
      onScriptRequested() {
        onDiagnosticsChange({ scriptRequested: true });
      },
      onScriptLoaded() {
        onDiagnosticsChange({ scriptLoaded: true });
      },
    })
      .then(() => {
        if (disposed || !containerRef.current) {
          return;
        }
        if (!window.BMapGL) {
          throw new Error("baidu_runtime_missing");
        }
        if (mapRef.current) {
          setMapReady(true);
          onDiagnosticsChange({
            readyResolved: true,
            hasBMapGL: true,
            mapCreated: true,
            errorMessage: "",
          });
          return;
        }

        try {
          const BMapGL = window.BMapGL;
          containerRef.current.innerHTML = "";
          const map = new BMapGL.Map(containerRef.current);
          map.enableScrollWheelZoom(true);
          const handleClick = (event: any) => {
            const latlng = event.latlng || event.latLng;
            if (!latlng) {
              return;
            }
            const converted = bd09ToWgs84(Number(latlng.lat), Number(latlng.lng));
            onSelectRef.current({
              lat: Number(converted.lat.toFixed(6)),
              lon: Number(converted.lon.toFixed(6)),
            });
          };
          map.addEventListener("click", handleClick);
          mapRef.current = map;
          clickHandlerRef.current = handleClick;
          setMapReady(true);
          onDiagnosticsChange({
            readyResolved: true,
            hasBMapGL: true,
            mapCreated: true,
            errorMessage: "",
          });
        } catch {
          throw new Error("baidu_map_init_failed");
        }
      })
      .catch((error) => {
        const nextMessage = toErrorMessage(error, t);
        if (!disposed) {
          setErrorMessage(nextMessage);
          onDiagnosticsChange({
            readyResolved: error instanceof Error && error.message === "baidu_sdk_timeout" ? false : true,
            hasBMapGL: Boolean(window.BMapGL),
            mapCreated: false,
            errorMessage: nextMessage,
          });
        }
      });

    return () => {
      disposed = true;
      if (mapRef.current) {
        try {
          if (clickHandlerRef.current && typeof mapRef.current.removeEventListener === "function") {
            mapRef.current.removeEventListener("click", clickHandlerRef.current);
          }
          if (typeof mapRef.current.destroy === "function") {
            mapRef.current.destroy();
          }
        } catch {
          // Swallow SDK teardown errors so the page can recover on the next mount.
        }
      }
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }
      mapRef.current = null;
      clickHandlerRef.current = null;
    };
  }, [ak, onDiagnosticsChange, t]);

  useEffect(() => {
    onDiagnosticsChange({
      center: {
        lat: Number(center[0].toFixed(6)),
        lon: Number(center[1].toFixed(6)),
      },
    });
  }, [center, onDiagnosticsChange]);

  useEffect(() => {
    if (!mapReady || !mapRef.current || !window.BMapGL) {
      return;
    }
    const BMapGL = window.BMapGL;
    const convertedCenter = wgs84ToBd09(center[0], center[1]);
    const centerPoint = new BMapGL.Point(convertedCenter.lon, convertedCenter.lat);
    mapRef.current.centerAndZoom(centerPoint, zoom);
    mapRef.current.clearOverlays();

    if (!hasMarker) {
      return;
    }

    const markerPoint = new BMapGL.Point(convertedCenter.lon, convertedCenter.lat);
    const marker = new BMapGL.Marker(markerPoint);
    const label = new BMapGL.Label(markerLabel || t("map.popupFallback"), {
      position: markerPoint,
      offset: new BMapGL.Size(18, -18),
    });
    marker.setLabel(label);

    const circle = new BMapGL.Circle(markerPoint, confirmed ? 2200 : 1600, {
      strokeColor: "#4f7cff",
      fillColor: "#7ea5ff",
      fillOpacity: 0.18,
      strokeWeight: 2,
    });
    mapRef.current.addOverlay(circle);
    mapRef.current.addOverlay(marker);
  }, [center, confirmed, hasMarker, mapReady, markerLabel, t, zoom]);

  if (!ak.trim()) {
    return (
      <div className="flex h-[320px] items-center justify-center bg-slate-50 px-6 text-center text-sm text-slate-500 md:h-[340px]">
        {t("map.baiduKeyMissing")}
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div className="flex h-[320px] items-center justify-center bg-slate-50 px-6 text-center text-sm text-rose-600 md:h-[340px]">
        {errorMessage}
      </div>
    );
  }

  return <div ref={containerRef} className="h-[320px] w-full md:h-[340px]" />;
}

export default function LocationMapCard(props: LocationMapCardProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const {
    mapSettings,
    mapSettingsLoading,
    mapRuntimeDiagnostics,
    resultVm,
    setMapRuntimeDiagnostics,
    setNotice,
    viewMode,
  } = useWeatherWearSession();

  const [resolvedTextPin, setResolvedTextPin] = useState<LocationMapCardProps["locationPin"]>(null);
  const geocodeAbortRef = useRef<AbortController | null>(null);
  const lastSearchResolveKeyRef = useRef("");
  const defaultCenter = useMemo<[number, number]>(
    () => [mapSettings?.default_center_lat ?? 39.9042, mapSettings?.default_center_lon ?? 116.4074],
    [mapSettings?.default_center_lat, mapSettings?.default_center_lon],
  );
  const effectiveLocationPin =
    props.locationPin?.lat != null && props.locationPin?.lon != null ? props.locationPin : resolvedTextPin;
  const searchLocationLabel = useMemo(() => {
    if (props.draftCoords) {
      return "";
    }
    if (props.locationPin?.lat != null && props.locationPin?.lon != null) {
      return "";
    }
    const label = props.searchLocationLabel.trim();
    if (!label) {
      return "";
    }
    return label;
  }, [props.draftCoords, props.locationPin?.lat, props.locationPin?.lon, props.searchLocationLabel]);

  useEffect(() => {
    if (props.draftCoords) {
      setResolvedTextPin(null);
      return;
    }
    if (props.locationPin?.lat != null && props.locationPin?.lon != null) {
      setResolvedTextPin(null);
      return;
    }
    if (!searchLocationLabel) {
      setResolvedTextPin(null);
      return;
    }
    setResolvedTextPin((current) => (current?.label === searchLocationLabel ? current : null));
  }, [props.draftCoords, props.locationPin, searchLocationLabel]);

  useEffect(() => {
    if (mapSettingsLoading || mapSettings?.provider !== "osm") {
      geocodeAbortRef.current?.abort();
      geocodeAbortRef.current = null;
      if (mapSettings?.provider !== "osm") {
        lastSearchResolveKeyRef.current = "";
      }
      return;
    }
    if (props.draftCoords || (props.locationPin?.lat != null && props.locationPin?.lon != null) || !searchLocationLabel) {
      geocodeAbortRef.current?.abort();
      geocodeAbortRef.current = null;
      lastSearchResolveKeyRef.current = "";
      return;
    }
    if (resolvedTextPin?.label === searchLocationLabel) {
      return;
    }

    const resolveKey = `${mapSettings.provider}|${searchLocationLabel}`;
    if (lastSearchResolveKeyRef.current === resolveKey) {
      return;
    }
    lastSearchResolveKeyRef.current = resolveKey;

    const controller = new AbortController();
    geocodeAbortRef.current = controller;
    const localeValue = document?.documentElement?.lang || "zh-CN";
    const query = encodeURIComponent(searchLocationLabel);
    const url = `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&q=${query}`;

    void fetch(url, {
      signal: controller.signal,
      headers: {
        "Accept-Language": localeValue,
      },
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`osm_geocode_${response.status}`);
        }
        return (await response.json()) as Array<Record<string, unknown>>;
      })
      .then((items) => {
        if (!Array.isArray(items) || !items.length) {
          return;
        }
        const first = items[0];
        const lat = Number(first.lat);
        const lon = Number(first.lon);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
          return;
        }
        const label = String(first.display_name || searchLocationLabel).trim() || searchLocationLabel;
        setResolvedTextPin({
          lat: Number(lat.toFixed(6)),
          lon: Number(lon.toFixed(6)),
          label,
          source: "osm_frontend_geocode",
          confirmed: true,
          zoom_hint: 9,
        });
      })
      .catch((error) => {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        setResolvedTextPin(null);
      });

    return () => {
      controller.abort();
      if (geocodeAbortRef.current === controller) {
        geocodeAbortRef.current = null;
      }
    };
  }, [
    mapSettings?.provider,
    mapSettingsLoading,
    props.draftCoords,
    props.locationPin?.lat,
    props.locationPin?.lon,
    resolvedTextPin?.label,
    searchLocationLabel,
  ]);

  const mapState = useLocationPin(effectiveLocationPin, props.draftCoords, {
    defaultCenter,
    defaultZoom: mapSettings?.default_zoom ?? 3,
    draftLabel: t("map.selectedLabel"),
  });

  const displayCoords =
    mapState.hasMarker && mapState.center
      ? `${mapState.center[0].toFixed(4)}, ${mapState.center[1].toFixed(4)}`
      : t("map.emptyCoords");
  const centerPayload = useMemo<QueryCoords>(
    () => ({
      lat: Number(mapState.center[0].toFixed(6)),
      lon: Number(mapState.center[1].toFixed(6)),
    }),
    [mapState.center],
  );
  const updateMapDiagnostics = useCallback(
    (patch: Partial<MapRuntimeDiagnostics>) =>
      setMapRuntimeDiagnostics((current) => ({
        ...current,
        ...patch,
      })),
    [setMapRuntimeDiagnostics],
  );
  const lastLoggedDiagnosticsRef = useRef("");

  useEffect(() => {
    if (mapSettingsLoading) {
      return;
    }

    if (mapSettings?.provider === "baidu") {
      setMapRuntimeDiagnostics((current) => ({
        ...current,
        provider: "baidu",
        center: centerPayload,
      }));
      return;
    }

    setMapRuntimeDiagnostics({
      provider: "osm",
      scriptRequested: false,
      scriptLoaded: false,
      readyResolved: true,
      hasBMapGL: typeof window !== "undefined" && Boolean(window.BMapGL),
      mapCreated: true,
      center: centerPayload,
      errorMessage: "",
    });
  }, [centerPayload, mapSettings?.provider, mapSettingsLoading, setMapRuntimeDiagnostics]);

  useEffect(() => {
    if (mapRuntimeDiagnostics.provider !== "baidu") {
      lastLoggedDiagnosticsRef.current = "";
      return;
    }

    const snapshot = JSON.stringify({
      provider: mapRuntimeDiagnostics.provider,
      scriptRequested: mapRuntimeDiagnostics.scriptRequested,
      scriptLoaded: mapRuntimeDiagnostics.scriptLoaded,
      readyResolved: mapRuntimeDiagnostics.readyResolved,
      hasBMapGL: mapRuntimeDiagnostics.hasBMapGL,
      mapCreated: mapRuntimeDiagnostics.mapCreated,
      errorMessage: mapRuntimeDiagnostics.errorMessage,
    });

    if (!snapshot || snapshot === lastLoggedDiagnosticsRef.current) {
      return;
    }
    lastLoggedDiagnosticsRef.current = snapshot;

    const isError = Boolean(mapRuntimeDiagnostics.errorMessage);
    void postClientLogEvent({
      type: isError ? "frontend.map.baidu.error" : "frontend.map.baidu.diagnostics",
      message: isError ? "Baidu map runtime error captured." : "Baidu map runtime diagnostics updated.",
      level: isError ? "warning" : "info",
      payload: {
        ...mapRuntimeDiagnostics,
        path: window.location.pathname,
        request_id: resultVm?.summary.request_id || "",
        session_locale: resultVm?.summary.locale || document?.documentElement?.lang || "",
      },
    }).catch(() => undefined);
  }, [mapRuntimeDiagnostics, resultVm?.summary.locale, resultVm?.summary.request_id]);

  const switchToOsmMutation = useMutation({
    mutationFn: () =>
      updateMapSettings({
        provider: "osm",
        baidu_ak: mapSettings?.baidu_ak ?? null,
        osm_tile_url: mapSettings?.osm_tile_url ?? null,
        osm_attribution: mapSettings?.osm_attribution ?? null,
        default_center_lat: mapSettings?.default_center_lat ?? null,
        default_center_lon: mapSettings?.default_center_lon ?? null,
        default_zoom: mapSettings?.default_zoom ?? null,
      }),
    onSuccess() {
      void queryClient.invalidateQueries({ queryKey: ["map-settings"] });
      setNotice({
        tone: "info",
        message: t("map.switchToOsmSuccess"),
      });
    },
    onError() {
      setNotice({
        tone: "error",
        message: t("map.switchToOsmFailed"),
      });
    },
  });

  return (
    <section className="panel p-5">
      <div className="section-title">{t("map.title")}</div>
      <div className="muted-copy mt-2">{t("map.description")}</div>

      <div className="mt-4 overflow-hidden rounded-[26px] border border-slate-200">
        {mapSettingsLoading ? (
          <div className="flex h-[320px] items-center justify-center bg-slate-50 text-sm text-slate-500 md:h-[340px]">
            {t("common.loading")}
          </div>
        ) : mapSettings?.provider === "baidu" ? (
          <BaiduMapFrame
            ak={mapSettings.baidu_ak}
            center={mapState.center}
            zoom={mapState.zoom}
            hasMarker={mapState.hasMarker}
            confirmed={mapState.confirmed}
            markerLabel={mapState.markerLabel || t("map.popupFallback")}
            searchLabel={searchLocationLabel}
            onSelect={props.onSelect}
            onResolveSearchLocation={(coords, label) => {
              setResolvedTextPin({
                lat: coords.lat,
                lon: coords.lon,
                label,
                source: "baidu_frontend_geocode",
                confirmed: true,
                zoom_hint: 9,
              });
            }}
            onDiagnosticsChange={updateMapDiagnostics}
          />
        ) : (
          <LeafletMapCanvas
            center={mapState.center}
            zoom={mapState.zoom}
            hasMarker={mapState.hasMarker}
            confirmed={mapState.confirmed}
            markerLabel={mapState.markerLabel || t("map.popupFallback")}
            displayCoords={displayCoords}
            tileUrl={mapSettings?.osm_tile_url || "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"}
            attribution={mapSettings?.osm_attribution || "&copy; OpenStreetMap contributors"}
            onSelect={props.onSelect}
          />
        )}
      </div>

      <div className="mt-4 rounded-2xl bg-slate-50 p-4">
        <div className="field-label">{mapState.confirmed ? t("map.confirmedLabel") : t("map.selectedLabel")}</div>
        <div className="mt-2 text-base font-semibold text-slate-900">{mapState.markerLabel || t("map.emptyLabel")}</div>
        <div className="mt-2 text-sm text-slate-600">
          {t("advanced.coords")}: {displayCoords}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <button type="button" className="primary-button" disabled={!props.draftCoords || props.isPending} onClick={props.onUseDraft}>
          {t("map.useLocation")}
        </button>
        <button type="button" className="secondary-button" disabled={!props.draftCoords} onClick={props.onClearDraft}>
          {t("map.clearDraft")}
        </button>
        {props.locationPin?.confirmed && props.onReselectLocation ? (
          <button type="button" className="ghost-button" onClick={props.onReselectLocation}>
            {t("candidate.reselect")}
          </button>
        ) : null}
        {viewMode === "developer" && mapSettings?.provider === "baidu" && mapRuntimeDiagnostics.errorMessage ? (
          <button
            type="button"
            className="secondary-button"
            onClick={() => switchToOsmMutation.mutate()}
            disabled={switchToOsmMutation.isPending}
          >
            {switchToOsmMutation.isPending ? t("common.saving") : t("map.switchToOsm")}
          </button>
        ) : null}
      </div>

      {viewMode === "developer" ? <RuntimeDiagnosticsPanel diagnostics={mapRuntimeDiagnostics} /> : null}
    </section>
  );
}
