"""
Comprehensive Test Suite for SANKALP Intelligent Journey Recovery Agent.
Uses standard library unittest.
Verifies all algorithmic, agentic, domain, and resilience capabilities.
"""
import unittest
from datetime import datetime, timedelta
from sankalp.models import UserConstraints, TransitMode, BookingStatus
from sankalp.mock_data import get_base_date, get_available_legs
from sankalp.engine import MultiModalGraphPathfinder, MonteCarloDelaySimulator, DecisionEngine
from sankalp.tools import (
    BookingSessionPrepTool,
    PaymentAndTicketExecutionTool,
    ConflictingSensorResolutionTool,
    JourneyMonitorDaemon,
    LiveNTESStatusTool
)
from sankalp.agent import SankalpAgent
from sankalp.orchestrator import SankalpOrchestrator

class TestSankalpEngine(unittest.TestCase):
    def setUp(self):
        self.base_date = get_base_date()
        self.exam_time = (self.base_date + timedelta(days=1)).replace(hour=9, minute=0)
        self.constraints = UserConstraints(
            origin="Bhopal",
            destination="Bengaluru",
            exam_reporting_time=self.exam_time,
            hard_arrival_deadline=self.exam_time - timedelta(hours=2),
            budget_max=4000.0,
            safe_buffer_minutes=120
        )

    def test_multimodal_graph_pathfinder(self):
        """Verify that graph pathfinder connects multimodal routes across rail, bus, and flight."""
        legs = get_available_legs(self.base_date)
        pathfinder = MultiModalGraphPathfinder(legs)
        itineraries = pathfinder.find_all_feasible_itineraries(
            origin_stations=["BPL", "RKMP", "Bhopal ISBT", "BHO"],
            destination_stations=["SBC", "YPR", "SMVB", "BLR"],
            base_time=self.base_date,
            hard_arrival_deadline=self.constraints.hard_arrival_deadline,
            exam_reporting_time=self.exam_time
        )
        self.assertGreaterEqual(len(itineraries), 5, "Graph pathfinder should find at least 5 distinct multimodal corridors")
        # Verify bus+flight corridor is discovered
        bus_flight_found = any(
            any(l.mode == TransitMode.BUS for l in it.legs) and any(l.mode == TransitMode.FLIGHT for l in it.legs)
            for it in itineraries
        )
        self.assertTrue(bus_flight_found, "Indore bus + flight multimodal corridor must be natively discovered by graph search")

    def test_monte_carlo_delay_simulation(self):
        """Verify 10,000-trial Monte Carlo simulation computes mathematically valid bounds."""
        engine = DecisionEngine(self.constraints)
        plans = engine.build_candidate_itineraries(self.base_date)
        ranked = engine.score_and_rank(plans)
        self.assertTrue(len(ranked) > 0)
        for p in ranked:
            self.assertGreaterEqual(p.monte_carlo_punctuality, 0.0)
            self.assertLessEqual(p.monte_carlo_punctuality, 1.0)
            ci_low, ci_high = p.confidence_interval_95
            self.assertLessEqual(ci_low, p.monte_carlo_punctuality)
            self.assertGreaterEqual(ci_high, p.monte_carlo_punctuality)

    def test_maut_scoring_budget_boundary(self):
        """Verify that within-budget options with high punctuality rank above over-budget flights."""
        engine = DecisionEngine(self.constraints)
        plans = engine.build_candidate_itineraries(self.base_date)
        ranked = engine.score_and_rank(plans)
        # Top choice must be within budget
        top = ranked[0]
        self.assertLessEqual(top.total_fare, self.constraints.budget_max, f"Top ranked option ({top.name}) should respect budget ceiling")
        self.assertIn("BALANCED", top.category)

    def test_consequential_action_gate_security(self):
        """Verify that unauthorized financial execution raises PermissionError."""
        payment_tool = PaymentAndTicketExecutionTool()
        with self.assertRaises(PermissionError):
            payment_tool.execute("SESSION_123", total_amount=2850.0, user_authorized=False)

    def test_conflicting_telemetry_sensor_fusion(self):
        """Verify multi-source Bayesian telemetry reconciliation under sensor ambiguity."""
        tool = ConflictingSensorResolutionTool()
        res = tool.resolve_discrepancy("20846")
        self.assertTrue(res["discrepancy_detected"])
        self.assertGreater(res["reconciled_delay_minutes"], 50)
        self.assertIn("RailMadad", res["authoritative_source"])

    def test_gateway_circuit_breaker_resilience(self):
        """Verify payment gateway HTTP 503 circuit-breaker retry."""
        tool = PaymentAndTicketExecutionTool()
        receipt = tool.execute("SESSION_123", total_amount=2850.0, user_authorized=True, simulate_gateway_retry=True)
        self.assertEqual(receipt["payment_status"], "SUCCESS")
        self.assertEqual(len(receipt["resilience_log"]), 3)
        self.assertIn("Circuit Breaker Tripped", receipt["resilience_log"][1])

    def test_dynamic_constraint_mutation(self):
        """Verify agent adaptability when user changes requirements mid-flight."""
        agent = SankalpAgent("2458901234", "12628", self.base_date)
        agent.execute_react_cycle("Bhopal to Bengaluru exam")
        
        # Mutate: exam preponed to 07:30 AM, budget expanded to 10,000
        new_exam = (self.base_date + timedelta(days=1)).replace(hour=7, minute=30)
        mut = agent.mutate_constraints(new_reporting_time=new_exam, new_budget=10000.0)
        
        self.assertEqual(mut["status"], "CONSTRAINTS_MUTATED")
        self.assertTrue(len(mut["evicted_routes"]) > 0, "Trains arriving after 05:30 AM must be evicted")
        self.assertIn("IndiGo", mut["new_top_recommendation"].name, "Fast air corridor should be elevated under earlier deadline")

    def test_interstate_bus_and_multimodal_corridors(self):
        """Verify that pure interstate AC sleeper bus and rail+bus corridors are discovered and scored."""
        engine = DecisionEngine(self.constraints)
        plans = engine.build_candidate_itineraries(self.base_date)
        ranked = engine.score_and_rank(plans)
        
        # 1. Verify pure interstate sleeper bus corridor is discovered
        pure_bus_corridors = [p for p in ranked if all(l.mode == TransitMode.BUS for l in p.legs)]
        self.assertGreaterEqual(len(pure_bus_corridors), 1, "At least one pure interstate sleeper bus corridor must be found")
        vrl_route = next((p for p in pure_bus_corridors if "VRL" in p.name), None)
        self.assertIsNotNone(vrl_route, "Nagpur-Bengaluru VRL Sleeper Bus route must be discovered")
        self.assertLessEqual(vrl_route.total_fare, 2500.0, "Pure bus route must be highly cost-effective")
        self.assertGreaterEqual(vrl_route.monte_carlo_punctuality, 0.90, "Highway sleeper corridor should have high reliability")

        # 2. Verify rail + sleeper bus corridor is discovered
        rail_bus_corridors = [
            p for p in ranked
            if any(l.mode == TransitMode.RAIL for l in p.legs) and any(l.mode == TransitMode.BUS for l in p.legs)
        ]
        self.assertGreaterEqual(len(rail_bus_corridors), 1, "At least one Rail + Bus multi-modal corridor must be found")
        vb_vrl = next((p for p in rail_bus_corridors if "Vande Bharat" in p.name and "VRL" in p.name), None)
        self.assertIsNotNone(vb_vrl, "Vande Bharat + VRL Multi-Axle AC Sleeper corridor must be discovered")
        self.assertIn("Namma Metro Purple Line", vb_vrl.last_mile.carrier_name, "Must connect to Namma Metro from Majestic Bus Stand")

    def test_in_transit_disruption_and_last_mile_metro_rescue(self):
        """Verify that cascade re-planning addresses the 07:10 AM station arrival with Metro rescue."""
        agent = SankalpAgent("2458901234", "12628", self.base_date)
        cycle = agent.execute_react_cycle("Bhopal to Bengaluru exam")
        # Select Vande Bharat + Wainganga route
        vb_route = next(p for p in cycle["ranked_plans"] if "Vande Bharat" in p.name and "Wainganga" in p.name)
        agent.prepare_consequential_booking(vb_route.itinerary_id)
        agent.execute_consequential_gate(agent.active_session_token, user_authorized=True)
        
        # Inject 110-minute delay
        replan = agent.trigger_in_transit_disruption(delay_minutes=110)
        sol = replan["cascade_replan"]
        
        self.assertIn("Rajdhani", sol["new_connecting_carrier"])
        self.assertIn("Namma Metro Purple Line", sol["last_mile_override"])
        self.assertGreaterEqual(sol["exam_slack_minutes"], 60, "Must guarantee >= 60 mins slack before exam gate")

if __name__ == "__main__":
    unittest.main()

