import {
  createContext,
  type Dispatch,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  type SetStateAction,
  useState,
  type PropsWithChildren,
} from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  cancelQuery,
  deleteFavorite,
  fetchDeveloperSession,
  fetchExamples,
  fetchFavorites,
  fetchHistory,
  fetchMapSettings,
  fetchRuntimeHealth,
  lockDeveloperSession,
  postQuery,
  saveFavorite,
  unlockDeveloperSession,
} from "../../shared/api";
import { useQueryProgress } from "../../shared/hooks/useQueryProgress";
import type {
  AdvancedTab,
  ConfirmationMode,
  DeveloperSessionState,
  ExamplesResponse,
  FavoriteLocation,
  GenderMode,
  HistoryItem,
  LocaleCode,
  MapRuntimeDiagnostics,
  MapSettingsResponse,
  QueryCoords,
  QueryProgressState,
  RequestKind,
  ResultViewModel,
  RuntimeHealth,
  ViewMode,
} from "../../shared/types";

const LOCALE_KEY = "weatherwear_locale";
const VIEW_MODE_KEY = "weatherwear_view_mode";
const CONFIRMATION_MODE_KEY = "weatherwear_confirmation_mode_default";
const RESULT_SESSION_KEY = "weatherwear_last_result";

function toDateInputValue(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

type NoticeTone = "info" | "warning" | "error";

interface SessionNotice {
  tone: NoticeTone;
  message: string;
}

interface WeatherWearSessionValue {
  locale: LocaleCode;
  setLocale: (value: LocaleCode) => void;
  viewMode: ViewMode;
  setViewMode: (value: ViewMode) => void;
  confirmationMode: ConfirmationMode;
  setConfirmationMode: (value: ConfirmationMode) => void;
  queryText: string;
  setQueryText: (value: string) => void;
  gender: GenderMode;
  setGender: (value: GenderMode) => void;
  occasionText: string;
  setOccasionText: (value: string) => void;
  targetDate: string;
  setTargetDate: (value: string) => void;
  draftCoords: QueryCoords | null;
  setDraftCoords: (coords: QueryCoords | null) => void;
  resultVm: ResultViewModel | null;
  selectedCandidateId: string;
  setSelectedCandidateId: (candidateId: string) => void;
  requestKind: RequestKind;
  showAllCandidates: boolean;
  setShowAllCandidates: (value: boolean) => void;
  recentQueries: string[];
  historyItems: HistoryItem[];
  historyLoading: boolean;
  favorites: FavoriteLocation[];
  favoritesLoading: boolean;
  examples: ExamplesResponse["items"];
  runtimeHealth: RuntimeHealth | undefined;
  runtimeHealthLoading: boolean;
  runtimeHealthError: Error | null;
  queryError: Error | null;
  isPending: boolean;
  queryPaused: boolean;
  progressState: QueryProgressState;
  notice: SessionNotice | null;
  setNotice: (notice: SessionNotice | null) => void;
  dismissNotice: () => void;
  activeAdvancedTab: AdvancedTab;
  setActiveAdvancedTab: (tab: AdvancedTab) => void;
  developerSession: DeveloperSessionState | undefined;
  developerSessionLoading: boolean;
  mapSettings: MapSettingsResponse | undefined;
  mapSettingsLoading: boolean;
  mapRuntimeDiagnostics: MapRuntimeDiagnostics;
  setMapRuntimeDiagnostics: Dispatch<SetStateAction<MapRuntimeDiagnostics>>;
  unlockDeveloperMode: (pin: string) => Promise<boolean>;
  lockDeveloperMode: () => Promise<void>;
  clearWorkspace: () => void;
  pauseActiveQuery: () => void;
  submitTextQuery: (query?: string, mode?: ConfirmationMode) => void;
  submitMapQuery: (coords?: QueryCoords | null, mode?: ConfirmationMode) => void;
  confirmCandidate: (candidateId?: string) => void;
  rerunStrictSelection: () => void;
  runRecentQuery: (query: string) => void;
  runHistoryQuery: (item: HistoryItem) => void;
  runFavoriteQuery: (favorite: FavoriteLocation) => void;
  saveCurrentFavorite: () => void;
  removeFavorite: (id: string) => void;
  isCurrentFavorite: boolean;
}

const WeatherWearSessionContext = createContext<WeatherWearSessionValue | null>(null);

function writeJson(key: string, value: unknown, storage: Storage = window.localStorage) {
  storage.setItem(key, JSON.stringify(value));
}

function readStoredString<T extends string>(key: string, fallback: T): T {
  if (typeof window === "undefined") {
    return fallback;
  }
  const raw = window.localStorage.getItem(key);
  return raw ? (raw as T) : fallback;
}

function normalizeResultViewModel(resultVm: Partial<ResultViewModel> | ResultViewModel | null): ResultViewModel | null {
  if (!resultVm) {
    return null;
  }
  const summary = (resultVm.summary ?? {}) as Partial<ResultViewModel["summary"]>;
  const queryContext = summary.query_context;
  return {
    ...resultVm,
    summary: {
      ...summary,
      resolution_final_status: summary.resolution_final_status || summary.resolution_status || "",
      cached_resolution_status: summary.cached_resolution_status || "",
      retrieval_mode: summary.retrieval_mode || "rules_only",
      vector_leg_status: summary.vector_leg_status || "unknown",
      vector_leg_skipped_reason: summary.vector_leg_skipped_reason || "",
      fashion_generation_mode: summary.fashion_generation_mode || "",
      query_context: {
        gender: (queryContext?.gender || "neutral") as GenderMode,
        occasion_text: queryContext?.occasion_text || "",
        occasion_tags: Array.isArray(queryContext?.occasion_tags) ? queryContext.occasion_tags : [],
        primary_scene: queryContext?.primary_scene || "",
        context_tags: Array.isArray(queryContext?.context_tags) ? queryContext.context_tags : [],
        target_date: queryContext?.target_date || "",
        forecast_mode: queryContext?.forecast_mode || "current",
      },
    },
    knowledge_basis: resultVm.knowledge_basis ?? { status: "no_match", summary: "", items: [] },
    debug_sections: {
      ...(resultVm.debug_sections ?? {}),
      knowledge: Array.isArray((resultVm.debug_sections as Record<string, unknown> | undefined)?.knowledge)
        ? ((resultVm.debug_sections as Record<string, unknown>).knowledge as unknown[])
        : [],
    },
  } as ResultViewModel;
}

function readStoredResult(): ResultViewModel | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.sessionStorage.getItem(RESULT_SESSION_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<ResultViewModel>;
    return normalizeResultViewModel(parsed);
  } catch {
    return null;
  }
}

