"""
SANKALP: Web Server & Live Application Gateway
Zero-dependency HTTP server using Python standard library (ThreadingHTTPServer).
Serves:
1. Live Interactive SANKALP Product UI at http://localhost:8080/
2. REST APIs powering live ReAct agent, Decision Science, and Chaos Engineering.
"""
import os
import sys
import json
import socket
from datetime import datetime, timedelta
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any

from sankalp.orchestrator import SankalpOrchestrator
from sankalp.mock_data import get_base_date, STATIONS_DB, search_stations, get_station_by_code
from sankalp.models import Itinerary

PORT = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# SANKALP Runtime Engine Bootstrap
# Initialize the persistent orchestrator, triage baseline disruption,
# calibrate default constraints, and compute initial Pareto-optimal frontiers.
# ---------------------------------------------------------------------------
base_date = get_base_date()
orchestrator = SankalpOrchestrator(
    pnr="2458901234",
    cancelled_train_no="12628",
    base_date=base_date
)
orchestrator.step1_disruption_triage()
exam_time_default = (base_date + timedelta(days=1)).replace(hour=9, minute=0)
orchestrator.step2_elicit_constraints(exam_time_default, 4000.0, "Whitefield Kadugodi, Bengaluru")
orchestrator.step3_explore_and_rank_plans()


def serialize_itinerary(p: Itinerary) -> Dict[str, Any]:
    """
    Serializes an Itinerary domain model into a structured, JSON-ready payload
    for frontend rendering and external REST client consumption.
    """
    return {
        "itinerary_id": p.itinerary_id,
        "name": p.name,
        "category": p.category,
        "total_fare": p.total_fare,
        "num_transfers": p.num_transfers,
        "final_arrival_time": p.final_arrival_time.strftime("%b %d, %I:%M %p") if p.final_arrival_time else "",
        "venue_arrival_time": p.venue_arrival_time.strftime("%b %d, %I:%M %p") if p.venue_arrival_time else "",
        "venue_buffer_minutes": p.venue_buffer_minutes,
        "monte_carlo_punctuality": p.monte_carlo_punctuality,
        "confidence_interval_95": [round(p.confidence_interval_95[0], 4), round(p.confidence_interval_95[1], 4)],
        "disruption_risk": p.disruption_risk,
        "utility_score": p.utility_score,
        "is_budget_exceeded": p.is_budget_exceeded,
        "last_mile": {
            "mode": p.last_mile.mode.value if p.last_mile else "",
            "carrier_name": p.last_mile.carrier_name if p.last_mile else "",
            "from_hub": p.last_mile.from_hub if p.last_mile else "",
            "to_venue": p.last_mile.to_venue if p.last_mile else "",
            "duration_minutes": p.last_mile.duration_minutes if p.last_mile else 0,
            "fare": p.last_mile.fare if p.last_mile else 0.0,
            "fixed_rail_guarantee": p.last_mile.fixed_rail_guarantee if p.last_mile else False
        } if p.last_mile else None,
        "legs": [
            {
                "leg_id": l.leg_id,
                "mode": l.mode.value,
                "carrier_id": l.carrier_id,
                "carrier_name": l.carrier_name,
                "from_station": l.from_station,
                "to_station": l.to_station,
                "departure_time": l.departure_time.strftime("%I:%M %p"),
                "arrival_time": l.arrival_time.strftime("%I:%M %p"),
                "fare": l.fare,
                "travel_class": l.travel_class,
                "status": l.status.value,
                "historical_punctuality": l.historical_punctuality,
                "quota": l.quota.value
            }
            for l in p.legs
        ]
    }


def serialize_step(st) -> Dict[str, Any]:
    return {
        "thought": st.thought,
        "action": st.action,
        "action_input": st.action_input,
        "observation": st.observation,
        "reflexion": st.reflexion
    }


class SankalpHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Concise logging
        sys.stderr.write(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]} {args[1]}\n")

    def send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, filepath: str, content_type: str = "text/html; charset=utf-8"):
        if not os.path.exists(filepath):
            self.send_error(404, f"File {os.path.basename(filepath)} not found.")
            return
        with open(filepath, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/app", "/index.html"):
            app_html = os.path.join(BASE_DIR, "app.html")
            self.send_file(app_html)
        elif path == "/offline_bundle.js":
            bundle_js = os.path.join(BASE_DIR, "offline_bundle.js")
            self.send_file(bundle_js, "application/javascript; charset=utf-8")
        elif path == "/api/stations":
            self.send_json([
                {
                    "code": s.code,
                    "name": s.name,
                    "city": s.city,
                    "state": s.state,
                    "zone": s.zone,
                    "station_type": s.station_type,
                    "lat": s.lat,
                    "lon": s.lon
                }
                for s in STATIONS_DB
            ])
        elif path == "/api/stations/search":
            qs = parse_qs(parsed.query)
            q = qs.get("q", [""])[0]
            matches = search_stations(q, limit=10)
            self.send_json([
                {
                    "code": s.code,
                    "name": s.name,
                    "city": s.city,
                    "state": s.state,
                    "zone": s.zone,
                    "station_type": s.station_type
                }
                for s in matches
            ])
        elif path == "/api/status":
            res = {
                "pnr": orchestrator.state.user_pnr,
                "cancelled_train": orchestrator.state.cancelled_train,
                "disruption_verified": orchestrator.state.disruption_verified,
                "tdr_filed": orchestrator.state.tdr_filed,
                "refund_amount": orchestrator.state.refund_amount,
                "constraints": {
                    "origin": orchestrator.constraints.origin,
                    "destination": orchestrator.constraints.destination,
                    "exam_reporting_time": orchestrator.constraints.exam_reporting_time.strftime("%b %d, %I:%M %p"),
                    "hard_arrival_deadline": orchestrator.constraints.hard_arrival_deadline.strftime("%b %d, %I:%M %p"),
                    "budget_max": orchestrator.constraints.budget_max,
                    "exam_venue_area": orchestrator.constraints.exam_venue_area
                },
                "candidate_plans": [serialize_itinerary(p) for p in orchestrator.candidate_plans],
                "react_steps": [serialize_step(s) for s in orchestrator.agent.steps],
                "active_itinerary": serialize_itinerary(orchestrator.state.active_itinerary) if orchestrator.state.active_itinerary else None,
                "booked_pnr": orchestrator.state.booked_pnr
            }
            self.send_json(res)
        elif path == "/api/plans":
            plans = [serialize_itinerary(p) for p in orchestrator.candidate_plans]
            self.send_json({"plans": plans, "count": len(plans)})
        else:
            # Fallback to local files if present
            clean_path = path.lstrip("/")
            local_file = os.path.join(BASE_DIR, clean_path)
            if os.path.exists(local_file) and os.path.isfile(local_file):
                ctype = "text/html"
                if local_file.endswith(".css"): ctype = "text/css"
                elif local_file.endswith(".js"): ctype = "application/javascript"
                elif local_file.endswith(".json"): ctype = "application/json"
                elif local_file.endswith(".png"): ctype = "image/png"
                elif local_file.endswith(".svg"): ctype = "image/svg+xml"
                self.send_file(local_file, content_type=ctype)
            else:
                self.send_error(404, "Endpoint not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            body = {}

        if path == "/api/route":
            origin = body.get("origin", "BPL").strip()
            destination = body.get("destination", "SBC").strip()
            exam_hour = float(body.get("exam_hour", 9.0))
            budget = float(body.get("budget", 4000.0))
            venue = body.get("venue_area", "")

            h = int(exam_hour)
            m = int((exam_hour - h) * 60)
            target_time = (orchestrator.base_date + timedelta(days=1)).replace(hour=h, minute=m)

            ranked_plans = orchestrator.route_corridor(
                origin=origin,
                destination=destination,
                exam_time=target_time,
                budget=budget,
                venue_area=venue
            )

            self.send_json({
                "status": "ROUTE_DISCOVERED",
                "origin": origin,
                "destination": destination,
                "exam_reporting_time": target_time.strftime("%b %d, %I:%M %p"),
                "budget": budget,
                "plans": [serialize_itinerary(p) for p in ranked_plans],
                "react_steps": [serialize_step(s) for s in orchestrator.agent.steps]
            })

        elif path == "/api/pnr/lookup":
            pnr = body.get("pnr", "2458901234")
            pnr_info = orchestrator.lookup_pnr(pnr)
            self.send_json(pnr_info)

        elif path == "/api/elicit":
            exam_hour = float(body.get("exam_hour", 9))
            budget = float(body.get("budget", 4000.0))
            venue = body.get("venue_area", "Whitefield Kadugodi, Bengaluru")

            h = int(exam_hour)
            m = int((exam_hour - h) * 60)
            new_exam_time = (orchestrator.base_date + timedelta(days=1)).replace(hour=h, minute=m)

            orchestrator.step2_elicit_constraints(new_exam_time, budget, venue)
            orchestrator.agent.execute_react_cycle(f"Reporting at {h:02d}:{m:02d}, budget INR {budget}")
            ranked_plans = orchestrator.step3_explore_and_rank_plans()

            self.send_json({
                "status": "CONSTRAINTS_UPDATED",
                "exam_reporting_time": new_exam_time.strftime("%b %d, %I:%M %p"),
                "budget_max": budget,
                "plans": [serialize_itinerary(p) for p in ranked_plans],
                "react_steps": [serialize_step(s) for s in orchestrator.agent.steps]
            })

        elif path == "/api/mutate":
            # Dynamic Constraint Mutation (PS Section 5)
            exam_hour = float(body.get("exam_hour", 7.5)) # 07:30 AM
            budget = float(body.get("budget", 10000.0))

            h = int(exam_hour)
            m = int((exam_hour - h) * 60)
            new_exam_time = (orchestrator.base_date + timedelta(days=1)).replace(hour=h, minute=m)

            mutation_res = orchestrator.agent.mutate_constraints(new_exam_time, budget)
            orchestrator.candidate_plans = mutation_res["ranked_plans"]

            self.send_json({
                "status": "MUTATION_COMPLETE",
                "previous_exam_time": mutation_res["previous_exam_time"],
                "new_exam_time": mutation_res["new_exam_time"],
                "previous_budget": mutation_res["previous_budget"],
                "new_budget": mutation_res["new_budget"],
                "evicted_routes": mutation_res["evicted_routes"],
                "top_recommendation": serialize_itinerary(mutation_res["new_top_recommendation"]) if mutation_res["new_top_recommendation"] else None,
                "plans": [serialize_itinerary(p) for p in orchestrator.candidate_plans],
                "reflexion": mutation_res["reflexion"]
            })

        elif path == "/api/book/prep":
            itin_id = body.get("itinerary_id")
            session = orchestrator.agent.prepare_consequential_booking(itin_id)
            self.send_json({
                "status": "SESSION_PREPARED",
                "session_id": session["session_id"],
                "upi_intent_uri": session["upi_intent_uri"],
                "payable_amount": session["payable_amount"],
                "verification_type": session["verification_type"],
                "last_mile": {
                    "carrier_name": session["last_mile"].carrier_name,
                    "duration_minutes": session["last_mile"].duration_minutes,
                    "fare": session["last_mile"].fare
                } if session["last_mile"] else None
            })

        elif path == "/api/book/execute":
            sess_id = body.get("session_id", orchestrator.agent.active_session_token or "IRCTC_SESS_DEFAULT")
            sim_retry = bool(body.get("simulate_gateway_retry", True))

            receipt = orchestrator.agent.execute_consequential_gate(
                session_id=sess_id,
                user_authorized=True,
                simulate_gateway_retry=sim_retry
            )
            self.send_json({
                "status": "BOOKING_CONFIRMED",
                "pnr": receipt["pnr"],
                "coach_berth": receipt["coach_berth"],
                "qr_token": receipt["qr_token"],
                "resilience_log": receipt["resilience_log"],
                "monitored_carrier": receipt["monitored_carrier"]
            })

        elif path == "/api/chaos/conflict":
            conflict_res = orchestrator.resolve_conflicting_telemetry("20846")
            self.send_json(conflict_res)

        elif path == "/api/chaos/delay":
            delay_mins = int(body.get("delay_minutes", 110))
            replan_res = orchestrator.agent.trigger_in_transit_disruption(delay_mins)
            self.send_json(replan_res)

        else:
            self.send_error(404, "Endpoint not found")


def run_server():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), SankalpHandler)
    print(f"================================================================================")
    print(f"      S A N K A L P  :  Live Application Server Running on Port {PORT}")
    print(f"================================================================================")
    print(f"  • Interactive Product UI : http://localhost:{PORT}/")
    print(f"  • Core REST APIs         : http://localhost:{PORT}/api/status")
    print(f"================================================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()


if __name__ == "__main__":
    run_server()
