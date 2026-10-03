# SANKALP — Product Specification
**Version:** 1.0.0  
**Status:** Approved for Implementation (Phase 0)  
**Target Delivery:** High-Impact Portfolio & Engineering Demonstration  

---

## 1. Executive Summary & Problem Space

Every day in India, millions of passengers rely on Indian Railways, intercity state and private buses, and regional flights. When an unexpected disruption strikes—such as a cancelled train, derailment, dense fog alert, or massive delay—passengers are thrust into chaos. 

Existing travel platforms (IRCTC, RedBus, MakeMyTrip, Google Flights) operate in strict silos:
- They assume static schedules and do not calculate cumulative cascade failure probabilities across transfers.
- They do not combine disparate modes (e.g., taking an intercity bus to an airport hub to catch a flight).
- They lack intelligent recovery re-planning when a traveller is already mid-journey and a connecting leg is compromised.

**SANKALP** (संकेत / संकल्प: *Resolute Journey Recovery*) is an autonomous multi-modal journey recovery platform designed specifically for Indian transit. When a journey is cancelled or delayed, SANKALP ingests the passenger's current location, required destination, strict arrival deadline, and budget. It computes multi-modal routes across rail, bus, and flight, runs 10,000 Monte Carlo delay simulations to determine real on-time arrival probabilities, and presents exactly three clear choices: **Safest**, **Balanced**, and **Cheapest**.

> **Crucial Portfolio Distinction:**  
> SANKALP is an engineering portfolio project demonstrating algorithmic rigor, statistical modeling, clean separation of concerns, and tasteful minimalist UI design. It does not process real payments or book real tickets. All schedule inventory is clearly labeled as **"Simulated schedules"**.

---

## 2. User Personas & Core Scenarios

### Persona A: The Time-Critical Commuter ("The Interview Candidate")
- **Scenario:** Ravi is travelling from Pune to Mumbai for an in-person job interview at 2:00 PM. At 7:30 AM, his Deccan Queen express train is cancelled due to track maintenance at the Bhor Ghat.
- **Pain Point:** Cannot risk arriving late. Needs the route with the highest statistical certainty of arriving before 1:30 PM, even if it requires an AC Shivneri bus or shared taxi to Dadar.
- **SANKALP Value:** Delivers the **Safest** plan with an explicit $P(\text{on-time})$ confidence score (e.g., 96% ± 0.4%) and buffer cushion.

### Persona B: The Budget-Conscious Long-Distance Traveller ("The Student")
- **Scenario:** Ananya is travelling from Gorakhpur to New Delhi with a strict budget cap of ₹1,200. Her sleeper train is cancelled.
- **Pain Point:** Flights are unaffordable (₹4,500+). Needs an alternative combination of regional express trains and state transport buses that stays strictly within budget.
- **SANKALP Value:** Delivers the **Cheapest** plan guaranteed under budget, while enforcing minimum connection safety.

### Persona C: The Stranded Mid-Route Traveller ("The Broken Connection")
- **Scenario:** Priya is traveling from Kolkata to Bhopal with a planned train transfer at Jabalpur. Her first train suffers a 90-minute delay due to signal failure.
- **Pain Point:** Her connecting train departs before she arrives. What now?
- **SANKALP Value:** The **Simulate a Delay** engine detects that $P(\text{on-time})$ drops below viable limits, triggers an instant on-demand re-plan, and redirects her to an intercity bus departing from Jabalpur bus stand directly to Bhopal.

---

## 3. Product Scope & Functional Requirements

### 3.1 Universal Geographic Coverage
- **FR-01: Zero Hardcoding.** The application logic must accept *any* valid origin and destination in India. No city, station name, train number, or venue may be hardcoded into decision algorithms or API routing logic.
- **FR-02: Place Resolution & Autocomplete.** The system bundles an open-licensed dataset of Indian transit hubs (railway stations, airport IATA codes, and intercity bus terminals) with geographic coordinates (latitude, longitude) and zone/hub metadata.
- **FR-03: Explicit Corridor Failure.** If a corridor cannot be served within the deadline and budget (e.g., impossible geography or insufficient time), the system returns an explicit, explanatory empty state. It will *never* silently fall back to a dummy route.

### 3.2 Search & Parameters
- **FR-04: Mandatory Search Inputs:**
  - `origin_id`: Departure place/station ID or name.
  - `destination_id`: Destination place/station ID or name.
  - `deadline`: Strict ISO-8601 target arrival timestamp with explicit timezone (`Asia/Kolkata`).
  - `budget_inr`: Maximum budget in Indian Rupees (converted internally to integer paise: $1\text{ INR} = 100\text{ paise}$).
  - `earliest_departure`: Optional earliest departure time (defaults to current time in `Asia/Kolkata`).

### 3.3 Transparent Data Disclosure
- **FR-05: Simulation Disclosure.** In accordance with the honest data mandate, every UI card, API payload, and view renders the explicit disclosure: **"Simulated schedules"**. At no point are schedules presented as live IRCTC or GDS inventory.

### 3.4 The Recommendation Triad (Pareto Selection)
Instead of overwhelming the user with dozens of unranked options, SANKALP filters the candidate graph search into the Pareto-optimal frontier and extracts exactly three options:
1. **Safest:** Maximizes on-time probability $P(\text{on-time})$ while respecting budget and minimum buffers.
2. **Balanced:** Maximizes a multi-attribute utility function balancing on-time probability, buffer margin, price, and comfort.
3. **Cheapest:** Minimizes monetary cost among plans meeting an acceptable baseline reliability threshold ($P(\text{on-time}) \ge 0.70$).