function buildFavoriteFromResult(resultVm: ResultViewModel | null): FavoriteLocation | null {
  const normalizedResult = normalizeResultViewModel(resultVm);
  if (!normalizedResult?.summary.confirmed_location_label) {
    return null;
  }
  const lat = normalizedResult.location_pin.lat;
  const lon = normalizedResult.location_pin.lon;
  if (lat == null || lon == null) {
    return null;
  }
  const label = normalizedResult.summary.confirmed_location_label;
  const queryContext = normalizedResult.summary.query_context;
  return {
    id: `${lat}:${lon}:${label}`,
    label,
    lat,
    lon,
    source: normalizedResult.summary.location_source,
    query_text: normalizedResult.summary.user_input || label,
    gender: queryContext.gender,
    occasion_text: queryContext.occasion_text,
    target_date: queryContext.target_date,
    added_at: new Date().toISOString(),
  };
}

function normalizeConfirmationMode(value: string | undefined): ConfirmationMode {
  return value === "strict" ? "strict" : "smart";
}

function isAbortError(error: unknown): boolean {
  if (!error) {
    return false;
  }
  if (error instanceof DOMException && error.name === "AbortError") {
    return true;
  }
  if (error instanceof Error && error.name === "AbortError") {
    return true;
  }
  return typeof error === "object" && error !== null && "name" in error && (error as { name?: string }).name === "AbortError";
}

