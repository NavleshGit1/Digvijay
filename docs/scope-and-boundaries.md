# AirOps Nexus — Scope, Boundaries, and Prototype Dimensions

**Status:** Signed-off Scope Specification (Phase 0, Task P0-1)  
**Version:** 1.0 (Phase 0 Baseline)  
**Classification:** Unclassified · Synthetic Data Prototype  
**Problem Statement Reference:** 26250 — Air Power: Dynamic Air Operations and Resource Optimisation

---

## 1. System Mission & Core Vision

AirOps Nexus is a resilient, intelligent decision-support platform designed to manage and dynamically re-optimise air operations and operational resource allocations. The platform integrates:
1. Constraint-based operational scheduling.
2. Dynamic event-driven replanning.
3. Predictive machine learning models for maintenance downtime, task delay, and disruption risk.
4. Discrete-event digital twin simulation for risk and robustness evaluation.
5. Grounded explainability and an AI Assistant backed by Retrieval-Augmented Generation (RAG).
6. Immutable audit trails, governance, and strict human-in-the-loop oversight.

---

## 2. Strict Scope Boundaries & Ethical Guardrails

### 2.1 In-Scope Capabilities
- **Operational & Logistics Resource Scheduling:** Allocation of fictional flight and maintenance assets, personnel crews, specialized ground equipment, zone bays, and consumables.
- **Readiness & Serviceability Monitoring:** Tracking asset health indicators, maintenance schedules, qualification renewals, and spares availability.
- **Disruption Impact Assessment:** Graph-based evaluation of delays, maintenance extensions, asset groundings, and resupply disruptions.
- **Automated Re-planning Proposals:** CP-SAT constraint programming generating proposed schedule adaptations without modifying active plans automatically.
- **What-If Digital Twin Simulation:** Monte Carlo simulation comparing baseline and revised schedules under stochastic uncertainties.
- **Grounded Audited Governance:** Multi-role workflow requiring authorized human approval for plan adoption, full state change tracking, and tamper-evident audit logging.

### 2.2 Out-of-Scope Capabilities (Explicit Exclusions)
- **NO Real-World Tactical or Combat Operations:** No targeting, kinetic strike coordination, weapons guidance, or combat engagement logic.
- **NO Real Defense Data:** No classified, restricted, or actual operational data. All records are 100% synthetic and generated deterministically via pseudo-random distributions.
- **NO Autonomous Execution / Machine Approval:** Models and solvers only generate recommendations (proposals). No automated plan deployment or silent schedule overwrite is permitted.
- **NO Fabricated UI Data:** Components must never hard-code metrics, KPI values, or mock statuses. All values flow through typed API responses with explicit provenance tags (`observed`, `predicted`, `simulated`, `generated`, `synthetic`, `demo`).

---

## 3. Prototype Sizing & Target Dimensions

These dimensions establish the baseline complexity for data generation, the CP-SAT solver, the digital twin simulator, and the frontend data tables:

| Dimension | Proposed Prototype Baseline | Configurable Range | Notes |
| :--- | :--- | :--- | :--- |
| **Fictional Assets** | 40 assets | 20 – 100 | Multi-role air assets and specialized support vehicles across 4 types |
| **Personnel Crew** | 120 personnel | 50 – 300 | Pilots, maintenance technicians, mission specialists with varied qualifications |
| **Active Tasks** | 300 tasks | 100 – 1,000 | Sorties, pre-flight checks, routine maintenance, inspections |
| **Planning Horizon** | 7 days (168 hours) | 3 – 14 days | Rolling operational window |
| **Discretization Slot** | 15 minutes | 5 – 60 minutes | Time slot granularity for constraint interval variables |
| **Fictional Zones** | 6 operational zones | 3 – 12 zones | Fictional airfields, maintenance hangars, staging sectors |
| **Inventory Categories**| 25 spare parts / components | 10 – 100 parts | Tracked spares and consumable buffers |
| **Planning Lead-Time** | 2 hours | 1 – 6 hours | Frozen window buffer for immediate active commitments |

---

## 4. Time Management & Display Standards

- **Internal Storage & API:** Strictly UTC ISO 8601 strings (`YYYY-MM-DDTHH:MM:SSZ`).
- **Display Time Zone:** Single configured display time zone across the UI (Default: `UTC` or `ZULU` format, toggleable to local demo environment).
- **Time Representation:** All scheduling and simulation logic operates relative to a centralized system clock (`Clock` interface). In demo and simulation modes, time may be pinned or advanced without altering operating system clocks.

---

## 5. Role Definitions & Access Boundaries

The system enforces four distinct operational roles with strict server-side authorization:

1. **Planner (`ROLE_PLANNER`):**
   - Creates scenarios, schedules baseline plans, initiates replanning jobs, injects simulated disruption events, triggers task status transitions (`start`, `complete`).
   - Cannot approve or reject proposed plans.
2. **Reviewer / Approver (`ROLE_REVIEWER`):**
   - Reviews proposed plans, inspects plan diffs, evaluations, and explainability traces.
   - Authorizes plan approval or rejection with mandatory rationale.
   - Cannot directly run optimiser jobs or alter raw assets/personnel records.
3. **Analyst (`ROLE_ANALYST`):**
   - Inspects model cards, feature drift, anomaly findings, Monte Carlo twin distributions, and performance metrics.
   - Marks anomaly findings as reviewed or false positives.
   - Read-only on operational scheduling and approvals.
4. **Administrator (`ROLE_ADMIN`):**
   - System configuration: objective weight sets, constraint definitions, model promotion and rollback, user management, demo environment reset, clock manipulation, engine toggles.
   - Full audit logging access.

---

## 6. MVP vs. Stretch Scope Prioritization

### 6.1 MVP (Must-Have for Milestone M1 & M2)
- Monorepo, Docker Compose, CI pipeline with type synchronization.
- Synthetic deterministic generator with dataset versioning and content hashes.
- Full 10 hard constraints evaluated via CP-SAT and independent pure-Python validator.
- End-to-end 10-step operational replanning flow with locked task executions.
- Sibling staleness, rollback proposal, and approval-time revalidation.
- Predictive models for maintenance downtime (LightGBM quantile), task delay (XGBoost), and disruption risk (calibrated classifier).
- Discrete-event SimPy digital twin with common random numbers Monte Carlo comparison.
- Grounded AI Assistant with read-only tools and pgvector RAG.
- Append-only hash-chained audit log and RFC 7807 problem+json error formatting.

### 6.2 Stretch / Optional (Behind Feature Flags — Section 7 Descoping Ladder)
- Resource-demand forecasting model (seasonal naive / LightGBM global).
- PyTorch autoencoder for anomaly detection (Isolation Forest is default).
- Dynamic drag-and-drop schedule editing with live constraint validation.
- Advanced WeasyPrint PDF report design polish (CSV streaming is primary).
- Alternative proposals generation (side-by-side multi-objective comparison).
- Reproducibility export bundles (`.zip` with `manifest.json` and verification scripts).
