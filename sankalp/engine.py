"""
Decision Science & Combinatorial Graph Engine for SANKALP.
Implements:
1. Multi-Modal Station Graph Pathfinder (Combinatorial Search with Hub Interchanges)
2. Rigorous Monte Carlo Probabilistic Delay Simulation (10,000 iterations per route)
3. Calibrated Multi-Attribute Utility Theory (MAUT) Scoring & Pareto Optimization
4. Last-Mile Rapid Transit Integration (Namma Metro Purple Line / Vayu Vajra)
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
import math
import numpy as np

from .models import JourneyLeg, Itinerary, UserConstraints, TransitMode, BookingStatus, LastMileTransit
from .mock_data import (
    get_available_legs,
    STATION_HUBS,
    get_last_mile_options,
    get_last_mile_options_generic,
    generate_corridor_legs,
    get_station_by_code
)

class MultiModalGraphPathfinder:
    """
    Combinatorial pathfinder that explores paths across the multi-modal station network:
    Hubs: BPL, RKMP, ISBT, BHO, IDR, ET, NGP, SBC, YPR, SMVB, BLR.
    Supports interchange hub mapping and multimodal modal switches (Bus -> Flight, Rail -> Metro).
    """
    def __init__(self, legs: List[JourneyLeg]):
        self.legs = legs
        self.adjacency: Dict[str, List[JourneyLeg]] = {}
        for leg in legs:
            self.adjacency.setdefault(leg.from_station, []).append(leg)

    def find_all_feasible_itineraries(
        self,
        origin_stations: List[str],
        destination_stations: List[str],
        base_time: datetime,
        hard_arrival_deadline: datetime,
        exam_reporting_time: datetime,
        min_transfer_buffer_mins: int = 30,
        max_hops: int = 2,
        dest_city: str = "",
        venue_area: str = ""
    ) -> List[Itinerary]:
        discovered_itineraries: List[Itinerary] = []

        def are_stations_connected(stn_a: str, stn_b: str) -> bool:
            if stn_a == stn_b:
                return True
            hub_a = STATION_HUBS.get(stn_a)
            hub_b = STATION_HUBS.get(stn_b)
            return hub_a is not None and hub_a == hub_b

        def is_destination(stn: str) -> bool:
            if stn in destination_stations:
                return True
            hub = STATION_HUBS.get(stn)
            return any(hub == STATION_HUBS.get(d) for d in destination_stations if hub is not None)

        def dfs(current_station: str, current_time: datetime, path: List[JourneyLeg], depth: int):
            if path and is_destination(current_station):
                # Valid path discovered
                itin_id = f"ITIN_{'_'.join(l.carrier_id for l in path)}"
                name = self._generate_itinerary_name(path)
                category = self._assign_initial_category(path)

                # Attach optimal last-mile connection
                last_mile = get_last_mile_options_generic(path[-1].to_station, dest_city=dest_city, venue=venue_area)[0]

                itin = Itinerary(
                    itinerary_id=itin_id,
                    name=name,
                    category=category,
                    legs=list(path),
                    last_mile=last_mile
                )
                itin.calculate_totals(exam_reporting_time)

                # Filter: Final venue arrival must be before exam reporting time
                if itin.venue_arrival_time and itin.venue_arrival_time <= exam_reporting_time:
                    discovered_itineraries.append(itin)
                return

            if depth >= max_hops + 1:
                return

            # Explore all out-legs from current station or equivalent interchange hub
            candidate_departures: List[JourneyLeg] = []
            for stn_from, leg_list in self.adjacency.items():
                if are_stations_connected(current_station, stn_from):
                    candidate_departures.extend(leg_list)

            for leg in candidate_departures:
                # Timing viability
                if not path:
                    # First leg: Must depart after base_time
                    if leg.departure_time >= base_time:
                        dfs(leg.to_station, leg.arrival_time, path + [leg], depth + 1)
                else:
                    # Subsequent leg: Enforce Minimum Connection Time (MCT)
                    transfer_mins = int((leg.departure_time - current_time).total_seconds() / 60)
                    
                    # Buffer requirements based on junction complexity
                    if leg.mode == TransitMode.FLIGHT:
                        required_buffer = 120 # Airport check-in & security buffer
                    elif leg.from_station in ("NGP", "ET", "Bhopal ISBT", "Nagpur Ganeshpeth ISBT", "Hyderabad MGBS"):
                        required_buffer = 45 # Major railway junction / bus interchange
                    else:
                        required_buffer = min_transfer_buffer_mins

                    if transfer_mins >= required_buffer:
                        dfs(leg.to_station, leg.arrival_time, path + [leg], depth + 1)

        for origin in origin_stations:
            dfs(origin, base_time, [], 0)

        # Deduplicate itineraries with identical leg sequences
        unique_itineraries = []
        seen_keys = set()
        for it in discovered_itineraries:
            key = tuple(l.carrier_id for l in it.legs)
            if key not in seen_keys:
                seen_keys.add(key)
                unique_itineraries.append(it)

        return unique_itineraries

    def _generate_itinerary_name(self, legs: List[JourneyLeg]) -> str:
        if len(legs) == 1:
            return f"Direct {legs[0].carrier_name}"
        elif len(legs) == 2:
            return f"{legs[0].carrier_name} + {legs[1].carrier_name} via {legs[0].to_station}"
        else:
            return " -> ".join(l.carrier_name for l in legs)

    def _assign_initial_category(self, legs: List[JourneyLeg]) -> str:
        if any(l.mode == TransitMode.FLIGHT for l in legs):
            return "SAFE (AIR)"
        if all(l.mode == TransitMode.BUS for l in legs):
            return "BUDGET SAVER (EXPRESS SLEEPER BUS)"
        if any(l.mode == TransitMode.BUS for l in legs):
            return "BALANCED (MULTI-MODAL RAIL + BUS)"
        if len(legs) > 1 and any("Vande Bharat" in l.carrier_name for l in legs):
            return "BALANCED"
        return "BUDGET"


class MonteCarloDelaySimulator:
    """
    Evaluates stochastic disruption risks using a true 10,000-trial Monte Carlo simulation.
    Train delays are modeled as right-skewed Log-Normal distributions:
    ln(Delay) ~ N(mu, sigma^2) parameterized by historical NTES telemetry.
    """
    def __init__(self, num_simulations: int = 10000, seed: int = 42):
        self.num_simulations = num_simulations
        self.rng = np.random.default_rng(seed)

    def simulate_itinerary(
        self,
        itinerary: Itinerary,
        exam_reporting_time: datetime
    ) -> Tuple[float, Tuple[float, float], float]:
        """
        Runs Monte Carlo simulation for an itinerary.
        Returns:
            (punctuality_probability, (ci_lower_95, ci_upper_95), disruption_risk)
        """
        n = self.num_simulations
        legs = itinerary.legs
        if not legs:
            return 0.0, (0.0, 0.0), 1.0

        # Generate simulated delays for each leg in minutes
        leg_delays = []
        for leg in legs:
            m = max(2.0, leg.mean_delay_mins)
            s = max(2.0, leg.delay_std_mins)
            variance = s ** 2
            mu = np.log((m ** 2) / np.sqrt(variance + m ** 2))
            sigma = np.sqrt(np.log(1.0 + (variance / (m ** 2))))

            sampled_delays = self.rng.lognormal(mean=mu, sigma=sigma, size=n)
            sampled_delays = np.clip(sampled_delays, 0.0, 300.0) # Clip physical extremes
            leg_delays.append(sampled_delays)

        # Check transfer viability across all junctions in each trial
        transfers_successful = np.ones(n, dtype=bool)

        for i in range(len(legs) - 1):
            scheduled_buffer = int((legs[i+1].departure_time - legs[i].arrival_time).total_seconds() / 60)
            tau_walk = 20 if legs[i].to_station in ("ET", "NGP") else 15
            if legs[i+1].mode == TransitMode.FLIGHT:
                tau_walk = 60 # Airport gate closure / security buffer

            effective_buffer = scheduled_buffer - tau_walk
            transfer_margin = effective_buffer - (leg_delays[i] - 0.3 * leg_delays[i+1])
            transfers_successful = transfers_successful & (transfer_margin >= 0)

        # Check venue arrival before exam reporting
        final_leg_delay = leg_delays[-1]
        last_mile_mins = itinerary.last_mile.duration_minutes if itinerary.last_mile else 60
        last_mile_variance = itinerary.last_mile.traffic_variance_mins if itinerary.last_mile else 15

        # Sample last-mile traffic variance
        sampled_lm_delay = self.rng.uniform(0.0, float(last_mile_variance), size=n)

        # Total arrival at exam venue
        scheduled_arrival = legs[-1].arrival_time + timedelta(minutes=last_mile_mins)
        scheduled_slack = int((exam_reporting_time - scheduled_arrival).total_seconds() / 60)

        total_delay = final_leg_delay + sampled_lm_delay
        arrival_on_time = (scheduled_slack - total_delay) >= 0

        # Combined success: All transfers intact AND venue reached on time
        overall_success = transfers_successful & arrival_on_time
        success_count = np.sum(overall_success)

        punctuality_prob = float(success_count / n)

        # 95% Confidence Interval via Wilson Score / Normal Approximation
        stderr = math.sqrt(max(0.0, punctuality_prob * (1.0 - punctuality_prob) / n))
        ci_lower = max(0.0, punctuality_prob - 1.96 * stderr)
        ci_upper = min(1.0, punctuality_prob + 1.96 * stderr)

        disruption_risk = round(1.0 - punctuality_prob, 4)

        return round(punctuality_prob, 4), (round(ci_lower, 4), round(ci_upper, 4)), disruption_risk


class DecisionEngine:
    """
    Decision Science Engine:
    Integrates Combinatorial Graph Pathfinder, Monte Carlo Probabilistic Simulation,
    and Multi-Attribute Utility Theory (MAUT) with strict budget-feasibility gating.
    """
    def __init__(self, constraints: UserConstraints):
        self.constraints = constraints
        self.simulator = MonteCarloDelaySimulator(num_simulations=10000)

    def build_candidate_itineraries(self, base_date: datetime) -> List[Itinerary]:
        """
        Dynamically discovers multi-modal corridors across rail, bus, and air.
        """
        orig_raw = getattr(self.constraints, "origin", "BPL")
        dest_raw = getattr(self.constraints, "destination", "SBC")
        venue_area = getattr(self.constraints, "exam_venue_area", "City Center")

        # Check if corridor matches Bhopal -> Bengaluru benchmark
        is_bhopal = any(k in orig_raw.upper() for k in ["BPL", "BHOPAL", "RKMP"])
        is_bengaluru = any(k in dest_raw.upper() for k in ["BLR", "BENGALURU", "BANGALORE", "SBC", "YPR", "SMVB"])

        if is_bhopal and is_bengaluru:
            all_legs = get_available_legs(base_date)
            origin_nodes = ["BPL", "RKMP", "Bhopal ISBT", "Bhopal Nadra Bus Stand", "BHO"]
            dest_nodes = ["SBC", "YPR", "SMVB", "BLR", "Bengaluru Majestic Bus Stand"]
            dest_city = "Bengaluru"
        else:
            orig_code = orig_raw.split("(")[-1].replace(")", "").strip() if "(" in orig_raw else orig_raw.strip().upper()
            dest_code = dest_raw.split("(")[-1].replace(")", "").strip() if "(" in dest_raw else dest_raw.strip().upper()

            orig_stn = get_station_by_code(orig_code)
            dest_stn = get_station_by_code(dest_code)

            all_legs = generate_corridor_legs(orig_code, dest_code, base_date)
            origin_nodes = list(set([l.from_station for l in all_legs if l.from_station in (orig_code, f"{orig_stn.city if orig_stn else orig_code} ISBT") or "AIR" in l.from_station or l.from_station == orig_code]))
            dest_nodes = list(set([l.to_station for l in all_legs if l.to_station in (dest_code, f"{dest_stn.city if dest_stn else dest_code} Central Bus Stand") or "AIR" in l.to_station or l.to_station == dest_code]))
            if not origin_nodes:
                origin_nodes = [orig_code]
            if not dest_nodes:
                dest_nodes = [dest_code]
            dest_city = dest_stn.city if dest_stn else dest_code

        pathfinder = MultiModalGraphPathfinder(all_legs)

        candidates = pathfinder.find_all_feasible_itineraries(
            origin_stations=origin_nodes,
            destination_stations=dest_nodes,
            base_time=base_date,
            hard_arrival_deadline=self.constraints.hard_arrival_deadline,
            exam_reporting_time=self.constraints.exam_reporting_time,
            min_transfer_buffer_mins=30,
            max_hops=2,
            dest_city=dest_city,
            venue_area=venue_area
        )

        return candidates

    def score_and_rank(self, itineraries: List[Itinerary]) -> List[Itinerary]:
        """
        Ranks candidate recovery corridors using Calibrated MAUT Scoring.
        Enforces a hard budget-feasibility boundary: within-budget options that meet
        high punctuality (>90%) are prioritized over emergency budget-busting flights.
        """
        valid_plans = []
        c = self.constraints

        for itin in itineraries:
            # 1. Physical Deadline Verification at Exam Venue
            if itin.venue_arrival_time is None or itin.venue_arrival_time > c.exam_reporting_time:
                continue

            # 2. Run 10,000-trial Monte Carlo delay simulation
            p_ontime, ci, risk = self.simulator.simulate_itinerary(
                itinerary=itin,
                exam_reporting_time=c.exam_reporting_time
            )

            itin.monte_carlo_punctuality = p_ontime
            itin.confidence_interval_95 = ci
            itin.disruption_risk = risk

            # Disqualify extreme risk routes (P_ontime < 75%)
            if p_ontime < 0.75:
                continue

            # 3. Compute Normalized MAUT Component Scores
            # S_time: Utility of venue arrival buffer.
            # Optimal buffer is 90 to 180 mins. Beyond 240 mins, marginal utility plateaus.
            buffer_mins = itin.venue_buffer_minutes
            if buffer_mins < 30:
                s_time = 0.10 # Danger zone
            elif buffer_mins <= 180:
                s_time = 0.50 + 0.50 * (buffer_mins / 180.0)
            else:
                s_time = 1.0 # Fully saturated comfort buffer

            # S_cost: Budget Feasibility Score
            cost = itin.total_fare
            if cost <= c.budget_max:
                itin.is_budget_exceeded = False
                # Scale from 0.40 (at budget limit) to 1.0 (free)
                s_cost = 1.0 - (cost / max(c.budget_max, 1.0)) * 0.60
            else:
                itin.is_budget_exceeded = True
                # Severe step penalty for exceeding user budget ceiling
                overage = cost - c.budget_max
                s_cost = max(0.02, 0.20 - (overage / 5000.0) * 0.18)

            # S_comfort: Travel class comfort minus transfer friction
            comfort_classes = ("3A", "2A", "1A", "CC", "AC_SEATER", "AC_SLEEPER", "ECONOMY")
            comfort_base = 0.95 if any(l.travel_class in comfort_classes for l in itin.legs) else 0.60
            transfer_penalty = itin.num_transfers * 0.12
            s_comfort = max(0.10, comfort_base - transfer_penalty)

            # 4. Calibrated MAUT Multi-Attribute Utility
            # Weights: Punctuality (0.40), Arrival Buffer (0.30), Budget (0.20), Comfort (0.10)
            utility = (
                0.40 * p_ontime +
                0.30 * s_time +
                0.20 * s_cost +
                0.10 * s_comfort
            )

            # Over-budget penalty gate: Cap utility of budget-violating routes
            # so they never artificially outrank high-punctuality affordable options
            if itin.is_budget_exceeded:
                utility = min(utility, 0.749) # Strict cap below top-tier affordable routes

            itin.utility_score = round(utility, 4)

            # Assign Descriptive Categories
            has_flight = any(l.mode == TransitMode.FLIGHT for l in itin.legs)
            has_bus = any(l.mode == TransitMode.BUS for l in itin.legs)
            has_rail = any(l.mode == TransitMode.RAIL for l in itin.legs)
            all_bus = all(l.mode == TransitMode.BUS for l in itin.legs)

            if itin.is_budget_exceeded and p_ontime >= 0.95:
                itin.category = "CONTINGENCY (OVER-BUDGET AIR)"
            elif not itin.is_budget_exceeded and p_ontime >= 0.95:
                if all_bus:
                    itin.category = "BALANCED (INTERSTATE AC SLEEPER BUS)"
                elif has_bus and has_rail:
                    itin.category = "BALANCED (MULTI-MODAL RAIL + BUS)"
                else:
                    itin.category = "BALANCED (RECOMMENDED)"
            elif not itin.is_budget_exceeded and p_ontime >= 0.88:
                if all_bus or (has_bus and has_rail):
                    itin.category = "BUDGET SAVER (HIGHWAY BUS CORRIDOR)"
                else:
                    itin.category = "BUDGET SAVER"
            else:
                itin.category = "FEASIBLE ALTERNATIVE"

            valid_plans.append(itin)

        # Sort descending by utility score
        valid_plans.sort(key=lambda x: x.utility_score, reverse=True)
        return valid_plans
