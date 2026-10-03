/**
 * API client functions for communicating with FastAPI backend.
 * Gracefully falls back to client-side offline engine when hosted statically (e.g. GitHub Pages).
 */

import {
  ApprovePlanResponse,
  ConfirmTokenResponse,
  ParseQueryResponse,
  Place,
  PlaceSearchResponse,
  RecoverySearchResponse,
  SimulateDelayResponse,
  TripDetail,
} from "./types";
import {
  offlineApprovePlan,
  offlineExecuteRecoverySearch,
  offlineGetPlaceById,
  offlineGetTripDetails,
  offlineIssueToken,
  offlineParseNaturalLanguageQuery,
  offlineSearchPlaces,
  offlineSimulateDelay,
} from "./offline_engine";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });

  if (!res.ok) {
    let errorMessage = `API error ${res.status}: ${res.statusText}`;
    try {
      const errorJson = await res.json();
      if (errorJson.detail) {
        errorMessage = typeof errorJson.detail === "string" ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // Keep default message
    }
    throw new Error(errorMessage);
  }

  return res.json() as Promise<T>;
}

export async function searchPlaces(query: string = "", limit: number = 10): Promise<PlaceSearchResponse> {
  try {
    const params = new URLSearchParams({ q: query, limit: String(limit) });
    return await fetchJson<PlaceSearchResponse>(`/v1/places/search?${params.toString()}`);
  } catch (err) {
    // Offline / static fallback
    const places = offlineSearchPlaces(query, limit);
    return {
      query,
      count: places.length,
      results: places,
    };
  }
}

export async function getPlaceById(placeId: string): Promise<Place> {
  try {
    return await fetchJson<Place>(`/v1/places/${encodeURIComponent(placeId)}`);
  } catch (err) {
    const p = offlineGetPlaceById(placeId);
    if (!p) throw new Error(`Place not found: ${placeId}`);
    return p;
  }
}

export async function executeRecoverySearch(payload: {
  origin_id: string;
  destination_id: string;
  deadline: string;
  budget_paise?: number;
  departure_after?: string;
}): Promise<RecoverySearchResponse> {
  try {
    return await fetchJson<RecoverySearchResponse>("/v1/recover/search", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  } catch (err) {
    return offlineExecuteRecoverySearch(payload);
  }
}

export async function requestApprovalToken(itineraryId: string): Promise<ConfirmTokenResponse> {
  try {
    return await fetchJson<ConfirmTokenResponse>("/v1/recover/confirm-token", {
      method: "POST",
      body: JSON.stringify({ itinerary_id: itineraryId }),
    });
  } catch (err) {
    return offlineIssueToken(itineraryId);
  }
}

export async function approveRecoveryPlan(payload: {
  itinerary_id: string;
  approval_token: string;
  origin_id: string;
  destination_id: string;
  total_fare_paise: number;
  p_ontime: number;
  itinerary: any;
}): Promise<ApprovePlanResponse> {
  try {
    return await fetchJson<ApprovePlanResponse>("/v1/recover/approve", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  } catch (err) {
    return offlineApprovePlan(payload);
  }
}

export async function getTripDetails(tripId: string): Promise<TripDetail> {
  try {
    return await fetchJson<TripDetail>(`/v1/trips/${encodeURIComponent(tripId)}`);
  } catch (err) {
    const trip = offlineGetTripDetails(tripId);
    if (!trip) throw new Error(`Trip not found: ${tripId}`);
    return trip;
  }
}

export async function simulateDelay(payload: {
  trip_id: string;
  leg_index: number;
  injected_delay_minutes: number;
}): Promise<SimulateDelayResponse> {
  try {
    return await fetchJson<SimulateDelayResponse>("/v1/trip/simulate-delay", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  } catch (err) {
    return offlineSimulateDelay(payload);
  }
}

export async function parseNaturalLanguageQuery(query: string): Promise<ParseQueryResponse> {
  try {
    return await fetchJson<ParseQueryResponse>("/v1/recover/parse-query", {
      method: "POST",
      body: JSON.stringify({ query }),
    });
  } catch (err) {
    return offlineParseNaturalLanguageQuery(query);
  }
}
