# AirOps Nexus

> **Problem Statement 26250 · Air Power: Dynamic Air Operations and Resource Optimisation**  
> *Synthetic Operational Decision-Support Platform · Milestone M1 Production Baseline*

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5-3178C6.svg)](https://www.typescriptlang.org/)
[![OR-Tools](https://img.shields.io/badge/OR--Tools-CP--SAT-orange.svg)](https://developers.google.com/optimization)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

---

## Executive Overview

**AirOps Nexus** is a dynamic decision-support platform designed for high-tempo air operations planning, resource allocation, and real-time disruption recovery. It combines deterministic constraint programming (**Google OR-Tools CP-SAT**), graph-theoretic impact traversal (**NetworkX**), immutable cryptographic audit ledgers, and a modern reactive command dashboard to solve complex multi-dimensional scheduling under strict operational rules.

All data utilized within this platform is **strictly synthetic**, engineered to stress-test mathematical solvers, dependency DAGs, and human-in-the-loop governance workflows across realistic operational dimensions (40 fictional aircraft, 120 crew personnel, 300 mission sorties, and 6 operational sectors).

---

## Core Architectural Invariants

AirOps Nexus is built upon five foundational principles:

1. **Deterministic Constraint Safety:**  
   Every generated schedule satisfies 10 mathematical hard constraints. Solver outputs are independently verified by a standalone pure-Python validator prior to persisting any proposed plan.
2. **Strict Human-in-the-Loop (HITL) Governance:**  
   Schedulers and replanning engines generate **proposals only** (`status="proposed"`). Solvers, automated engines, and AI services have **zero authority to modify or activate approved schedules**. Plan activation requires explicit Reviewer authorization with mandatory justification.
3. **Cryptographic Tamper-Evident Audit Ledger:**  
   All state transitions, schedule approvals, overrides, and administrative changes are recorded in an append-only, SHA-256 hash-chained audit ledger, preventing undetected modifications.
4. **Reproducible Virtual Clock:**  
   A centralized `ClockProtocol` eliminates non-deterministic `datetime.now()` calls. Operations and benchmarks are pinned to historical `as_of` snapshots, ensuring 100% test reproducibility.
5. **Stability & Churn Minimization:**  
   When operational disruptions occur (e.g. unscheduled maintenance or delay overruns), replanning incorporates a **frozen window** (preserving commitments within $T_{\text{now}} + \Delta t_{\text{frozen}}$) and an objective penalty term that minimizes schedule churn (unnecessary reassignment of tasks, assets, and crew).

---

## System Architecture

The platform is structured as a **Modular Monolith** with containerized micro-services orchestrated via Docker Compose:

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

## Key Modules & Capabilities

### 1. Deterministic Scheduling & Validator (Phase 4)
- **Baseline Scheduler:** Greedy topological ordering baseline used for cold-start initialization and benchmark comparison.
- **CP-SAT Optimizer:** Formulates mission scheduling as a Constraint Satisfaction & Optimization problem. Optimizes for minimum total mission delay, minimal turnaround gaps, and preferred asset utilization.
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

### 2. Plan Governance & Diff Engine (Phase 5)
- **Approval Workflow:** Planners propose plans; only designated **Reviewers** can approve or reject with mandatory rationale justification.
- **Optimistic Concurrency:** HTTP `If-Match` headers with plan snapshot SHA-256 hashes prevent concurrent overwrite conflicts (HTTP 412).
- **Idempotency Guard:** `Idempotency-Key` headers ensure safe re-submission of approval decisions.
- **Fine-Grained Diff Engine:** Computes exact assignment deltas between versions:
  - Added tasks, removed tasks, shifted tasks (with minute deltas).
  - Asset and crew reassignment tracking.
  - Metric deltas (delay changes, runtime, completion percentage).
- **Rollback Engine:** Safe proposal generation from historical versions without destructive history truncation.

### 3. Events, Replanning & Disruption Management (Phase 6 / Milestone M1)
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

---

## Milestone M1: 10-Step Operational Disruption Flow

The vertical slice of the operational disruption cycle is fully implemented and tested:

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

1. **Dataset Loaded:** Active seeded dataset verified (100 sorties, 40 assets, 120 crew).
2. **Baseline Generated:** Solved via CP-SAT solver and stored as Plan Version 1.
3. **Reviewer Approves Baseline:** Reviewer persona verifies schedule and commits with ETag header.
4. **Maintenance Disruption Injected:** Turbofan vibration delay (+90 min) injected on active asset.
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
- **Cryptographic Audit:** All write operations record actor, role, client IP, timestamp, and SHA-256 hash.

---

## User Interface & Mission Control

The frontend application provides 11 dedicated command views:

- **Overview (`/`):** High-level fleet readiness gauges, active sorties, tactical base map, and live alert banners.
- **Operations & Disruption Sandbox (`/operations`):** Live alert triage, delay overrun simulation slider, NetworkX impact graph, and CP-SAT replanning triggers.
- **Schedule & Gantt (`/schedule`):** Interactive timeline visualization, plan version switching, solver status indicators, and replan stability churn metrics.
- **Assets (`/assets`):** Airframe status, flight hours, next inspection countdowns, and maintenance records.
- **Personnel (`/personnel`):** Flight crew and technician roster, certification status, and flight-hour fatigue meters.
- **Maintenance (`/maintenance`):** Scheduled periodic inspections, maintenance rules, spare parts demand, and delay injection dialogs.
- **Scenarios (`/scenarios`):** Digital twin simulation configuration sandbox *(Phase 8 foundation)*.
- **Intelligence (`/intelligence`):** Predictive risk model dashboards *(Phase 7 foundation)*.
- **Assistant (`/assistant`):** Read-only operational AI assistant *(Phase 9 foundation)*.
- **Reports (`/reports`):** Operational report generator and audit exporter *(Phase 10 foundation)*.
- **Settings (`/settings`):** Constraint registry tuning, user administration, and system health checks.

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
# Run complete test suite (55 tests across all phases)
docker compose exec backend pytest tests/ -v

# Run Phase 6 replanning and Milestone M1 tests specifically
docker compose exec backend pytest tests/test_phase6_replanning.py -v

# Run frontend type checking
npm --prefix frontend run type-check

# Run frontend linter
npm --prefix frontend run lint

# Build frontend production bundle
npm --prefix frontend run build
```

---

## Project Roadmap

| Phase | Description | Status |
| :---: | :--- | :---: |
| **Phase 0** | Foundations, Data Dictionary & OpenAPI Contracts | Completed |
| **Phase 1** | Platform Skeleton, RBAC, Clock & Audit Ledger | Completed |
| **Phase 2** | Relational Data Foundation, Generator & Quality Fusion | Completed |
| **Phase 3** | Resource CRUD, Maintenance Windows & Overview UI | Completed |
| **Phase 4** | Deterministic CP-SAT Optimizer & Invariant Validator | Completed |
| **Phase 5** | Plan Governance, Reviewer Approvals & Diff Engine | Completed |
| **Phase 6** | **Events, Replanning & Anti-Flapping Alerts (Milestone M1)** | **Completed** |
| **Phase 7** | Predictive ML Platform (Downtime, Delay & Disruption Models) | *Upcoming* |
| **Phase 8** | Digital Twin & Monte Carlo Simulation Engine | *Upcoming* |
| **Phase 9** | Intelligence Layer, Explainability (SHAP) & RAG Assistant | *Upcoming* |
| **Phase 10** | Reports Generation & Administrative Settings | *Upcoming* |
| **Phase 11** | Hardening, Performance Benchmarking & Final Release | *Upcoming* |

---

## Operational Safety & Compliance Notice

> **IMPORTANT:** AirOps Nexus is a scientific research and decision-support prototype operating exclusively on synthetic data. All tail numbers, personnel identities, callsigns, missions, and geographic zones are procedurally generated fiction. Schedulers and automated algorithms generate **proposals only**; final authority remains strictly with certified human operators.
