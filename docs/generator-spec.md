# AirOps Nexus — Synthetic Data Generator Specification

**Status:** Approved Specification (Phase 0, Task P0-6 & P0-11)  
**Version:** 1.1 (Includes Task Executions, Usage Counters, and Logistics)  
**Primary Engine:** `app/engines/data_fusion/generator.py` (NumPy `Generator`, Faker)

---

## 1. Deterministic Seeding & Content Hashing

1. **Seed Sequence Architecture:**
   - The generator accepts a master 64-bit integer seed (e.g., `seed = 42`) and an `as_of` ISO timestamp.
   - Master randomness is initialized via `numpy.random.SeedSequence(seed)`. Independent child sequences are spawned per entity stream (assets, personnel, tasks, disruptions, executions).
2. **Dataset Fingerprinting:**
   - Once generation completes, all serialized entities are sorted canonically and hashed via SHA-256.
   - The resulting `dataset_hash` covers `(generator_version, seed, as_of, entities_payload)`. The test suite asserts that running the generator with the identical `(seed, as_of)` produces the exact same hash byte-for-byte.

---

## 2. Entity Distributions & Baseline Population

### 2.1 Operational Assets (Default: $N = 40$)
- **Types:**
  - `FIGHTER_MULTIROLE` (45%): Fast turnaround, high maintenance sensitivity.
  - `TRANSPORT_CARGO` (25%): Long duration sorties, high cargo capacity.
  - `RECON_SURVEILLANCE` (20%): Medium duration, specialized avionics payload.
  - `REFUELER_TANKER` (10%): High flight hour accrual, critical bottleneck.
- **Initial Health Score:** Beta distribution ($\alpha = 8, \beta = 2$) scaled to $[0.50, 1.00]$.
- **Usage Counters:**
  - `flight_hours`: Lognormal distribution ($\mu = 450, \sigma = 120$ hours).
  - `cycles`: Poisson distribution ($\lambda = 320$ takeoffs/landings).

### 2.2 Personnel & Qualifications (Default: $N = 120$)
- **Roles:** Pilots (35%), Maintenance Crew (45%), Mission Specialists (20%).
- **Qualifications:** 8 discrete synthetic qualification codes (`QUAL_NIGHT_OPS`, `QUAL_INSTRUMENT`, `QUAL_AVIONICS_LV3`, `QUAL_ENGINE_OVERHAUL`, etc.).
- **Availability Shifts:** 3 standard 8-hour rotating shifts across a 24-hour cycle.

### 2.3 Operational Tasks (Default: $N = 300$)
- **Categories:** Patrol Sortie (35%), Maintenance Inspection (25%), Ferry Transit (15%), Logistics Air-drop (15%), Readiness Drill (10%).
- **Duration:** Log-normal distribution with mode at 90 minutes (bounds: 30 minutes to 360 minutes).
- **Release and Deadlines:** Distributed across the 7-day planning horizon with Poisson arrival rates.
- **Dependencies:** 20% of tasks have precedence dependencies (DAG generated with NetworkX, guaranteed cycle-free).

### 2.4 Logistics & Spares Inventory (Default: 25 tracked parts)
- **Initial Inventory:** Triangular distribution per part at each zone (min: 2, mode: 10, max: 25).
- **Safety Levels:** Fixed thresholds (e.g., 3 units for critical actuators, 8 units for consumable seals).
- **Resupply Pipelines:** Resupply orders with lead times sampled from uniform distribution $U(24, 72)$ hours.

---

## 3. Historical Executions & ML Training Labels

To train predictive models without data leakage, the generator synthesizes historical task executions prior to $t_{\text{as\_of}}$:
1. **Maintenance Downtime Target ($y_{\text{downtime}}$):**
   - Synthesized using a base log-normal duration plus linear effects from asset age, accumulated flight hours, and technician experience:
     $$\ln(y) = \beta_0 + \beta_1 \cdot \text{AssetAge} + \beta_2 \cdot \text{AccumulatedHours} + \epsilon, \quad \epsilon \sim \mathcal{N}(0, \sigma^2)$$
2. **Task Delay Target ($y_{\text{delay}}$):**
   - Zero-inflated continuous distribution: 70% completed on time ($\text{delay} = 0$), 30% delayed with Pareto-distributed delays.
3. **Disruption Risk Target ($y_{\text{disruption}}$):**
   - Binary label ($0 = \text{nominal}, 1 = \text{disrupted}$) generated from logistic function of environmental variability, equipment health, and resource tightness.

---

## 4. Injected Anomalies for Validation Testing

The generator injects synthetic anomalies with ground-truth labels (`is_anomaly = True`) to evaluate Tier 1 and Tier 2 detection:
1. **Tier 1 (Deterministic Integrity Violations):**
   - Impossible time ranges (`end_time < start_time`).
   - Foreign key reference to non-existent asset.
   - Out-of-bounds health score ($1.45$ or $-0.20$).
2. **Tier 2 (Subtle Multi-Variate Inconsistencies):**
   - Asset with zero flight hours undergoing overhaul.
   - Sudden spike in maintenance duration for a routine 15-minute inspection (50 hours).
   - Sensor drift on asset readiness scores while operational utilization is at 100%.
