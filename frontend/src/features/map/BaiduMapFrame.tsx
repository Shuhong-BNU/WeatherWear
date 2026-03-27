import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import type { MapRuntimeDiagnostics, QueryCoords } from "../../shared/types";
import { bd09ToWgs84, wgs84ToBd09 } from "./coordinateTransforms";

const BAIDU_FRAME_SOURCE = "weatherwear-baidu-frame";
const BAIDU_PARENT_SOURCE = "weatherwear-baidu-parent";
const BAIDU_READY_TIMEOUT_MS = 8000;

interface BaiduMapFrameProps {
  ak: string;
  center: [number, number];
  zoom: number;
  hasMarker: boolean;
  confirmed: boolean;
  markerLabel: string;
  searchLabel?: string;
  onSelect: (coords: QueryCoords) => void;
  onResolveSearchLocation?: (coords: QueryCoords, label: string) => void;
  onDiagnosticsChange: (patch: Partial<MapRuntimeDiagnostics>) => void;
}

interface FrameEventPayload {
  source?: string;
  frameId?: string;
  type?: string;
  payload?: Record<string, unknown>;
}

function buildSrcDoc(params: {
  ak: string;
  frameId: string;
  popupFallback: string;
  loadFailedMessage: string;
  loadTimeoutMessage: string;
  runtimeMissingMessage: string;
  initFailedMessage: string;
}) {
  const {
    ak,
    frameId,
    popupFallback,
    loadFailedMessage,
    loadTimeoutMessage,
    runtimeMissingMessage,
    initFailedMessage,
  } = params;

  return `<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <style>
      html, body, #map {
        width: 100%;
        height: 100%;
        margin: 0;
        padding: 0;
        overflow: hidden;
        background: #f8fafc;
      }
      #map-status {
        position: absolute;
        inset: 0;
        display: none;
        align-items: center;
        justify-content: center;
        padding: 24px;
        box-sizing: border-box;
        color: #dc2626;
        font: 14px/1.7 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        text-align: center;
        background: #f8fafc;
      }
    </style>
  </head>
  <body>
    <div id="map"></div>
    <div id="map-status"></div>
    <script>
      (function () {
        var FRAME_ID = ${JSON.stringify(frameId)};
        var FRAME_SOURCE = ${JSON.stringify(BAIDU_FRAME_SOURCE)};
        var PARENT_SOURCE = ${JSON.stringify(BAIDU_PARENT_SOURCE)};
        var POPUP_FALLBACK = ${JSON.stringify(popupFallback)};
        var LOAD_FAILED = ${JSON.stringify(loadFailedMessage)};
        var LOAD_TIMEOUT = ${JSON.stringify(loadTimeoutMessage)};
        var RUNTIME_MISSING = ${JSON.stringify(runtimeMissingMessage)};
        var INIT_FAILED = ${JSON.stringify(initFailedMessage)};
        var map = null;
        var statusEl = document.getElementById("map-status");
        var mapRoot = document.getElementById("map");
        var timeout = null;

        function post(type, payload) {
          window.parent.postMessage(
            {
              source: FRAME_SOURCE,
              frameId: FRAME_ID,
              type: type,
              payload: payload || {},
            },
            "*"
          );
        }

        function setStatus(message) {
          statusEl.textContent = message || "";
          statusEl.style.display = message ? "flex" : "none";
        }

        function render(payload) {
          if (!map || !window.BMapGL || !payload || !payload.center) {
            return;
          }
          var BMapGL = window.BMapGL;
          var point = new BMapGL.Point(payload.center.lon, payload.center.lat);
          map.centerAndZoom(point, Number(payload.zoom || 9));
          map.clearOverlays();
          if (!payload.hasMarker) {
            if (payload.searchLabel) {
              resolveSearchLabel(String(payload.searchLabel), Number(payload.zoom || 9));
            }
            return;
          }

          var marker = new BMapGL.Marker(point);
          var label = new BMapGL.Label(payload.markerLabel || POPUP_FALLBACK, {
            position: point,
            offset: new BMapGL.Size(18, -18),
          });
          marker.setLabel(label);

          var circle = new BMapGL.Circle(point, payload.confirmed ? 2200 : 1600, {
            strokeColor: "#4f7cff",
            fillColor: "#7ea5ff",
            fillOpacity: 0.18,
            strokeWeight: 2,
          });

          map.addOverlay(circle);
          map.addOverlay(marker);
        }

        function resolveSearchLabel(label, zoom) {
          if (!label || !map || !window.BMapGL || !window.BMapGL.Geocoder) {
            return;
          }
          try {
            var BMapGL = window.BMapGL;
            var geocoder = new BMapGL.Geocoder();
            geocoder.getPoint(label, function (point) {
              if (!point) {
                post("search-unresolved", { label: label });
                return;
              }
              map.centerAndZoom(point, Number(zoom || 9));
              map.clearOverlays();
              var marker = new BMapGL.Marker(point);
              var popupLabel = new BMapGL.Label(label || POPUP_FALLBACK, {
                position: point,
                offset: new BMapGL.Size(18, -18),
              });
              marker.setLabel(popupLabel);
              map.addOverlay(marker);
              post("search-resolved", {
                label: label,
                lat: Number(point.lat),
                lon: Number(point.lng),
              });
            });
          } catch (error) {
            post("search-unresolved", {
              label: label,
              message: error && error.message ? error.message : String(error || ""),
            });
          }
        }

        function createMap() {
          if (!window.BMapGL) {
            setStatus(RUNTIME_MISSING);
            post("runtime-missing", {});
            return;
          }

          try {
            var BMapGL = window.BMapGL;
            map = new BMapGL.Map(mapRoot);
            map.enableScrollWheelZoom(true);
            map.addEventListener("click", function (event) {
              var latlng = event && (event.latlng || event.latLng);
              if (!latlng) {
                return;
              }
              post("select", {
                lat: Number(latlng.lat),
                lon: Number(latlng.lng),
              });
            });
            setStatus("");
            post("ready", {});
          } catch (error) {
            setStatus(INIT_FAILED);
            post("init-error", {
              message: error && error.message ? error.message : String(error || ""),
            });
          }
        }

        window.addEventListener("message", function (event) {
          var data = event.data || {};
          if (data.source !== PARENT_SOURCE || data.frameId !== FRAME_ID || data.type !== "render") {
            return;
          }
          render(data.payload || {});
        });

        window.__weatherwearBaiduSdkError__ = function () {
          if (timeout) {
            window.clearTimeout(timeout);
          }
          setStatus(LOAD_FAILED);
          post("script-error", {});
        };

        window.__weatherwearBaiduSdkReady__ = function () {
          if (timeout) {
            window.clearTimeout(timeout);
          }
          post("script-loaded", {});
          createMap();
        };

        post("script-requested", {});
        timeout = window.setTimeout(function () {
          setStatus(LOAD_TIMEOUT);
          post("timeout", {});
        }, ${BAIDU_READY_TIMEOUT_MS});
      })();
    </script>
    <script
      src="https://api.map.baidu.com/api?v=1.0&type=webgl&ak=${encodeURIComponent(ak)}&callback=__weatherwearBaiduSdkReady__"
      onerror="window.__weatherwearBaiduSdkError__ && window.__weatherwearBaiduSdkError__()"
    ></script>
  </body>
</html>`;
}

