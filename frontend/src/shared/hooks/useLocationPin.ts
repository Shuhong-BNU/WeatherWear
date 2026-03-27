import { useMemo } from "react";
import type { LocationPin, QueryCoords } from "../types";

const DEFAULT_CENTER: [number, number] = [20.0, 100.0];
const DEFAULT_ZOOM = 3;

export function useLocationPin(
  locationPin: LocationPin | null | undefined,
  draftCoords: QueryCoords | null,
  options?: {
    defaultCenter?: [number, number];
    defaultZoom?: number;
    draftLabel?: string;
  },
) {
  const defaultCenter = options?.defaultCenter || DEFAULT_CENTER;
  const defaultZoom = options?.defaultZoom || DEFAULT_ZOOM;
  const draftLabel = options?.draftLabel || "Selected coordinates";

  return useMemo(() => {
    if (locationPin?.lat != null && locationPin?.lon != null && locationPin.confirmed) {
      return {
        center: [locationPin.lat, locationPin.lon] as [number, number],
        zoom: locationPin.zoom_hint || 8,
        markerLabel: locationPin.label,
        markerSource: locationPin.source,
        confirmed: true,
        hasMarker: true,
      };
    }

    if (draftCoords) {
      return {
        center: [draftCoords.lat, draftCoords.lon] as [number, number],
        zoom: 9,
        markerLabel: `${draftLabel}: ${draftCoords.lat}, ${draftCoords.lon}`,
        markerSource: "draft_map_pin",
        confirmed: false,
        hasMarker: true,
      };
    }

    return {
      center: defaultCenter,
      zoom: defaultZoom,
      markerLabel: "",
      markerSource: "",
      confirmed: false,
      hasMarker: false,
    };
  }, [defaultCenter, defaultZoom, draftCoords, draftLabel, locationPin]);
}
