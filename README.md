# AirOps Nexus

> **Problem Statement 26250 · Air Power: Dynamic Air Operations and Resource Optimisation**  
> *Synthetic Operational Decision-Support Platform · Enterprise Production Release*

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6.svg)](https://www.typescriptlang.org/)
[![OR-Tools](https://img.shields.io/badge/OR--Tools-CP--SAT-orange.svg)](https://developers.google.com/optimization)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

---

## Executive Overview

**AirOps Nexus** is an enterprise-grade dynamic decision-support platform designed for high-tempo air operations planning, resource allocation, and real-time disruption recovery. It unites deterministic mathematical constraint programming (**Google OR-Tools CP-SAT**), graph-theoretic impact traversal (**NetworkX**), tamper-evident cryptographic audit ledgers, and a modern reactive command dashboard to solve complex multi-dimensional scheduling under strict operational rules.

The platform operates as a resilient operational command center: when unscheduled maintenance, weather ground stops, or mission priority changes disrupt commitments, AirOps Nexus detects downstream cascading consequences, executes constrained replanning with frozen-window stability, and presents fine-grained diffs for human reviewer approval.

All data utilized within this platform is **strictly synthetic**, engineered to stress-test mathematical solvers, dependency DAGs, and human-in-the-loop governance workflows across realistic operational dimensions (40 fictional aircraft, 120 crew personnel, 300 mission sorties, and 6 operational sectors).

---

## Core Architectural Invariants

AirOps Nexus is built upon five non-negotiable operational principles:

1. **Deterministic Constraint Safety:**  
   Every generated schedule strictly satisfies 10 mathematical hard constraints. Solver outputs are independently verified by a standalone pure-Python validator prior to persisting any proposed plan.
2. **Strict Human-in-the-Loop (HITL) Governance:**  
   Schedulers and replanning engines generate **proposals only** (`status="proposed"`). Solvers, automated engines, and AI services have **zero authority to modify or activate approved schedules**. Plan activation requires explicit Reviewer authorization with mandatory justification.
3. **Cryptographic Tamper-Evident Audit Ledger:**  
   All state transitions, schedule approvals, overrides, and administrative changes are recorded in an append-only, SHA-256 hash-chained audit ledger, mathematically preventing undetected modifications.
4. **Reproducible Virtual Clock:**  
   A centralized `ClockProtocol` eliminates non-deterministic `datetime.now()` calls. Operations and benchmarks are pinned to historical `as_of` snapshots, ensuring 100% test reproducibility.
5. **Stability & Churn Minimization:**  
   When operational disruptions occur, replanning incorporates a **frozen window** (preserving commitments within $T_{\text{now}} + \Delta t_{\text{frozen}}$) and an objective penalty term that minimizes schedule churn (unnecessary reassignment of tasks, assets, and crew).

---

## System Architecture

The platform is structured as a high-performance **Modular Monolith** with containerized micro-services orchestrated via Docker Compose:

```
                                  [ User Browser ]
                                         │
                                         ▼
                            [ Caddy Reverse Proxy (:80) ]
                            ┌────────────┴────────────┐
                            ▼                         ▼
                 [ React + Vite UI (:5173) ]   [ FastAPI API (:8000) ]
                                                      │
                       ┌──────────────────────────────┼──────────────────────────────┐
                       ▼                              ▼                              ▼
            [ PostgreSQL 16 + pgvector ]      [ Redis 7.0 ]                 [ MinIO (S3) ]
            • Relational Core                 • Job Queues (Celery)         • Artifacts
            • Audit Hash Chain                • Distributed Locks           • Parquet Datasets
            • Plan Versions & Tasks           • Pub/Sub & WebSockets        • Model Registry
                       │                              │
                       └──────────────┬───────────────┘
                                      ▼
                        [ Celery Distributed Workers ]
                        • Baseline CP-SAT Solver
                        • NetworkX Impact Traversal
                        • Constrained Replanning Engine
                        • Anti-Flapping Alert Evaluator
```

### Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend Framework** | **Python 3.12 / FastAPI** | Async REST APIs, OpenAPI 3.1 specification, WebSockets |
| **ORM & Database** | **SQLAlchemy 2.0 / PostgreSQL 16** | Relational transactions, JSONB metrics, pgvector storage |
| **Constraint Solver** | **Google OR-Tools (CP-SAT)** | MILP solver for deterministic task, asset & crew scheduling |
| **Graph Analytics** | **NetworkX 3.0** | Multi-entity dependency graph & cascading impact traversal |
| **Task Queue & Cache**| **Celery / Redis 7** | Distributed job processing, atomic locks, real-time events |
| **Object Storage** | **MinIO (S3-compatible)** | Parquet datasets, solver logs, export artifacts |
| **Reverse Proxy** | **Caddy 2.8** | Single-port routing, CORS, security headers, compression |
| **Frontend SPA** | **React 18 / TypeScript / Vite 5** | Strict-typed client, Lucide icons, glassmorphic dark theme |
| **Styling** | **Tailwind CSS & CSS Tokens** | Tactical command center aesthetics, responsive layouts |

---

## Core System Modules & Capabilities

### 1. Mathematical Constraint Scheduling & Dual-Validator Engine
- **Baseline Scheduler:** Topological ordering heuristic for cold-start initialization and benchmark comparison.
- **CP-SAT Mixed Integer Programming Optimizer:** Formulates flight schedules, maintenance blocks, and crew assignments into an optimal timeline. Minimizes mission delay, turnaround gaps, and preferred asset utilization.
- **Independent 10-Invariant Validator:** Validates proposed schedules against:
  - `HC_ASSET_CAPACITY`: Single task per asset at any timestamp.
  - `HC_CREW_QUALIFICATIONS`: Sortie crew requirements matched to certified personnel.
  - `HC_MAINT_WINDOWS`: Zero task overlap with scheduled aircraft maintenance.
  - `HC_PRECEDENCE`: Strict DAG dependency sequence (predecessors must complete before successors start).
  - `HC_TURNAROUND`: Minimum buffer time between consecutive flights on the same airframe.
  - `HC_DUTY_HOURS`: Crew flight hours stay within maximum fatigue limits.
  - `HC_ZONE_RANGE`: Asset operational range matches assigned zone distance.
  - `HC_RUNWAY_SLOTS`: Base departure/arrival slot concurrency limits respected.
  - `HC_SPARES_AVAILABILITY`: Required maintenance parts inventory validated.
  - `HC_NO_OVERLAPPING_SORTIES`: Personnel cannot be assigned to overlapping missions.

### 2. Plan Governance, Lifecycle & Assignment Diff Engine
- **Reviewer-Only RBAC:** Planners propose schedules; only designated **Reviewers** can approve or reject with mandatory justification.
- **Optimistic Concurrency:** HTTP `If-Match` headers with plan snapshot SHA-256 hashes prevent concurrent overwrite conflicts (HTTP 412).
- **Idempotency Guard:** `Idempotency-Key` headers ensure safe re-submission of approval decisions without double-execution.
- **Fine-Grained Diff Engine:** Computes exact assignment deltas between versions:
  - Added tasks, removed tasks, shifted tasks (with minute-level precision).
  - Asset allocations and crew roster reassignment tracking.
  - Objective metric deltas (delay changes, runtime, completion percentage).
- **Rollback Engine:** Safe proposal generation from historical versions without destructive history truncation.

### 3. Real-Time Disruption Recovery & Constrained Replanning
- **Operational Alerts Subsystem:**
  - Evaluates live conditions across fleet maintenance, stock levels, and task deadlines.
  - **15-Minute Anti-Flapping Deduplication:** Hashes events into unique `dedup_key` values; sliding window prevents alert fatigue.
  - Hysteresis buffers and auto-resolution when normal conditions resume.
  - Interactive triage actions: *Acknowledge* and *Resolve*.
- **NetworkX Impact Detector:**
  - Injects maintenance delays or asset groundings via REST API.
  - Traverses the bipartite multi-entity graph to identify:
    - **Direct Collisions:** Tasks directly scheduled during the extended maintenance window.
    - **Cascading Ripple Effects:** Downstream DAG flight sorties suffering schedule slippage.
    - **Resource Bottlenecks:** Grounded crew and depleted spare parts.
- **Constrained Replanning Engine:**
  - Solves the recovery problem using approved plan state as warm-start hints.
  - **Frozen Window Cutoff:** Sorties within $T_{\text{now}} + \text{frozen\_window\_minutes}$ or flagged `is_locked` remain fixed.
  - **Churn Minimization:** Mathematical penalty minimizes operational friction:
    $$\min \quad \alpha \cdot \text{Delay} + \beta \cdot \text{ShiftTime} + \gamma \cdot \text{AssetReassignments}$$

### 4. Fleet, Crew & Maintenance Resource Management
- **Asset Registry:** Airframe status, flight hours, engine cycle tracking, zone restrictions, and maintenance countdowns.
- **Personnel Roster:** Pilot and technician certifications, callsigns, flight fatigue hours, and qualification verification.
- **Maintenance & Logistics:** Scheduled periodic inspections, maintenance rule catalogues, spare parts consumption, and minimum safety level monitoring.
- **Data Quality Fusion:** Real-time validation checking temporal sanity, bounded values, and anomaly preservation across data adapters.

### 5. Cryptographic Audit Chain & Provenance Engine
- **Tamper-Evident Ledger:** Every state-altering action records actor ID, role, client IP, action type, payload hash, and SHA-256 link to the previous record.
- **Signed Audit Export:** Downloadable CSV/JSON export with cryptographic integrity headers verifying chain continuity.
- **Data Provenance Envelopes:** Strict tagging of all data values with operational origins (`observed`, `predicted`, `simulated`, `generated`, `synthetic`, `demo`).

---

## End-to-End Operational Disruption & Recovery Workflow

The system provides an integrated 10-step recovery cycle demonstrated live across the platform:

```
  [1. Seeded Dataset] ──▶ [2. Baseline Plan Generated] ──▶ [3. Reviewer Approves Baseline]
                                                                      │
  [6. CP-SAT Replanning] ◀── [5. NetworkX Impact Detect] ◀── [4. Maintenance Delay Injected]
         │
         ▼
  [7. Compare Plan Diff] ──▶ [8. Reviewer Approves Replan] ──▶ [9. v1 Superseded, v2 Active]
                                                                      │
                                                                      ▼
                                                          [10. Immutable Audit Trail]
```

1. **Dataset Loaded:** Active operational dataset verified (100 sorties, 40 assets, 120 crew, 6 sectors).
2. **Baseline Generated:** Solved via CP-SAT solver and stored as Plan Version 1.
3. **Reviewer Approves Baseline:** Reviewer persona verifies schedule and commits with ETag concurrency guard.
4. **Maintenance Disruption Injected:** Unscheduled turbofan vibration delay (+90 min) injected on active asset.
5. **NetworkX Impact Detected:** Precedence ripples and direct collisions identified in real time.
6. **Constrained Replanning Executed:** CP-SAT replan generates proposal Version 2 with frozen window and churn index.
7. **Diff Compared:** Reviewer queries assignment shifts (`/plans/{plan_id}/diff`) and metric deltas.
8. **Reviewer Approves Proposal:** Mandatory justification rationale recorded.
9. **Atomic Transition:** Version 1 superseded; Version 2 becomes active approved plan.
10. **Immutable Audit Trail:** Chain-hashed audit log and approval records preserve complete decision history.

---

## Security & Role-Based Access Control (RBAC)

The system enforces strict server-side RBAC across four predefined operational personas:

| Role | Username | Seeded Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Planner** | `planner@airops.local` | `PlannerSecurePass2026!` | Create baseline/replan jobs, inject disruptions, simulate delays |
| **Reviewer** | `reviewer@airops.local` | `ReviewerSecurePass2026!` | Approve/reject proposals, inspect diffs, trigger rollbacks |
| **Analyst** | `analyst@airops.local` | `AnalystSecurePass2026!` | Read-only access to schedules, Gantt charts, KPIs, telemetry |
| **Admin** | `admin@airops.local` | `AdminSecurePass2026!` | Manage users, configure constraint sets, export audit logs |

- **Password Hashing:** Argon2id with random 16-byte salt.
- **Authentication:** JWT Bearer tokens with configurable expiration and automatic frontend refresh.
- **Audit Verification:** All write operations record actor, role, client IP, timestamp, and SHA-256 hash.

---

## User Interface & Mission Control

The frontend application provides 11 dedicated command views:

- **Overview (`/`):** Tactical fleet readiness gauges, active sorties, dynamic base sector map, and instant alert banners.
- **Operations & Disruption Sandbox (`/operations`):** Live alert triage, delay overrun simulation slider, NetworkX impact graph, and CP-SAT replanning triggers.
- **Schedule & Gantt (`/schedule`):** Multi-layer timeline visualization, plan version comparative viewer, solver status indicators, and replan stability churn metrics.
- **Assets (`/assets`):** Airframe status, flight hours, next inspection countdowns, and maintenance records.
- **Personnel (`/personnel`):** Flight crew and technician roster, certification status, duty hours, and flight-hour fatigue meters.
- **Maintenance (`/maintenance`):** Scheduled periodic inspections, maintenance rules, spare parts inventory consumption, and delay injection dialogs.
- **Scenarios (`/scenarios`):** Operational scenario configuration and simulation sandbox.
- **Intelligence (`/intelligence`):** Predictive risk models, downtime forecasts, feature attribution charts, and failure probability tracking.
- **Assistant (`/assistant`):** Operational decision-support assistant with verified citations and provenance tagging.
- **Reports (`/reports`):** Standard operational reporting engine with multi-format export (PDF/CSV) and audit parameter headers.
- **Settings (`/settings`):** Global constraint registry parameter tuning, user administration, and system health checks.

---

## Getting Started

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/)
- [Node.js](https://nodejs.org/) v18+ *(for local frontend development)*
- [Python](https://www.python.org/) 3.12+ *(for local backend development)*

### 1. Launch with Docker Compose (Recommended)

Clone the repository and spin up all 6 infrastructure and application services:

```bash
# Clone the repository
git clone https://github.com/NavleshGit1/Digvijay.git
cd Digvijay

# Create environment configuration from template
cp .env.example .env

# Build and start all services in detached mode
docker compose up -d --build
```

### 2. Verify Services

Once running, the stack provides the following endpoints:

| Service | URL | Notes |
| :--- | :--- | :--- |
| **Frontend Web App** | [http://localhost](http://localhost) | Caddy reverse proxy port 80 |
| **Backend REST API** | [http://localhost:8000](http://localhost:8000) | FastAPI direct port |
| **Interactive API Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger UI / OpenAPI docs |
| **Alternative API Docs** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | ReDoc format |
| **MinIO Console** | [http://localhost:9001](http://localhost:9001) | S3 Object storage UI (`airops` / `airops_minio_secret_2026`) |
| **PostgreSQL Database** | `localhost:5432` | Database: `airops_nexus` (`airops` / `airops_secret_2026`) |
| **Redis Cache & Broker**| `localhost:6379` | Key-value store and Celery broker |

---

## Testing & Quality Assurance

The codebase includes comprehensive test suites across unit, integration, and solver levels:

```bash
# Run complete test suite (55 tests across scheduling, replanning, governance, and resources)
docker compose exec backend pytest tests/ -v

# Run replanning engine and disruption recovery tests
docker compose exec backend pytest tests/test_phase6_replanning.py -v

# Run frontend type checking
npm --prefix frontend run type-check

# Run frontend linter
npm --prefix frontend run lint

# Build frontend production bundle
npm --prefix frontend run build
```

---

## Operational Safety & Compliance Notice

> **IMPORTANT:** AirOps Nexus is a scientific research and decision-support prototype operating exclusively on synthetic data. All tail numbers, personnel identities, callsigns, missions, and geographic zones are procedurally generated fiction. Schedulers and automated algorithms generate **proposals only**; final authority remains strictly with certified human operators.
