import type {
  ConfirmationMode,
  DeveloperSessionState,
  ExamplesResponse,
  FavoriteLocation,
  GenderMode,
  HistoryItem,
  LogSource,
  LogTailResponse,
  LocaleCode,
  MapSettingsResponse,
  MapSettingsTestResponse,
  MapSettingsUpdatePayload,
  ModelConnectionTestPayload,
  ModelConnectionTestResponse,
  ModelSettingsResponse,
  ModelSettingsUpdatePayload,
  QueryCoords,
  QueryResponse,
  RuntimeHealth,
} from "./types";

interface QueryPayload {
  query_text?: string;
  selected_candidate_id?: string;
  confirmation_mode?: ConfirmationMode;
  selected_coords?: QueryCoords | null;
  gender?: GenderMode;
  occasion_text?: string;
  target_date?: string;
  locale?: LocaleCode;
  client_request_id?: string;
  signal?: AbortSignal;
}

interface ClientLogEventPayload {
  type: string;
  message: string;
  level?: string;
  payload?: Record<string, unknown>;
}

let clientLogEndpointAvailable: boolean | null = null;

interface FavoritePayload {
  id?: string;
  label: string;
  lat: number;
  lon: number;
  source: string;
  query_text: string;
  gender: GenderMode;
  occasion_text: string;
  target_date: string;
}

async function expectJson<T>(response: Response, fallbackMessage: string): Promise<T> {
  if (!response.ok) {
    throw new Error(fallbackMessage);
  }
  return response.json() as Promise<T>;
}

export async function fetchRuntimeHealth(locale: LocaleCode): Promise<RuntimeHealth> {
  const response = await fetch(`/api/health/runtime?locale=${encodeURIComponent(locale)}`, {
    credentials: "include",
  });
  return expectJson<RuntimeHealth>(response, "Failed to load runtime health.");
}

export async function fetchExamples(): Promise<ExamplesResponse> {
  const response = await fetch("/api/examples", {
    credentials: "include",
  });
  return expectJson<ExamplesResponse>(response, "Failed to load example locations.");
}

export async function postQuery(payload: QueryPayload): Promise<QueryResponse> {
  const response = await fetch("/api/query", {
    method: "POST",
    credentials: "include",
    signal: payload.signal,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query_text: payload.query_text ?? "",
      selected_candidate_id: payload.selected_candidate_id ?? "",
      confirmation_mode: payload.confirmation_mode ?? "smart",
      selected_coords: payload.selected_coords ?? null,
      gender: payload.gender ?? "neutral",
      occasion_text: payload.occasion_text ?? "",
      target_date: payload.target_date ?? "",
      locale: payload.locale ?? "zh-CN",
      client_request_id: payload.client_request_id ?? "",
    }),
  });
  return expectJson<QueryResponse>(response, "Query request failed.");
}

export async function cancelQuery(requestId: string): Promise<{ ok: boolean }> {
  const response = await fetch("/api/query/cancel", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ request_id: requestId }),
  });
  return expectJson<{ ok: boolean }>(response, "Failed to cancel query.");
}

export async function postClientLogEvent(payload: ClientLogEventPayload): Promise<{ ok: boolean }> {
  if (clientLogEndpointAvailable === false) {
    return { ok: false };
  }
  try {
    const response = await fetch("/api/logs/client-event", {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        type: payload.type,
        message: payload.message,
        level: payload.level ?? "info",
        payload: payload.payload ?? {},
      }),
    });
    if (response.status === 404 || response.status === 405) {
      clientLogEndpointAvailable = false;
      return { ok: false };
    }
    clientLogEndpointAvailable = true;
    return expectJson<{ ok: boolean }>(response, "Failed to write client log event.");
  } catch {
    return { ok: false };
  }
}

export async function fetchModelSettings(): Promise<ModelSettingsResponse> {
  const response = await fetch("/api/settings/model", {
    credentials: "include",
  });
  return expectJson<ModelSettingsResponse>(response, "Failed to load model settings.");
}

