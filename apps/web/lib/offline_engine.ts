/**
 * SANKALP Client-Side Deterministic Engine (Offline / Static GitHub Pages Mode).
 * 
 * Enables the complete interactive web app to run statically on GitHub Pages (github.io)
 * without requiring a live Python backend to be active on the recruiter's machine.
 */

import stationsData from "./stations.json";
import {
  ApprovePlanResponse,
  ConfirmTokenResponse,
  Leg,
  ParseQueryResponse,
  Place,
  RecoverySearchResponse,
  ScoredItinerary,
  SimulateDelayResponse,
  TripDetail,
} from "./types";

const STATIONS: Place[] = (stationsData as any[]).map((s) => ({
  id: s.id,
  name: s.name,
  code: s.code,
  place_type: s.type as any,
  city: s.city,
  state: s.state,
  latitude: s.lat,
  longitude: s.lon,
  tier: s.tier || 1,
  aliases: s.aliases || [],
}));

export function offlineSearchPlaces(query: string = "", limit: number = 10): Place[] {
  const q = query.trim().toLowerCase();
  if (!q) {
    // Return major metro stations first
    return STATIONS.slice(0, limit);
  }
  return STATIONS.filter(
    (p) =>
      p.code.toLowerCase().includes(q) ||
      p.name.toLowerCase().includes(q) ||
      p.city.toLowerCase().includes(q) ||
      p.aliases.some((a) => a.toLowerCase().includes(q))
  ).slice(0, limit);
}

export function offlineGetPlaceById(placeId: string): Place | null {
  const norm = placeId.trim().toUpperCase();
  return STATIONS.find((p) => p.id === placeId || p.code.toUpperCase() === norm) || null;
}

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371.0;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c);
}

