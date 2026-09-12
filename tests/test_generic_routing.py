"""
Unit tests for Production-Grade Generic Pan-India Multi-Corridor Recovery.
"""
import unittest
from datetime import datetime, timedelta
from sankalp.models import UserConstraints, TransitMode, BookingStatus
from sankalp.mock_data import (
    get_base_date,
    search_stations,
    get_station_by_code,
    generate_corridor_legs,
    get_last_mile_options_generic,
    STATIONS_DB
)
from sankalp.engine import DecisionEngine, MultiModalGraphPathfinder
from sankalp.orchestrator import SankalpOrchestrator

class TestGenericRouting(unittest.TestCase):
    def setUp(self):
        self.base_date = get_base_date()
        self.exam_time = (self.base_date + timedelta(days=1)).replace(hour=9, minute=0)

    def test_station_directory_search(self):
        """Verify pan-India station directory and fuzzy search."""
        self.assertGreaterEqual(len(STATIONS_DB), 30)
        
        # Exact code lookup
        delhi = get_station_by_code("NDLS")
        self.assertIsNotNone(delhi)
        self.assertEqual(delhi.city, "New Delhi")

        # Fuzzy search by city name
        mumbai_matches = search_stations("Mumbai")
        self.assertTrue(any(s.code in ("CSMT", "MMCT", "BOM") for s in mumbai_matches))

        # Search by airport code
        blr_air = get_station_by_code("BLR")
        self.assertEqual(blr_air.station_type, "AIRPORT")

    def test_generic_corridor_generation(self):
        """Verify dynamic leg generation across rail, bus, and flight for arbitrary corridors."""
        legs = generate_corridor_legs("NDLS", "CSMT", self.base_date)
        self.assertGreaterEqual(len(legs), 4)

        modes = set(l.mode for l in legs)
        self.assertIn(TransitMode.RAIL, modes)
        self.assertIn(TransitMode.BUS, modes)
        self.assertIn(TransitMode.FLIGHT, modes)

    def test_generic_decision_engine_routing(self):
        """Verify DecisionEngine routes and ranks plans for non-Bhopal corridor (e.g. NDLS -> CSMT)."""
        constraints = UserConstraints(
            origin="NDLS",
            destination="CSMT",
            exam_reporting_time=self.exam_time,
            hard_arrival_deadline=self.exam_time - timedelta(hours=2),
            budget_max=6000.0,
            exam_venue_area="Bandra Kurla Complex, Mumbai"
        )
        engine = DecisionEngine(constraints)
        plans = engine.build_candidate_itineraries(self.base_date)
        self.assertGreater(len(plans), 0, "Should discover feasible recovery itineraries for Delhi -> Mumbai")

        ranked = engine.score_and_rank(plans)
        self.assertTrue(len(ranked) > 0)
        top = ranked[0]
        self.assertIsNotNone(top.last_mile)
        # Verify Mumbai rapid transit is attached
        self.assertIn("Mumbai", top.last_mile.carrier_name)

    def test_pnr_lookup_and_route_corridor(self):
        """Verify orchestrator PNR triage and corridor routing."""
        orch = SankalpOrchestrator("2458901234", "12628", self.base_date)
        pnr_info = orch.lookup_pnr("4890123456")
        self.assertEqual(pnr_info["origin"], "NDLS")
        self.assertEqual(pnr_info["destination"], "CSMT")
        self.assertTrue(pnr_info["disrupted"])

        # Test dynamic corridor route
        ranked_plans = orch.route_corridor(
            origin="PNBE",
            destination="NDLS",
            exam_time=self.exam_time,
            budget=3000.0,
            venue_area="Connaught Place, New Delhi"
        )
        self.assertGreater(len(ranked_plans), 0)
        self.assertEqual(orch.constraints.origin, "PNBE")
        self.assertEqual(orch.constraints.destination, "NDLS")

if __name__ == "__main__":
    unittest.main()