function createClientRequestId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `ww-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function buildLocaleNormalizationSignature(resultVm: ResultViewModel, nextLocale: LocaleCode) {
  const normalizedResult = normalizeResultViewModel(resultVm);
  if (!normalizedResult) {
    return nextLocale;
  }
  const coords =
    normalizedResult.summary.location_source === "map_pin" &&
    normalizedResult.location_pin.lat != null &&
    normalizedResult.location_pin.lon != null
      ? `${normalizedResult.location_pin.lat}:${normalizedResult.location_pin.lon}`
      : "";
  return [
    normalizedResult.summary.user_input,
    normalizedResult.summary.location_source,
    normalizedResult.summary.confirmation_mode,
    normalizedResult.summary.query_context.gender,
    normalizedResult.summary.query_context.occasion_text,
    normalizedResult.summary.query_context.target_date,
    coords,
    normalizedResult.summary.locale,
    nextLocale,
  ].join("|");
}

export function WeatherWearSessionProvider(props: PropsWithChildren) {
  const { i18n, t } = useTranslation();
  const queryClient = useQueryClient();
  const [locale, setLocaleState] = useState<LocaleCode>(() => readStoredString<LocaleCode>(LOCALE_KEY, "zh-CN"));
  const [viewMode, setViewModeState] = useState<ViewMode>(() => readStoredString<ViewMode>(VIEW_MODE_KEY, "user"));
  const [confirmationMode, setConfirmationModeState] = useState<ConfirmationMode>(() =>
    readStoredString<ConfirmationMode>(CONFIRMATION_MODE_KEY, "smart"),
  );
  const localeRef = useRef<LocaleCode>(locale);
  const [queryText, setQueryText] = useState("");
  const [gender, setGender] = useState<GenderMode>("neutral");
  const [occasionText, setOccasionText] = useState("");
  const [targetDate, setTargetDate] = useState(() => toDateInputValue(new Date()));
  const [draftCoords, setDraftCoords] = useState<QueryCoords | null>(null);
  const [resultVm, setResultVm] = useState<ResultViewModel | null>(() => readStoredResult());
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [requestKind, setRequestKind] = useState<RequestKind>("text");
  const [showAllCandidates, setShowAllCandidates] = useState(false);
  const [notice, setNotice] = useState<SessionNotice | null>(null);
  const [activeAdvancedTab, setActiveAdvancedTab] = useState<AdvancedTab>("location");
  const localeRefreshAttemptRef = useRef("");
  const activeQueryAbortRef = useRef<AbortController | null>(null);
  const activeQueryRequestIdRef = useRef("");
  const [queryPaused, setQueryPaused] = useState(false);
  const [mapRuntimeDiagnostics, setMapRuntimeDiagnostics] = useState<MapRuntimeDiagnostics>({
    provider: "osm",
    scriptRequested: false,
    scriptLoaded: false,
    readyResolved: true,
    hasBMapGL: false,
    mapCreated: false,
    center: null,
    errorMessage: "",
  });

  useEffect(() => {
    localeRef.current = locale;
    void i18n.changeLanguage(locale);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LOCALE_KEY, locale);
    }
  }, [i18n, locale]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(VIEW_MODE_KEY, viewMode);
    }
  }, [viewMode]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(CONFIRMATION_MODE_KEY, confirmationMode);
    }
  }, [confirmationMode]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      if (resultVm) {
        writeJson(RESULT_SESSION_KEY, resultVm, window.sessionStorage);
      } else {
        window.sessionStorage.removeItem(RESULT_SESSION_KEY);
      }
    }
  }, [resultVm]);

  useEffect(() => {
    if (!resultVm) {
      return;
    }
    setGender((current) => {
      const nextGender = resultVm.summary.query_context.gender;
      if (!nextGender) {
        return current;
      }
      if (nextGender === "neutral" && current !== "neutral") {
        return current;
      }
      return nextGender;
    });
    setOccasionText((current) => resultVm.summary.query_context.occasion_text || current);
    setTargetDate((current) => resultVm.summary.query_context.target_date || current);
  }, [resultVm]);

  const runtimeHealthQuery = useQuery<RuntimeHealth>({
    queryKey: ["runtime-health", locale],
    queryFn: () => fetchRuntimeHealth(locale),
    staleTime: 60_000,
  });

  const examplesQuery = useQuery<ExamplesResponse>({
    queryKey: ["examples"],
    queryFn: fetchExamples,
    staleTime: Infinity,
  });

  const historyQuery = useQuery<HistoryItem[]>({
    queryKey: ["history"],
    queryFn: fetchHistory,
    staleTime: 10_000,
  });

  const favoritesQuery = useQuery<FavoriteLocation[]>({
    queryKey: ["favorites"],
    queryFn: fetchFavorites,
    staleTime: 10_000,
  });

  const developerSessionQuery = useQuery<DeveloperSessionState>({
    queryKey: ["developer-session"],
    queryFn: fetchDeveloperSession,
    staleTime: 5_000,
  });

  const mapSettingsQuery = useQuery<MapSettingsResponse>({
    queryKey: ["map-settings"],
    queryFn: fetchMapSettings,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (developerSessionQuery.data?.required && !developerSessionQuery.data.unlocked && viewMode === "developer") {
      setViewModeState("user");
    }
  }, [developerSessionQuery.data, viewMode]);

  const cancelActiveQueryOnServer = useCallback(() => {
    const requestId = activeQueryRequestIdRef.current;
    if (!requestId) {
      return;
    }
    activeQueryRequestIdRef.current = "";
    void cancelQuery(requestId).catch(() => undefined);
  }, []);

  const queryMutation = useMutation({
    mutationFn: (payload: Parameters<typeof postQuery>[0]) => {
      const controller = new AbortController();
      const clientRequestId = createClientRequestId();
      activeQueryAbortRef.current = controller;
      activeQueryRequestIdRef.current = clientRequestId;
      setQueryPaused(false);
      return postQuery({ ...payload, client_request_id: clientRequestId, signal: controller.signal });
    },
    onSuccess(data) {
      const normalizedResult = normalizeResultViewModel(data.view_model);
      setResultVm(normalizedResult);
      setSelectedCandidateId(normalizedResult?.clarification.recommended_candidate_id || "");
      setShowAllCandidates(false);
      setActiveAdvancedTab(normalizedResult?.clarification.needed ? "location" : "timeline");
      void queryClient.invalidateQueries({ queryKey: ["history"] });
    },
    onError(error) {
      if (!isAbortError(error)) {
        setQueryPaused(false);
        return;
      }
      setQueryPaused(true);
    },
    onSettled() {
      activeQueryAbortRef.current = null;
      activeQueryRequestIdRef.current = "";
    },
  });

  const saveFavoriteMutation = useMutation({
    mutationFn: saveFavorite,
    onSuccess() {
      void queryClient.invalidateQueries({ queryKey: ["favorites"] });
    },
  });

  const deleteFavoriteMutation = useMutation({
    mutationFn: deleteFavorite,
    onSuccess() {
      void queryClient.invalidateQueries({ queryKey: ["favorites"] });
    },
  });

  const unlockDeveloperMutation = useMutation({
    mutationFn: unlockDeveloperSession,
    onSuccess() {
      void queryClient.invalidateQueries({ queryKey: ["developer-session"] });
    },
  });

  const lockDeveloperMutation = useMutation({
    mutationFn: lockDeveloperSession,
    onSuccess() {
      void queryClient.invalidateQueries({ queryKey: ["developer-session"] });
    },
  });

  const progressState = useQueryProgress({
    isPending: queryMutation.isPending,
    isError: Boolean(queryMutation.error) && !isAbortError(queryMutation.error),
    isPaused: queryPaused,
    resultVm,
    requestKind,
  });

  const historyItems = historyQuery.data || [];
  const favorites = favoritesQuery.data || [];
  const recentQueries = useMemo(() => {
    const seen = new Set<string>();
    const next: string[] = [];
    for (const item of historyItems) {
      const value = item.query_text.trim();
      if (!value || seen.has(value)) {
        continue;
      }
      seen.add(value);
      next.push(value);
      if (next.length >= 8) {
        break;
      }
    }
    return next;
  }, [historyItems]);

  const setLocale = useCallback((value: LocaleCode) => {
    localeRef.current = value;
    setLocaleState(value);
  }, []);

  const setViewMode = useCallback((value: ViewMode) => {
    setViewModeState(value);
  }, []);

  const setConfirmationMode = useCallback((value: ConfirmationMode) => {
    setConfirmationModeState(value);
  }, []);

  const rerunResultForLocale = useCallback(
    (targetLocale: LocaleCode) => {
      if (!resultVm || queryMutation.isPending) {
        return;
      }

      const confirmation = normalizeConfirmationMode(resultVm.summary.confirmation_mode);
      const selectedCoords =
        resultVm.summary.location_source === "map_pin" &&
        resultVm.location_pin.lat != null &&
        resultVm.location_pin.lon != null
          ? { lat: resultVm.location_pin.lat, lon: resultVm.location_pin.lon }
          : undefined;

      if (selectedCoords) {
        queryMutation.mutate({
          query_text: resultVm.summary.user_input || "",
          confirmation_mode: confirmation,
          selected_coords: selectedCoords,
          gender: resultVm.summary.query_context.gender,
          occasion_text: resultVm.summary.query_context.occasion_text,
          target_date: resultVm.summary.query_context.target_date,
          locale: targetLocale,
        });
        return;
      }

      const baseQuery = (resultVm.summary.user_input || queryText).trim();
      if (!baseQuery) {
        return;
      }

      queryMutation.mutate({
        query_text: baseQuery,
        confirmation_mode: confirmation,
        gender: resultVm.summary.query_context.gender,
        occasion_text: resultVm.summary.query_context.occasion_text,
        target_date: resultVm.summary.query_context.target_date,
        locale: targetLocale,
      });
    },
    [queryMutation, queryText, resultVm],
  );

  useEffect(() => {
    if (!resultVm || queryMutation.isPending) {
      return;
    }

    const resultLocale = resultVm.summary.locale;
    if (!resultLocale || resultLocale === locale) {
      localeRefreshAttemptRef.current = "";
      return;
    }

    const refreshKey = buildLocaleNormalizationSignature(resultVm, locale);
    if (localeRefreshAttemptRef.current === refreshKey) {
      return;
    }

    localeRefreshAttemptRef.current = refreshKey;
    rerunResultForLocale(locale);
  }, [locale, queryMutation.isPending, rerunResultForLocale, resultVm]);

  const clearWorkspace = useCallback(() => {
    cancelActiveQueryOnServer();
    activeQueryAbortRef.current?.abort();
    activeQueryAbortRef.current = null;
    setQueryPaused(false);
    setQueryText("");
    setGender("neutral");
    setOccasionText("");
    setTargetDate(toDateInputValue(new Date()));
    setDraftCoords(null);
    setResultVm(null);
    setSelectedCandidateId("");
    setShowAllCandidates(false);
    setActiveAdvancedTab("location");
  }, [cancelActiveQueryOnServer]);

  const submitTextQuery = useCallback(
    (query?: string, mode?: ConfirmationMode) => {
      const finalQuery = (query ?? queryText).trim();
      if (!finalQuery) {
        return;
      }
      setQueryPaused(false);
      setRequestKind("text");
      queryMutation.mutate({
        query_text: finalQuery,
        confirmation_mode: mode ?? confirmationMode,
        gender,
        occasion_text: occasionText.trim(),
        target_date: targetDate,
        locale: localeRef.current,
      });
    },
    [confirmationMode, gender, occasionText, queryMutation, queryText, targetDate],
  );

  const submitMapQuery = useCallback(
    (coords?: QueryCoords | null, mode?: ConfirmationMode) => {
      const finalCoords = coords ?? draftCoords;
      if (!finalCoords) {
        return;
      }
      setQueryPaused(false);
      setRequestKind("map");
      queryMutation.mutate({
        query_text: "",
        confirmation_mode: mode ?? confirmationMode,
        selected_coords: finalCoords,
        gender,
        occasion_text: occasionText.trim(),
        target_date: targetDate,
        locale: localeRef.current,
      });
    },
    [confirmationMode, draftCoords, gender, occasionText, queryMutation, targetDate],
  );

  const confirmCandidate = useCallback(
    (candidateId?: string) => {
      const finalCandidateId = candidateId || selectedCandidateId;
      if (!resultVm || !finalCandidateId) {
        return;
      }
      setQueryPaused(false);
      setRequestKind("confirm");
      queryMutation.mutate({
        query_text: resultVm.summary.user_input || queryText.trim(),
        selected_candidate_id: finalCandidateId,
        confirmation_mode: confirmationMode,
        selected_coords:
          resultVm.summary.location_source === "map_pin" && resultVm.location_pin.lat != null && resultVm.location_pin.lon != null
            ? { lat: resultVm.location_pin.lat, lon: resultVm.location_pin.lon }
            : undefined,
        gender,
        occasion_text: occasionText.trim(),
        target_date: targetDate,
        locale: localeRef.current,
      });
    },
    [confirmationMode, gender, occasionText, queryMutation, queryText, resultVm, selectedCandidateId, targetDate],
  );

  const pauseActiveQuery = useCallback(() => {
    cancelActiveQueryOnServer();
    if (!activeQueryAbortRef.current) {
      return;
    }
    activeQueryAbortRef.current.abort();
    activeQueryAbortRef.current = null;
    activeQueryRequestIdRef.current = "";
    setQueryPaused(true);
    setNotice({
      tone: "info",
      message: t("query.pausedNotice"),
    });
  }, [cancelActiveQueryOnServer, t]);

  const rerunStrictSelection = useCallback(() => {
    setConfirmationModeState("strict");
    if (resultVm?.summary.location_source === "map_pin" && resultVm.location_pin.lat != null && resultVm.location_pin.lon != null) {
      submitMapQuery({ lat: resultVm.location_pin.lat, lon: resultVm.location_pin.lon }, "strict");
      return;
    }
    const baseQuery = resultVm?.summary.user_input || queryText.trim();
    if (baseQuery) {
      submitTextQuery(baseQuery, "strict");
    }
  }, [queryText, resultVm, submitMapQuery, submitTextQuery]);

  const runRecentQuery = useCallback(
    (query: string) => {
      setQueryText(query);
      submitTextQuery(query);
    },
    [submitTextQuery],
  );

  const runHistoryQuery = useCallback(
    (item: HistoryItem) => {
      const mode = normalizeConfirmationMode(item.confirmation_mode);
      setGender(item.gender || "neutral");
      setOccasionText(item.occasion_text || "");
      setTargetDate(item.target_date || toDateInputValue(new Date()));
      if (item.location_source === "map_pin" && item.selected_coords) {
        setQueryText(item.query_text || item.confirmed_location_label);
        setDraftCoords(item.selected_coords);
        submitMapQuery(item.selected_coords, mode);
        return;
      }
      const fallbackQuery = item.query_text || item.confirmed_location_label;
      setQueryText(fallbackQuery);
      submitTextQuery(fallbackQuery, mode);
    },
    [submitMapQuery, submitTextQuery],
  );

  const runFavoriteQuery = useCallback(
    (favorite: FavoriteLocation) => {
      setGender(favorite.gender || "neutral");
      setOccasionText(favorite.occasion_text || "");
      setTargetDate(favorite.target_date || toDateInputValue(new Date()));
      setQueryText(favorite.query_text);
      setDraftCoords({ lat: favorite.lat, lon: favorite.lon });
      submitMapQuery({ lat: favorite.lat, lon: favorite.lon });
    },
    [submitMapQuery],
  );

  const saveCurrentFavorite = useCallback(() => {
    const favorite = buildFavoriteFromResult(resultVm);
    if (!favorite) {
      return;
    }
    const exists = favorites.some((item) => item.id === favorite.id);
    if (exists) {
      deleteFavoriteMutation.mutate(favorite.id);
      return;
    }
    saveFavoriteMutation.mutate(favorite);
  }, [deleteFavoriteMutation, favorites, resultVm, saveFavoriteMutation]);

  const removeFavorite = useCallback(
    (id: string) => {
      deleteFavoriteMutation.mutate(id);
    },
    [deleteFavoriteMutation],
  );

  const unlockDeveloperMode = useCallback(
    async (pin: string) => {
      try {
        await unlockDeveloperMutation.mutateAsync(pin);
        setNotice(null);
        return true;
      } catch {
        setNotice({
          tone: "error",
          message: t("shell.devUnlockFailed"),
        });
        return false;
      }
    },
    [t, unlockDeveloperMutation],
  );

  const lockDeveloperMode = useCallback(async () => {
    await lockDeveloperMutation.mutateAsync();
    setViewModeState("user");
  }, [lockDeveloperMutation]);

  const currentFavorite = useMemo(() => buildFavoriteFromResult(resultVm), [resultVm]);
  const isCurrentFavorite = useMemo(
    () => Boolean(currentFavorite && favorites.some((item) => item.id === currentFavorite.id)),
    [currentFavorite, favorites],
  );
  const visibleQueryError = isAbortError(queryMutation.error) ? null : (queryMutation.error as Error | null);

  const dismissNotice = useCallback(() => setNotice(null), []);

  const value = useMemo<WeatherWearSessionValue>(
    () => ({
      locale,
      setLocale,
      viewMode,
      setViewMode,
      confirmationMode,
      setConfirmationMode,
      queryText,
      setQueryText,
      gender,
      setGender,
      occasionText,
      setOccasionText,
      targetDate,
      setTargetDate,
      draftCoords,
      setDraftCoords,
      resultVm,
      selectedCandidateId,
      setSelectedCandidateId,
      requestKind,
      showAllCandidates,
      setShowAllCandidates,
      recentQueries,
      historyItems,
      historyLoading: historyQuery.isLoading,
      favorites,
      favoritesLoading: favoritesQuery.isLoading,
      examples: examplesQuery.data?.items || [],
      runtimeHealth: runtimeHealthQuery.data,
      runtimeHealthLoading: runtimeHealthQuery.isLoading,
      runtimeHealthError: runtimeHealthQuery.error as Error | null,
      queryError: visibleQueryError,
      isPending: queryMutation.isPending,
      queryPaused,
      progressState,
      notice,
      setNotice,
      dismissNotice,
      activeAdvancedTab,
      setActiveAdvancedTab,
      developerSession: developerSessionQuery.data,
      developerSessionLoading: developerSessionQuery.isLoading || unlockDeveloperMutation.isPending || lockDeveloperMutation.isPending,
      mapSettings: mapSettingsQuery.data,
      mapSettingsLoading: mapSettingsQuery.isLoading,
      mapRuntimeDiagnostics,
      setMapRuntimeDiagnostics,
      unlockDeveloperMode,
      lockDeveloperMode,
      clearWorkspace,
      pauseActiveQuery,
      submitTextQuery,
      submitMapQuery,
      confirmCandidate,
      rerunStrictSelection,
      runRecentQuery,
      runHistoryQuery,
      runFavoriteQuery,
      saveCurrentFavorite,
      removeFavorite,
      isCurrentFavorite,
    }),
    [
      activeAdvancedTab,
      clearWorkspace,
      confirmCandidate,
      confirmationMode,
      developerSessionQuery.data,
      developerSessionQuery.isLoading,
      dismissNotice,
      draftCoords,
      examplesQuery.data?.items,
      favorites,
      favoritesQuery.isLoading,
      gender,
      historyItems,
      historyQuery.isLoading,
      isCurrentFavorite,
      locale,
      lockDeveloperMode,
      lockDeveloperMutation.isPending,
      mapSettingsQuery.data,
      mapSettingsQuery.isLoading,
      mapRuntimeDiagnostics,
      notice,
      occasionText,
      pauseActiveQuery,
      progressState,
      queryMutation.isPending,
      queryPaused,
      queryText,
      recentQueries,
      requestKind,
      rerunStrictSelection,
      resultVm,
      runFavoriteQuery,
      runHistoryQuery,
      runRecentQuery,
      runtimeHealthQuery.data,
      runtimeHealthQuery.error,
      runtimeHealthQuery.isLoading,
      saveCurrentFavorite,
      selectedCandidateId,
      setConfirmationMode,
      setLocale,
      setViewMode,
      showAllCandidates,
      submitMapQuery,
      submitTextQuery,
      targetDate,
      unlockDeveloperMode,
      unlockDeveloperMutation.isPending,
      visibleQueryError,
      viewMode,
    ],
  );

  return (
    <WeatherWearSessionContext.Provider value={value}>
      {props.children}
    </WeatherWearSessionContext.Provider>
  );
}

export function useWeatherWearSession() {
  const context = useContext(WeatherWearSessionContext);
  if (!context) {
    throw new Error("useWeatherWearSession must be used within WeatherWearSessionProvider.");
  }
  return context;
}
