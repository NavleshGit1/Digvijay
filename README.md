# AirOps Nexus

> **Problem Statement 26250 · Air Power: Dynamic Air Operations and Resource Optimisation**  
> *Synthetic Data Research Prototype · Decision Support Platform*

AirOps Nexus is a resilient, intelligent decision-support platform designed to manage and dynamically re-optimise air operations and operational resource allocations.

---

## Key Features & Architecture Principles
- **Data-Driven UI:** Generated TypeScript types from OpenAPI 3.1 contracts with explicit `data_kind` provenance envelopes (`observed`, `predicted`, `simulated`, `generated`, `synthetic`, `demo`).
- **Constraint Safety:** 10 hard constraints evaluated by OR-Tools CP-SAT and re-checked by an independent pure-Python validator.
- **Human Oversight:** Strict role separation (`Planner`, `Reviewer`, `Analyst`, `Admin`). Approvals require Reviewer authorization; the AI Assistant has zero write authority.
- **Tamper-Evident Audit:** Append-only cryptographic SHA-256 hash chaining on all protected mutations.
- **Virtual Clock:** Centralized `Clock` protocol with stored `as_of` snapshots ensuring 100% reproducible test and demo executions.

---

## Repository Structure
```
Digvijay/
├── docs/                       # Specifications, ADRs, Data Dictionary, OpenAPI contract
│   ├── adr/                    # Architecture Decision Records (0001 - 0006)
│   ├── data-dictionary.md      # Schema specifications, ERD, and mathematical KPI formulas
│   ├── openapi.json            # Frozen OpenAPI 3.1 contract
│   ├── constraint-definitions.md # The 10 hard constraints and soft objectives
│   └── ...
├── backend/                    # Modular Monolith FastAPI backend
│   ├── app/
│   │   ├── api/                # Versioned REST routers & SSE stream
│   │   ├── core/               # Settings, Clock protocol, security, exceptions, locks
│   │   ├── db/                 # SQLAlchemy 2.0 session and base
│   │   ├── models/             # Identity, clock, audit logs, jobs
│   │   ├── schemas/            # Pydantic request and response schemas
│   │   ├── services/           # Business logic and transaction management
│   │   └── worker/             # Celery worker application and background tasks
│   └── tests/                  # Unit tests (clock, auth, audit hash chain)
├── frontend/                   # React 18 + TypeScript + Vite SPA
│   ├── src/
│   │   ├── layouts/            # AppShell, persistent Sidebar (11 links), Topbar
│   │   ├── components/         # Shared UI, KPI cards, badges, page-state feedback
│   │   ├── pages/              # All 11 mission views, LoginPage, NotFoundPage
│   │   └── services/           # Typed API client and SSE consumer
├── scripts/                    # AST Clock linter and helper scripts
├── docker-compose.yml          # Core profiles: postgres (pgvector), redis, minio, backend, worker, caddy
└── CONTRIBUTING.md             # Team conventions, quality gates, Definition of Done
```

---

## Quick Start (Docker Compose)
1. Ensure Docker Desktop is running.
2. Launch core infrastructure and application containers:
   ```bash
   docker compose up -d
   ```
3. Open your browser:
   - **Frontend Mission Interface:** [http://localhost](http://localhost) (or [http://localhost:5173](http://localhost:5173) in Vite dev mode)
   - **FastAPI OpenAPI Interactive Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **MinIO Object Console:** [http://localhost:9001](http://localhost:9001)

---

## Quality & Verification Commands
- **AST Clock Linter (Enforce Zero Direct Time Calls):**
  ```bash
  python scripts/lint_clock.py backend/app
  ```
- **Frontend Build & Type Check:**
  ```bash
  npm --prefix frontend run build
  ```
