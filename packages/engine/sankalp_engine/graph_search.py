"""Time-dependent multi-modal graph search.

Design Principles:
- Finds direct routes and connecting itineraries with up to 2 transfers.
- Strict enforcement of Minimum Connection Time (MCT) between consecutive legs.
- Time-bounded: prunes paths whose scheduled arrival exceeds the deadline minus safety buffer.
- Pure Python with no global mutable state, zero I/O.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple

from .datasource import TransportDataSource
from .models import (
    IST,
    ExclusionCode,
    ExclusionRationale,
    Itinerary,
    Leg,
    Transfer,
)


def find_candidate_itineraries(
    origin_id: str,
    destination_id: str,
    departure_after: datetime,
    deadline: datetime,
    data_source: TransportDataSource,
    max_transfers: int = 2,
    safety_buffer_minutes: int = 15,
    max_wait_minutes: int = 360,  # Max 6 hours layover
) -> Tuple[list[Itinerary], list[ExclusionRationale]]:
    """Execute time-dependent graph search to find valid itineraries.
    
    Returns:
        valid_itineraries: List of complete, feasible itineraries.
        pruned_rationales: Explanations for candidate paths that were pruned early.
    """
    if departure_after.tzinfo is None:
        departure_after = departure_after.replace(tzinfo=IST)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=IST)

    latest_allowed_arrival = deadline - timedelta(minutes=safety_buffer_minutes)

    valid_itineraries: list[Itinerary] = []
    pruned_rationales: list[ExclusionRationale] = []

    # -------------------------------------------------------------------------
    # 1. Direct Routes (0 Transfers)
    # -------------------------------------------------------------------------
    direct_legs = data_source.find_direct_legs(
        origin_id=origin_id,
        destination_id=destination_id,
        departure_after=departure_after,
        departure_before=deadline,
    )

    for leg in direct_legs:
        if leg.arrival_time <= latest_allowed_arrival:
            itin = Itinerary(
                itinerary_id=f"itin_dir_{leg.leg_id}_{uuid.uuid4().hex[:6]}",
                legs=[leg],
                transfers=[],
                total_duration_minutes=leg.duration_minutes,
                total_fare_paise=leg.fare_paise,
                departure_time=leg.departure_time,
                arrival_time=leg.arrival_time,
            )
            valid_itineraries.append(itin)
        else:
            diff_mins = int((leg.arrival_time - deadline).total_seconds() / 60.0)
            pruned_rationales.append(
                ExclusionRationale(
                    itinerary_summary=f"Direct {leg.operator_name} ({leg.identifier})",
                    code=ExclusionCode.DEADLINE_BREACH,
                    reason_text=(
                        f"Arrives at {leg.arrival_time.strftime('%I:%M %p')}, "
                        f"which is {max(1, diff_mins)} minutes past your deadline."
                    ),
                )
            )

    if max_transfers < 1:
        return valid_itineraries, pruned_rationales

    # -------------------------------------------------------------------------
    # 2. Routes with 1 Transfer (Origin -> H1 -> Destination)
    # -------------------------------------------------------------------------
    candidate_hubs = data_source.find_candidate_connecting_hubs(
        origin_id=origin_id,
        destination_id=destination_id,
        max_hubs=10,
        max_detour_ratio=1.45,
    )

    for hub_id in candidate_hubs:
        hub_place = data_source.get_place(hub_id)
        hub_name = hub_place.name if hub_place else hub_id

        # First leg: Origin -> Hub
        legs_1 = data_source.find_direct_legs(
            origin_id=origin_id,
            destination_id=hub_id,
            departure_after=departure_after,
            departure_before=latest_allowed_arrival - timedelta(hours=1),
        )

        for l1 in legs_1:
            # Second leg: Hub -> Destination
            # Departure must be after l1 arrives + minimum conceivable buffer
            legs_2 = data_source.find_direct_legs(
                origin_id=hub_id,
                destination_id=destination_id,
                departure_after=l1.arrival_time + timedelta(minutes=15),
                departure_before=deadline,
            )

            for l2 in legs_2:
                wait_minutes = int((l2.departure_time - l1.arrival_time).total_seconds() / 60.0)
                mct = data_source.get_minimum_connection_time(l1.mode, l2.mode)

                if wait_minutes < mct:
                    # Connection time violated
                    pruned_rationales.append(
                        ExclusionRationale(
                            itinerary_summary=f"{l1.identifier} -> {l2.identifier} via {hub_name}",
                            code=ExclusionCode.CONNECTION_RISK,
                            reason_text=(
                                f"Transfer slack at {hub_name} is only {wait_minutes} mins, "
                                f"which is below the required {mct} mins minimum connection time."
                            ),
                        )
                    )
                    continue

                if wait_minutes > max_wait_minutes:
                    # Layover too long
                    continue

                if l2.arrival_time > latest_allowed_arrival:
                    diff_mins = int((l2.arrival_time - deadline).total_seconds() / 60.0)
                    pruned_rationales.append(
                        ExclusionRationale(
                            itinerary_summary=f"{l1.identifier} -> {l2.identifier} via {hub_name}",
                            code=ExclusionCode.DEADLINE_BREACH,
                            reason_text=(
                                f"Arrives at {l2.arrival_time.strftime('%I:%M %p')}, "
                                f"which is {max(1, diff_mins)} minutes past your deadline."
                            ),
                        )
                    )
                    continue

                # Valid 1-transfer itinerary found!
                total_duration = int((l2.arrival_time - l1.departure_time).total_seconds() / 60.0)
                total_fare = l1.fare_paise + l2.fare_paise
                transfer = Transfer(
                    place_id=hub_id,
                    arrival_time=l1.arrival_time,
                    departure_time=l2.departure_time,
                    wait_minutes=wait_minutes,
                    min_connection_minutes=mct,
                    mode_from=l1.mode,
                    mode_to=l2.mode,
                    is_intermodal=(l1.mode != l2.mode),
                )

                itin = Itinerary(
                    itinerary_id=f"itin_1t_{l1.leg_id}_{l2.leg_id}_{uuid.uuid4().hex[:6]}",
                    legs=[l1, l2],
                    transfers=[transfer],
                    total_duration_minutes=total_duration,
                    total_fare_paise=total_fare,
                    departure_time=l1.departure_time,
                    arrival_time=l2.arrival_time,
                )
                valid_itineraries.append(itin)

    # -------------------------------------------------------------------------
    # 3. Routes with 2 Transfers (if direct + 1-transfer yield <= 4 options)
    # -------------------------------------------------------------------------
    if max_transfers >= 2 and len(valid_itineraries) < 6 and len(candidate_hubs) >= 2:
        # Evaluate primary hub pairs
        for i in range(min(4, len(candidate_hubs))):
            h1 = candidate_hubs[i]
            for j in range(i + 1, min(6, len(candidate_hubs))):
                h2 = candidate_hubs[j]
                
                # Check legs 1, 2, 3
                l1_candidates = data_source.find_direct_legs(
                    origin_id, h1, departure_after, latest_allowed_arrival - timedelta(hours=3)
                )
                for l1 in l1_candidates[:2]:
                    mct1 = data_source.get_minimum_connection_time(l1.mode, l1.mode)
                    l2_candidates = data_source.find_direct_legs(
                        h1, h2, l1.arrival_time + timedelta(minutes=mct1), latest_allowed_arrival - timedelta(hours=1)
                    )
                    for l2 in l2_candidates[:2]:
                        wait1 = int((l2.departure_time - l1.arrival_time).total_seconds() / 60.0)
                        actual_mct1 = data_source.get_minimum_connection_time(l1.mode, l2.mode)
                        if wait1 < actual_mct1 or wait1 > max_wait_minutes:
                            continue

                        mct2 = data_source.get_minimum_connection_time(l2.mode, l2.mode)
                        l3_candidates = data_source.find_direct_legs(
                            h2, destination_id, l2.arrival_time + timedelta(minutes=mct2), deadline
                        )
                        for l3 in l3_candidates[:2]:
                            wait2 = int((l3.departure_time - l2.arrival_time).total_seconds() / 60.0)
                            actual_mct2 = data_source.get_minimum_connection_time(l2.mode, l3.mode)
                            if wait2 < actual_mct2 or wait2 > max_wait_minutes:
                                continue
                            if l3.arrival_time > latest_allowed_arrival:
                                continue

                            # Valid 2-transfer itinerary!
                            t1 = Transfer(
                                place_id=h1,
                                arrival_time=l1.arrival_time,
                                departure_time=l2.departure_time,
                                wait_minutes=wait1,
                                min_connection_minutes=actual_mct1,
                                mode_from=l1.mode,
                                mode_to=l2.mode,
                                is_intermodal=(l1.mode != l2.mode),
                            )
                            t2 = Transfer(
                                place_id=h2,
                                arrival_time=l2.arrival_time,
                                departure_time=l3.departure_time,
                                wait_minutes=wait2,
                                min_connection_minutes=actual_mct2,
                                mode_from=l2.mode,
                                mode_to=l3.mode,
                                is_intermodal=(l2.mode != l3.mode),
                            )
                            total_dur = int((l3.arrival_time - l1.departure_time).total_seconds() / 60.0)
                            itin = Itinerary(
                                itinerary_id=f"itin_2t_{l1.leg_id}_{l3.leg_id}_{uuid.uuid4().hex[:6]}",
                                legs=[l1, l2, l3],
                                transfers=[t1, t2],
                                total_duration_minutes=total_dur,
                                total_fare_paise=l1.fare_paise + l2.fare_paise + l3.fare_paise,
                                departure_time=l1.departure_time,
                                arrival_time=l3.arrival_time,
                            )
                            valid_itineraries.append(itin)

    return valid_itineraries, pruned_rationales
