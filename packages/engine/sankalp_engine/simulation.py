"""Vectorized Monte Carlo simulation of multi-modal transit delays.

Design Principles:
- Vectorized 10,000 trials using NumPy for sub-30ms execution.
- Shifted log-normal distributions model right-skewed delays for Rail, Road, and Air.
- Cascading delay propagation: checks if transfer slack drops below Minimum Connection Time (MCT).
  If slack < MCT, the connection is broken and the trial is marked as failed.
- Computes P(on time) with Wilson Score 95% confidence intervals.
- Pure Python and NumPy, zero external I/O.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
import numpy as np

from .models import IST, Itinerary, SimulationMetrics, TransitMode
from .statistics import sample_lognormal_delays, wilson_score_interval

# Default calibrated parameters for Indian transit modes
DEFAULT_MODE_PARAMS = {
    TransitMode.TRAIN: {"mu": 2.65, "sigma": 0.75, "min_delay": 0.0},  # Median ~14m
    TransitMode.BUS: {"mu": 2.30, "sigma": 0.60, "min_delay": 0.0},    # Median ~10m
    TransitMode.FLIGHT: {"mu": 1.95, "sigma": 0.50, "min_delay": 0.0}, # Median ~7m
}


def simulate_itinerary_delays(
    itinerary: Itinerary,
    deadline: datetime,
    trials_count: int = 10000,
    seed: int = 42,
    mode_params: Optional[dict[TransitMode, dict[str, float]]] = None,
    injected_delays: Optional[dict[int, float]] = None,
) -> SimulationMetrics:
    """Run a vectorized Monte Carlo simulation to evaluate on-time arrival probability.
    
    Args:
        itinerary: The candidate itinerary to evaluate.
        deadline: The strict arrival deadline in Asia/Kolkata.
        trials_count: Number of simulation trials (default 10,000).
        seed: Seed for reproducible PRNG.
        mode_params: Optional overrides for log-normal parameters by mode.
        injected_delays: Optional dictionary mapping leg_index to fixed delay in minutes
                         (used by the disruption simulator).
    """
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=IST)

    params = mode_params or DEFAULT_MODE_PARAMS
    rng = np.random.default_rng(seed)

    # Convert deadline to minutes relative to scheduled final arrival
    # buffer_minutes > 0 means scheduled arrival is before the deadline
    scheduled_arrival = itinerary.arrival_time
    deadline_slack_minutes = (deadline - scheduled_arrival).total_seconds() / 60.0

    k = len(itinerary.legs)
    if k == 0:
        return SimulationMetrics(
            p_ontime=0.0,
            p_ontime_ci_low=0.0,
            p_ontime_ci_high=0.0,
            trials_count=trials_count,
            median_delay_minutes=0.0,
            p90_delay_minutes=0.0,
            missed_connection_rate=1.0,
        )

    # Boolean mask: True while the journey is still progressing (no broken connections)
    active_trials = np.ones(trials_count, dtype=bool)

    # Tracks the cumulative arrival delay (in minutes) at the end of each leg
    last_arrival_delay = np.zeros(trials_count, dtype=np.float64)

    for leg_idx, leg in enumerate(itinerary.legs):
        # 1. Sample or inject leg delay
        if injected_delays and leg_idx in injected_delays:
            # Fixed delay injected for simulation testing
            fixed_delay = float(injected_delays[leg_idx])
            leg_delay = np.full(trials_count, fixed_delay, dtype=np.float64)
        else:
            cfg = params.get(leg.mode, DEFAULT_MODE_PARAMS[TransitMode.TRAIN])
            leg_delay = sample_lognormal_delays(
                mu=cfg["mu"],
                sigma=cfg["sigma"],
                trials_count=trials_count,
                rng=rng,
                min_delay_minutes=cfg.get("min_delay", 0.0),
            )

        if leg_idx == 0:
            # First leg: arrival delay is simply the first leg's running delay
            last_arrival_delay = leg_delay
        else:
            # Transfer from leg_idx - 1 to leg_idx
            transfer = itinerary.transfers[leg_idx - 1]
            scheduled_transfer_minutes = float(transfer.wait_minutes)
            mct = float(transfer.min_connection_minutes)

            # Available slack at transfer in this trial:
            # slack = scheduled_wait - arrival_delay_from_previous_leg
            available_slack = scheduled_transfer_minutes - last_arrival_delay

            # Check if connection was missed
            # If available_slack < mct, passenger cannot make the connecting departure
            connection_missed = available_slack < mct
            active_trials = active_trials & (~connection_missed)

            # For successful connections, calculate if departure is delayed
            # If arrival + mct > scheduled_dep, departure is delayed by (mct - available_slack)
            departure_delay = np.maximum(0.0, mct - available_slack)

            # Arrival delay of this leg = departure delay + en-route running delay
            last_arrival_delay = departure_delay + leg_delay

    # At final destination:
    # A trial is on time iff:
    # 1. All connections were made (active_trials is True)
    # 2. Cumulative arrival delay <= deadline_slack_minutes
    on_time_mask = active_trials & (last_arrival_delay <= deadline_slack_minutes)
    successes = int(np.sum(on_time_mask))
    p_ontime = successes / float(trials_count)

    # Compute Wilson Score 95% Confidence Interval
    ci_low, ci_high = wilson_score_interval(successes, trials_count)

    # Missed connection rate across all transfers
    missed_count = int(np.sum(~active_trials))
    missed_connection_rate = missed_count / float(trials_count)

    # Delay statistics among completed journeys
    completed_delays = last_arrival_delay[active_trials]
    if len(completed_delays) > 0:
        median_delay = float(np.median(completed_delays))
        p90_delay = float(np.percentile(completed_delays, 90))
    else:
        median_delay = 999.0
        p90_delay = 999.0

    return SimulationMetrics(
        p_ontime=p_ontime,
        p_ontime_ci_low=ci_low,
        p_ontime_ci_high=ci_high,
        trials_count=trials_count,
        median_delay_minutes=median_delay,
        p90_delay_minutes=p90_delay,
        missed_connection_rate=missed_connection_rate,
    )