export default function BaiduMapFrame(props: BaiduMapFrameProps) {
  const { t } = useTranslation();
  const { ak, center, confirmed, hasMarker, markerLabel, onDiagnosticsChange, onResolveSearchLocation, onSelect, searchLabel, zoom } = props;
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const onSelectRef = useRef(onSelect);
  const onResolveSearchLocationRef = useRef(onResolveSearchLocation);
  const frameIdRef = useRef(`weatherwear-baidu-${Math.random().toString(36).slice(2)}`);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => {
    onSelectRef.current = onSelect;
  }, [onSelect]);

  useEffect(() => {
    onResolveSearchLocationRef.current = onResolveSearchLocation;
  }, [onResolveSearchLocation]);

  const srcDoc = useMemo(
    () =>
      buildSrcDoc({
        ak,
        frameId: frameIdRef.current,
        popupFallback: t("map.popupFallback"),
        loadFailedMessage: t("map.baiduLoadFailed"),
        loadTimeoutMessage: t("map.baiduLoadTimeout"),
        runtimeMissingMessage: t("map.baiduRuntimeMissing"),
        initFailedMessage: t("map.baiduMapInitFailed"),
      }),
    [ak, t],
  );

  useEffect(() => {
    setMapReady(false);
    onDiagnosticsChange({
      provider: "baidu",
      scriptRequested: true,
      scriptLoaded: false,
      readyResolved: false,
      hasBMapGL: false,
      mapCreated: false,
      errorMessage: "",
    });
  }, [ak, onDiagnosticsChange]);

  useEffect(() => {
    const frameId = frameIdRef.current;
    const handleMessage = (event: MessageEvent<FrameEventPayload>) => {
      const data = event.data;
      if (!data || data.source !== BAIDU_FRAME_SOURCE || data.frameId !== frameId) {
        return;
      }

      if (data.type === "script-requested") {
        onDiagnosticsChange({
          provider: "baidu",
          scriptRequested: true,
          scriptLoaded: false,
          readyResolved: false,
          hasBMapGL: false,
          mapCreated: false,
          errorMessage: "",
        });
        return;
      }

      if (data.type === "script-loaded") {
        onDiagnosticsChange({
          scriptLoaded: true,
        });
        return;
      }

      if (data.type === "ready") {
        setMapReady(true);
        onDiagnosticsChange({
          scriptLoaded: true,
          readyResolved: true,
          hasBMapGL: true,
          mapCreated: true,
          errorMessage: "",
        });
        return;
      }

      if (data.type === "select") {
        const lat = Number(data.payload?.lat);
        const lon = Number(data.payload?.lon);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
          return;
        }
        const converted = bd09ToWgs84(lat, lon);
        onSelectRef.current({
          lat: Number(converted.lat.toFixed(6)),
          lon: Number(converted.lon.toFixed(6)),
        });
        return;
      }

      if (data.type === "search-resolved") {
        const lat = Number(data.payload?.lat);
        const lon = Number(data.payload?.lon);
        const label = String(data.payload?.label || "").trim();
        if (!Number.isFinite(lat) || !Number.isFinite(lon) || !label) {
          return;
        }
        const converted = bd09ToWgs84(lat, lon);
        onResolveSearchLocationRef.current?.(
          {
            lat: Number(converted.lat.toFixed(6)),
            lon: Number(converted.lon.toFixed(6)),
          },
          label,
        );
        return;
      }

      if (data.type === "timeout") {
        setMapReady(false);
        onDiagnosticsChange({
          readyResolved: false,
          hasBMapGL: false,
          mapCreated: false,
          errorMessage: t("map.baiduLoadTimeout"),
        });
        return;
      }

      const errorMessage =
        data.type === "runtime-missing"
          ? t("map.baiduRuntimeMissing")
          : data.type === "init-error"
            ? t("map.baiduMapInitFailed")
            : t("map.baiduLoadFailed");

      setMapReady(false);
      onDiagnosticsChange({
        scriptLoaded: data.type === "runtime-missing" || data.type === "init-error",
        readyResolved: true,
        hasBMapGL: data.type === "init-error",
        mapCreated: false,
        errorMessage,
      });
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [onDiagnosticsChange, t]);

  useEffect(() => {
    onDiagnosticsChange({
      center: {
        lat: Number(center[0].toFixed(6)),
        lon: Number(center[1].toFixed(6)),
      },
    });
  }, [center, onDiagnosticsChange]);

  useEffect(() => {
    if (!mapReady) {
      return;
    }
    const targetWindow = iframeRef.current?.contentWindow;
    if (!targetWindow) {
      return;
    }

    const convertedCenter = wgs84ToBd09(center[0], center[1]);
    targetWindow.postMessage(
      {
        source: BAIDU_PARENT_SOURCE,
        frameId: frameIdRef.current,
        type: "render",
        payload: {
          center: {
            lat: convertedCenter.lat,
            lon: convertedCenter.lon,
          },
          zoom,
          hasMarker,
          confirmed,
          markerLabel,
          searchLabel,
        },
      },
      "*",
    );
  }, [center, confirmed, hasMarker, mapReady, markerLabel, searchLabel, zoom]);

  if (!ak.trim()) {
    return (
      <div className="flex h-[320px] items-center justify-center bg-slate-50 px-6 text-center text-sm text-slate-500 md:h-[340px]">
        {t("map.baiduKeyMissing")}
      </div>
    );
  }

  return (
    <iframe
      ref={iframeRef}
      title="Baidu map"
      srcDoc={srcDoc}
      className="h-[320px] w-full border-0 md:h-[340px]"
    />
  );
}