export async function updateModelSettings(payload: ModelSettingsUpdatePayload): Promise<ModelSettingsResponse> {
  const response = await fetch("/api/settings/model", {
    method: "PUT",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return expectJson<ModelSettingsResponse>(response, "Failed to save model settings.");
}

export async function testModelSettings(
  payload: ModelConnectionTestPayload,
): Promise<ModelConnectionTestResponse> {
  const response = await fetch("/api/settings/model/test", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return expectJson<ModelConnectionTestResponse>(response, "Failed to test model connection.");
}

export async function fetchDeveloperSession(): Promise<DeveloperSessionState> {
  const response = await fetch("/api/dev/session", {
    credentials: "include",
  });
  return expectJson<DeveloperSessionState>(response, "Failed to load developer session.");
}

export async function unlockDeveloperSession(pin: string): Promise<DeveloperSessionState> {
  const response = await fetch("/api/dev/unlock", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ pin }),
  });
  return expectJson<DeveloperSessionState>(response, "Failed to unlock developer session.");
}

export async function lockDeveloperSession(): Promise<DeveloperSessionState> {
  const response = await fetch("/api/dev/lock", {
    method: "POST",
    credentials: "include",
  });
  return expectJson<DeveloperSessionState>(response, "Failed to lock developer session.");
}

export async function fetchMapSettings(): Promise<MapSettingsResponse> {
  const response = await fetch("/api/settings/map", {
    credentials: "include",
  });
  return expectJson<MapSettingsResponse>(response, "Failed to load map settings.");
}

export async function updateMapSettings(payload: MapSettingsUpdatePayload): Promise<MapSettingsResponse> {
  const response = await fetch("/api/settings/map", {
    method: "PUT",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return expectJson<MapSettingsResponse>(response, "Failed to save map settings.");
}

export async function testMapSettings(payload: MapSettingsUpdatePayload): Promise<MapSettingsTestResponse> {
  const response = await fetch("/api/settings/map/test", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return expectJson<MapSettingsTestResponse>(response, "Failed to test map settings.");
}

export async function fetchHistory(): Promise<HistoryItem[]> {
  const response = await fetch("/api/history", {
    credentials: "include",
  });
  return expectJson<HistoryItem[]>(response, "Failed to load history.");
}

export async function deleteHistory(id: string): Promise<{ ok: boolean }> {
  const response = await fetch(`/api/history/${encodeURIComponent(id)}`, {
    method: "DELETE",
    credentials: "include",
  });
  return expectJson<{ ok: boolean }>(response, "Failed to delete history item.");
}

export async function fetchFavorites(): Promise<FavoriteLocation[]> {
  const response = await fetch("/api/favorites", {
    credentials: "include",
  });
  return expectJson<FavoriteLocation[]>(response, "Failed to load favorites.");
}

export async function saveFavorite(payload: FavoritePayload): Promise<FavoriteLocation> {
  const response = await fetch("/api/favorites", {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return expectJson<FavoriteLocation>(response, "Failed to save favorite.");
}

export async function deleteFavorite(id: string): Promise<{ ok: boolean }> {
  const response = await fetch(`/api/favorites/${encodeURIComponent(id)}`, {
    method: "DELETE",
    credentials: "include",
  });
  return expectJson<{ ok: boolean }>(response, "Failed to delete favorite.");
}

export async function fetchLogSources(): Promise<LogSource[]> {
  const response = await fetch("/api/logs/sources", {
    credentials: "include",
  });
  return expectJson<LogSource[]>(response, "Failed to load log sources.");
}

export async function fetchLogTail(source: string, lines = 200): Promise<LogTailResponse> {
  const response = await fetch(
    `/api/logs/tail?source=${encodeURIComponent(source)}&lines=${encodeURIComponent(String(lines))}`,
    {
      credentials: "include",
    },
  );
  return expectJson<LogTailResponse>(response, "Failed to load log tail.");
}
