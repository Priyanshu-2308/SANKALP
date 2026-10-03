"""Comprehensive End-to-End Verification of SANKALP Frontend & API Services.

Simulates the full user journey:
1. Verify Next.js frontend pages (Home, Results, Confirm, Trip) return HTTP 200.
2. Place search and station autocomplete.
3. Journey recovery search yielding Pareto triad (Safest, Balanced, Cheapest).
4. Single-use cryptographic approval token issuance.
5. Atomic approval and trip creation.
6. Single-use token replay rejection (HTTP 410 Gone).
7. Active trip audit verification.
8. Real-time delay injection simulation and on-demand fallback re-planning.
"""

from datetime import datetime, timedelta, timezone
import json
import sys
import urllib.request
import urllib.error

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FRONTEND_URL = "http://localhost:3000"
BACKEND_URL = "http://127.0.0.1:8000"


def http_get(url: str) -> tuple[int, dict | str]:
    req = urllib.request.Request(url, headers={"User-Agent": "SANKALP-E2E-Tester"})
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(content)
            except Exception:
                return resp.status, content
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            return e.code, json.loads(content)
        except Exception:
            return e.code, content


def http_post(url: str, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "SANKALP-E2E-Tester"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content)
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            return e.code, json.loads(content)
        except Exception:
            return e.code, {"raw": content}


