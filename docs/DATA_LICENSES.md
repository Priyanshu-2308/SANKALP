# SANKALP — Data Provenance & Open Licenses

## 1. Overview
SANKALP bundles a cleaned, verified dataset of Indian transit hubs in `data/stations.json` along with default connection and mode parameters in `data/connections_mct.json` and `data/generator_config.json`.

In accordance with Section 3 of the product brief, SANKALP explicitly discloses the sources, licenses, and synthetic boundaries of all data.

---

## 2. Bundled Station & Place Dataset (`data/stations.json`)

### Sources
1. **Indian Railways Stations & Coordinates:**
   - **Source:** Ministry of Railways, Government of India via the Open Government Data (OGD) Platform India ([data.gov.in](https://data.gov.in)).
   - **License:** Government Open Data License - India (GODL) under the National Data Sharing and Accessibility Policy (NDSAP).
   - **Permitted Uses:** Worldwide, royalty-free, non-exclusive use, reuse, adaptation, and sharing with attribution.
   - **Data Extracted:** Official Station Codes (e.g. `NDLS`, `CSMT`, `PUNE`, `HWH`), official English station names, railway zones, and geographical coordinates (latitude/longitude).

2. **Indian Commercial Airports:**
   - **Source:** OpenFlights Airport Database and OurAirports India dataset.
   - **License:** Public Domain / Open Database License (ODbL).
   - **Data Extracted:** IATA 3-letter airport codes (e.g. `DEL`, `BOM`, `BLR`), official airport names, runway reference coordinates.

3. **Interstate Bus Terminals (ISBTs):**
   - **Source:** OpenStreetMap contributors.
   - **License:** Open Data Commons Open Database License (ODbL 1.0).
   - **Data Extracted:** Major state transport bus depots (e.g. Maharana Pratap ISBT Delhi, Swargate Pune, Kempegowda Bus Station Bengaluru), verified coordinates.

---

## 3. Synthetic Schedule & Delay Model Disclosure

**CRITICAL MANDATE:**  
Live Indian rail availability, reservation status, and real-time bus telemetry are proprietary and not freely available through public APIs. SANKALP **does not scrape, reverse-engineer, or automate** IRCTC, RedBus, or any private booking portal.

Instead:
- All itineraries, schedules, seat availabilities, and fare quotes are generated deterministically by the `SeededScheduleGenerator` engine.
- Geographic distances are strictly calculated using the Haversine formula over real latitude and longitude coordinates.
- Transit times and speeds are calibrated to realistic mode performance (Superfast rail ~65–95 km/h, Intercity road bus ~40–60 km/h, Domestic air ~720 km/h cruise).
- Delay distributions are modeled using shifted log-normal distributions calibrated to Indian transport variability.
- Every simulated schedule is stamped with `"is_simulated": true` and labeled in the user interface as **"Simulated schedules"**.