- **FR-06: Plain-Language Justification.** Each of the 3 recommended options contains a 1-sentence plain-English reason explaining why it was selected (e.g., *"Highest on-time arrival confidence (95.2%) with a 75-minute safety buffer at Kanpur"*).
- **FR-07: Plain-Language Pruning Explanations.** For candidates that were pruned, the response provides an explicit exclusion rationale (e.g., *"Excluded: Arrives at 6:42 PM, which is 42 minutes past your 6:00 PM deadline"* or *"Excluded: Transfer slack at Itarsi (18 mins) is below the required 30 mins minimum"*).

### 3.5 Approval & Single-Use Token Flow
- **FR-08: Zero Financial Storage.** SANKALP never collects card details, UPI IDs, bank pins, or personal financial data.
- **FR-09: Single-Use Cryptographic Approval Token.**
  - When the user selects an itinerary and navigates to `/confirm`, the backend generates a short-lived, single-use cryptographically signed token (TTL: 15 minutes).
  - Approving the plan sends a POST request with the token.
  - The server verifies the token, marks it as redeemed in an atomic SQLite transaction, and records an audit log entry.
  - Any attempt to reuse the token, submit an expired token, or forge an itinerary fails with HTTP 400/410.
- **FR-10: Operator Handoff Mock.** Upon successful approval, the UI displays a confirmation screen noting that in a production deployment, this step hands off to the respective transport operator booking portals.

### 3.6 Disruption Simulation & On-Demand Re-Planning
- **FR-11: Interactive Delay Injection.** On the `/trip` page, the user can inspect the approved plan and trigger a disruption (e.g., select Leg 1 and inject a +60 min delay).
- **FR-12: Instant Recalculation.** The backend recalculates the cascaded arrival distribution and new on-time probability on demand (no background queues).
- **FR-13: Dynamic Re-route Resolution.** If the injected delay causes a missed transfer or causes $P(\text{on-time})$ to drop below 50%, SANKALP automatically invokes the engine from the disrupted location at the delayed timestamp to find and present an immediate replacement itinerary.

---

## 4. Non-Functional Requirements & Design Principles

| Dimension | Specification | Verification Method |
|---|---|---|
| **Response Latency** | Engine search + 10,000 Monte Carlo trials under 350ms median; API end-to-end under 500ms. | Automated benchmark suite in CI (`tests/benchmark_test.py`). |
| **Code Simplicity** | Pure Python standard library + NumPy for engine. No complex ORMs, no microservices, clean type annotations. | Code review & strict linter rules. |
| **Responsiveness** | Fluid responsive layout from 360px (mobile) to 1440px (desktop). | Playwright visual viewport tests at 375px, 768px, and 1280px. |
| **Accessibility** | High-contrast palette, semantic HTML, ARIA landmarks, full keyboard operability. | WCAG 2.1 AA audit with Chrome DevTools MCP. |
| **Determinism** | Identical search inputs + seed produce 100% identical itineraries and simulation metrics. | Hypothesis property test (`test_determinism`). |
| **Financial Units** | All monetary calculations in integer paise ($1\text{ INR} = 100\text{ paise}$). Never use floating-point numbers for currency. | Type checking & unit tests. |

---

## 5. UI/UX Specifications (Based on Stitch Design 5680212938138663204)

The user experience strictly follows the minimalist aesthetic established in Stitch project `5680212938138663204`:
- **Clean Aesthetic:** White/off-white background (`#f8fafc` / `#ffffff`), thin borders (`#e2e8f0`), restrained typography (Inter), single primary accent (deep teal/emerald `#005c55` / `#0f766e`).
- **Four Core Views:**
  1. **Home (`/`):** Centered search box with Origin, Destination, Deadline picker, Budget field, Swap button, and quick-fill corridor chips.
  2. **Results (`/results`):** 3-card comparison grid highlighting *Safest*, *Balanced*, and *Cheapest*, complete with arrival time, price, probability badge, and "Select route" action.
  3. **Confirm (`/confirm`):** Detailed itinerary breakdown, leg-by-leg timeline, transfer buffers, price breakdown, and one-click "Confirm and book" approval action protected by token.
  4. **Trip & Simulator (`/trip`):** Active journey sentinel view displaying live remaining buffer, timeline nodes, and an interactive "Simulate Delay" control with instant re-plan comparison.

---

## 6. Open Product Questions for User Alignment

1. **Station Dataset Granularity:** Should the bundled dataset prioritize the top ~500 most active Indian railway stations, metro airports, and major interstate bus terminals, or a broader set of ~2,000+ stations? (Recommended: Top ~600 primary stations + 35 major airports + 100 bus hubs for optimal search speed and realistic regional connectivity).
2. **Transit Modes in V1:** Rail, Intercity Bus, and Domestic Flights are included. Should local feeder transit (e.g. Metro / Cab transfer between an airport and railway station within the same city hub) be modeled as a fixed transfer buffer or as distinct legs? (Recommended: Modeled as an inter-modal transfer buffer with fixed transfer time and fare table).
3. **Budget Overflow Policy:** If no route exists under the user's budget, should the engine return an explicit empty state explaining the budget shortfall, or should it show the cheapest available route with a prominent "Exceeds budget by ₹X" warning? (Recommended: Return an explicit empty state stating the minimum budget required, honoring the strict budget constraint).
