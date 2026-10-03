/**
 * TypeScript domain and API types for SANKALP Web Client.
 * Synchronized with backend Pydantic models.
 */

export interface Place {
  id: string;
  name: string;
  code: string;
  place_type: "RAIL_STATION" | "AIRPORT" | "BUS_TERMINAL";
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  tier: number;
  aliases: string[];
}

export interface PlaceSearchResponse {
  query: string;
  count: number;
  results: Place[];
}

export interface Leg {
  leg_id: string;
  origin_id: string;
  destination_id: string;
  mode: "TRAIN" | "FLIGHT" | "BUS" | "CAB";
  departure_time: string;
  arrival_time: string;
  duration_minutes: number;
  distance_km: number;
  fare_paise: number;
  fare_inr: number;
  operator_name: string;
  identifier: string;
  is_simulated: boolean;
}

export interface Transfer {
  place_id: string;
  arrival_time: string;
  departure_time: string;
  wait_minutes: number;
  min_connection_minutes: number;
  mode_from: "TRAIN" | "FLIGHT" | "BUS" | "CAB";
  mode_to: "TRAIN" | "FLIGHT" | "BUS" | "CAB";
  is_intermodal: boolean;
}

export interface SimulationMetrics {
  p_ontime: number;
  p_ontime_ci_95: [number, number];
  trials_count: number;
  median_delay_minutes: number;
  p90_delay_minutes: number;
  missed_connection_rate: number;
}

export interface ScoredItinerary {
  itinerary_id: string;
  tag: "SAFEST" | "BALANCED" | "CHEAPEST";
  plain_reason: string;
  total_duration_minutes: number;
  total_fare_paise: number;
  total_fare_inr: number;
  departure_time: string;
  arrival_time: string;
  num_transfers: number;
  is_multimodal: boolean;
  buffer_minutes: number;
  utility_score: number;
  legs: Leg[];
  transfers: Transfer[];
  metrics: SimulationMetrics;
}

export interface PrunedCandidate {
  itinerary_summary: string;
  code: string;
  reason_text: string;
}

export interface RecoverySearchResponse {
  search_id: string;
  origin: Record<string, any>;
  destination: Record<string, any>;
  deadline: string;
  budget_paise: number;
  budget_inr: number;
  total_candidates_searched: number;
  execution_time_ms: number;
  data_disclaimer: string;
  recommendations: {
    safest?: ScoredItinerary;
    balanced?: ScoredItinerary;
    cheapest?: ScoredItinerary;
  };
  pruned_candidates: PrunedCandidate[];
}

export interface ConfirmTokenResponse {
  itinerary_id: string;
  approval_token: string;
  expires_at: string;
  ttl_seconds: number;
}

export interface ApprovePlanResponse {
  status: string;
  trip_id: string;
  itinerary_id: string;
  approved_at: string;
}

export interface TripDetail {
  trip_id: string;
  approval_token: string;
  itinerary_id: string;
  origin_id: string;
  destination_id: string;
  action: string;
  total_fare_paise: number;
  total_fare_inr: number;
  p_ontime: number;
  created_at: string;
  itinerary: any;
}

export interface SimulateDelayResponse {
  trip_id: string;
  leg_index: number;
  injected_delay_minutes: number;
  original_p_ontime: number;
  recalculated_metrics: SimulationMetrics;
  is_deadline_at_risk: boolean;
  risk_explanation: string;
  replacement_plan?: ScoredItinerary | null;
}

export interface ParseQueryResponse {
  raw_query: string;
  origin?: Place | null;
  destination?: Place | null;
  deadline?: string | null;
  budget_paise?: number | null;
  budget_inr?: number | null;
  injected_delay_minutes?: number | null;
  is_cancellation: boolean;
  confidence_score: number;
  explanation: string;
}