export function offlineExecuteRecoverySearch(payload: {
  origin_id: string;
  destination_id: string;
  deadline: string;
  budget_paise?: number;
}): RecoverySearchResponse {
  const orig = offlineGetPlaceById(payload.origin_id) || STATIONS[0];
  const dest = offlineGetPlaceById(payload.destination_id) || STATIONS[1];
  const dist = Math.max(120, haversineKm(orig.latitude, orig.longitude, dest.latitude, dest.longitude));
  const now = new Date();

  // Safest: High buffer Superfast Rail or Direct Flight
  const safestDep = new Date(now.getTime() + 90 * 60 * 1000);
  const safestDur = Math.round(dist / 1.1) + 40; // minutes
  const safestArr = new Date(safestDep.getTime() + safestDur * 60 * 1000);
  const safestFarePaise = Math.round(dist * 165);

  const safestLeg: Leg = {
    leg_id: `leg_sf_${orig.code}_${dest.code}`,
    origin_id: orig.id,
    destination_id: dest.id,
    mode: dist > 600 ? "FLIGHT" : "TRAIN",
    departure_time: safestDep.toISOString(),
    arrival_time: safestArr.toISOString(),
    duration_minutes: safestDur,
    distance_km: dist,
    fare_paise: safestFarePaise,
    fare_inr: Math.round(safestFarePaise / 100),
    operator_name: dist > 600 ? "Vistara Air Feeder" : "Vande Bharat Superfast",
    identifier: dist > 600 ? "UK-821" : "22436",
    is_simulated: true,
  };

  const safestItin: ScoredItinerary = {
    itinerary_id: `itin_safest_${Date.now()}`,
    tag: "SAFEST",
    plain_reason: `Highest arrival certainty via ${safestLeg.operator_name} with conservative safety buffer.`,
    total_duration_minutes: safestDur,
    total_fare_paise: safestFarePaise,
    total_fare_inr: Math.round(safestFarePaise / 100),
    departure_time: safestDep.toISOString(),
    arrival_time: safestArr.toISOString(),
    num_transfers: 0,
    is_multimodal: false,
    buffer_minutes: 75,
    utility_score: 0.94,
    legs: [safestLeg],
    transfers: [],
    metrics: {
      p_ontime: 0.994,
      p_ontime_ci_95: [0.991, 0.997],
      trials_count: 10000,
      median_delay_minutes: 8,
      p90_delay_minutes: 18,
      missed_connection_rate: 0.0,
    },
  };

  // Balanced: Express Rail + Bus transfer or direct Express
  const balDep = new Date(now.getTime() + 120 * 60 * 1000);
  const balDur = Math.round(dist * 1.15) + 30;
  const balArr = new Date(balDep.getTime() + balDur * 60 * 1000);
  const balFarePaise = Math.round(dist * 115);

  const balLeg: Leg = {
    leg_id: `leg_bal_${orig.code}_${dest.code}`,
    origin_id: orig.id,
    destination_id: dest.id,
    mode: "TRAIN",
    departure_time: balDep.toISOString(),
    arrival_time: balArr.toISOString(),
    duration_minutes: balDur,
    distance_km: dist,
    fare_paise: balFarePaise,
    fare_inr: Math.round(balFarePaise / 100),
    operator_name: "Intercity Superfast Express",
    identifier: "12952",
    is_simulated: true,
  };

  const balancedItin: ScoredItinerary = {
    itinerary_id: `itin_bal_${Date.now()}`,
    tag: "BALANCED",
    plain_reason: "Optimal trade-off balancing expenditure, travel duration, and on-time certainty.",
    total_duration_minutes: balDur,
    total_fare_paise: balFarePaise,
    total_fare_inr: Math.round(balFarePaise / 100),
    departure_time: balDep.toISOString(),
    arrival_time: balArr.toISOString(),
    num_transfers: 0,
    is_multimodal: false,
    buffer_minutes: 45,
    utility_score: 0.88,
    legs: [balLeg],
    transfers: [],
    metrics: {
      p_ontime: 0.965,
      p_ontime_ci_95: [0.961, 0.969],
      trials_count: 10000,
      median_delay_minutes: 14,
      p90_delay_minutes: 26,
      missed_connection_rate: 0.0,
    },
  };

  // Cheapest: Overnight AC Sleeper Bus or Mail/Express Rail
  const chpDep = new Date(now.getTime() + 150 * 60 * 1000);
  const chpDur = Math.round(dist * 1.45) + 60;
  const chpArr = new Date(chpDep.getTime() + chpDur * 60 * 1000);
  const chpFarePaise = Math.round(dist * 75);

  const chpLeg: Leg = {
    leg_id: `leg_chp_${orig.code}_${dest.code}`,
    origin_id: orig.id,
    destination_id: dest.id,
    mode: "BUS",
    departure_time: chpDep.toISOString(),
    arrival_time: chpArr.toISOString(),
    duration_minutes: chpDur,
    distance_km: dist,
    fare_paise: chpFarePaise,
    fare_inr: Math.round(chpFarePaise / 100),
    operator_name: "Volvo Multi-Axle Intercity",
    identifier: "EXP-702",
    is_simulated: true,
  };

  const cheapestItin: ScoredItinerary = {
    itinerary_id: `itin_chp_${Date.now()}`,
    tag: "CHEAPEST",
    plain_reason: "Economical multi-modal path maximizing rupee efficiency while meeting deadline.",
    total_duration_minutes: chpDur,
    total_fare_paise: chpFarePaise,
    total_fare_inr: Math.round(chpFarePaise / 100),
    departure_time: chpDep.toISOString(),
    arrival_time: chpArr.toISOString(),
    num_transfers: 0,
    is_multimodal: false,
    buffer_minutes: 30,
    utility_score: 0.79,
    legs: [chpLeg],
    transfers: [],
    metrics: {
      p_ontime: 0.925,
      p_ontime_ci_95: [0.919, 0.931],
      trials_count: 10000,
      median_delay_minutes: 22,
      p90_delay_minutes: 42,
      missed_connection_rate: 0.0,
    },
  };

  return {
    search_id: `sch_offline_${Date.now()}`,
    origin: orig as any,
    destination: dest as any,
    deadline: payload.deadline,
    budget_paise: payload.budget_paise || 500000,
    budget_inr: Math.round((payload.budget_paise || 500000) / 100),
    total_candidates_searched: 18,
    execution_time_ms: 28.4,
    data_disclaimer: "Simulated schedules based on static network data. Running in client-side demo mode.",
    recommendations: {
      safest: safestItin,
      balanced: balancedItin,
      cheapest: cheapestItin,
    },
    pruned_candidates: [
      {
        itinerary_summary: `Express via Central Hub (3 Transfers)`,
        code: "EXCESSIVE_TRANSFERS",
        reason_text: "Violates maximum transfer threshold (> 2 transfers).",
      },
      {
        itinerary_summary: `Direct Feeder (Late Departure)`,
        code: "MISSED_DEADLINE",
        reason_text: "Arrival exceeds passenger deadline constraint.",
      },
    ],
  };
}

export function offlineIssueToken(itineraryId: string): ConfirmTokenResponse {
  const token = `tok_demo_${Math.random().toString(36).substring(2)}${Math.random().toString(36).substring(2)}`;
  return {
    itinerary_id: itineraryId,
    approval_token: token,
    expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
    ttl_seconds: 900,
  };
}

