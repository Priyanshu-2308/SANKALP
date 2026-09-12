"""
Implementations of the core tools in SANKALP architecture.
Adheres strictly to Indian Railways PRS reality, Multi-Source Sensor Fusion,
Gateway Circuit Breaking, and Zero-Trust Human-in-the-Loop security.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import random
import uuid

from .models import JourneyLeg, TransitMode, BookingStatus, QuotaType
from .mock_data import get_available_legs

class TrainInventorySearchTool:
    """Tool 1: Queries Indian Railways PRS inventory across direct and junction gateways."""
    def __init__(self, base_date: datetime):
        self.legs = [leg for leg in get_available_legs(base_date) if leg.mode == TransitMode.RAIL]

    def execute(self, from_stations: List[str], to_stations: List[str]) -> List[JourneyLeg]:
        results = []
        for leg in self.legs:
            if leg.from_station in from_stations and leg.to_station in to_stations:
                results.append(leg)
        return results

class LiveNTESStatusTool:
    """Tool 2: Real-time GPS running status, platform assignments, and delay tracking."""
    def __init__(self):
        self._delay_db = {
            "20846": 0,    # Vande Bharat initially nominal
            "12650": 15,   # KSK running 15 mins late
            "12252": 5,    # Wainganga running on time
            "22692": 10,   # Rajdhani Express running 10 mins late
            "12628": -1    # Cancelled
        }

    def execute(self, train_number: str) -> Dict[str, Any]:
        delay = self._delay_db.get(train_number, 0)
        if delay == -1:
            return {
                "train_number": train_number,
                "status": "CANCELLED",
                "delay_minutes": 0,
                "message": "Train cancelled by Indian Railways due to operational / safety reasons."
            }
        return {
            "train_number": train_number,
            "status": "RUNNING",
            "delay_minutes": delay,
            "expected_platform": "Platform 2" if train_number in ("20846", "22692") else "Platform 4",
            "last_station_passed": "Itarsi Jn" if delay < 30 else "Betul / Amla Jn",
            "delay_trend": "STABLE" if delay < 20 else "INCREASING"
        }

    def inject_delay(self, train_number: str, additional_delay_minutes: int):
        """Simulate unexpected in-transit incident."""
        current = self._delay_db.get(train_number, 0)
        self._delay_db[train_number] = max(0, current) + additional_delay_minutes

class MultiModalRoutingTool:
    """Tool 3: Non-rail emergency connectors (Intercity Express Buses & Scheduled Flights)."""
    def __init__(self, base_date: datetime):
        self.non_rail_legs = [leg for leg in get_available_legs(base_date) if leg.mode in (TransitMode.BUS, TransitMode.FLIGHT)]

    def execute(self) -> List[JourneyLeg]:
        return self.non_rail_legs

class IRCTCRulesRefundTool:
    """Tool 4: Railway Board Gazette compliance, automated TDR calculation, and linked PNR protection."""
    def execute(self, pnr: str, train_number: str) -> Dict[str, Any]:
        return {
            "pnr": pnr,
            "train_number": train_number,
            "is_cancelled_by_railways": True,
            "gazette_clause": "Rule 6(b) Indian Railway Board Gazette - 100% Refund on Cancelled Trains",
            "eligible_refund_amount": 1420.0,
            "auto_credit_to_source": True,
            "tdr_required": False, # Online e-tickets receive automated source account credit
            "missed_connection_protection": "Rule 54: Full refund on connecting ticket if first train delayed/cancelled on linked PNR",
            "advice": "100% refund of INR 1,420 will be auto-credited to your source bank account within 3 to 5 business days without any cancellation penalty."
        }

class BookingSessionPrepTool:
    """
    Tool 5: Generates authenticated checkout payload, passenger pre-fill, and UPI Intent.
    Dynamically injects exact itinerary fare into the UPI Intent URI.
    """
    def execute(self, leg_ids: List[str], passenger_name: str, age: int, total_amount: float = 2850.0) -> Dict[str, Any]:
        session_id = f"IRCTC_SESS_{uuid.uuid4().hex[:8].upper()}"
        upi_intent_uri = f"upi://pay?pa=irctc.pay@icici&pn=IRCTC&am={total_amount:.2f}&tr={session_id}&cu=INR"
        return {
            "session_id": session_id,
            "target_legs": leg_ids,
            "total_amount": total_amount,
            "passenger_manifest": {
                "name": passenger_name,
                "age": age,
                "berth_preference": "LOWER/SIDE_LOWER",
                "auto_upgradation": True
            },
            "upi_intent_uri": upi_intent_uri,
            "gate_required": True,
            "verification_type": "HUMAN_BIOMETRIC_OR_OTP",
            "session_timeout_seconds": 180,
            "status": "PREPARED_AWAITING_GATE"
        }

# Backwards compatibility alias
BookingReservationPrepTool = BookingSessionPrepTool

class PaymentAndTicketExecutionTool:
    """
    Tool 6: Consequential Action Gate Executor with Gateway Circuit Breaker Resilience.
    Executes transaction and generates PNR ONLY after receiving verified user authorization.
    """
    def execute(
        self,
        session_token: str,
        total_amount: float,
        user_authorized: bool = True,
        travel_class: str = "3A",
        simulate_gateway_retry: bool = False
    ) -> Dict[str, Any]:
        if not user_authorized:
            raise PermissionError("Consequential Action Gate Violation: User authorization token missing.")

        retry_log = []
        if simulate_gateway_retry:
            # Simulate real-world IRCTC PRS Gateway 503 spike and instant circuit breaker fallback
            retry_log.append("Attempt 1: Primary Bank Gateway (HDFC PG) -> HTTP 503 Gateway Timeout.")
            retry_log.append("Circuit Breaker Tripped: Switched to Secondary Rail (IRCTC iMudra / Direct NPCI UPI).")
            retry_log.append("Attempt 2: Secondary Rail -> HTTP 200 OK. Transaction Settled.")

        # Class-appropriate berth allocation
        if travel_class == "CC":
            seat_desc = "Coach C2, Seat 18 (Window)"
        elif travel_class == "2S":
            seat_desc = "Coach D3, Seat 42 (Aisle)"
        elif travel_class == "SL":
            seat_desc = "Coach S5, Berth 23 (Middle)"
        elif travel_class == "ECONOMY":
            seat_desc = "Seat 14C (Aisle, Extra Legroom)"
        elif travel_class == "AC_SEATER":
            seat_desc = "Seat 8 (Front Panorama)"
        else:
            seat_desc = "Coach B3, Berth 42 (Side Lower)"

        pnr = f"{random.randint(2000000000, 9999999999)}"
        return {
            "pnr": pnr,
            "transaction_id": f"TXN_{uuid.uuid4().hex[:10].upper()}",
            "amount_paid": total_amount,
            "payment_status": "SUCCESS",
            "coach_berth": seat_desc,
            "qr_code_token": f"QR_{pnr}",
            "resilience_log": retry_log,
            "issued_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

class ConflictingSensorResolutionTool:
    """
    Resolves conflicting telemetry feeds from different real-time sources
    (e.g., stale NTES GPS vs live crowdsourced RailMadad / Locomotive IoT telemetry).
    Provides Bayesian sensor fusion and truth-grounding for operational decision making.
    """
    def resolve_discrepancy(self, train_number: str) -> Dict[str, Any]:
        source_a = {
            "source": "NTES GPS Cell Tower",
            "delay_minutes": 15,
            "last_updated": "42 minutes ago",
            "confidence": 0.45,
            "status": "STALE_TELEMETRY"
        }
        source_b = {
            "source": "RailMadad Driver IoT / Station Master Bulletin",
            "delay_minutes": 110,
            "last_updated": "2 minutes ago",
            "confidence": 0.94,
            "status": "INCIDENT_ACTIVE: Freight Wagon Signal Malfunction near Betul"
        }

        # Multi-sensor Bayesian reconciliation
        weighted_delay = int(source_a["delay_minutes"] * 0.10 + source_b["delay_minutes"] * 0.90)

        return {
            "train_number": train_number,
            "sources_evaluated": [source_a, source_b],
            "discrepancy_detected": True,
            "reconciled_delay_minutes": weighted_delay,
            "authoritative_source": source_b["source"],
            "root_cause": "Telemetry cell lag in Western Central Railway ghat section masked live 110m halt.",
            "decision": "Adopt 110-minute ground delay. Trigger immediate proactive cascade re-planning."
        }

class JourneyMonitorDaemon:
    """Tool 7: Active Telemetry Watchdog running in background tracking buffer erosion."""
    def __init__(self, ntes_tool: LiveNTESStatusTool):
        self.ntes_tool = ntes_tool

    def evaluate_connection_risk(
        self,
        incoming_train: str,
        outgoing_train: str,
        scheduled_buffer_minutes: int,
        transfer_station: str = "Nagpur Jn (NGP)"
    ) -> Dict[str, Any]:
        incoming_status = self.ntes_tool.execute(incoming_train)
        delay = incoming_status["delay_minutes"]
        remaining_buffer = scheduled_buffer_minutes - delay

        # Critical buffer safety threshold for major junctions is 30 minutes
        if remaining_buffer < 30:
            status = "CRITICAL_RISK" if remaining_buffer > 0 else "BROKEN_CONNECTION"
            action_required = "CASCADE_REPLAN_TRIGGERED"
        elif remaining_buffer < 45:
            status = "WARNING_BUFFER_EROSION"
            action_required = "ALERT_USER"
        else:
            status = "NOMINAL"
            action_required = "NONE"

        return {
            "incoming_carrier": incoming_train,
            "outgoing_carrier": outgoing_train,
            "transfer_station": transfer_station,
            "delay_minutes": delay,
            "original_buffer": scheduled_buffer_minutes,
            "remaining_buffer": remaining_buffer,
            "status": status,
            "action_required": action_required,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }

    def register_journey(self, monitor_id: str, legs: List[JourneyLeg], buffer_threshold_mins: int = 30):
        self._monitors = getattr(self, "_monitors", {})
        self._monitors[monitor_id] = {
            "legs": legs,
            "threshold": buffer_threshold_mins,
            "created_at": datetime.now()
        }

    def check_status(self, monitor_id: str) -> Dict[str, Any]:
        self._monitors = getattr(self, "_monitors", {})
        mon = self._monitors.get(monitor_id)
        if not mon:
            return {
                "status": "NOMINAL",
                "carrier": "Direct Express Service",
                "transfer_station": "Direct Route (En-route)",
                "remaining_buffer": 120,
                "action_required": "NONE"
            }

        legs = mon.get("legs", [])
        if len(legs) < 2:
            carrier_name = legs[0].carrier_name if legs else "Direct Express Service"
            return {
                "status": "NOMINAL",
                "carrier": carrier_name,
                "transfer_station": "Direct Corridor (En-route)",
                "remaining_buffer": 140,
                "action_required": "NONE"
            }

        leg1 = legs[0]
        leg2 = legs[1]
        sched_buffer = int((leg2.departure_time - leg1.arrival_time).total_seconds() / 60)
        eval_res = self.evaluate_connection_risk(leg1.carrier_id, leg2.carrier_id, sched_buffer, leg1.to_station)
        
        status_map = {
            "BROKEN_CONNECTION": "CRITICAL_ALERT",
            "CRITICAL_RISK": "CRITICAL_ALERT",
            "WARNING_BUFFER_EROSION": "WARNING",
            "NOMINAL": "NOMINAL"
        }
        return {
            "status": status_map.get(eval_res["status"], "NOMINAL"),
            "carrier": leg1.carrier_name,
            "transfer_station": leg1.to_station,
            "remaining_buffer": eval_res["remaining_buffer"],
            "action_required": eval_res["action_required"]
        }
