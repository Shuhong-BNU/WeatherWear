export type LocaleCode = "zh-CN" | "en-US";
export type ConfirmationMode = "smart" | "strict";
export type ViewMode = "user" | "developer";
export type RequestKind = "text" | "map" | "confirm";
export type AdvancedTab = "location" | "timeline" | "debug";
export type MapProvider = "osm" | "baidu";
export type GenderMode = "male" | "female" | "neutral";

export interface QueryCoords {
  lat: number;
  lon: number;
}

export interface LocationPin {
  lat: number | null;
  lon: number | null;
  label: string;
  source: string;
  confirmed: boolean;
  zoom_hint: number;
}

export interface ClarificationOption {
  candidate_id: string;
  label: string;
  confidence: number;
  source: string;
  coords: string;
  reason: string;
  recommended: boolean;
}

export interface TimelineStep {
  id: string;
  title: string;
  role: string;
  status: "success" | "error";
  elapsed_ms: number;
  cumulative_ms: number;
  step_kind: string;
  used_llm: boolean;
  fallback_used: boolean;
  provider: string;
  model: string;
  decision_reason: string;
  input_summary: string;
  output_summary: string;
  metadata: Record<string, unknown>;
  error: string;
}

export interface WeatherMetric {
  key: string;
  label: string;
  value: string;
  icon: string;
  tone: string;
  subvalue_left?: string;
  subvalue_right?: string;
}

export interface FashionSection {
  key: string;
  title: string;
  content: string;
}

export interface Badge {
  key: string;
  label: string;
  value: string;
}

export interface KnowledgeBasisItem {
  id: string;
  label: string;
  short_reason: string;
}

export interface KnowledgeBasisViewModel {
  status: "matched" | "merged" | "no_match";
  summary: string;
  items: KnowledgeBasisItem[];
}

export interface MapRuntimeDiagnostics {
  provider: MapProvider;
  scriptRequested: boolean;
  scriptLoaded: boolean;
  readyResolved: boolean;
  hasBMapGL: boolean;
  mapCreated: boolean;
  center: QueryCoords | null;
  errorMessage: string;
}

export interface ResultViewModel {
  summary: {
    request_id: string;
    user_input: string;
    plan_intent?: string;
    plan_location?: string;
    selected_city: string;
    resolution_status: string;
    resolution_final_status?: string;
    cached_resolution_status?: string;
    resolution_confidence: number;
    message: string;
    error: string;
    used_fast_path: boolean;
    graph_runtime: string;
    total_elapsed_ms: number;
    requested_at: string;
    completed_at: string;
    models_used: string[];
    confirmation_mode: ConfirmationMode;
    location_source: string;
    location_source_label: string;
    selected_coords?: QueryCoords;
    timezone_label: string;
    confirmed_location_label: string;
    locale?: LocaleCode;
    retrieval_mode?: "hybrid" | "rules_only";
    vector_leg_status?: string;
    vector_leg_skipped_reason?: string;
    fashion_generation_mode?: string;
    query_context: {
      gender: GenderMode;
      occasion_text: string;
      occasion_tags: string[];
      primary_scene?: string;
      context_tags?: string[];
      target_date: string;
      forecast_mode: "current" | "forecast_day";
    };
  };
  hero_summary: {
    title: string;
    condition: string;
    condition_emoji: string;
    temperature: string;
    feels_like: string;
    daily_range_text: string;
    advice_label: string;
    one_line_advice: string;
    status_message: string;
    query_path: string;
  };
  weather: {
    ok: boolean;
    city: string;
    coords: string;
    temperature: string;
    feels_like: string;
    temp_min: string;
    temp_max: string;
    daily_range_text: string;
    description: string;
    humidity: string;
    wind: string;
    source: string;
    data_mode: string;
    observed_at: string;
    observed_at_local: string;
    city_local_time: string;
    timezone_label: string;
    request_elapsed_ms: number;
    error: string;
    forecast_date: string;
    forecast_mode: "current" | "forecast_day";
  };
  weather_metrics: WeatherMetric[];
  fashion: {
    text: string;
    headline_advice: string;
    time_of_day_advice: string;
    layering_advice: string;
    bottomwear_advice: string;
    shoes_accessories_advice: string;
    notes_advice: string;
    source: string;
    used_llm: boolean;
    error: string;
  };
  fashion_sections: FashionSection[];
  knowledge_basis: KnowledgeBasisViewModel;
  decision_factors: string[];
  explanation_reasons: string[];
  bottomwear_section: {
    title: string;
    content: string;
  };
  location_pin: LocationPin;
  clarification: {
    needed: boolean;
    message: string;
    recommended_candidate_id: string;
    recommended_label?: string;
    current_selection_label?: string;
    options: ClarificationOption[];
  };
  clarification_panel: {
    title?: string;
    subtitle?: string;
    current_selection_label?: string;
    recommended_candidate_id?: string;
    options?: ClarificationOption[];
  };
  timeline_steps: TimelineStep[];
  trace: Array<Record<string, unknown>>;
  warnings: string[];
  badges: Badge[];
  recent_queries: string[];
  dependency_status: Record<string, unknown>;
  metrics_snapshot: Record<string, number>;
  debug_sections: Record<string, unknown>;
}

export interface QueryResponse {
  ok: boolean;
  view_model: ResultViewModel;
}

export interface ExamplesResponse {
  items: Array<{
    label: string;
    query_text: string;
  }>;
}

export interface ProgressStep {
  label: string;
  state: "complete" | "current" | "upcoming";
}