export function offlineApprovePlan(payload: {
  itinerary_id: string;
  approval_token: string;
  origin_id: string;
  destination_id: string;
  total_fare_paise: number;
  p_ontime: number;
  itinerary: any;
}): ApprovePlanResponse {
  // Check if token was used
  const usedTokens = JSON.parse(localStorage.getItem("sankalp_used_tokens") || "[]");
  if (usedTokens.includes(payload.approval_token)) {
    throw new Error(
      "Approval token is invalid, expired, or has already been used. Each approval token can only be redeemed once."
    );
  }
  usedTokens.push(payload.approval_token);
  localStorage.setItem("sankalp_used_tokens", JSON.stringify(usedTokens));

  const tripId = `trip_${Date.now()}`;
  const tripData: TripDetail = {
    trip_id: tripId,
    approval_token: payload.approval_token,
    itinerary_id: payload.itinerary_id,
    origin_id: payload.origin_id,
    destination_id: payload.destination_id,
    action: "APPROVED",
    total_fare_paise: payload.total_fare_paise,
    total_fare_inr: Math.round(payload.total_fare_paise / 100),
    p_ontime: payload.p_ontime,
    created_at: new Date().toISOString(),
    itinerary: payload.itinerary,
  };
  localStorage.setItem(`sankalp_trip_${tripId}`, JSON.stringify(tripData));

  return {
    status: "APPROVED",
    trip_id: tripId,
    itinerary_id: payload.itinerary_id,
    approved_at: new Date().toISOString(),
  };
}

export function offlineGetTripDetails(tripId: string): TripDetail | null {
  const item = localStorage.getItem(`sankalp_trip_${tripId}`);
  if (item) {
    try {
      return JSON.parse(item);
    } catch {
      return null;
    }
  }
  return null;
}

export function offlineSimulateDelay(payload: {
  trip_id: string;
  leg_index: number;
  injected_delay_minutes: number;
}): SimulateDelayResponse {
  const trip = offlineGetTripDetails(payload.trip_id);
  const origP = trip ? trip.p_ontime : 0.95;
  const isAtRisk = payload.injected_delay_minutes >= 45;
  const recalcP = Math.max(0.22, origP - (payload.injected_delay_minutes / 180) * 0.7);

  let replacementPlan: ScoredItinerary | null = null;
  if (isAtRisk) {
    const dest = STATIONS[1];
    replacementPlan = {
      itinerary_id: `itin_rec_${Date.now()}`,
      tag: "SAFEST",
      plain_reason: "Autonomous express bypass avoiding delayed rail corridor.",
      total_duration_minutes: 240,
      total_fare_paise: 185000,
      total_fare_inr: 1850,
      departure_time: new Date(Date.now() + 45 * 60 * 1000).toISOString(),
      arrival_time: new Date(Date.now() + 285 * 60 * 1000).toISOString(),
      num_transfers: 0,
      is_multimodal: true,
      buffer_minutes: 60,
      utility_score: 0.91,
      legs: [
        {
          leg_id: "leg_rec_1",
          origin_id: "inter_hub",
          destination_id: dest.id,
          mode: "FLIGHT",
          departure_time: new Date(Date.now() + 45 * 60 * 1000).toISOString(),
          arrival_time: new Date(Date.now() + 165 * 60 * 1000).toISOString(),
          duration_minutes: 120,
          distance_km: 500,
          fare_paise: 185000,
          fare_inr: 1850,
          operator_name: "Air India Express Feeder",
          identifier: "AI-409",
          is_simulated: true,
        },
      ],
      transfers: [],
      metrics: {
        p_ontime: 0.982,
        p_ontime_ci_95: [0.978, 0.986],
        trials_count: 10000,
        median_delay_minutes: 9,
        p90_delay_minutes: 19,
        missed_connection_rate: 0.0,
      },
    };
  }

  return {
    trip_id: payload.trip_id,
    leg_index: payload.leg_index,
    injected_delay_minutes: payload.injected_delay_minutes,
    original_p_ontime: origP,
    recalculated_metrics: {
      p_ontime: recalcP,
      p_ontime_ci_95: [Math.max(0.18, recalcP - 0.03), Math.min(1.0, recalcP + 0.03)],
      trials_count: 10000,
      median_delay_minutes: Math.round(payload.injected_delay_minutes * 0.7),
      p90_delay_minutes: Math.round(payload.injected_delay_minutes * 1.2),
      missed_connection_rate: isAtRisk ? 0.48 : 0.05,
    },
    is_deadline_at_risk: isAtRisk,
    risk_explanation: isAtRisk
      ? `ALERT: +${payload.injected_delay_minutes}m delay reduces arrival certainty to ${Math.round(recalcP * 100)}%. SANKALP has computed an instant recovery route below.`
      : `STABLE: The +${payload.injected_delay_minutes}m delay is absorbed by safety buffer. On-time arrival certainty remains ${Math.round(recalcP * 100)}%.`,
    replacement_plan: replacementPlan,
  };
}

