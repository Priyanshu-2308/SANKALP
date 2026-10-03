# SANKALP — Technical Interview Deep Dive & Engineering Notes

This document provides in-depth technical explanations and answers to 10 key architectural, mathematical, and algorithmic questions about SANKALP. It is designed to demonstrate deep systems thinking, statistical rigor, and pragmatic software engineering.

---

### Q1: Why use a vectorized Monte Carlo simulation with Log-Normal distributions instead of simple expected values or standard deviations?

**Answer:**
Transit delays are fundamentally **non-linear, strictly non-negative, and right-skewed with heavy tails**. Simple expected-value models fail for two mathematical reasons:

1. **The Maximum Operator and Jensen's Inequality:**
   In multi-leg transit, the arrival time at destination is governed by connection checks:
   $$\text{Arrival}_{i+1} = \max(\text{Scheduled Departure}_{i+1}, \text{Actual Arrival}_i + \text{MCT}) + \text{Duration}_{i+1}$$
   Because the $\max$ operator is convex, Jensen's inequality dictates:
   $$\mathbb{E}[\max(X, Y)] \ge \max(\mathbb{E}[X], \mathbb{E}[Y])$$
   Using expected values $\mathbb{E}[X]$ systematically **underestimates transfer failure rates** and produces overly optimistic on-time arrival probabilities.

2. **Heavy-Tailed Asymmetry:**
   A train cannot arrive 2 hours earlier than scheduled, but it can easily be 4 hours late. A Gaussian distribution $\mathcal{N}(\mu, \sigma^2)$ is symmetric and predicts non-zero probabilities for negative delays (arriving in negative time). 
   
   A **Log-Normal distribution** $\text{Delay} \sim \text{Lognormal}(\mu, \sigma^2)$ enforces:
   - $\text{Delay} \in [0, \infty)$
   - Low median delay with a long, fat tail representing extreme disruption events (derailments, fog, signal failures).

By running 10,000 empirical draws through the actual transfer timeline, we capture the exact probability mass that spills past the connection threshold.

---

### Q2: Why compute Wilson Score confidence intervals instead of normal Wald approximations?

**Answer:**
The standard textbook confidence interval (the Wald interval):
$$\hat{p} \pm z \sqrt{\frac{\hat{p}(1-\hat{p})}{n}}$$
relies on the Central Limit Theorem and assumes a normal distribution around the sample proportion $\hat{p}$.

However, the Wald interval breaks down catastrophically in two edge cases common in transit reliability:
1. **Extreme Proportions ($\hat{p} \to 1.0$ or $\hat{p} \to 0.0$):**
   If a high-buffer route succeeds in all 10,000 trials ($\hat{p} = 1.0$), the Wald standard error is $\sqrt{\frac{1(0)}{n}} = 0$, producing a misleading confidence interval of $[1.0, 1.0]$—falsely claiming 100% certainty with zero margin of error. Worse, for smaller sample sizes near boundaries, it can produce nonsensical bounds $> 1.0$ or $< 0.0$.
2. **Asymmetric Coverage:**
   The true binomial distribution near 1.0 is highly skewed; an interval centered symmetrically around $\hat{p}$ has poor non-coverage properties.

