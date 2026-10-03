"""Multi-corridor benchmark suite evaluating 8 diverse Indian transit corridors.

Mandate from Section 4 & 10 of Specification:
- Evaluates the complete end-to-end decision pipeline over at least 8 varied corridors:
  (long distance, short regional, with and without airports, late-night deadlines, tight budgets).
- Records performance metrics (search time, simulation time, P(on-time), Pareto recommendations).
- Asserts median search + simulation execution time <= 500ms.
"""

import json
import statistics
import time
from datetime import datetime, timedelta
from pathlib import Path
from sankalp_engine.engine import find_journey_recovery
from sankalp_engine.generator import SeededScheduleGenerator
from sankalp_engine.models import IST, RecommendationTag

BENCHMARK_OUTPUT_PATH = Path("data/benchmark_results.json")


def test_eight_corridors_benchmark_suite() -> None:
    gen = SeededScheduleGenerator()
    base_time = datetime(2026, 10, 6, 8, 0, tzinfo=IST)

    corridors = [
        {
            "name": "1. Metro-to-Metro (Long Distance)",
            "origin": "STN_NDLS",
            "destination": "STN_CSMT",
            "departure": base_time,
            "deadline": base_time + timedelta(hours=22),
            "budget_paise": 400000,  # ₹4,000
            "type": "long_distance_metro",
        },
        {
            "name": "2. Short Regional Corridor",
            "origin": "STN_PUNE",
            "destination": "STN_CSMT",
            "departure": base_time,
            "deadline": base_time + timedelta(hours=6),
            "budget_paise": 150000,  # ₹1,500
            "type": "short_regional",
        },
        {
            "name": "3. Tier-2 to Tier-1 Rail Corridor",
            "origin": "STN_GKP",
            "destination": "STN_NDLS",
            "departure": base_time,
            "deadline": base_time + timedelta(hours=18),
            "budget_paise": 200000,  # ₹2,000
            "type": "tier2_to_tier1",
        },
        {
            "name": "4. Remote / Non-Airport Corridor",
            "origin": "STN_KLK",
            "destination": "STN_NDLS",
            "departure": base_time,
            "deadline": base_time + timedelta(hours=8),
            "budget_paise": 120000,  # ₹1,200
            "type": "remote_regional",
        },
        {
            "name": "5. Cross-Country Diagonal Corridor",
            "origin": "STN_GHY",
            "destination": "STN_SBC",
            "departure": base_time,
            "deadline": base_time + timedelta(hours=48),
            "budget_paise": 650000,  # ₹6,500
            "type": "cross_country_diagonal",
        },
        {
            "name": "6. Tight Deadline Corridor",
            "origin": "STN_LKO",
            "destination": "STN_CNB",
            "departure": base_time + timedelta(hours=10),
            "deadline": base_time + timedelta(hours=13),
            "budget_paise": 80000,  # ₹800
            "type": "tight_deadline",
        },
        {
            "name": "7. Tight Budget Corridor",
            "origin": "STN_ADI",
            "destination": "STN_ST",
            "departure": base_time,
            "deadline": base_time + timedelta(hours=7),
            "budget_paise": 30000,  # ₹300 tight budget
            "type": "tight_budget",
        },
        {
            "name": "8. Multimodal Transfer Corridor",
            "origin": "STN_BSB",
            "destination": "STN_PUNE",
            "departure": base_time,
            "deadline": base_time + timedelta(hours=32),
            "budget_paise": 350000,  # ₹3,500
            "type": "multimodal_transfer",
        },
    ]

    benchmark_records = []
    execution_times_ms = []

    print("\n--- SANKALP 8-CORRIDOR ENGINE BENCHMARK ---")
    for c in corridors:
        t_start = time.perf_counter()
        result = find_journey_recovery(
            origin_id=c["origin"],
            destination_id=c["destination"],
            departure_after=c["departure"],
            deadline=c["deadline"],
            budget_paise=c["budget_paise"],
            data_source=gen,
            trials_count=10000,
            seed=42,
        )
        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        execution_times_ms.append(t_elapsed_ms)

        # Basic validity checks
        assert result.data_disclaimer == "Simulated schedules"
        assert result.origin.id == c["origin"]
        assert result.destination.id == c["destination"]

        has_recommendations = len(result.recommendations) > 0
        safest_p = (
            result.recommendations[RecommendationTag.SAFEST].metrics.p_ontime
            if RecommendationTag.SAFEST in result.recommendations
            else 0.0
        )
        cheapest_fare = (
            result.recommendations[RecommendationTag.CHEAPEST].itinerary.total_fare_paise // 100
            if RecommendationTag.CHEAPEST in result.recommendations
            else 0
        )

        record = {
            "corridor": c["name"],
            "type": c["type"],
            "execution_time_ms": round(t_elapsed_ms, 2),
            "candidates_evaluated": result.total_candidates_searched,
            "recommendations_found": len(result.recommendations),
            "safest_p_ontime": round(safest_p, 4),
            "cheapest_fare_inr": cheapest_fare,
        }
        benchmark_records.append(record)
        print(f"[{record['corridor']}] Latency: {record['execution_time_ms']}ms | Evaluated: {record['candidates_evaluated']} | P(Safest): {safest_p*100:.1f}%")

    median_latency_ms = statistics.median(execution_times_ms)
    p90_latency_ms = sorted(execution_times_ms)[int(len(execution_times_ms) * 0.9)]
    print(f"\nMedian Latency: {median_latency_ms:.2f}ms | P90 Latency: {p90_latency_ms:.2f}ms")

    # Save benchmark records to disk for documentation reference
    BENCHMARK_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(BENCHMARK_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": datetime.now(IST).isoformat(),
                "trials_per_candidate": 10000,
                "median_latency_ms": round(median_latency_ms, 2),
                "p90_latency_ms": round(p90_latency_ms, 2),
                "corridors": benchmark_records,
            },
            f,
            indent=2,
        )

    # Invariant assertion: Median latency across the 8 varied corridors must be well under 500ms
    assert median_latency_ms < 500.0, f"Engine median latency {median_latency_ms}ms exceeds 500ms SLA"
