"""Deterministic seeded schedule generator.

Design Principles:
- Implements TransportDataSource.
- Pure Python and standard library (math, json, hashlib, random).
- Seeded pseudo-random generation: same (origin, dest, date, salt) strictly returns identical schedules.
- Realistic geography (Haversine over actual Indian station coordinates).
- Realistic speeds, operating hours, and fare bands in integer paise.
- All schedules are explicitly stamped as is_simulated=True.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from .datasource import TransportDataSource
from .geo import detour_ratio, place_distance_km
from .models import IST, Leg, Place, PlaceType, TransitMode

# Default paths relative to project root
DEFAULT_STATIONS_PATH = Path("data/stations.json")
DEFAULT_MCT_PATH = Path("data/connections_mct.json")
DEFAULT_CONFIG_PATH = Path("data/generator_config.json")


class SeededScheduleGenerator(TransportDataSource):
    """Generates plausible, deterministic transport schedules for any corridor in India."""

    def __init__(
        self,
        stations_path: Optional[Path | str] = None,
        mct_path: Optional[Path | str] = None,
        config_path: Optional[Path | str] = None,
        seed_salt: str = "sankalp-v1",
    ) -> None:
        self._seed_salt = seed_salt
        self._places_by_id: dict[str, Place] = {}
        self._places_by_code: dict[str, Place] = {}
        self._places: list[Place] = []
        self._mct_matrix: dict[str, int] = {}
        self._default_mct: int = 30
        self._config: dict[str, Any] = {}

        self._load_datasets(
            Path(stations_path) if stations_path else DEFAULT_STATIONS_PATH,
            Path(mct_path) if mct_path else DEFAULT_MCT_PATH,
            Path(config_path) if config_path else DEFAULT_CONFIG_PATH,
        )

    def _load_datasets(self, stations_path: Path, mct_path: Path, config_path: Path) -> None:
        """Load and index bundled datasets from disk."""
        if stations_path.exists():
            with open(stations_path, "r", encoding="utf-8") as f:
                raw_stations = json.load(f)
                for s in raw_stations:
                    place = Place(
                        id=s["id"],
                        name=s["name"],
                        code=s["code"],
                        place_type=PlaceType(s["type"]),
                        city=s["city"],
                        state=s["state"],
                        latitude=float(s["lat"]),
                        longitude=float(s["lon"]),
                        aliases=s.get("aliases", []),
                        tier=s.get("tier", 2),
                    )
                    self._places_by_id[place.id] = place
                    self._places_by_code[place.code.upper()] = place
                    self._places.append(place)

        if mct_path.exists():
            with open(mct_path, "r", encoding="utf-8") as f:
                mct_data = json.load(f)
                self._default_mct = mct_data.get("default_mct_minutes", 30)
                self._mct_matrix = mct_data.get("matrix", {})

        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)

    # -------------------------------------------------------------------------
    # TransportDataSource Protocol Methods
    # -------------------------------------------------------------------------

    def get_place(self, place_id: str) -> Optional[Place]:
        return self._places_by_id.get(place_id)

    def get_place_by_code(self, code: str) -> Optional[Place]:
        return self._places_by_code.get(code.strip().upper())

    def get_all_places(self) -> list[Place]:
        return list(self._places)

    def search_places(self, query: str, limit: int = 10) -> list[Place]:
        q = query.strip().lower()
        if not q:
            # Return top-tier hubs if empty query
            return sorted(self._places, key=lambda p: (p.tier, p.name))[:limit]

        # Score matches: exact code > starts with > substring in name/city/aliases
        scored: list[tuple[int, Place]] = []
        for p in self._places:
            code_lower = p.code.lower()
            name_lower = p.name.lower()
            city_lower = p.city.lower()
            aliases_lower = [a.lower() for a in p.aliases]

            if code_lower == q:
                score = 100
            elif code_lower.startswith(q):
                score = 80
            elif city_lower == q:
                score = 75
            elif city_lower.startswith(q):
                score = 65
            elif name_lower.startswith(q):
                score = 60
            elif any(q == a for a in aliases_lower):
                score = 55
            elif q in name_lower or q in city_lower or any(q in a for a in aliases_lower):
                score = 40
            else:
                continue

            # Prioritize tier 1 hubs when scores are tied
            tier_bonus = (4 - p.tier) * 2
            scored.append((score + tier_bonus, p))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [p for _, p in scored[:limit]]

    def get_minimum_connection_time(self, mode_from: TransitMode, mode_to: TransitMode) -> int:
        key = f"{mode_from.value}_TO_{mode_to.value}"
        return self._mct_matrix.get(key, self._default_mct)

    def find_candidate_connecting_hubs(
        self,
        origin_id: str,
        destination_id: str,
        max_hubs: int = 12,
        max_detour_ratio: float = 1.45,
    ) -> list[str]:
        orig = self.get_place(origin_id)
        dest = self.get_place(destination_id)
        if not orig or not dest:
            return []

        direct_dist = place_distance_km(orig, dest)
        if direct_dist <= 25.0:
            return []

        candidates: list[tuple[float, Place]] = []
        for p in self._places:
            if p.id == orig.id or p.id == dest.id:
                continue
            # Hubs must be significant junction hubs (Tier 1 or 2)
            if p.tier > 2:
                continue

            orig_to_hub = place_distance_km(orig, p)
            hub_to_dest = place_distance_km(p, dest)

            # Must make progress towards the destination
            if orig_to_hub >= direct_dist * 0.95 or hub_to_dest >= direct_dist * 0.95:
                continue

            ratio = detour_ratio(orig, p, dest)
            if ratio <= max_detour_ratio:
                candidates.append((ratio, p))

        # Sort by most direct detour
        candidates.sort(key=lambda item: item[0])
        return [p.id for _, p in candidates[:max_hubs]]

    def find_direct_legs(
        self,
        origin_id: str,
        destination_id: str,
        departure_after: datetime,
        departure_before: datetime,
    ) -> list[Leg]:
        orig = self.get_place(origin_id)
        dest = self.get_place(destination_id)
        if not orig or not dest or orig.id == dest.id:
            return []

        # Enforce timezone
        if departure_after.tzinfo is None:
            departure_after = departure_after.replace(tzinfo=IST)
        if departure_before.tzinfo is None:
            departure_before = departure_before.replace(tzinfo=IST)

        dist_km = place_distance_km(orig, dest)
        if dist_km < 5.0:
            return []

        legs: list[Leg] = []
        # Check day window (sample departures across days if window spans multiple days)
        current_day = departure_after.date()
        end_day = departure_before.date()
        
        day_count = (end_day - current_day).days + 1
        for day_offset in range(day_count):
            target_date = current_day + timedelta(days=day_offset)
            legs.extend(self._generate_daily_legs(orig, dest, dist_km, target_date))

        # Filter strictly within the requested departure window
        valid_legs = [
            leg for leg in legs
            if departure_after <= leg.departure_time <= departure_before
        ]

        # Sort chronologically by departure time
        valid_legs.sort(key=lambda l: l.departure_time)
        return valid_legs

    # -------------------------------------------------------------------------
    # Internal Seeded Generation Engine
    # -------------------------------------------------------------------------

    def _generate_daily_legs(
        self,
        orig: Place,
        dest: Place,
        dist_km: float,
        target_date: datetime.date,
    ) -> list[Leg]:
        """Generate deterministic schedules for a specific day between two nodes."""
        date_str = target_date.strftime("%Y-%m-%d")
        seed_key = f"{orig.id}:{dest.id}:{date_str}:{self._seed_salt}"
        seed_hash = hashlib.md5(seed_key.encode("utf-8")).hexdigest()
        seed_int = int(seed_hash, 16) % (2**31)

        daily_legs: list[Leg] = []

        # 1. Flight Schedules (Commercial airports, distance >= 250 km)
        if orig.place_type == PlaceType.AIRPORT and dest.place_type == PlaceType.AIRPORT and dist_km >= 250.0:
            daily_legs.extend(self._generate_flights(orig, dest, dist_km, target_date, seed_int))

        # 2. Rail Schedules (Rail stations, 40 km <= distance <= 3500 km)
        if orig.place_type == PlaceType.RAIL_STATION and dest.place_type == PlaceType.RAIL_STATION and 40.0 <= dist_km <= 3500.0:
            daily_legs.extend(self._generate_trains(orig, dest, dist_km, target_date, seed_int))

        # 3. Intercity Bus Schedules (Bus terminals or Tier-1/2 rail stations for regional hops <= 850 km)
        is_bus_eligible = (
            (orig.place_type == PlaceType.BUS_TERMINAL or orig.tier <= 2)
            and (dest.place_type == PlaceType.BUS_TERMINAL or dest.tier <= 2)
            and 20.0 <= dist_km <= 850.0
        )
        if is_bus_eligible:
            daily_legs.extend(self._generate_buses(orig, dest, dist_km, target_date, seed_int))

        return daily_legs

    def _generate_trains(
        self, orig: Place, dest: Place, dist_km: float, target_date: datetime.date, seed: int
    ) -> list[Leg]:
        """Generate plausible train schedules between two stations."""
        legs: list[Leg] = []
        speed_cfg = self._config.get("speed_profile_kmh", {}).get("TRAIN", {})
        avg_speed = speed_cfg.get("avg", 70.0)
        fare_cfg = self._config.get("fare_rate_paise_per_km", {}).get("TRAIN", {})

        # Departure count depends on distance and importance
        if dist_km <= 300:
            departure_hours = [6, 8, 11, 14, 17, 19, 21]
        elif dist_km <= 900:
            departure_hours = [6, 12, 16, 20, 22]
        else:
            departure_hours = [7, 15, 20]

        train_types = [
            ("Vande Bharat Express", 85.0, fare_cfg.get("ac2", 220), "20800"),
            ("Superfast Express", 70.0, fare_cfg.get("ac3", 145), "12950"),
            ("Express Mail", 60.0, fare_cfg.get("sleeper", 55), "11040"),
            ("Intercity SF", 72.0, fare_cfg.get("ac3", 145), "12120"),
        ]

        for i, hour in enumerate(departure_hours):
            leg_seed = (seed + i * 997) % (2**31)
            minute_offset = (leg_seed % 9) * 5  # 0 to 40 mins in 5 min steps
            dep_dt = datetime(
                target_date.year, target_date.month, target_date.day, hour, minute_offset, tzinfo=IST
            )

            t_idx = (leg_seed + i) % len(train_types)
            t_name, t_speed, rate_paise, num_prefix = train_types[t_idx]

            # Calculate duration in minutes (plus 10m buffer for stops)
            duration_mins = int((dist_km / t_speed) * 60) + 15
            arr_dt = dep_dt + timedelta(minutes=duration_mins)

            train_num = int(num_prefix) + (leg_seed % 80)
            fare_paise = max(8000, int(dist_km * rate_paise))  # Minimum ₹80

            legs.append(
                Leg(
                    leg_id=f"leg_train_{orig.code}_{dest.code}_{dep_dt.strftime('%H%M')}_{i}",
                    origin_id=orig.id,
                    destination_id=dest.id,
                    mode=TransitMode.TRAIN,
                    departure_time=dep_dt,
                    arrival_time=arr_dt,
                    duration_minutes=duration_mins,
                    distance_km=dist_km,
                    fare_paise=fare_paise,
                    operator_name="Indian Railways",
                    identifier=f"{t_name} #{train_num}",
                    is_simulated=True,
                )
            )

        return legs

    def _generate_buses(
        self, orig: Place, dest: Place, dist_km: float, target_date: datetime.date, seed: int
    ) -> list[Leg]:
        """Generate plausible bus schedules between two hubs."""
        legs: list[Leg] = []
        speed_cfg = self._config.get("speed_profile_kmh", {}).get("BUS", {})
        avg_speed = speed_cfg.get("avg", 48.0)
        fare_cfg = self._config.get("fare_rate_paise_per_km", {}).get("BUS", {})

        departure_hours = [7, 9, 13, 16, 20, 22] if dist_km <= 350 else [18, 20, 22]
        operators = [
            ("State Express AC", avg_speed, fare_cfg.get("ac_sleeper", 175)),
            ("Intercity Deluxe", avg_speed * 0.9, fare_cfg.get("ordinary", 85)),
            ("Premium Multi-Axle Volvo", avg_speed * 1.1, fare_cfg.get("ac_sleeper", 175) + 30),
        ]

        for i, hour in enumerate(departure_hours):
            leg_seed = (seed + i * 613) % (2**31)
            minute = (leg_seed % 12) * 5
            dep_dt = datetime(
                target_date.year, target_date.month, target_date.day, hour, minute, tzinfo=IST
            )

            op_idx = (leg_seed + i) % len(operators)
            op_name, op_speed, rate_paise = operators[op_idx]

            duration_mins = int((dist_km / op_speed) * 60) + 10
            arr_dt = dep_dt + timedelta(minutes=duration_mins)
            fare_paise = max(6000, int(dist_km * rate_paise))  # Minimum ₹60

            legs.append(
                Leg(
                    leg_id=f"leg_bus_{orig.code}_{dest.code}_{dep_dt.strftime('%H%M')}_{i}",
                    origin_id=orig.id,
                    destination_id=dest.id,
                    mode=TransitMode.BUS,
                    departure_time=dep_dt,
                    arrival_time=arr_dt,
                    duration_minutes=duration_mins,
                    distance_km=dist_km,
                    fare_paise=fare_paise,
                    operator_name=op_name,
                    identifier=f"Bus {orig.code[:3]}-{dest.code[:3]}-{100 + i}",
                    is_simulated=True,
                )
            )

        return legs

    def _generate_flights(
        self, orig: Place, dest: Place, dist_km: float, target_date: datetime.date, seed: int
    ) -> list[Leg]:
        """Generate plausible flight schedules between two airports."""
        legs: list[Leg] = []
        flight_cfg = self._config.get("speed_profile_kmh", {}).get("FLIGHT", {})
        cruise_speed = flight_cfg.get("cruise_speed", 720.0)
        taxi_mins = flight_cfg.get("taxi_takeoff_landing_minutes", 40)
        fare_cfg = self._config.get("fare_rate_paise_per_km", {}).get("FLIGHT", {})

        base_fare = fare_cfg.get("base_fare_paise", 220000)
        rate_paise = fare_cfg.get("rate_per_km_paise", 380)

        # High volume corridors get more flights
        flight_hours = [6, 9, 13, 17, 20] if dist_km <= 1500 else [7, 14, 19]
        airlines = [
            ("IndiGo", "6E"),
            ("Air India", "AI"),
            ("Akasa Air", "QP"),
        ]

        for i, hour in enumerate(flight_hours):
            leg_seed = (seed + i * 443) % (2**31)
            minute = (leg_seed % 6) * 10
            dep_dt = datetime(
                target_date.year, target_date.month, target_date.day, hour, minute, tzinfo=IST
            )

            duration_mins = int((dist_km / cruise_speed) * 60) + taxi_mins
            arr_dt = dep_dt + timedelta(minutes=duration_mins)

            air_idx = (leg_seed + i) % len(airlines)
            airline_name, code_prefix = airlines[air_idx]
            flight_num = 100 + (leg_seed % 899)
            fare_paise = int(base_fare + dist_km * rate_paise)

            legs.append(
                Leg(
                    leg_id=f"leg_air_{orig.code}_{dest.code}_{dep_dt.strftime('%H%M')}_{i}",
                    origin_id=orig.id,
                    destination_id=dest.id,
                    mode=TransitMode.FLIGHT,
                    departure_time=dep_dt,
                    arrival_time=arr_dt,
                    duration_minutes=duration_mins,
                    distance_km=dist_km,
                    fare_paise=fare_paise,
                    operator_name=airline_name,
                    identifier=f"{code_prefix}-{flight_num}",
                    is_simulated=True,
                )
            )

        return legs