export function offlineParseNaturalLanguageQuery(text: string): ParseQueryResponse {
  const cleaned = text.trim();
  const isCancellation = /\b(cancelled|canceled|diverted|broken)\b/i.test(cleaned);

  // 1. Extract Delay
  let injectedDelayMinutes: number | null = null;
  const delayMatch = cleaned.match(/\b(?:delayed|late|delay of)\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m)\b/i);
  if (delayMatch) {
    const qty = parseFloat(delayMatch[1]);
    const unit = delayMatch[2].toLowerCase();
    injectedDelayMinutes = unit.startsWith("h") ? qty * 60 : qty;
  }

  // 2. Extract Budget
  let budgetInr: number | null = null;
  let budgetPaise: number | null = null;
  const budgetMatch = cleaned.match(/(?:under|budget|max|within|limit of|₹|rs\.?|inr)\s*(\d+(?:,\d+)?)\s*(?:rupees|rs|inr)?\b/i) ||
                      cleaned.match(/[₹]\s*(\d+(?:,\d+)?)\b/);
  if (budgetMatch) {
    const num = parseInt(budgetMatch[1].replace(/,/g, ""), 10);
    budgetInr = num;
    budgetPaise = num * 100;
  }

  // 3. Extract Deadline
  const now = new Date();
  let deadline: string | null = null;
  const timeMatch = cleaned.match(/\b(?:by|before|reach by|arrive by)?\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b/i) ||
                    cleaned.match(/\b(?:reach by|arrive by|before)\s+(\d{1,2})(?::(\d{2}))?(?!\s*(?:hours?|hrs?|h|mins?|minutes?))\b/i);
  if (timeMatch) {
    let hour = parseInt(timeMatch[1], 10);
    const minute = timeMatch[2] ? parseInt(timeMatch[2], 10) : 0;
    const meridiem = timeMatch[3] ? timeMatch[3].toLowerCase() : null;

    if (meridiem === "pm" && hour < 12) hour += 12;
    else if (meridiem === "am" && hour === 12) hour = 0;

    const cand = new Date(now);
    cand.setHours(hour, minute, 0, 0);
    if (cand.getTime() <= now.getTime()) {
      cand.setDate(cand.getDate() + 1);
    }
    deadline = cand.toISOString();
  } else {
    deadline = new Date(now.getTime() + 18 * 60 * 60 * 1000).toISOString();
  }

  // 4. Extract Origin and Destination
  let origin: Place | null = null;
  let destination: Place | null = null;

  const routeMatch = cleaned.match(/\b(?:from|leaving|departing|at)\s+([A-Za-z\s]+?)\s+(?:to|heading to|towards|for)\s+([A-Za-z\s]+?)(?:,|\.|\s+(?:is|was|must|before|by|under|budget|delayed|due)|$)/i) ||
                     cleaned.match(/\b([A-Za-z\s]{3,25})\s+(?:to|->)\s+([A-Za-z\s]{3,25})(?:,|\.|\s+(?:is|was|must|before|by|under|budget|delayed)|$)/i);

  if (routeMatch) {
    const noiseWords = new Set(["my", "the", "train", "flight", "trip", "stuck", "in", "currently"]);
    const cleanTokens = (s: string) => s.split(/\s+/).filter(t => !noiseWords.has(t.toLowerCase())).join(" ");
    const origQuery = cleanTokens(routeMatch[1].trim());
    const destQuery = cleanTokens(routeMatch[2].trim());

    if (origQuery) {
      const candidates = offlineSearchPlaces(origQuery, 1);
      if (candidates.length > 0) origin = candidates[0];
    }
    if (destQuery) {
      const candidates = offlineSearchPlaces(destQuery, 1);
      if (candidates.length > 0) destination = candidates[0];
    }
  }

  let confidence = 0.5;
  if (origin && destination) confidence = 0.95;
  else if (origin || destination) confidence = 0.75;

  return {
    raw_query: text,
    origin,
    destination,
    deadline,
    budget_paise: budgetPaise,
    budget_inr: budgetInr,
    injected_delay_minutes: injectedDelayMinutes,
    is_cancellation: isCancellation,
    confidence_score: confidence,
    explanation: origin && destination
      ? `Identified transit corridor from ${origin.name} (${origin.code}) to ${destination.name} (${destination.code}).`
      : "Processed journey constraints. Origin or destination partially inferred.",
  };
}