def run_e2e_verification() -> None:
    print("=" * 60)
    print("SANKALP END-TO-END FLOW VERIFICATION")
    print("=" * 60)

    # 1. Next.js Home Page
    print("\n[Step 1] Verifying Next.js Home Page (/) ...")
    status, body = http_get(f"{FRONTEND_URL}/")
    assert status == 200, f"Expected 200, got {status}"
    assert "Find your alternative route." in body, "Hero title missing from HTML"
    assert "SANKALP" in body, "Brand missing from HTML"
    print("  [OK] Next.js Home Page rendered successfully (HTTP 200)")

    # 2. Next.js Status & Disclaimer
    print("\n[Step 2] Verifying FastAPI root and health ...")
    status, body = http_get(f"{BACKEND_URL}/")
    assert status == 200
    assert body["status"] == "operational"
    assert "Simulated schedules" in body["data_disclaimer"]
    print(f"  [OK] Backend status operational with simulated data disclaimer")
    print(f"\n[Step 3] Searching stations via autocomplete ...")
    status, body = http_get(f"{BACKEND_URL}/v1/places/search?limit=5")
    assert status == 200
    assert len(body["results"]) >= 2
    orig = body["results"][0]
    dest = body["results"][1]
    print(f"  [OK] Resolved Origin: {orig['name']} ({orig['code']}) [{orig['place_type']}]")
    print(f"  [OK] Resolved Destination: {dest['name']} ({dest['code']}) [{dest['place_type']}]")

    # 4. Multi-modal Journey Recovery Search
    print("\n[Step 4] Executing multi-modal recovery search (10k Monte Carlo trials) ...")
    now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    deadline = (now + timedelta(hours=36)).isoformat()
    search_payload = {
        "origin_id": orig["id"],
        "destination_id": dest["id"],
        "departure_after": (now + timedelta(hours=1)).isoformat(),
        "deadline": deadline,
        "budget_paise": 600000,
    }
    status, search_res = http_post(f"{BACKEND_URL}/v1/recover/search", search_payload)
    assert status == 200, f"Search failed with status {status}: {search_res}"
    recs = search_res["recommendations"]
    assert len(recs) >= 1, "Expected at least 1 Pareto recommendation"
    print(f"  [OK] Search completed in {search_res['execution_time_ms']:.2f}ms")
    print(f"  [OK] Found {len(recs)} Pareto triad options:")
    for tag, itin in recs.items():
        print(f"    - [{tag.upper()}] ₹{itin['total_fare_inr']} | {itin['total_duration_minutes']}m | P(on-time): {itin['metrics']['p_ontime']*100:.1f}% | 95% CI: [{itin['metrics']['p_ontime_ci_95'][0]*100:.1f}%, {itin['metrics']['p_ontime_ci_95'][1]*100:.1f}%]")

    # Select the Safest or first available recommendation
    chosen_tag = "safest" if "safest" in recs else next(iter(recs.keys()))
    chosen_itin = recs[chosen_tag]

    # 5. Next.js Results Page Check
    print("\n[Step 5] Checking Next.js Results Page (/results) ...")
    status, body = http_get(f"{FRONTEND_URL}/results?origin_id={orig['id']}&destination_id={dest['id']}&deadline={deadline}")
    assert status == 200
    print("  [OK] Next.js Results Page rendered successfully (HTTP 200)")

    # 6. Issue Single-Use Approval Token
    print("\n[Step 6] Issuing single-use approval token ...")
    status, token_res = http_post(
        f"{BACKEND_URL}/v1/recover/confirm-token",
        {"itinerary_id": chosen_itin["itinerary_id"]},
    )
    assert status == 200
    token = token_res["approval_token"]
    assert len(token) >= 32
    assert token_res["ttl_seconds"] == 900
    print(f"  [OK] Single-use token issued: {token[:12]}... (15m TTL)")

    # 7. Next.js Confirm Page Check
    print("\n[Step 7] Checking Next.js Confirm Page (/confirm) ...")
    status, body = http_get(f"{FRONTEND_URL}/confirm?itinerary_id={chosen_itin['itinerary_id']}&token={token}")
    assert status == 200
    print("  [OK] Next.js Confirm Page rendered successfully (HTTP 200)")

    # 8. Atomically Redeem Token & Approve Trip
    print("\n[Step 8] Atomically redeeming token to approve journey ...")
    approve_payload = {
        "itinerary_id": chosen_itin["itinerary_id"],
        "approval_token": token,
        "origin_id": orig["id"],
        "destination_id": dest["id"],
        "total_fare_paise": chosen_itin["total_fare_paise"],
        "p_ontime": chosen_itin["metrics"]["p_ontime"],
        "itinerary": chosen_itin,
    }
    status, approve_res = http_post(f"{BACKEND_URL}/v1/recover/approve", approve_payload)
    assert status == 200, f"Approval failed: {approve_res}"
    trip_id = approve_res["trip_id"]
    print(f"  [OK] Journey approved atomically! Trip ID: {trip_id}")

    # 9. Single-Use Replay Attack Test
    print("\n[Step 9] Testing single-use replay protection (attempting to reuse token) ...")
    status, replay_res = http_post(f"{BACKEND_URL}/v1/recover/approve", approve_payload)
    assert status == 410, f"Expected 410 Gone, got {status}: {replay_res}"
    print(f"  [OK] Replay rejected with HTTP 410 Gone: {replay_res.get('detail')}")

    # 10. Audit Log Retrieval & Next.js Trip Page
    print("\n[Step 10] Verifying Trip Audit Log and Next.js Trip Monitor Page (/trip/[id]) ...")
    status, trip_data = http_get(f"{BACKEND_URL}/v1/trips/{trip_id}")
    assert status == 200
    assert trip_data["trip_id"] == trip_id
    assert trip_data["action"] == "APPROVED"

    status, body = http_get(f"{FRONTEND_URL}/trip/{trip_id}")
    assert status == 200
    print(f"  [OK] Next.js Trip Monitor Page /trip/{trip_id} loaded successfully (HTTP 200)")

    # 11. Interactive Disruption Simulator & Re-routing
    print("\n[Step 11] Running interactive disruption simulation (+60 min delay) ...")
    sim_payload = {
        "trip_id": trip_id,
        "leg_index": 0,
        "injected_delay_minutes": 60.0,
    }
    status, sim_res = http_post(f"{BACKEND_URL}/v1/trip/simulate-delay", sim_payload)
    assert status == 200
    print(f"  [OK] Recalculated 10,000 trials with +60m delay:")
    print(f"    - Original certainty: {sim_res['original_p_ontime']*100:.1f}%")
    print(f"    - Recalculated certainty: {sim_res['recalculated_metrics']['p_ontime']*100:.1f}%")
    print(f"    - Deadline at risk: {sim_res['is_deadline_at_risk']}")
    print(f"    - Risk explanation: {sim_res['risk_explanation']}")
    if sim_res["replacement_plan"]:
        print(f"    - Autonomous recovery alternative computed: {sim_res['replacement_plan']['tag']} (Fare: ₹{sim_res['replacement_plan']['total_fare_inr']})")

    # 12. Conversational NL Query Parser Verification
    print("\n[Step 12] Testing Natural Language Journey Query Parsing ...")
    nl_query_text = (
        f"My train from {orig['name']} to {dest['name']} was delayed by 2 hours, "
        "need to arrive before 10 PM under 2500 rupees"
    )
    status, nl_res = http_post(f"{BACKEND_URL}/v1/recover/parse-query", {"query": nl_query_text})
    assert status == 200, f"NL parse failed: {nl_res}"
    assert nl_res["origin"] is not None and nl_res["origin"]["id"] == orig["id"]
    assert nl_res["destination"] is not None and nl_res["destination"]["id"] == dest["id"]
    assert nl_res["budget_inr"] == 2500
    assert nl_res["injected_delay_minutes"] == 120.0
    print(f"  [OK] NL query successfully parsed:")
    print(f"    - Confidence: {nl_res['confidence_score']*100:.0f}%")
    print(f"    - Origin: {nl_res['origin']['name']} ({nl_res['origin']['code']})")
    print(f"    - Destination: {nl_res['destination']['name']} ({nl_res['destination']['code']})")
    print(f"    - Parsed Budget: ₹{nl_res['budget_inr']}")
    print(f"    - Explanation: {nl_res['explanation']}")

    print("\n" + "=" * 60)
    print("ALL 12 END-TO-END VERIFICATION STEPS PASSED PERFECTLY!")
    print("=" * 60)



if __name__ == "__main__":
    run_e2e_verification()