export interface QueryProgressState {
  visible: boolean;
  title: string;
  detail: string;
  tone: "idle" | "running" | "success" | "warning" | "error" | "paused";
  progress: number;
  elapsedSeconds: number;
  steps: ProgressStep[];
}

export interface FavoriteLocation {
  id: string;
  label: string;
  lat: number;
  lon: number;
  source: string;
  query_text: string;
  gender: GenderMode;
  occasion_text: string;
  target_date: string;
  added_at: string;
}

export interface HistoryItem {
  id: string;
  created_at: string;
  request_id: string;
  locale: LocaleCode;
  query_text: string;
  gender: GenderMode;
  occasion_text: string;
  target_date: string;
  confirmed_location_label: string;
  location_source: string;
  confirmation_mode: string;
  query_path: string;
  headline_advice: string;
  weather_summary: string;
  selected_coords?: QueryCoords | null;
}

export interface ModelProviderDraft {
  provider?: string | null;
  name?: string | null;
  base_url?: string | null;
  model?: string | null;
  proxy_url?: string | null;
  temperature?: number | null;
  timeout_seconds?: number | null;
  api_key?: string | null;
}

export interface ModelProviderPublic {
  name: string;
  provider: string;
  base_url: string;
  model: string;
  proxy_url: string;
  temperature: number;
  timeout_seconds: number;
  enabled: boolean;
  missing_fields: string[];
  has_api_key: boolean;
}

export interface ModelSettingsResponse {
  default_provider: "default" | "alternate";
  active_provider: "default" | "alternate";
  providers: Record<"default" | "alternate", ModelProviderPublic>;
  embedding: {
    enabled: boolean;
    inherit_from_chat_provider: boolean;
    provider: string;
    base_url: string;
    model: string;
    proxy_url: string;
    runtime_provider: string;
    runtime_base_url: string;
    runtime_proxy_url: string;
    timeout_seconds: number;
    missing_fields: string[];
    has_api_key: boolean;
    embedding_fingerprint: string;
    health: {
      status?: string;
      provider?: string;
      model?: string;
      dimensions?: number;
      index_compatible?: boolean | null;
      latency_ms?: number;
      degrade_reason?: string;
      last_checked_at?: string;
      [key: string]: unknown;
    };
  };
}

export interface ModelSettingsUpdatePayload {
  slot: "default" | "alternate";
  provider: ModelProviderDraft;
  embedding?: {
    enabled?: boolean | null;
    inherit_from_chat_provider?: boolean | null;
    provider?: string | null;
    base_url?: string | null;
    model?: string | null;
    proxy_url?: string | null;
    timeout_seconds?: number | null;
    api_key?: string | null;
  } | null;
  clear_api_key?: boolean;
  clear_embedding_api_key?: boolean;
  default_provider?: "default" | "alternate";
}

export interface ModelConnectionTestPayload {
  slot: "default" | "alternate";
  provider?: ModelProviderDraft;
  embedding?: {
    enabled?: boolean | null;
    inherit_from_chat_provider?: boolean | null;
    provider?: string | null;
    base_url?: string | null;
    model?: string | null;
    proxy_url?: string | null;
    timeout_seconds?: number | null;
    api_key?: string | null;
  } | null;
}

export interface ModelConnectionTestResponse {
  ok: boolean;
  message: string;
  provider: string;
  model: string;
  latency_ms: number;
  dimensions: number;
  index_compatible: boolean | null;
  degrade_reason: string;
  embedding_fingerprint: string;
}

export interface DeveloperSessionState {
  required: boolean;
  unlocked: boolean;
}

export interface MapSettingsResponse {
  provider: MapProvider;
  baidu_ak: string;
  baidu_ak_configured: boolean;
  osm_tile_url: string;
  osm_attribution: string;
  default_center_lat: number;
  default_center_lon: number;
  default_zoom: number;
}

export interface MapSettingsUpdatePayload {
  provider: MapProvider;
  baidu_ak?: string | null;
  osm_tile_url?: string | null;
  osm_attribution?: string | null;
  default_center_lat?: number | null;
  default_center_lon?: number | null;
  default_zoom?: number | null;
}

export interface MapSettingsTestResponse {
  ok: boolean;
  message: string;
  provider: MapProvider;
}

export interface LogSource {
  source: string;
  label: string;
  kind: string;
  size_bytes: number;
  updated_at: string;
}

export interface LogTailResponse {
  source: string;
  kind: string;
  lines: string[];
  events: Array<Record<string, unknown>>;
}

export interface RuntimeModuleStatus {
  available?: boolean;
  version?: string;
  error?: string;
}

export interface RuntimeHealth {
  python_version?: string;
  platform?: string;
  llm_configured?: boolean;
  llm_model?: string;
  llm_provider?: string;
  missing_llm_fields?: string[];
  openweather_configured?: boolean;
  embedding_health?: {
    status?: string;
    provider?: string;
    model?: string;
    dimensions?: number;
    index_compatible?: boolean | null;
    latency_ms?: number;
    degrade_reason?: string;
    last_checked_at?: string;
    [key: string]: unknown;
  };
  embedding_index?: {
    backend?: string;
    knowledge_version?: string;
    index_compatible?: boolean | null;
    embedding_provider?: string;
    embedding_model?: string;
    embedding_dim?: number | null;
    embedding_fingerprint?: string;
    [key: string]: unknown;
  };
  suggestions?: string[];
  modules?: Record<string, RuntimeModuleStatus>;
  web_stack?: {
    compatible?: boolean;
    issues?: string[];
    recommended?: Record<string, string>;
  };
  [key: string]: unknown;
}