The **Wilson Score Interval** inverts the score test under the null hypothesis:
$$p \approx \frac{\hat{p} + \frac{z^2}{2n} \pm z \sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$
It guarantees:
- Bounds are strictly bounded in $[0, 1]$.
- Even if $\hat{p} = 1.0$ at $n = 10,000$, Wilson yields $[0.9996, 1.0000]$ at $z = 1.96$ (95% confidence), accurately reflecting that future runs could encounter extreme rare-tail failures.

---

### Q3: Why use Pareto multi-objective optimization rather than a single weighted-sum utility function?

**Answer:**
A standard shortcut in routing algorithms is to minimize a linear cost function:
$$\text{Cost} = w_1 \cdot \text{Duration} + w_2 \cdot \text{Fare} - w_3 \cdot P(\text{on-time})$$

This approach suffers from severe drawbacks:
1. **Arbitrary Hyperparameters:** Any choice of weights ($w_1, w_2, w_3$) imposes an arbitrary trade-off that cannot fit different traveller personas (e.g., an executive catching an international flight vs. a student travelling on a budget).
2. **Inability to Find Non-Convex Pareto Points:** Linear combinations cannot discover solutions residing on non-convex regions of the trade-off frontier.
3. **Loss of Explainability:** A user cannot understand what a score of `0.784` means, but they immediately understand:
   - *"This is the Safest route (99.7% on-time, +60m buffer)."*
   - *"This is the Cheapest route (₹450, 4 hours longer)."*

SANKALP identifies the **Pareto-dominant set** (solutions where no objective can be improved without degrading another) and extracts the canonical triad:
- **Safest:** Absolute maximum $P(\text{on-time})$ and safety buffer.
- **Balanced:** Knee point of the Pareto frontier offering the best marginal gain in reliability per rupee and minute.
- **Cheapest:** Minimum monetary cost satisfying the deadline.

---

### Q4: How do you mathematically guarantee that an over-budget plan never outscores an affordable plan?

**Answer:**
In [`scoring.py`](packages/engine/sankalp_engine/scoring.py), we enforce the **Hard Budget Invariant**:

$$\text{If } \text{Fare} > \text{Budget}: \quad \text{Utility} = \min(0.34, \text{Utility}_{\text{raw}} \times 0.50)$$

Conversely, any viable itinerary that meets the user's budget and has an arrival probability $P(\text{on-time}) \ge 0.65$ has a base utility:
$$\text{Utility}_{\text{viable}} \ge 0.40$$

Because $\max(\text{Utility}_{\text{over-budget}}) = 0.34 < 0.40 \le \min(\text{Utility}_{\text{viable}})$, it is a mathematical impossibility for an over-budget route to outrank an affordable, viable itinerary. This ensures financial safety without dropping emergency alternatives if no affordable route exists.

---

### Q5: How did you achieve a median latency of ~36ms for 10,000 trials in Python?

**Answer:**
Naive Python loops iterating $10,000$ times across multiple legs would take $1.5$ to $3.0$ seconds due to Python's dynamic dispatch, bytecode interpretation, and object allocation overhead.

In [`simulation.py`](packages/engine/sankalp_engine/simulation.py), we achieve C-level speeds using **vectorized NumPy operations**:
1. **Pre-allocated 2D Matrices:** For an itinerary with $L$ legs, we generate the entire delay matrix of shape $(L, 10000)$ in a single call:
   ```python
   delays = np.random.lognormal(mean=mu_vec, sigma=sigma_vec, size=(trials, L)).T
   ```
2. **Contiguous Memory & SIMD:** The random number generator operates in continuous C memory buffers with hardware vectorization (AVX2/AVX-512).
3. **Vectorized Transfer Checks:** We simulate cascading delays across connections using cumulative additions and vectorized boolean masks rather than per-trial branching.
4. **Result:** Running 10,000 trials across an itinerary takes **$\approx 8$ to $12\text{ms}$**, allowing SANKALP to evaluate dozens of candidate paths within a **$36.7\text{ms}$ median total response time**.

---

### Q6: How do you prevent double-booking or replay attacks without distributed locks (e.g. Redis)?

**Answer:**
Instead of introducing distributed infrastructure like Redis or ZooKeeper, SANKALP leverages **SQLite's ACID transactions and Write-Ahead Logging (WAL)** in [`database.py`](apps/api/app/database.py).

We enforce an **atomic conditional update** pattern:
```sql
UPDATE approval_tokens
SET is_used = 1, used_at = ?
WHERE token = ? 
  AND is_used = 0 
  AND expires_at > ?;
```

**Why this is race-condition proof:**
1. SQLite in WAL mode allows concurrent readers while serializing write transactions with immediate table locking.
2. The database engine evaluates `is_used = 0 AND expires_at > ?` inside the atomic write lock.
3. If two concurrent requests arrive with the identical token, exactly one transaction updates `rowcount = 1`. The second concurrent request matches `rowcount = 0`.
4. If `rowcount == 0`, the FastAPI endpoint immediately raises **`HTTP 410 Gone`**, guaranteeing single-use idempotency with zero external network overhead.

---

### Q7: Explain cascading transfer failure dynamics in multi-modal networks and Minimum Connection Time (MCT).

**Answer:**
A multi-modal journey consists of ordered legs $L_1, L_2, \dots, L_k$ separated by transfers $T_1, \dots, T_{k-1}$.
A transfer is valid if and only if:
$$\text{Scheduled Departure}(L_{i+1}) - \text{Scheduled Arrival}(L_i) \ge \text{MCT}(M_i, M_{i+1})$$

In SANKALP:
- **Intramodal Rail Transfer:** $MCT = 20\text{ minutes}$ (platform change within the same station).
- **Intermodal Transfer (Train to Airport / Bus):** $MCT = 90\text{ to } 120\text{ minutes}$ (includes city transit, baggage retrieval, airport security queues).

**Cascading Failure Mechanism:**
During simulation trial $t$:
$$\text{Actual Arrival}_t(L_i) = \text{Scheduled Arrival}(L_i) + \text{Injected Delay}_t(L_i)$$
If:
$$\text{Scheduled Departure}(L_{i+1}) < \text{Actual Arrival}_t(L_i) + \text{MCT}(M_i, M_{i+1})$$
The passenger misses connection $L_{i+1}$. Because subsequent legs are departed, the transfer is severed. In trial $t$, the passenger arrival time at final destination becomes $\infty$ (or penalty failure), correctly pulling down $P(\text{on-time})$ and increasing the `missed_connection_rate` metric.

---

### Q8: Why did you write an AST-based guard test in the test suite?

**Answer:**
In portfolio and interview projects, a common anti-pattern is **"demo cheating"**—hardcoding specific station names, routes, or train numbers (e.g. `if origin == "DELHI": return MOCK_DELHI_ROUTE`).

In [`tests/guards/test_no_hardcoded_places.py`](tests/guards/test_no_hardcoded_places.py), we enforce an automated **Abstract Syntax Tree (AST)** guard:
1. It recursively traverses the AST of every `.py` file in `packages/engine` and `apps/api/app`.
2. It inspects all string constants (`ast.Constant`) while ignoring docstrings.
3. It checks tokens against a forbidden list of major Indian cities (`mumbai`, `delhi`, `kolkata`, `chennai`, etc.) and station codes (`ndls`, `csmt`, `hwh`, etc.).
4. If an engineer hardcodes a city or station name into algorithmic code, the test suite **fails immediately in CI**.

This guarantees that the decision engine is purely algorithmic and operates strictly over the bundled graph dataset.

---

### Q9: How does the deterministic seeded schedule generator work, and why not use live APIs or random seeds?

**Answer:**
1. **Honest Data Architecture:** Indian Railways (IRCTC) and domestic flight GDS APIs do not offer open, free, unauthenticated public endpoints. Using unofficial scrapers leads to broken builds and CAPTCHA failures.
2. **Determinism via Hashing:**
   [`SeededScheduleGenerator`](packages/engine/sankalp_engine/generator.py) uses pseudo-random number generators seeded with:
   $$\text{Seed} = \text{hash}\Big(\text{origin\_id} + \text{dest\_id} + \text{date\_str} + \text{"sankalp\_v1"}\Big)$$
   This ensures that querying the same corridor on the same date always returns the identical schedule, making property tests and benchmarks completely reproducible.
3. **Geographic Realism:**
   Leg distances are computed using the **Haversine formula** across verified station coordinates (`data/stations.json`). Transit speeds and fares are derived from realistic empirical Indian transit parameters (Train: 65 km/h @ ₹1.2/km; Flight: 650 km/h @ ₹4.5/km; Bus: 45 km/h @ ₹1.5/km).

---

### Q10: What architectural trade-offs did you make for this project vs. a production enterprise system?

**Answer:**

| Dimension | SANKALP Implementation | Enterprise Production Alternative | Rationale & Trade-off |
|---|---|---|---|
| **Architecture** | Clean Decoupled Monorepo | Event-Driven Microservices (Kafka) | Monorepo eliminates network serialization overhead, deploys as a single unit, and keeps the code readable for code review. |
| **Storage** | SQLite 3 (WAL Mode) | PostgreSQL + Redis Cluster | SQLite provides zero external dependencies, embedded sub-millisecond queries, and atomic concurrency without database management overhead. |
| **Pathfinding** | Time-Dependent BFS (up to 2 transfers) with geographic bounding | Contraction Hierarchies (RAPTOR / CSA / GraphHopper) | For regional transit with $< 200$ primary hubs, pruned BFS runs in $< 50\text{ms}$ with zero preprocessing compilation time. |
| **Delay Data** | Log-Normal Seeded Monte Carlo Simulation | Live GPS Telemetry / GTFS-RT Stream Processing | Live telemetry requires multi-million dollar API access; empirical Monte Carlo captures the true statistical shape of disruptions. |
| **Authentication** | Ephemeral Single-Use Approval Tokens | OAuth2 / OIDC / JWT + Payment Gateway | Zero financial exposure and zero PII storage ensures privacy, zero PCI-DSS scope, and pure focus on decision intelligence. |
