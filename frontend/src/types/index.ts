/** Shared API types mirroring the backend contracts. */

export type UserRole = "admin" | "operator" | "hotel_manager";
export type HotelStatus = "active" | "inactive" | "onboarding";
export type BinType = "organic" | "non_organic" | "mixed";
export type BinStatus = "online" | "offline" | "maintenance";
export type AlertType =
  | "bin_full"
  | "bin_battery_low"
  | "bin_offline"
  | "system"
  | "custom";
export type AlertSeverity = "info" | "warning" | "critical";
export type AlertStatus = "open" | "acknowledged" | "resolved";
export type PredictionStatus = "success" | "failed";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiError {
  error: { code: string; message: string; details?: unknown };
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Hotel {
  id: string;
  name: string;
  address: string | null;
  city: string;
  country: string;
  latitude: number | null;
  longitude: number | null;
  contact_email: string | null;
  contact_phone: string | null;
  number_of_rooms: number | null;
  status: HotelStatus;
  manager_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface SmartBin {
  id: string;
  code: string;
  name: string | null;
  hotel_id: string;
  bin_type: BinType;
  status: BinStatus;
  capacity_liters: number | null;
  latitude: number | null;
  longitude: number | null;
  fill_level: number | null;
  battery_level: number | null;
  last_reading_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SensorReading {
  id: string;
  bin_id: string;
  fill_level: number;
  weight_kg: number | null;
  temperature_c: number | null;
  humidity: number | null;
  battery_level: number | null;
  recorded_at: string;
  created_at: string;
}

export interface WasteCollection {
  id: string;
  hotel_id: string;
  bin_id: string | null;
  collected_at: string;
  organic_weight_kg: number;
  non_organic_weight_kg: number;
  total_weight_kg: number;
  organic_percentage: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Prediction {
  id: string;
  collection_id: string;
  status: PredictionStatus;
  predicted_energy_kwh: number | null;
  predicted_biogas_m3: number | null;
  co2_saved_kg: number | null;
  model_version: string | null;
  error_message: string | null;
  created_at: string;
}

export interface Alert {
  id: string;
  hotel_id: string | null;
  bin_id: string | null;
  type: AlertType;
  severity: AlertSeverity;
  status: AlertStatus;
  title: string;
  message: string | null;
  context: Record<string, unknown> | null;
  acknowledged_by: string | null;
  acknowledged_at: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SystemStatus {
  ai: string;
  mqtt: string;
  websocket: string;
  websocket_connections: number;
}

export interface HotelCreate {
  name: string;
  address?: string | null;
  city: string;
  country?: string;
  latitude?: number | null;
  longitude?: number | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  number_of_rooms?: number | null;
  status?: HotelStatus;
  manager_id?: string | null;
}
export type HotelUpdate = Partial<HotelCreate>;

export interface SmartBinCreate {
  code: string;
  name?: string | null;
  hotel_id: string;
  bin_type?: BinType;
  status?: BinStatus;
  capacity_liters?: number | null;
  latitude?: number | null;
  longitude?: number | null;
}
export type SmartBinUpdate = Partial<SmartBinCreate>;

export interface WasteCollectionCreate {
  hotel_id: string;
  bin_id?: string | null;
  collected_at?: string | null;
  organic_weight_kg: number;
  non_organic_weight_kg: number;
  notes?: string | null;
}
export type WasteCollectionUpdate = Partial<Omit<WasteCollectionCreate, "hotel_id">>;

export interface AlertCreate {
  hotel_id?: string | null;
  bin_id?: string | null;
  type?: AlertType;
  severity?: AlertSeverity;
  title: string;
  message?: string | null;
}

export interface BinReadingEvent {
  type: "bin.reading";
  data: {
    bin_id: string;
    code: string;
    hotel_id: string;
    status: BinStatus;
    fill_level: number;
    battery_level: number | null;
    temperature_c: number | null;
    humidity: number | null;
    weight_kg: number | null;
    recorded_at: string | null;
  };
}

export interface AlertEvent {
  type: "alert";
  data: {
    id: string;
    hotel_id: string | null;
    bin_id: string | null;
    alert_type: AlertType;
    severity: AlertSeverity;
    status: AlertStatus;
    title: string;
    message: string | null;
    created_at: string | null;
  };
}

export interface ConnectionAckEvent {
  type: "connection.ack";
}

export type RealtimeEvent = BinReadingEvent | AlertEvent | ConnectionAckEvent;

export interface WasteDistribution {
  organic_kg: number;
  non_organic_kg: number;
  total_kg: number;
  organic_percentage: number | null;
}

export interface TimeseriesBucket {
  bucket: string;
  count: number;
  organic_kg: number;
  non_organic_kg: number;
  total_kg: number;
}

export type TimeseriesGranularity = "day" | "month";

export interface DashboardStats {
  today_collections: number;
  organic_waste_kg: number;
  non_organic_waste_kg: number;
  total_waste_kg: number;
  predicted_energy_kwh: number;
  predicted_biogas_m3: number;
  co2_saved_kg: number;
  hotels_connected: number;
  total_bins: number;
  online_bins: number;
  open_alerts: number;
  system: SystemStatus;
}

// --------------------------------------------------------------------------- //
// Collection Requests — the core product workflow. Mirrors the backend
// `requests` feature (features/requests/schemas.py + state_machine.py).
// --------------------------------------------------------------------------- //
export type RequestStatus =
  | "pending"
  | "ai_failed"
  | "accepted"
  | "rejected"
  | "on_the_way"
  | "collected"
  | "completed";

export type RequestAIStatus = "pending" | "success" | "failed";

export interface RequestPhoto {
  id: string;
  storage_path: string;
  content_type: string | null;
  size_bytes: number | null;
  created_at: string;
}

export interface CollectionRequest {
  id: string;
  hotel_id: string;
  status: RequestStatus;

  declared_weight_kg: number;
  collected_weight_kg: number | null;
  distance_to_plant_km: number | null;

  ai_status: RequestAIStatus;
  ai_quality_score: number | null;
  ai_organic_purity: number | null;
  ai_contamination: number | null;
  ai_estimated_methane_m3: number | null;
  ai_estimated_energy_kwh: number | null;
  ai_estimated_co2_kg: number | null;
  ai_priority_score: number | null;
  ai_confidence: number | null;
  ai_model_version: string | null;
  ai_error: string | null;

  decided_by: string | null;
  decided_at: string | null;
  rejection_reason: string | null;
  operator_notes: string | null;
  completed_at: string | null;

  photos: RequestPhoto[];

  created_at: string;
  updated_at: string;
}

export interface CollectionRequestCreate {
  declared_weight_kg: number;
}

export interface RequestDecision {
  accept: boolean;
  rejection_reason?: string | null;
  notes?: string | null;
}

export interface RequestTransition {
  target: RequestStatus;
  collected_weight_kg?: number | null;
  notes?: string | null;
}

// ---- Request-centric analytics (dashboard) ----
export interface RequestStats {
  total_requests: number;
  status_counts: Record<RequestStatus, number>;
  declared_weight_kg: number;
  collected_weight_kg: number;
  estimated_methane_m3: number;
  estimated_energy_kwh: number;
  estimated_co2_kg: number;
  avg_quality_score: number | null;
  acceptance_rate: number | null;
}

export interface HotelRankingRow {
  hotel_id: string;
  hotel_name: string;
  request_count: number;
  total_weight_kg: number;
  total_methane_m3: number;
  avg_quality_score: number | null;
}

export interface OperatorRankingRow {
  operator_id: string;
  operator_name: string;
  handled_count: number;
  completed_count: number;
}

export interface RequestTimeseriesBucket {
  bucket: string;
  count: number;
  declared_weight_kg: number;
  estimated_methane_m3: number;
}
