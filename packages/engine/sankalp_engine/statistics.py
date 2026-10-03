"""Statistical utilities and confidence intervals for SANKALP.

Design Principles:
- Pure functions using standard library math and numpy.
- Wilson Score 95% confidence interval for binomial proportions.
- Lognormal delay sampling parameters calibrated to Indian transport modes.
"""

from __future__ import annotations

import math
from typing import Tuple
import numpy as np

# Standard 95% two-tailed critical value for normal distribution
Z_95 = 1.959963984540054


def wilson_score_interval(successes: int, trials: int, confidence_z: float = Z_95) -> Tuple[float, float]:
    """Calculate the Wilson Score 95% confidence interval for a binomial proportion.
    
    Why Wilson Score instead of Normal Approximation (Wald):
    - When probability is close to 1.0 (e.g. 98% on-time) or 0.0, the Wald interval
      (p ± z*sqrt(p(1-p)/n)) produces invalid values > 1.0 or < 0.0 and undercovers.
    - Wilson Score interval is asymmetric, strictly bounded in [0, 1], and remains
      accurate even at extreme probabilities or with moderate sample sizes.
    """
    if trials <= 0:
        return 0.0, 0.0

    p_hat = successes / trials
    z = confidence_z
    z2 = z * z
    n = float(trials)

    denominator = 1.0 + (z2 / n)
    center = (p_hat + (z2 / (2.0 * n))) / denominator

    # Standard error term inside the square root
    variance_term = (p_hat * (1.0 - p_hat) / n) + (z2 / (4.0 * (n ** 2)))
    spread = (z * math.sqrt(max(0.0, variance_term))) / denominator

    ci_low = max(0.0, center - spread)
    ci_high = min(1.0, center + spread)

    return ci_low, ci_high


def sample_lognormal_delays(
    mu: float,
    sigma: float,
    trials_count: int,
    rng: np.random.Generator,
    min_delay_minutes: float = 0.0,
) -> np.ndarray:
    """Generate vectorized log-normal delays in minutes.
    
    Transit delays in India exhibit strong right-skew: most departures run with
    nominal delays (0-15 mins), while a distinct right tail experiences significant
    delays due to signaling, crossing, or traffic bottlenecks.
    """
    # Generate log-normal samples: delay = exp(N(mu, sigma^2))
    raw_delays = rng.lognormal(mean=mu, sigma=sigma, size=trials_count)
    if min_delay_minutes > 0.0:
        raw_delays = np.maximum(min_delay_minutes, raw_delays)
    return raw_delays
