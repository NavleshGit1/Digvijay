# AirOps Nexus — System Architecture, Tech Flow and Technology Stack

Problem Statement 26250 · Air Power: Dynamic Air Operations and Resource Optimisation · Synthetic data only · Architecture v1.0, derived from AirOps\_Nexus\_Final\_Prototype\_Requirements.md

## 1. Architectural drivers

The requirements file asks for one coherent workflow (load, inspect, baseline, disrupt, assess, predict, replan, compare, explain, approve, audit) rather than disconnected demos. The architecture is therefore a modular monolith (one FastAPI service with strict engine interfaces), asynchronous workers, one PostgreSQL system of record, and a typed API contract that the React frontend consumes without fabricating any value. Microservices, Kafka and distributed compute are deliberately excluded until a measured need justifies them (file sections 2 and 15).

| # | Principle (file section 2) | Architectural mechanism |
| --- | --- | --- |
| 1 | Data-driven UI | OpenAPI contract generated from FastAPI; TypeScript client generated from it; no KPI literals in components; every API value carries a data\_kind tag (observed, predicted, simulated, generated, synthetic, demo); static content wrapped in a DemoBadge |
| 2 | Constraint safety | ML outputs reach the solver only as parameters; hard constraints are encoded in CP-SAT and re-checked by an independent pure-Python validator before any plan is stored as proposed |
| 3 | Human oversight | Plan state machine (baseline, proposed, approved, rejected, superseded); only the approve endpoint with Approver permission can create an approved plan; assistant has no write tools |
| 4 | Traceability | UUID keys, UTC timestamps, version columns, provenance tables, run manifests, hash-chained audit log |
| 5 | Honest solver status | SolverStatus enum (optimal, feasible, infeasible, timeout, unknown, error) mapped explicitly from CP-SAT; a timeout is never reported as infeasible |
| 6 | Reproducibility | Run manifest stores seed, configuration hash, dataset version, model versions, solver version, git SHA, outputs and metrics; deterministic generator; single-thread reproducible solver mode |
| 7 | Graceful degradation | Engine health registry, feature flags and circuit breakers; failures return degraded or unavailable states with warnings, never default or fabricated numbers |
| 8 | Modular architecture | Engine Protocols (interfaces) under engines/; workers run the same code as the API; extraction into services only through a recorded architecture decision |
| 9 | Accessible interface | Radix primitives, keyboard support, AA-contrast tokens, table equivalents for every chart and Gantt, axe checks in CI |
| 10 | Security by design | Server-side permission dependency on every route, object-level checks, audit writer in the service layer |

## 2. Technology stack

### 2.1 Frontend

| Concern | Technology | Role |
| --- | --- | --- |
| Language and build | TypeScript 5, React 18, Vite | SPA, code-split by route |
| Routing and server state | React Router 6, TanStack Query | Lazy routes, caching, polling, retry on version conflict |
| UI state | Zustand (minimal) | Sidebar, filters, theme only |
| Styling and components | Tailwind CSS, CSS design tokens (tokens.css), shadcn/ui on Radix | Design system: Button, Badge, Card, Dialog, Tabs, Tooltip, Select, Input |
| Tables | TanStack Table plus TanStack Virtual | Server-side search, sort, filter, pagination |
| Charts | Apache ECharts | Line, bar, donut, histogram, box plot, feature-contribution charts |
| Timeline and Gantt | Custom SVG (d3-scale, visx) with virtualised rows | Resource and task timeline, with an accessible Table tab |
| Map | MapLibre GL JS with local GeoJSON of fictional zones, no external tiles | Overview map; implies no real feeds |
| Forms | React Hook Form plus Zod | Client validation mirroring server schemas |
| API client | openapi-typescript plus openapi-fetch | Types generated from backend OpenAPI |
| Live updates | Server-Sent Events with polling fallback | Job progress, alerts, freshness |
| Frontend QA | ESLint, Prettier, Vitest, Testing Library, Playwright, axe-core, MSW (tests only) | Unit, component, end-to-end, accessibility |

### 2.2 Backend and data platform

| Concern | Technology | Role |
| --- | --- | --- |
| Runtime and API | Python 3.12, FastAPI, Uvicorn and Gunicorn, Pydantic v2 | REST API, typed schemas, OpenAPI |
| Persistence | PostgreSQL 16, SQLAlchemy 2.0, Alembic, psycopg 3 | System of record, migrations, foreign keys, indexes |
| Vector and text search | pgvector plus Postgres full-text | RAG retrieval |
| Cache, broker, locks | Redis 7 | Celery broker, job progress, idempotency keys, rate limits, locks |
| Background jobs | Celery 5, Celery Beat, Flower | Queues: optimise, ml, simulate, report, ingest, default; scheduled checks |
| Object storage | MinIO (S3 API) | Model artefacts, datasets, report files, raw simulation output (Parquet) |
| Authentication | OAuth2 password flow, JWT access token plus rotating refresh cookie, Argon2id | Demo login with seeded accounts from environment |
| Authorisation | Permission-based RBAC dependency, object-level checks | Server-side enforcement on every route |
| Rate limiting | slowapi on Redis | Abuse protection |
| Validation | Pydantic, pandera | Row and DataFrame validation |
| Data processing | pandas, Polars, NumPy | Normalisation, feature engineering |
| Dataset versioning | DVC (MinIO remote) plus dataset\_versions table with content hash | Reproducible datasets |
| Synthetic data | Seeded generator (NumPy Generator, Faker) | Deterministic fictional data and injected anomalies |

### 2.3 Engines

| Concern | Technology | Role |
| --- | --- | --- |
| Optimisation | OR-Tools CP-SAT, NetworkX | Constraint scheduling, precedence graphs, impact propagation |
| Plan validation | Pure-Python hard-constraint validator, Hypothesis | Independent checking, property-based tests |
| ML models | scikit-learn, LightGBM, XGBoost, lifelines (survival), statsforecast or statsmodels, PyTorch (optional) | Predictors, baselines, optional autoencoder |
| Tuning and uncertainty | Optuna (optional), MAPIE | Hyperparameters, conformal prediction intervals |
| Tracking and registry | MLflow (PostgreSQL backend, MinIO artefacts) | Experiments, versions, aliases (candidate, champion) |
| Explainability | SHAP for tree models, solver trace explainer | Feature contributions; constraint evidence |
| Drift | Evidently plus custom PSI and KS tests | Feature and performance drift |
| Simulation | SimPy, NumPy SeedSequence, SciPy | Discrete-event twin, Monte Carlo, bootstrap intervals |
| Assistant | LLM gateway (hosted Claude API by default; self-hosted vLLM or Ollama option), sentence-transformers embeddings | Tool-calling assistant and RAG; synthetic data only |
| Reports | Jinja2, WeasyPrint, Plotly or Matplotlib static charts, CSV streaming | PDF and CSV exports |

### 2.4 Platform and quality

| Concern | Technology | Role |
| --- | --- | --- |
| Containers | Docker, Docker Compose | Reproducible local and demo deployment |
| Edge | Caddy | TLS, CORS allow-list, static SPA, reverse proxy |
| Observability | structlog (JSON), OpenTelemetry, Prometheus, Grafana, Loki (optional) | Logs, metrics, traces, dashboards |
| CI and quality | GitHub Actions, uv (lockfile), pnpm, ruff, mypy, pytest, pre-commit | Lint, type-check, test, build |
| Supply chain | pip-audit, npm audit, Trivy, gitleaks, Dependabot | Dependency and secret scanning |

All dependencies are pinned through lockfiles; version bumps go through CI.

## 3. System architecture

```
 USERS: Planner · Reviewer/Approver · Analyst · Administrator
        │ HTTPS
┌───────▼─────────────────────────────────────────────────────────┐
│ EDGE  Caddy: TLS · CORS allow-list · static SPA · reverse proxy  │
└───────┬──────────────────────────────┬──────────────────────────┘
        │ /                            │ /api/v1  and  /api/v1/stream (SSE)
┌───────▼─────────┐        ┌───────────▼────────────────────────────┐
│ React SPA       │───────▶│ FastAPI API (modular monolith)          │
│ 11 pages        │        │ routers → services → engines/repos      │
│ generated client│        │ auth/RBAC · audit · governance ·        │
└─────────────────┘        │ assistant · in-process model serving    │
                           └──┬───────────┬───────────────┬──────────┘
                              │ SQL       │ enqueue       │ S3 API
                 ┌────────────▼──┐  ┌─────▼──────┐  ┌─────▼───────┐
                 │ PostgreSQL 16 │  │ Redis      │  │ MinIO        │
                 │ + pgvector    │  │ broker,    │  │ artefacts,   │
                 │ (system of    │  │ cache,     │  │ datasets,    │
                 │  record)      │  │ locks      │  │ reports      │
                 └───────▲───────┘  └─────┬──────┘  └─────▲────────┘
                         │                │               │
                 ┌───────┴────────────────▼───────────────┴────────┐
                 │ CELERY WORKERS: optimise · ml · simulate ·       │
                 │ report · ingest · default      (+ Beat scheduler)│
                 │ engines: data_fusion · optimisation · replanning │
                 │ prediction · anomaly · digital_twin · explain    │
                 └───────────────┬─────────────────────────────────┘
                        track / register
                 ┌───────────────▼──┐        ┌──────────────────────┐
                 │ MLflow server    │        │ LLM gateway           │
                 │ (PG + MinIO)     │        │ hosted or self-hosted │
                 └──────────────────┘        └──────────────────────┘
 Observability: OpenTelemetry → Prometheus → Grafana · JSON logs → Loki
```

**Runtime units (Docker Compose):** caddy, frontend (static build), api, worker-optimise, worker-ml, worker-simulate, worker-report, worker-default (ingest, events, maintenance jobs), beat, postgres, redis, minio, mlflow, llm-gateway (optional profile), prometheus, grafana, otel-collector, loki (optional).

**Request pattern:** the SPA calls typed REST endpoints; reads are served by services and repositories; every mutation passes through a service that checks permission, validates, writes data and writes the audit record in one transaction.

**Job pattern:** any long-running action (optimisation, replanning, training, simulation, report, ingestion) returns 202 with a job\_id. The API enqueues to Celery through Redis; the worker updates progress in Redis and final state in PostgreSQL; the SPA follows state over SSE (polling fallback). Job states are queued, running, completed, failed and cancelled. Solver status is a separate field and is never merged into job state.

## 4. Backend module design

Layering rule: routers call services; services call engines and repositories. Routers hold no business logic. Engines depend on Protocol interfaces (DataSourceAdapter, Predictor, AnomalyDetector, Scheduler, Replanner, Simulator, Explainer) so they can be swapped, disabled or tested in isolation.

| Module (backend/app) | Responsibility | Key technology | Serves |
| --- | --- | --- | --- |
| api/ | Versioned routers, dependencies, SSE stream, error mapping | FastAPI | All pages |
| core/ | Settings, enums (single source of truth), security, logging, feature flags, engine health registry, problem+json errors | Pydantic settings, structlog | Principles 5, 7, 10 |
| db/ and models/ | Session management, ORM entities, migrations | SQLAlchemy, Alembic | File section 11 |
| schemas/ | Request and response models, shared enums, data\_kind envelope | Pydantic v2 | File section 10 |
| repositories/ | Query logic, filters, pagination, row-level scoping | SQLAlchemy | FR-03 |
| services/ | Use cases: plan, event, maintenance, approval, report, user, config services | Python | All FRs |
| engines/data\_fusion | Adapters, normalisation, validation, dedupe, reconciliation, provenance, freshness | pandas, pandera | FR-01 |
| engines/optimisation | Baseline scheduler, CP-SAT model, constraint modules, objectives, solver config, diagnostics, validator | OR-Tools | FR-05 |
| engines/replanning | Impact detection, trigger logic, frozen window, stability objective, plan diff | NetworkX | FR-06 |
| engines/prediction | Feature builders, model loader (MLflow alias), input and out-of-distribution checks, drift jobs | scikit-learn, LightGBM, XGBoost, lifelines | FR-07 |
| engines/anomaly\_detection | Deterministic rules first, Isolation Forest second, optional autoencoder | scikit-learn, PyTorch | FR-08 |
| engines/digital\_twin | Simulation environment, scenario presets, Monte Carlo runner, statistics | SimPy, SciPy | FR-09 |
| engines/explainability | SHAP explainer, solver and constraint trace, evidence references | SHAP | FR-10 |
| assistant/ | LLM gateway, tool registry, RAG, guardrails, history | pgvector | FR-11 |
| governance/ | Plan state machine, approvals, config versioning, model promotion gates | Python | FR-12, FR-14 |
| audit/ | Append-only writer, hash chain, query | PostgreSQL | FR-12 |

## 5. Data architecture

### 5.1 Entities (PostgreSQL, migrations through Alembic)

| Group | Tables |
| --- | --- |
| Identity | users, roles, user\_roles |
| Sources and provenance | data\_sources, ingestion\_runs, source\_records, dataset\_versions, data\_source\_freshness |
| Resources | assets, personnel, qualifications, personnel\_qualifications, resource\_inventory, zones |
| Work | tasks, task\_requirements, task\_dependencies, maintenance\_records, constraint\_definitions |
| Plans | plans, plan\_versions, plan\_assignments, plan\_validations, plan\_diffs (cached), replan\_triggers |
| Events and quality | events (with idempotency key), data\_quality\_issues, notifications |
| Jobs | optimisation\_jobs, jobs (generic job registry), idempotency\_keys |
| Simulation | simulation\_scenarios, simulation\_runs, simulation\_run\_trials |
| ML | models, model\_versions, model\_evaluations, training\_runs, predictions, anomaly\_findings, drift\_reports |
| Governance | approval\_records, audit\_logs, objective\_weight\_sets, system\_config\_versions, feature\_flags |
| Assistant | assistant\_conversations, assistant\_messages (metadata policy applies) |
| Reporting | reports, report\_jobs |

The file lists both assignments and plan\_assignments. Here, plan\_assignments is the only table (rows belong to one immutable plan version); assignments is a database view over the currently approved plan version.

### 5.2 Conventions

- UUID primary keys; UTC timestamps in storage; one configured display time zone applied in the UI.
- Every business row has is\_synthetic, created\_at, updated\_at, version, and source\_record\_id where applicable; plan and config rows are immutable once versioned.
- Foreign keys everywhere; indexes on status, asset\_id, task\_id, time ranges, plan\_version\_id, created\_at and audit filters.
- Provenance per record: source\_id, source\_record\_id, ingestion\_time, source\_update\_time, validation\_status, version.
- A data dictionary and entity relationship diagram live in docs/data-dictionary.md and are regenerated from the models in CI.

### 5.3 KPI definitions (computed server-side only)

| KPI | Definition |
| --- | --- |
| Asset availability | Active assets with status available and no active maintenance window, divided by total active assets |
| Serviceability | Available assets whose recorded readiness score meets the configured threshold, divided by total active assets |
| Eligible task | Task not cancelled or completed, inside the planning horizon, with at least one compatible asset and at least one qualified crew member in principle |
| Tasks scheduled | Eligible tasks with an assignment in the current approved plan, divided by eligible tasks |
| Maintenance workload | Planned hours of open maintenance in the window divided by available maintenance capacity hours |
| Overdue maintenance | Status not completed and planned end earlier than now |
| Crew availability | Qualified, available personnel divided by headcount required by scheduled tasks in the window |
| Utilisation | Assigned hours divided by available hours per resource, maintenance excluded |
| Weighted completion | Sum of weight times completed over sum of weight, for eligible tasks |
| Total delay | Sum over tasks of max(0, end minus due) |
| Plan churn | Assignments changed in resource or start time beyond tolerance, divided by total assignments |
| Slack and future readiness | Unassigned capacity hours remaining in the horizon and in the reserve buffer window after it |
| Health (recorded) vs health (estimated) | Two separate columns; the estimated one is a model output and always labelled predicted |

## 6. Data ingestion and fusion (FR-01)

```
Adapter (CSV / JSON / seed generator / future connector)
   → raw landing (source_records, immutable)
   → normalise (IDs, UTC timestamps, units, categories, status enums)
   → validate (schema, required fields, ranges, references, timestamp consistency)
   → detect (duplicates, missing, stale, conflicting values)
   → reconcile (documented rules) or hold for review
   → load to domain tables with provenance and dataset_version
   → update freshness per source → emit events and data_quality_issues
```

- **Adapters:** DataSourceAdapter Protocol with CSV, JSON and seed-generator implementations; connector stubs document the future authorised integrations without claiming access to real systems.
- **Reconciliation:** a rules table (source priority, latest-update-wins within tolerance, never overwrite a value that differs beyond tolerance). Conflicts above tolerance are written as data\_quality\_issues with status needs\_review; the existing value is kept, never silently overwritten.
- **Freshness:** each source has an expected update interval; Celery Beat evaluates it and the UI shows fresh, stale or unavailable.
- **Reproducibility:** the generator is versioned and takes a seed; the same seed and generator version yield an identical dataset\_version hash. All generated rows carry is\_synthetic = true, and the UI shows a persistent synthetic-data banner.
- **Idempotency:** re-ingesting the same source record (same source\_id and source\_record\_id and content hash) is a no-op.

## 7. API layer

### 7.1 Conventions

- Base path /api/v1, JSON, OpenAPI 3.1 published at /openapi.json and frozen per release in docs/api-contracts.md. The TypeScript client is generated from it.
- Pagination with limit and offset plus total; sorting with sort=field:asc; filters as query parameters; free-text search with q.
- Errors use RFC 7807 problem+json with stable codes: validation\_error, forbidden, conflict\_version, infeasible, solver\_timeout, engine\_unavailable, stale\_data. No stack traces leave the server.
- Optimistic concurrency: ETag and If-Match on plans, configuration and records; a stale write returns 409 conflict\_version.
- Idempotency: the Idempotency-Key header on event creation, optimisation jobs and approvals; a replay returns the original result and creates no second effect.
- Async jobs return 202 with a Location header; GET /jobs/{id} gives state and progress; POST /jobs/{id}/cancel cancels; /api/v1/stream (SSE) pushes updates.
- Evidence envelope: every derived value carries data\_kind; predicted values add model\_version, prediction\_timestamp and interval; simulated values add scenario\_id, run\_id and seed.
- Every route declares its required permission; the frontend never decides access.

### 7.2 Endpoint catalogue

(F) = listed in the requirements file. (+) = added in this architecture so that every functional requirement has a contract.

| Group | Endpoints | Notes |
| --- | --- | --- |
| Auth | POST /auth/login (+), POST /auth/refresh (+), POST /auth/logout (+), GET /auth/me (+) | Rate-limited; demo accounts seeded from environment |
| Overview and search | GET /overview (F), GET /search (+) | KPIs computed server-side per section 5.3 |
| Events | GET /events (F), GET /events/{id} (+), POST /events (+), PATCH /events/{id}/review (+) | POST is idempotent, validated, audited |
| Assets | GET /assets (F), GET /assets/{id} (+), PATCH /assets/{id} (+) | Detail includes maintenance and assigned tasks |
| Personnel | GET /personnel (F), GET /personnel/{id} (+), PATCH /personnel/{id} (+), GET /qualifications (+) | Eligibility and conflict checks |
| Tasks, inventory, zones | GET and POST /tasks (+), PATCH /tasks/{id} (+), GET /inventory (+), GET /zones (+) | Server-side validation |
| Maintenance | GET /maintenance (F), POST /maintenance (F), PATCH /maintenance/{id} (+), POST /maintenance/{id}/simulate-delay (+), GET /maintenance/{id}/impact (+) | Delay simulation creates an event |
| Plans | GET /plans (F), GET /plans/{id} (F), GET /plans/{id}/diff (+), GET /plans/{id}/validation (+), GET /plans/{id}/explanation (+), GET /plans/{id}/export (+), POST /plans/{id}/approve (F), POST /plans/{id}/reject (F) | Approve and reject need Reviewer permission and If-Match |
| Optimisation and jobs | POST /optimisation/jobs (F; mode baseline, optimise or replan), GET /jobs (+), GET /jobs/{id} (F), POST /jobs/{id}/cancel (+) | Solver status returned separately from job state |
| Scenarios | POST /scenarios (F), GET /scenarios (+), GET /scenarios/{id} (+), POST /scenarios/{id}/runs (F), GET /scenarios/{id}/runs/{run\_id} (F), POST /scenarios/{id}/runs/{run\_id}/cancel (+), GET /scenarios/{id}/runs/{run\_id}/export (+) | Export includes seed and configuration |
| Predictions | GET /predictions (F), POST /predictions/maintenance (F), POST /predictions/delay (F), POST /predictions/disruption-risk (+), POST /predictions/demand (+), GET /predictions/{id} (+) | Typed, versioned inputs and outputs |
| Anomalies and data quality | GET /anomalies (+), POST /anomalies/scan (+), PATCH /anomalies/{id}/review (+), GET /data-quality/issues (+) | Integrity errors and unusual-but-valid findings kept separate |
| Models | GET /models (F), GET /models/{id}/metrics (F), GET /models/{id}/versions (+), GET /models/{id}/card (+), GET /models/{id}/drift (+), POST /models/{id}/train (+), POST /models/{id}/versions/{v}/promote (+), POST /models/{id}/versions/{v}/rollback (+) | Train, promote and rollback are Admin only |
| Reports | GET /reports (F), POST /reports (+), GET /reports/{id} (+), GET /reports/{id}/download (+) with format csv or pdf | Generation is an async job |
| Audit | GET /audit-logs (F) | Filters: actor, action, entity, date, plan version, scenario |
| System and admin | GET /system/data-sources (F), POST /system/data-sources/{id}/ingest (+), GET /system/health (+), GET /system/environment (+), GET and PUT /system/config/objective-weights (+), PUT /system/engines/{name} (+), POST /admin/seed (+), GET and POST /users (+), PATCH /users/{id} (+), PUT /users/{id}/roles (+) | Admin only; every change audited |
| Assistant | POST /assistant/chat (+, streaming), GET /assistant/conversations (+) | Read-only tools; permission-scoped |

### 7.3 Permission matrix (enforced server-side)

| Capability | Planner | Reviewer | Analyst | Admin |
| --- | --- | --- | --- | --- |
| View assets, personnel, maintenance, events, plans | Yes | Yes | Yes | Yes |
| Create or update demo records | Yes | No | No | Yes |
| Inject simulated events, simulate delays | Yes | No | No | Yes |
| Create scenarios, run optimisation and simulation | Yes | No | No | Yes |
| Approve or reject a proposal | No | Yes | No | No |
| View predictions, model metrics, anomalies | Yes | Yes | Yes | Yes |
| Review anomaly findings | No | No | Yes | Yes |
| Train, promote or roll back models | No | No | No | Yes |
| Users, roles, connectors, configuration, engine toggles | No | No | No | Yes |
| Generate and export reports | Yes | Yes | Yes | Yes (scoped to permitted records) |
| View audit logs | Own actions | Yes | Yes | Yes |
| Use the assistant | Yes | Yes | Yes | Yes (tools scoped to the caller) |

## 8. Scheduling and optimisation engine (FR-05)

### 8.1 Flow

```
snapshot (dataset_version + active objective weight set + solver config)
  → baseline scheduler (weighted earliest-due-date dispatch, earliest feasible slot)
  → independent validator → plan_version type=baseline
  → CP-SAT optimiser (warm-started with baseline or approved plan)
  → independent validator → plan_version type=proposed (only if validation passes)
  → persist solver metadata and objective components → notify Reviewer
```

Time is discretised into configurable slots (default 15 minutes). Each task and compatible-asset pair gets an optional interval with a presence literal, so tasks that cannot be placed become explicit unscheduled tasks instead of a blanket infeasible result.

### 8.2 Hard constraints: encoding and independent check

| Hard constraint (FR-05) | CP-SAT encoding | Validator check (pure Python) |
| --- | --- | --- |
| Resource availability windows | Domain limits and forbidden intervals | Start and end inside a window |
| No incompatible simultaneous assignments | NoOverlap per asset and per person; mutual exclusion for incompatible pairs | Pairwise overlap scan |
| Qualifications and capabilities | Candidate pruning: only qualified optional intervals exist | Qualification lookup per assignment |
| Maintenance and downtime windows | Fixed intervals inside each asset NoOverlap | Overlap with confirmed windows |
| Capacity and quantity | Cumulative constraints per inventory item and zone | Running sum per slot |
| Durations and allowed time windows | Fixed interval size; release and deadline bounds | Duration equality and bounds |
| Precedence and dependencies | end(predecessor) + lag <= start(successor), conditional on presence | Topological order check (NetworkX) |
| Safety and policy restrictions (abstract, synthetic) | Rules from constraint\_definitions: minimum rest, maximum duty hours, per-zone concurrency, abstract restriction windows | Rule-by-rule evaluation |

### 8.3 Objective (soft terms, weights versioned in objective\_weight\_sets)

- Total delay (minimise).
- Weighted completion of eligible tasks (maximise, implemented as an unscheduled penalty).
- Change from the approved plan (minimise churn).
- Utilisation balance without eliminating needed slack.
- Preserved future capacity (reserve buffer window).

Weights are integers scaled for CP-SAT, validated (non-negative, bounded), shown in the UI, stored with every plan, and changed only through an audited Admin action that creates a new version.

### 8.4 Integration of predictions (decision)

Predictions never loosen or override a hard constraint. Hard windows come only from recorded or confirmed data. A predicted downtime extension (selectable percentile, default P80) is added as a soft-penalty buffer zone after the confirmed window, so the planner avoids risky placement without treating a model estimate as a fact. The plan stores which prediction ids and model versions it used.

### 8.5 Solver control and status

- Time limit per job; reproducible mode uses one worker and a fixed random seed; fast mode uses parallel workers and is labelled non-reproducible.
- Hints from baseline or approved plan; progress callback writes to Redis for SSE.
- Runtime, bound, gap, seed, solver version and configuration hash are stored in the manifest.

| CP-SAT outcome | Reported status | Meaning shown in UI |
| --- | --- | --- |
| OPTIMAL | optimal | Proven optimal for the stated model |
| FEASIBLE | feasible | Valid plan found, optimality not proven (for example time limit); best known solution returned and labelled |
| INFEASIBLE | infeasible | Proven infeasible; diagnostics attached |
| UNKNOWN with limit reached and no solution | timeout | No solution found within the limit; not a proof of infeasibility |
| UNKNOWN otherwise | unknown | Solver gave no conclusion |
| MODEL\_INVALID or exception | error | Failure with safe message and log reference |

### 8.6 Infeasibility diagnostics and validation

- Mandatory constraint groups carry assumption literals; on infeasibility the engine extracts a sufficient set of conflicting assumptions and names the tasks, resources and rules involved. If that fails, a relaxation run reports the smallest set of constraints to relax.
- The independent validator runs on every baseline, proposal and manual edit and stores its result in plan\_validations. A plan that fails validation is stored as invalid and cannot be proposed or approved.
- A proposal is a new plan\_version; the approved plan is never modified by the optimiser.
- Manual drag-and-drop is off by default; if enabled, every edit calls the validator and creates a new proposed version.

## 9. Dynamic replanning and event handling (FR-06)

1. **Ingest event:** POST /events (or a data-source event, or a simulated maintenance delay). Fields: timestamp, source, affected entity, severity, validation status, idempotency key. A repeated key returns the stored event and creates no new effect.
2. **Validate:** schema, referenced entity exists, time sanity; failures are stored as unvalidated and do not trigger replanning.
3. **Impact detection:** a graph traversal over assets, personnel, inventory, plan assignments and task dependencies (NetworkX) lists affected assignments, tasks and successors.
4. **Re-evaluate predictions:** for affected entities the maintenance, delay and disruption-risk models are re-run; results carry model version and timestamp.
5. **Feasibility check:** the validator re-checks the current approved plan against the updated data. If it is violated, or objective degradation exceeds a configured threshold, a replan is recommended.
6. **Trigger:** manually (Replan button, Maintenance page) or through a controlled workflow that only creates a proposal job (debounced, rate-limited). It never approves.
7. **Replan:** CP-SAT with a frozen window (unaffected assignments inside a configurable lead time are fixed) plus the churn term, so unaffected commitments are preserved where possible.
8. **Diff:** added, removed, moved and reassigned assignments, objective component differences, unresolved tasks (plan\_diffs).
9. **Record reason:** replan\_triggers stores event id, trigger type, user or system actor, and thresholds crossed.
10. **Proposal:** a new proposed plan\_version with based\_on\_version pointing at the current approved version; the Reviewer is notified.

Plan state machine: baseline, proposed, approved, rejected, superseded, invalid. Only approve moves a proposal to approved and the previous approved plan to superseded, inside one transaction with a version check.

## 10. Predictive ML platform (FR-07, file section 5)

### 10.1 Model suite

| Model | Target | Primary algorithm | Baseline | Split | Metrics | Uncertainty and explanation |
| --- | --- | --- | --- | --- | --- | --- |
| Maintenance downtime | Downtime hours (regression) or time to completion with censoring (survival) | LightGBM quantile regression; lifelines Cox or AFT if censored | Category median | Time-based plus asset-grouped | MAE, RMSE, pinball loss, interval coverage, concordance index | Quantile or MAPIE intervals; SHAP |
| Task delay | Delay minutes | XGBoost or LightGBM | Per task-type mean | Scenario and time-based | MAE, RMSE, error by category | SHAP |
| Disruption risk | Disruption occurs (binary or multi-class) | Gradient boosting with calibration (isotonic or Platt) | Logistic regression and prevalence | Scenario-grouped | Precision, recall, PR-AUC, Brier score, calibration curve | Calibrated probability; SHAP |
| Anomaly detection | Anomaly score | Isolation Forest; PyTorch autoencoder only if it measurably helps | Rule-based flags | Time-based, labelled injected anomalies | Precision at k, recall, false-positive rate | Per-feature deviation or SHAP |
| Resource demand (optional) | Demand per period | LightGBM global model | Seasonal naive and ETS | Rolling-origin | MASE, sMAPE, interval coverage | Prediction intervals |

### 10.2 Training and evaluation pipeline

```
ml/data_generation (generator version + seed) → datasets (DVC, dataset_version hash)
  → feature_engineering (versioned feature schema, pandera) → training (YAML config, seed, Optuna optional)
  → evaluation (held-out test used once; baseline comparison; per-category error analysis)
  → leakage checks → MLflow run (params, metrics, artefacts, dataset version, code SHA)
  → registry: candidate → promotion gate → champion alias → serving
```

- **Leakage controls (automated tests):** forbidden-feature list for label-derived fields, target-correlation scan, time-ordering assertion, no entity or scenario overlap across splits.
- **Model card per model** (docs/model-cards): target, intended use, feature schema and dictionary, training data and version, metrics, limitations, and an explicit statement that synthetic data cannot establish real-world performance.
- **Promotion gate:** candidate beats baseline by a configured margin, calibration acceptable, leakage tests pass, an Admin approves; promotion and rollback are audited.

### 10.3 Serving, monitoring and retraining

- **Serving:** POST /predictions/\* loads the champion by MLflow alias. Validation checks types, units and ranges; out-of-distribution warnings fire for unseen categories and values outside training percentiles; missing inputs follow a documented policy or return 422 with a reason. The response carries value, interval, model\_version, prediction\_timestamp, latency\_ms, warnings and data\_kind = predicted; each result is stored in predictions.
- **Monitoring:** a nightly Beat job computes feature drift (PSI, KS via Evidently) against the training reference and, when simulated outcome labels arrive, performance drift. Model failures and latency feed Prometheus; drift and failure status are visible in Intelligence and Settings.
- **Retraining:** a controlled async job creates a candidate; nothing replaces the champion until the gate passes.
- **Graceful degradation:** if a model is unavailable the API returns engine\_unavailable and the UI shows the gap; no fallback numbers are invented.

## 11. Anomaly and data-integrity detection (FR-08)

- **Tier 1, deterministic:** schema, range, referential, timestamp-consistency, duplicate and staleness rules run first and write data\_quality\_issues with class integrity\_error.
- **Tier 2, ML:** Isolation Forest scores only records that passed tier 1 and writes anomaly\_findings with class unusual\_but\_valid, anomaly score, severity (configured thresholds), contributing features, model version and review status.
- **Review workflow:** statuses new, reviewed, false\_positive, confirmed, with reviewer and timestamp, set from the Intelligence page (Analyst or Admin).
- **Evaluation:** the seed generator injects labelled anomalies (spikes, unit swaps, impossible combinations, drift); the evaluation report states precision, recall and the false-positive rate on clean data.
- **Optional autoencoder:** behind a feature flag and kept only if it measurably beats Isolation Forest at the available data scale.

## 12. Digital twin and scenario simulation (FR-09)

- **Model:** a SimPy discrete-event environment of fictional assets (states available, in\_use, maintenance, unavailable), personnel shifts, tasks with stochastic durations, maintenance with stochastic completion, and an event injector. A simulated clock supports time advancement.
- **Scenario presets** (deterministic JSON in simulation/scenarios): asset unavailability, maintenance delay, resource-capacity reduction, stale data, and abstract environmental restriction (a restriction window on a fictional zone that reduces capacity or limits time windows). Configurable fields: type, affected entity, duration, severity, environmental variability, number of runs, random seed, horizon.
- **Randomness:** SeedSequence(seed).spawn(N) gives each trial its own generator. Baseline and revised plans are run on the same child seeds (common random numbers), so comparisons are paired. Duration distributions (lognormal, triangular or PERT) and availability (Bernoulli) are configured in simulation/distributions; ML predictions may inform them only when explicitly flagged.
- **Plan execution inside the twin:** plan assignments are intent; a documented dispatch rule (right-shift with delay propagation, reassignment to a qualified free resource where allowed) handles disruptions. The simulator works on an in-memory copy through a read-only database role, and a test asserts it never writes to plans or approvals.
- **Execution:** Celery fans trials out in chunks, progress goes through Redis, cancel is cooperative plus revoke, and a failed trial is recorded and counted, never silently dropped.
- **Outputs:** per-trial metrics (completed tasks, weighted completion, total delay, makespan, utilisation, infeasible flag) in simulation\_run\_trials, raw output in MinIO as Parquet. Aggregates: mean, median, standard deviation, P5, P50, P95, bootstrap or t confidence intervals, infeasible-run rate, failed-run count, histograms, and paired baseline-versus-revised differences with intervals.
- **Manifest and labelling:** seed, configuration, run count, runtime, failures, code version, dataset version and model versions are stored. Scenarios can be saved and reopened; CSV or JSON export includes seed and configuration. Every result is labelled simulated and is never presented as an operational outcome.

## 13. Explainability and decision support (FR-10)

| Evidence class | Source | Method | Label |
| --- | --- | --- | --- |
| Model explanation | A stored prediction | SHAP for supported tree models, per prediction and global, with limitations stated | Estimated |
| Schedule explanation | Solver output and validator | Changed assignments, affected tasks, objective-term differences, binding constraints, unresolved tasks with reason codes, infeasibility conflict set | Measured from solver |
| Data provenance | Provenance tables | Links to source records, dataset version, model version | Observed |

- Binding constraints are computed by the validator as zero-slack hard-constraint instances after the solve (CP-SAT does not provide duals); the limitation is documented.
- Unresolved-task reasons come from deterministic per-task probes (which constraint blocks the earliest placement), not from a language model.
- An Explanation object holds evidence\_refs. With none, the API returns insufficient\_evidence; no explanation is fabricated.
- UI surfaces: an explanation panel in Schedule and Approvals, the feature-contribution chart in Intelligence, and badges for Measured, Estimated, Simulated and Generated.

## 14. AI assistant and RAG (FR-11)

```
Chat UI → POST /assistant/chat (SSE)
  → auth context (user, role) → input guard (length, injection heuristics)
  → LLM gateway with read-only tool schemas
  → tool call → Pydantic argument validation → permission check
  → same service layer and RBAC as REST → result wrapped as untrusted data
  → answer composer → citation check (every cited id was returned this turn)
  → response with sources and provenance label
```

- **Model:** an existing LLM behind a gateway interface (hosted by default; self-hosted vLLM or Ollama option for data sovereignty). No LLM is trained from scratch.
- **Tools (read-only):** get\_alert\_summary, get\_plan\_diff, get\_prediction\_provenance, get\_scenario\_summary, get\_data\_quality\_issues, get\_model\_metrics, search\_documents. No approve, configure or write tool exists in the registry, and a test asserts it.
- **RAG:** corpus is approved documentation, model cards and generated reports; heading-aware chunks of roughly 500 to 800 tokens; sentence-transformers embeddings; pgvector plus tsvector hybrid retrieval filtered by role and document version. RAG is used only for documentation questions; structured questions use API tools.
- **Untrusted content:** retrieved text, tool results and user text are delimited as data; instructions inside them are ignored.
- **Honesty:** when tools return nothing the assistant says the data is unavailable or the evidence is insufficient. Each answer is labelled as retrieved documents, API data or generated summary, with uncertainty and missing-source warnings.
- **Logging:** metadata by default (user, time, tools called, record ids, model, token counts, latency); message text retention is configurable (default 30 days, redacted), documented in the privacy policy.
- **Degradation:** controlled by a feature flag and health check; if the LLM is unavailable the page shows a disabled state and the rest of the system is unaffected.
- **Supported prompts:** the five examples in the requirements file (alert summary, plan-version difference, prediction model version, scenario results and limitations, data-quality issues).

## 15. Approval, audit, reports and administration (FR-12 to FR-14)

### 15.1 Approval workflow

1. A proposal appears in the Reviewer queue (Schedule, Proposals tab, and route /schedule/proposals/:planId) with the plan diff, validation result, solver status, objective differences, explanation and any simulation comparison.
2. POST /plans/{id}/approve or /reject requires Reviewer permission, a reason or comment, and If-Match; Idempotency-Key prevents double submission.
3. Server checks: plan state is proposed, validation passed, and the proposal based\_on\_version equals the current approved version; otherwise 409 conflict\_version so a stale proposal cannot overwrite a newer approved plan.
4. In one transaction: update state, supersede the previous approved plan, write approval\_records (user, action, timestamp, plan version, scenario id, reason) and the audit entry.
5. Rejected proposals stay stored and distinct. Nothing replaces the approved plan silently.

### 15.2 Audit

- audit\_logs is append-only: actor, role, action, entity type and id, before and after JSON, plan version, scenario id, reason, request id, UTC timestamp, previous hash and hash (hash chain for tamper evidence). Database permissions and a trigger block UPDATE and DELETE.
- The audit writer is called from the service layer through an @audited decorator inside the same transaction as the change, so a protected action cannot succeed without its record.
- Covered: approvals, rejections, record changes, user and role changes, objective weights, engine toggles, model promotions, ingestion, event injection, assistant tool calls (metadata).
- Searchable by actor, action, entity, date range, plan version and scenario; exportable to CSV.

### 15.3 Reports (FR-13)

| Report | Contents | Data kind shown |
| --- | --- | --- |
| Operational summary | KPIs, alerts, approved plan version, pending proposals | Observed, with simulated items labelled |
| Scenario comparison | Baseline versus revised across runs, distributions, intervals | Simulated |
| Model performance | Metrics, baselines, drift, limitations | Evaluated on synthetic test data |
| Resource utilisation | Utilisation by resource and period | Observed or plan-based |
| Maintenance and downtime | Recorded and predicted downtime, kept separate | Observed and predicted |
| Data quality | Issues, freshness, provenance coverage | Observed |
| Risk and anomaly | Findings, severity, review status | Predicted |
| Audit and approval history | Decisions with plan versions and reasons | Observed |

Generation: POST /reports creates a job on the report queue; queries run under the caller's permissions so exports contain only permitted records; Jinja2 renders HTML, WeasyPrint produces PDF, CSV is streamed; files are stored in MinIO and downloaded through short-lived signed URLs. Every report header states time window, scenario id, dataset version, model versions, plan version, generator version and data kind per metric. A test confirms report values equal the underlying scenario and version data.

### 15.4 Settings and administration (FR-14)

| Settings tab | Function | Guard |
| --- | --- | --- |
| User Management | Create or disable demo users, assign roles, show access level and last login | Admin only; last-admin protection; audited |
| Model Registry | Versions, dataset version, evaluation status and metrics, deployment status, promote and rollback | Promotion gate; audited |
| System Configuration | Objective weights (validated, versioned, effective for new jobs only), thresholds, reconciliation tolerance, time window | Validation plus audit |
| Data Sources | Connector status, last successful update, freshness, validation state, manual ingest | Admin; audited |
| Engines | Enable or disable optional engines (autoencoder, demand forecast, assistant and RAG, anomaly ML, parallel simulation) | Blocked while the engine is in use by a running job |
| Audit and Environment | Audit retention settings, build and environment information, dataset and generator versions | Read-mostly; changes audited |

## 16. Frontend architecture

### 16.1 Structure

Feature-based React project as specified in the requirements file: app/ (App, router, providers, query client), layouts/ (AppShell, Sidebar, Topbar, Breadcrumbs, MobileNavigation), pages/ (11 pages plus LoginPage and NotFoundPage), features/ (overview, operations, scheduling, assets, personnel, maintenance, intelligence, scenarios, assistant, reports, approvals, administration), components/ (ui, data-display, charts, tables, forms, feedback, permissions), services/ (api-client plus one module per domain), hooks/, lib/ (formatting only), types/ (generated), config/, styles/ (tokens.css, globals.css, charts.css). No business logic lives in components; KPIs, eligibility, validation outcomes and plan metrics all come from the API.

### 16.2 Routes

| Route | Page (sidebar item) | Roles | Main endpoints |
| --- | --- | --- | --- |
| /login | LoginPage | Public | /auth/\* |
| / | Overview | All | /overview, /events, /system/data-sources |
| /operations | Operations (Event Centre) | All | /events, /data-quality/issues, /jobs |
| /schedule | Schedule: Timeline, Gantt, Table, Proposals | All view; Planner runs | /plans, /optimisation/jobs, /jobs |
| /schedule/proposals/:planId | Proposal review | Reviewer decides | /plans/{id}, diff, validation, explanation, approve, reject |
| /assets and /assets/:id | Assets (Fleet Assets) | All view; Planner and Admin edit | /assets |
| /personnel | Personnel | All view; Planner and Admin edit | /personnel, /qualifications |
| /maintenance | Maintenance: Schedule, Upcoming, History | All view; Planner creates | /maintenance, simulate-delay, impact, /predictions/maintenance |
| /intelligence/:tab | Intelligence: maintenance-risk, task-delay, resource-demand, anomaly-detection, model-performance | All; Analyst reviews | /predictions, /anomalies, /models |
| /scenarios and /scenarios/:id | Scenarios (Digital Twin) | All view; Planner runs | /scenarios, runs |
| /assistant | AI Assistant | All | /assistant/\* |
| /reports/:type | Reports | All | /reports |
| /settings/:tab | Settings: users, models, config, sources, audit-environment | Admin | /users, /models, /system/\* |
| \* | NotFoundPage | Any | none |

### 16.3 Application shell

- **Sidebar (persistent, dark navy):** Overview, Operations, Schedule, Assets, Personnel, Maintenance, Intelligence, Scenarios, AI Assistant, Reports, Settings. Role-aware (Settings hidden for non-Admin), and every item routes to an implemented page. On narrow screens it becomes a drawer (MobileNavigation).
- **Topbar:** page title with breadcrumbs, global search (GET /search), data-freshness and connection indicator (from /system/data-sources and the SSE state), notifications (alerts over SSE), current demo user and role, user menu with logout.
- **Workspace pattern:** heading and description, right-aligned primary action, filters and date range, KPI row, main table, chart or timeline, secondary panels, and shared loading, empty, partial-data, stale-data and error states. Wide tables and timelines scroll horizontally without breaking the page.

### 16.4 Page map

| Page | Key components | Interactions |
| --- | --- | --- |
| Overview | KPI cards (availability, scheduled over eligible, in maintenance, crew), fictional-zone MapLibre map, alert feed, objectives and task status, readiness, data-source health | KPI click opens filtered detail; alert click opens the event; severity and type filter; last successful update shown; no Live label unless streaming |
| Operations | Event table and timeline, severity, source, entity, validation state, related plan or scenario | Inspect, mark reviewed, open impacted records, view resulting plan change |
| Schedule | Plan version and status, date range, filters, Timeline, Gantt and Table tabs, conflict and unassigned panel, utilisation summary, solver status, runtime and objective | Select task or resource for details, run optimisation with job progress, compare baseline and proposal, export, revalidate any edit |
| Assets | KPI cards, searchable sortable paginated table (ID, type, status, zone, next maintenance, health, actions), detail drawer | Open detail, view maintenance and tasks, change status with permission and audit, recorded versus estimated health shown separately |
| Personnel | Qualifications, availability windows, linked assignments, duty constraints | Eligibility inspection, conflict detection, permitted edits with audit |
| Maintenance | Tabs Schedule, Upcoming, History; table with work-order, asset, category, planned window, status, progress, predicted downtime column; detail panel | Create or update work order, simulate delay, impacted assignments, trigger impact assessment and replan, prediction source, model version, timestamp and interval |
| Intelligence | Tabs for the five model areas, KPI cards, predicted-versus-observed chart (only with valid test data), risk table, feature-contribution chart, model metadata panel, anomaly review list | Filter, open prediction detail, view evaluation report, mark anomaly reviewed |
| Scenarios | Scenario selector, configuration form (type, entity, duration, severity, variability, runs, seed), result tabs Summary, Schedule comparison, Outcome distribution, Run details | Validate inputs, start and cancel, status queued to completed, compare runs, save and reopen, export with seed; everything labelled simulated |
| AI Assistant | Conversation, prompt suggestions, source references, history panel, input | Read-only questions with citations and provenance labels; uncertainty and missing-source warnings |
| Reports | Eight report tabs, date range and filters, KPI cards, charts, underlying records table | Generate with status, CSV and PDF export, header with window, scenario, dataset and model versions |
| Settings | Tabs listed in section 15.4 | Admin-only changes with validation, confirmation and audit |

### 16.5 Shared components and states

- **ui:** Button, Badge, Card, Dialog, Tabs, Tooltip, Select, Input. **data-display:** KpiCard, StatusBadge, FreshnessIndicator, EmptyState, and DataKindBadge (Observed, Predicted, Simulated, Generated, Synthetic, Demo, Approved, Stale). **tables:** reusable searchable, sortable, paginated table. **charts:** ECharts wrappers with consistent palette, axes, tooltips and accessible labels. **feedback:** Skeleton, ErrorState, PartialDataBanner, StaleBanner, JobStatus. **permissions:** a Can component that hides or disables controls only; the server enforces access.
- Every primary button either performs its action or is visibly disabled with a reason. Destructive and consequential actions (approve, reject, promote, delete, role change) require a confirmation dialog.

### 16.6 Visual system and accessibility

- Fixed dark navy sidebar, light workspace, white cards with subtle borders, a single medium-blue accent; green, amber and red for healthy, warning and critical; blue-grey for informational or inactive states. Clean sans-serif, compact readable tables, simple line, bar and donut charts, restrained transitions. Colours are defined as tokens and checked for AA contrast.
- Colour is never the only signal (icons, text and patterns accompany status colours); every chart and the Gantt has a Table equivalent; full keyboard operation, visible focus, semantic landmarks, accessible labels, reduced-motion support; axe checks run in CI.
- The reference image sets structure and direction only; small unreadable text and fabricated values in it are not copied.

## 17. End-to-end tech flow

| Step | Frontend | API | Engine or worker | Data written |
| --- | --- | --- | --- | --- |
| 1 Load or generate snapshot | Settings, Data Sources | POST /admin/seed or POST /system/data-sources/{id}/ingest | ingest queue, data\_fusion | source\_records, domain tables, dataset\_versions, data\_quality\_issues, freshness |
| 2 Inspect state | Overview, Assets, Personnel, Maintenance, Operations | GET overview, assets, personnel, maintenance, events | Repositories, KPI service | None |
| 3 Baseline schedule | Schedule, Run optimisation (baseline) | POST /optimisation/jobs | Baseline scheduler, validator | plan, plan\_version (baseline), plan\_validations; the Reviewer's first approval makes it the current approved plan |
| 4 Introduce disruption | Maintenance, Simulate delay; Operations, inject event | POST /maintenance/{id}/simulate-delay, POST /events | Event service | events (idempotent), audit\_logs |
| 5 See affected records | Impact panel | GET /maintenance/{id}/impact | Replanning impact detector | notifications |
| 6 Predict and replan | Run optimisation (replan) | POST /predictions/\*, POST /optimisation/jobs | Prediction engine, CP-SAT, validator | predictions, replan\_triggers, proposed plan\_version, plan\_diffs |
| 7 Compare outcomes | Proposal review, Scenarios | GET diff and validation; POST scenario runs | digital\_twin | simulation\_runs, simulation\_run\_trials |
| 8 Explain | Explanation panel, Intelligence | GET explanation, GET model card | explainability | Cached explanation (derived) |
| 9 Approve or reject | Proposal review dialog | POST approve or reject | governance, audit | approval\_records, audit\_logs, plan states |
| 10 Retrieve decision trail | Reports, audit view | POST /reports, GET /audit-logs | report worker | reports, files in MinIO |

```
Job lifecycle (optimisation, replanning, training, simulation, report, ingestion)
client POST → api: validate + permission + idempotency → job row (queued) → Celery queue
  → worker: running (progress in Redis → SSE to UI)
      ├─ completed  (result id + solver status where relevant)
      ├─ failed     (error code, safe message, log reference)
      └─ cancelled  (cooperative stop, partial results marked)
```

## 18. Security architecture

- **Authentication:** demo login with Argon2id password hashes, short-lived JWT access tokens, rotating refresh token in an httpOnly secure cookie. Demo accounts are created by a seed script using environment-provided credentials; no credential is hard-coded or committed.
- **Authorisation:** a require(permission) dependency on every route plus object-level checks in services. The UI may hide controls, but a direct API call without permission returns 403 and is logged.
- **Input and output safety:** Pydantic validation on every body and query, parameterised SQL through the ORM, safe problem+json errors, strict CORS allow-list, security headers (CSP, HSTS, X-Content-Type-Options), rate limits on login and expensive endpoints.
- **Secrets and configuration:** environment variables or Docker secrets, .env.example only in the repository, gitleaks in pre-commit and CI.
- **Data protection:** DB roles with least privilege (application read-write, simulator read-only, audit insert-only); signed short-lived URLs for files; log scrubbing; is\_synthetic on every record and a persistent synthetic-data banner; no real classified or restricted information.
- **Assistant security:** read-only tools, argument validation, server-side permission checks, untrusted-data delimiting, citation verification, metadata-only logging by default.
- **Supply chain and hardening:** pinned lockfiles, pip-audit, npm audit, Trivy image scans, Dependabot, non-root containers with read-only file systems where possible.
- **Claims:** the prototype makes no claim of production security certification or certified defence use.

## 19. Non-functional design

- **Performance:** targets are set after benchmarking. A scripts/benchmark.py run measures and reports API latency (Prometheus histograms), model inference latency, optimisation runtime and timeout rate, simulation runtime, and the time from event ingestion to updated proposal (event received\_at to plan created\_at). Results go to docs/performance.md. Long work is always asynchronous with states queued, running, completed, failed and cancelled, plus progress where available.
- **Reliability:** structured JSON logs with request ids; retries only for safe and idempotent operations; timeouts on external calls, Celery soft and hard limits, and solver limits; engine health registry with circuit breakers; no success message before the result is verified; Alembic migrations and seed scripts; backup and export of demo artefacts through scripts/backup.sh (pg\_dump plus MinIO mirror).
- **Accessibility and usability:** as in section 16.6, plus loading, empty, stale-data, partial-data, error and success states on every data view, search, filter, sort and pagination on every table, and clear labels for synthetic, predicted, simulated and approved information.
- **Maintainability:** typed contracts end to end (backend enums and schemas generate the TypeScript types), modular engine interfaces, ruff, mypy, ESLint, Prettier and CI on every change, documented environment setup, no hard-coded KPI values.

## 20. Testing architecture (file section 12)

| Category | What is verified | Tooling |
| --- | --- | --- |
| Functional | Ingestion validates records and stores provenance; dashboard metrics equal database and API results; tables filter, sort, paginate and show empty and error states; the scheduler respects every implemented hard constraint; replanning identifies changed records and creates a new plan version; a proposal never overwrites the approved plan before approval; reports match their scenario and version; the assistant cites records or states insufficient evidence | pytest, Hypothesis property tests (validator cross-checked against CP-SAT output), Vitest, Playwright |
| AI and ML | Every model has a baseline and held-out evaluation; training reproducible from configuration and seed; leakage checks pass; predictions carry model version; missing and out-of-range inputs handled; drift and model failure visible; no synthetic accuracy presented as real-world validation (checked in model cards and UI copy) | pytest, MLflow, Evidently |
| Simulation | Fixed seeds reproduce scenario generation; inputs and outputs saved; Monte Carlo summaries use percentiles and intervals; infeasible and failed runs reported correctly; baseline and proposal compared on identical seeds; simulator never writes to plans | pytest, SimPy fixtures |
| Security | Unauthorised users cannot read protected records or approve; direct API calls cannot bypass UI permission hiding; inputs validated; no secrets in the repository; sensitive configuration changes audited; assistant cannot approve or alter constraints | pytest, Schemathesis against OpenAPI, gitleaks, pip-audit, Trivy |
| UX | Every sidebar link reaches an implemented page; every primary button works or is disabled with a reason; long jobs show progress and recover from failure; layouts hold at desktop and narrower widths; synthetic, predicted, simulated, stale and approved states are distinguishable; accessibility rules pass | Playwright, axe-core |
| Platform | Migrations apply and roll back; seed scripts are deterministic; contract tests keep generated types in sync; benchmark script runs | Alembic tests, CI, scripts/benchmark.py |

## 21. Deployment, DevOps and observability

- **Environments:** local development and demo both use Docker Compose (profiles: core, ml, assistant, observability); CI runs the same images.
- **CI pipeline:** lint (ruff, ESLint, Prettier), type-check (mypy, tsc), unit and integration tests, OpenAPI generation and type sync check, migration test, end-to-end tests, accessibility checks, dependency and secret scans, image build and scan.
- **Reproducible demo:** scripts/demo.sh runs a fixed-seed sequence: seed data, baseline plan, approval, event injection, replan, scenario run, approval, report export. The same seed and generator version produce the same dataset hash.
- **Observability:** Prometheus metrics (API latency, inference latency, solver runtime and timeout rate, simulation runtime, job states, drift flags), Grafana dashboards, OpenTelemetry traces from request to worker, JSON logs with request and job ids.
- **Repository layout:** frontend/, backend/, ml/ (data\_generation, datasets, feature\_engineering, training, evaluation, artifacts, experiments), simulation/ (scenarios, event\_generators, distributions, tests), docs/ (requirements, architecture, data-dictionary, api-contracts, model-cards, testing, deployment, performance, privacy), docker-compose.yml, .env.example, .gitignore, README. Large datasets and artefacts stay out of Git (DVC and MinIO).

## 22. Implementation roadmap

| Phase | Work | Priority |
| --- | --- | --- |
| 0 Contracts | Enums, KPI definitions, data dictionary, API contracts including the added endpoints, user roles, architecture decision records | Must |
| 1 Shell and design system | Tokens, AppShell, Sidebar, Topbar, routing, shared components and states | Must |
| 2 Data foundation | PostgreSQL schema and migrations, seeded generator, validation, provenance, freshness | Must |
| 3 Resources and overview | Assets, personnel, maintenance CRUD with audit, Overview dashboard | Must |
| 4 Scheduling | Baseline scheduler, CP-SAT model, independent validator, solver status handling | Must |
| 5 Governance | Plan versions, comparison, approval and rejection, audit history | Must |
| 6 Replanning and scenarios | Event workflow, impact detection, frozen window, scenario presets | Must |
| 7 ML | Reproducible pipelines, MLflow, serving APIs; maintenance downtime model first, then task delay and disruption risk | Must (one model), then Should |
| 8 Digital twin | SimPy twin, Monte Carlo, paired comparison and robustness metrics | Must (basic), Should (full) |
| 9 Intelligence layer | Anomaly detection, SHAP and constraint explanations, grounded assistant | Should (explanations first) |
| 10 Reporting and admin | Reports with exports, model registry, settings, Operations centre | Should |
| 11 Hardening | End-to-end tests, security checks, observability, Docker packaging, demo script, documentation | Must |

Shared types, the data model and API contracts are established before any page is built in isolation. Optional items (demand forecasting, autoencoder, parallel simulation, drag-and-drop editing, PDF export polish) remain behind feature flags until they prove value.

## 23. Traceability: every item in the requirements file and where it lives

| Requirement in the file | Architectural component | Section |
| --- | --- | --- |
| Product vision, core outcome (10 steps), scope boundary | End-to-end flow; synthetic-only enforcement; no tactical or weapons functions | 17, 18, 24 |
| Principles 1 to 10 | Mechanism table | 1 |
| Roles: Planner, Reviewer, Analyst, Administrator | RBAC permission matrix, server-side enforcement | 7.3, 18 |
| FR-01 Data ingestion | data\_fusion engine, adapters, provenance, freshness, reconciliation, seed generator | 5, 6 |
| FR-02 Overview dashboard | KPI service, Overview page, MapLibre fictional zones | 5.3, 16.4 |
| FR-03 Resource and task management | Repositories, CRUD endpoints, audited updates, paginated tables | 4, 7, 16.4 |
| FR-04 Maintenance management | Maintenance endpoints, predicted versus recorded downtime, delay simulation, impact | 7, 9, 16.4 |
| FR-05 Scheduling and optimisation | Baseline scheduler, CP-SAT, validator, statuses, diagnostics, versioned weights | 8 |
| FR-06 Replanning and events | Event service, idempotency, impact detection, frozen window, diff, trigger reason | 9 |
| FR-07 Predictive ML | Five-model suite, pipeline, MLflow, serving, drift, promotion | 10 |
| FR-08 Anomaly and integrity | Two-tier detection, review workflow, labelled evaluation | 11 |
| FR-09 Digital twin | SimPy, Monte Carlo, paired seeds, manifests | 12 |
| FR-10 Explainability | SHAP, solver evidence, provenance, insufficient\_evidence rule | 13 |
| FR-11 Assistant and RAG | Gateway, read-only tools, pgvector retrieval, guardrails | 14 |
| FR-12 Approval and audit | State machine, optimistic concurrency, hash-chained audit | 15.1, 15.2 |
| FR-13 Reports and analytics | Eight reports, CSV and PDF, headers with versions and data kind | 15.3 |
| FR-14 Settings and administration | Six settings tabs with guards | 15.4 |
| File 5.1 to 5.5 (ML principles) | Rules versus ML split, leakage controls, MLflow, typed serving, SHAP scope | 8, 10, 13 |
| Non-functional: performance, reliability, security, accessibility, maintainability | Benchmarking, engine health, security architecture, a11y rules, typed contracts | 18, 19 |
| Frontend design direction and shell | Visual system, sidebar of 11 items, topbar, responsive drawer | 16 |
| Pages 1 to 9 plus Operations and Personnel | Routes, page map, shared components | 16.2, 16.4 |
| Project structure and component conventions | Repository layout and component folders | 16.1, 21 |
| API contracts (21 endpoints) | Catalogue with original endpoints marked F and added ones marked + | 7 |
| Database entities | Entity groups, conventions, view for assignments | 5 |
| Testing and definition of done | Test matrix | 20 |
| Implementation order | Roadmap | 22 |
| Final release checklist | Verified through section 20 tests and the demo script | 20, 21 |
| Non-goals and assumptions | Decisions and limitations | 24 |

## 24. Decisions, assumptions and limitations

- **Modular monolith, not microservices:** one API plus workers is simpler to test and demo; extraction needs a recorded decision backed by measurements.
- **Celery and Redis, not Kafka:** event volumes in a synthetic prototype do not justify Kafka; revisit only if sustained ingestion throughput measurements require it.
- **PostgreSQL with pgvector:** one datastore for relational data, audit and retrieval, avoiding a separate vector database.
- **CP-SAT reproducibility:** reproducible mode (one worker, fixed seed) is the default for demos and tests; parallel mode is labelled non-reproducible.
- **Optional components:** autoencoder, demand forecasting, RAG, parallel simulation, drag-and-drop editing and PDF export are optional and flag-controlled, included only where testable benefit exists.
- **Self-hosted LLM option:** keeps the assistant usable without sending content to an external provider; the prototype uses synthetic data in either case.
- **Not defined by the problem statement, so not invented here:** real schemas, latency targets, accuracy targets and source-system integrations. They are set after benchmarking or supplied by an authorised source.
- **Limits of the claims:** synthetic-data results demonstrate that the pipeline works, not real-world military performance; the prototype is not certified or production-ready, and it is a human-supervised decision-support tool for logistics, readiness and general resource scheduling.

## 25. Phased implementation plan

This section turns the architecture into an executable plan. It refines the short roadmap in section 22 and takes precedence over it.

### 25.1 Planning assumptions

- **Team (assumption, adjust to reality):** five people, one per workstream. A = Platform and data, B = Optimisation and replanning, C = ML and simulation, D = Frontend, E = Security, QA and DevOps. Calendar below is 24 weeks of two-week sprints. With a smaller team keep the phase order and exit gates and stretch the calendar; use the descoping ladder in 25.8 to protect the core demo.
- **Prototype dimensions (proposed defaults, configurable, to be confirmed by benchmarking in Phase 4):** about 40 fictional assets, 120 personnel, 300 tasks, a 7-day planning horizon, 15-minute slots, 6 fictional zones. These are not from the problem statement; they exist so that the solver and UI can be sized and tested.
- **Working rules:** contracts first; every phase ends with a demo against a phase exit gate; nothing is marked done without tests, audit coverage where it applies, and the loading, empty, error and stale states for any new view; no hard-coded KPI values; every merged change passes CI.
- **Definition of Done (every task):** code reviewed; unit and integration tests pass; OpenAPI and generated types in sync; permissions enforced server-side and tested; audit entry for protected actions; documentation updated; demo data labelled synthetic.

### 25.2 Phase overview

| Phase | Name | Weeks | Goal | Exit gate (demonstrated) |
| --- | --- | --- | --- | --- |
| 0 | Foundations and contracts | 1-2 | Freeze everything other work depends on | Contracts v0.1 reviewed and frozen |
| 1 | Platform skeleton | 2-4 | Running shell, auth, jobs, audit, CI | Four roles log in; dummy job streams progress; audit entry written |
| 2 | Data foundation | 3-6 | Schema, generator, ingestion, provenance | Same seed gives same dataset hash; bad records caught |
| 3 | Resources and overview | 5-8 | Data visible and editable with permissions | Overview KPIs equal database values; CRUD audited |
| 4 | Scheduling | 7-11 | Baseline and CP-SAT plans, validated | Valid baseline and optimised plan on Schedule page |
| 5 | Governance | 10-12 | Plan versions, approval, audit trail | Proposal approved and rejected; stale proposal blocked |
| 6 | Events and replanning | 11-14 | Disruption to validated proposal | Milestone M1: full 10-step flow without ML |
| 7 | ML platform | 12-17 | Reproducible models served with versions | Predictions with version, interval and drift shown |
| 8 | Digital twin | 14-18 | Seeded Monte Carlo comparison | Paired baseline versus revised distributions |
| 9 | Intelligence layer | 16-20 | Anomalies, explanations, assistant | Explanations from real evidence; assistant cannot write |
| 10 | Reports and administration | 17-21 | Reports, registry, settings, event centre | Eight reports export; admin changes audited |
| 11 | Hardening and release | 20-24 | Tests, security, performance, demo | Release checklist (file section 14) fully ticked |

**Milestones:** M0 contracts frozen (end week 2); M1 vertical slice, full core outcome without ML (end week 14); M2 intelligence complete (end week 20); M3 release candidate (end week 22); M4 demo-ready and documented (end week 24).

### 25.3 Critical path and parallelism

Critical path: Phase 0 contracts, Phase 2 schema and generator, Phase 4 scheduler, Phase 5 plan versions and approval, Phase 6 replanning, which delivers M1. Parallel tracks: frontend shell and design system run alongside Phases 1 and 2 using the generated API client and mocks (tests only); ML data work starts as soon as the generator exists (week 6) using stubbed prediction endpoints until models are promoted; the twin starts once plans and events exist (week 14); reports and settings can start as soon as their source data exists.

### 25.4 Detailed phase plans

### Phase 0 - Foundations and contracts (weeks 1-2)

| ID | Task | Stream | Output |
| --- | --- | --- | --- |
| P0-1 | Confirm scope, MVP versus stretch list, roles, display time zone, prototype dimensions | All | Signed-off scope note |
| P0-2 | Data dictionary v1, ERD, shared enum registry, KPI definitions from section 5.3 | A | docs/data-dictionary.md |
| P0-3 | OpenAPI skeleton for all endpoints in section 7 (stubs), problem+json error model, pagination and filter conventions | A | Frozen OpenAPI v0.1, generated TypeScript types |
| P0-4 | Permission matrix finalised, demo account policy (credentials from environment) | E | Permission table and seed policy |
| P0-5 | Constraint catalogue: the synthetic abstract hard constraints with parameters | B | constraint\_definitions spec |
| P0-6 | Synthetic data generation spec: entities, distributions, injected anomalies, label rules for ML targets, seeds | A, C | Generator spec |
| P0-7 | Architecture decision records: modular monolith, Celery over Kafka, pgvector, CP-SAT reproducible mode, prediction-to-optimiser rule | All | docs/adr/ |
| P0-8 | Design tokens, page-state matrix, wireframe review against the reference image | D | Token file, wireframes |
| P0-9 | Repository, branching, review and CI conventions | E | CONTRIBUTING and templates |

**Exit gate:** contracts reviewed by all streams; a change-request process is agreed so contract edits are visible and versioned. **Main risk:** contracts drift later. Mitigation: type generation in CI fails when frontend and backend disagree.

### Phase 1 - Platform skeleton (weeks 2-4)

| ID | Task | Stream | Output |
| --- | --- | --- | --- |
| P1-1 | Monorepo scaffold, uv and pnpm lockfiles, pre-commit, ruff, mypy, ESLint, Prettier | E | Repo ready |
| P1-2 | CI pipeline: lint, type-check, tests, build, dependency and secret scans, type-sync check | E | Green pipeline |
| P1-3 | Docker Compose core profile: postgres, redis, minio, api, worker, caddy, health endpoints | E | One-command start |
| P1-4 | FastAPI app factory, settings, structlog, request ids, problem+json handlers, OpenTelemetry stub | A | API base |
| P1-5 | Alembic baseline, identity tables, login, refresh, logout, me, Argon2id, JWT, require(permission), rate limiting | A, E | Auth and RBAC |
| P1-6 | Audit writer with the audited decorator, append-only table, update and delete block, hash chain | A, E | Audit core |
| P1-7 | Celery queues, generic jobs table, SSE stream, job state and cancel endpoints | A | Async job framework |
| P1-8 | Engine health registry and feature flags | A | Degradation framework |
| P1-9 | Frontend scaffold: Vite, router, providers, generated client, AppShell, Sidebar with 11 items, Topbar, mobile drawer, tokens, shared ui, data-display, feedback and permissions components, LoginPage, NotFoundPage, placeholder pages | D | Navigable shell |

**Exit gate:** four demo roles log in; every sidebar link opens a page; a dummy job reports queued, running and completed over SSE; its audit record exists and cannot be altered; CI is green. **Main risk:** over-building infrastructure. Mitigation: only what later phases use; observability stack waits for Phase 11.

### Phase 2 - Data foundation (weeks 3-6)

| ID | Task | Stream | Output |
| --- | --- | --- | --- |
| P2-1 | Migrations for resources, work, events, provenance and quality entities with foreign keys and indexes | A | Schema v1 |
| P2-2 | Seeded synthetic generator v1 (assets, personnel, qualifications, zones, inventory, tasks, dependencies, maintenance, events), dataset\_version hash, POST /admin/seed | A | Reproducible dataset |
| P2-3 | DataSourceAdapter Protocol, CSV and JSON adapters, connector stubs | A | Adapters |
| P2-4 | Normalisation, validation (Pydantic, pandera), duplicate, missing, stale and conflict detection, reconciliation rules table, data\_quality\_issues | A | Fusion engine |
| P2-5 | Provenance records, freshness evaluation (Beat), GET /system/data-sources | A | Provenance and freshness |
| P2-6 | Repositories with filtering, sorting, pagination; KPI service skeleton | A | Query layer |
| P2-7 | DVC with MinIO for datasets | A, E | Dataset storage |
| P2-8 | Tests: seed determinism, validation cases, idempotent re-ingest, conflicts kept for review not overwritten | A, E | Passing suite |

**Exit gate:** the same seed and generator version produce the same dataset hash; injected invalid records are flagged; re-ingesting is a no-op; conflicting values appear as review items. **Main risk:** unrealistic synthetic data. Mitigation: documented rules with variation, and a disclosure in the data dictionary and UI.

### Phase 3 - Resources and overview (weeks 5-8)

| ID | Task | Stream | Output |
| --- | --- | --- | --- |
| P3-1 | Asset, personnel, task, inventory, zone and maintenance endpoints with server-side validation, role checks, audit | A | Resource APIs |
| P3-2 | Maintenance rule: reject incompatible assignments inside maintenance windows | A | Validation rule |
| P3-3 | GET /overview with all KPIs per section 5.3, GET /search, events list | A | Overview API |
| P3-4 | Reusable table (search, filter, sort, pagination, empty and error states) | D | Table component |
| P3-5 | Overview page: KPI cards, MapLibre map of fictional zones, alert feed, objectives and task status, data-source health, KPI click-through | D | Overview page |
| P3-6 | Assets page with detail drawer; Personnel page with qualifications, availability, eligibility; Maintenance page with tabs and detail panel (predicted column shown as not available yet) | D | Resource pages |
| P3-7 | Operations page v1: event table and timeline with filters | D | Event centre v1 |
| P3-8 | Tests: KPI values equal database, table behaviour, permission checks on edits | E | Passing suite |

**Exit gate:** every Overview number matches a direct database query; edits require permission and appear in the audit log; synthetic labels visible. **Main risk:** KPI definitions disagree between pages. Mitigation: one server-side KPI service.

### Phase 4 - Scheduling (weeks 7-11)

| ID | Task | Stream | Output |
| --- | --- | --- | --- |
| P4-1 | Baseline scheduler (weighted earliest-due-date dispatch, earliest feasible slot) | B | Baseline plans |
| P4-2 | The eight hard constraints as separate, individually testable modules | B | Constraint modules |
| P4-3 | Independent pure-Python validator covering all hard constraints | B | Validator |
| P4-4 | CP-SAT model: optional intervals, objective terms, versioned objective\_weight\_sets, reproducible configuration, hints, progress callback | B | Optimiser |
| P4-5 | Status mapping, infeasibility diagnostics through assumptions, unscheduled-task reason codes | B | Honest results |
| P4-6 | Plan persistence: plans, versions, assignments, validations, manifests, approved-assignments view | A, B | Plan storage |
| P4-7 | POST /optimisation/jobs (baseline and optimise), cancel, time limits | A, B | Job API |
| P4-8 | Schedule page: timeline, Gantt and table tabs, filters, detail panel, conflict and unassigned panel, utilisation summary, solver status, runtime, objective, run button with progress | D | Schedule page |
| P4-9 | Hypothesis property tests, solver-versus-validator cross-checks, benchmark across dataset sizes, tune slot size and limits | B, E | Benchmarks, tuning |

**Exit gate:** baseline and optimised plans pass the validator; every status type is reproducible in a test (optimal, feasible, infeasible, timeout); the Schedule page shows solver status and runtime honestly. **Main risk:** solver runtime on realistic size. Mitigation: early benchmarks in P4-9 (start it in week 8), slot-size tuning, decomposition by horizon or zone only if needed.

### Phase 5 - Governance (weeks 10-12)

| ID | Task | Stream | Output |
| --- | --- | --- | --- |
| P5-1 | Plan state machine, based\_on\_version, plan\_diffs service | A, B | Plan lifecycle |
| P5-2 | Approve and reject endpoints: Reviewer permission, reason, If-Match, Idempotency-Key, one-transaction supersede, approval\_records | A, E | Approval API |
| P5-3 | Audit log endpoint with filters and CSV export | A | Audit API |
| P5-4 | Proposal review page (route /schedule/proposals/:planId) with diff view, validation result, approve and reject dialog; Proposals tab in Schedule | D | Approval UI |
| P5-5 | Audit history view and filters | D | Audit UI |
| P5-6 | Tests: stale proposal returns 409, non-Reviewer blocked on direct API calls, optimiser cannot modify approved plan, double submit is idempotent | E | Passing suite |

**Exit gate:** a baseline is approved and becomes the current plan; a second proposal is approved and supersedes it; a stale proposal and an unauthorised call are both refused; every step is in the audit log.

### Phase 6 - Events and replanning (weeks 11-14)

| ID | Task | Stream | Output |
| --- | --- | --- | --- |
| P6-1 | Event service: POST /events, idempotency key, validation status, audit | A | Event ingestion |
| P6-2 | POST /maintenance/{id}/simulate-delay and PATCH maintenance; event types: asset unavailability, maintenance delay, capacity reduction, stale data, abstract environmental restriction | A | Disruption inputs |
| P6-3 | Impact detector (NetworkX graph over assets, personnel, inventory, assignments, dependencies) and GET /maintenance/{id}/impact | B | Impact assessment |
| P6-4 | Feasibility re-check of the approved plan with the validator; degradation threshold; replan recommendation | B | Trigger logic |
| P6-5 | Replan mode in the optimiser: frozen window, churn term, warm start from approved plan; replan\_triggers with reason | B | Replanning |
| P6-6 | Controlled workflow: auto-create a proposal job only (debounced, rate-limited), never approve; notifications to Reviewers | A, B | Event workflow |
| P6-7 | Plan diff and GET /plans/{id}/diff, objective-difference summary, unresolved tasks | B | Diff API |
| P6-8 | UI: Maintenance impact panel and Replan action; Operations page complete (inspect, mark reviewed, open impacted records, see resulting plan change); baseline-versus-proposal comparison in Schedule; clickable alerts on Overview | D | Disruption UI |
| P6-9 | Tests: duplicate events create no second effect; unaffected commitments preserved inside the frozen window; each disruption type produces an impact list | E | Passing suite |

**Exit gate (milestone M1):** a Planner loads a seeded dataset, generates and gets an approved baseline, injects a maintenance delay, sees affected tasks, runs replanning, compares the diff, and a Reviewer approves; the audit trail retrieves the whole decision. ML is not required yet; predictions show as not available. **Main risk:** replans shuffle too many assignments. Mitigation: tune the churn weight and frozen-window length with benchmarks, and show churn as a metric.

### Phase 7 - ML platform (weeks 12-17)

| ID | Task | Stream | Output |
| --- | --- | --- | --- |
| P7-1 | Generator extension for labels (downtime, delay, disruption) with documented rules; feature schema with pandera; leakage forbidden-feature list | C | Training data v1 |
| P7-2 | MLflow server (PostgreSQL and MinIO), registry aliases, experiment conventions | C, E | Tracking |
| P7-3 | Model 1, maintenance downtime: baseline, LightGBM quantile (survival model if censoring exists), time-aware and asset-grouped split, evaluation, model card | C | First model |
| P7-4 | Model 2, task delay: XGBoost or LightGBM versus per-type mean, error by category, model card | C | Second model |
| P7-5 | Model 3, disruption risk: calibrated classifier, PR-AUC, Brier, calibration curve, model card | C | Third model |
| P7-6 | Prediction engine and endpoints: input validation, out-of-distribution warnings, missing-input policy, interval, version, timestamp, latency, predictions table | A, C | Serving |
| P7-7 | Drift job (PSI, KS via Evidently), failure counters, promotion gate, train, promote and rollback endpoints | C, E | Model governance |
| P7-8 | Integration: predicted downtime as soft buffer in the optimiser (section 8.4); re-prediction step inside replanning | B, C | Predictions in planning |
| P7-9 | Optional, behind a flag: resource-demand forecast versus seasonal naive and ETS | C | Optional model |
| P7-10 | Frontend: Intelligence tabs (Maintenance Risk, Task Delay, Resource Demand, Model Performance), predicted-versus-observed chart only with valid test data, risk table, feature-contribution chart, metadata panel, prediction columns on Maintenance, synthetic-data disclaimer | D | Intelligence UI v1 |
| P7-11 | Tests: held-out evaluation exists for each model, training reproducible from configuration, leakage checks, model version on every prediction, missing and out-of-range input handling | E | Passing suite |

**Exit gate:** each promoted model beats its baseline on held-out synthetic data, with metrics reproducible from configuration; every prediction shows version, timestamp and interval; drift and failure status are visible; no UI text claims real-world accuracy. **Main risk:** synthetic data yields overly good metrics. Mitigation: noise, covariate shift and per-category error analysis in the evaluation, and a standing limitation note.

### Phase 8 - Digital twin (weeks 14-18)

| ID | Task | Stream | Output |
| --- | --- | --- | --- |
| P8-1 | SimPy environment: asset states, personnel shifts, stochastic task and maintenance durations, event injector, simulated clock | C | Twin core |
| P8-2 | Scenario presets (JSON) and distribution configs; validation of scenario inputs | C | Scenarios |
| P8-3 | Dispatch rule for plan execution under disruption; read-only database role for the simulator | C, E | Safe execution |
| P8-4 | Monte Carlo runner: SeedSequence child seeds, common random numbers for baseline and revised plans, Celery fan-out, progress, cancel, failed-trial capture | C | Runner |
| P8-5 | Statistics: mean, median, standard deviation, P5, P50, P95, bootstrap or t intervals, infeasible-run rate, paired differences; trials table plus Parquet in MinIO; manifest | C | Results |
| P8-6 | Scenario and run endpoints, save and reopen, export with seed and configuration | A | Scenario API |
| P8-7 | Scenarios page: configuration form, run controls, tabs Summary, Schedule comparison, Outcome distribution, Run details; every result labelled simulated | D | Scenarios UI |
| P8-8 | Tests: fixed seed reproduces results, inputs and outputs saved, failed and infeasible runs reported, identical seeds for both plans, simulator never writes to plans | E | Passing suite |

**Exit gate:** a scenario run with a fixed seed gives identical results twice; baseline and revised plans are compared on the same trials with confidence intervals; cancelling a run works; results are labelled simulated everywhere. **Main risk:** run time grows with run count. Mitigation: chunked fan-out, a default run count chosen from benchmarks, results streamed as chunks finish.

### Phase 9 - Intelligence layer (weeks 16-20)

| ID | Task | Stream | Output |
| --- | --- | --- | --- |
| P9-1 | Anomaly tier 1: deterministic integrity rules wired to data\_quality\_issues | A | Integrity checks |
| P9-2 | Anomaly tier 2: Isolation Forest, scores, severity, contributing features, anomaly\_findings, review workflow, evaluation on injected labelled anomalies and clean-data false-positive rate; autoencoder only if it measurably helps | C | Anomaly detection |
| P9-3 | Explainability engine: SHAP for supported models; solver evidence (changed assignments, affected tasks, objective differences, binding constraints through slack, unresolved-task reason codes, infeasibility conflict set); insufficient\_evidence rule | B, C | Explanations |
| P9-4 | Frontend: Anomaly Detection tab with review actions; explanation panel in Schedule and proposal review; evidence badges | D | Evidence UI |
| P9-5 | Assistant backend: LLM gateway, read-only tool registry, argument validation, permission checks, untrusted-data delimiting, citation verification, metadata-only logging, feature flag | A, E | Assistant core |
| P9-6 | RAG: ingest approved docs, model cards and reports; heading-aware chunking; embeddings; pgvector plus full-text hybrid retrieval with role filter | A, C | Retrieval |
| P9-7 | Assistant page: conversation, suggestions, source references, history, provenance labels, disabled state when unavailable | D | Assistant UI |
| P9-8 | Tests: prompt-injection cases, tool denylist (no approve or write tools), permission scoping, answers cite returned records or say evidence is insufficient | E | Passing suite |

**Exit gate (milestone M2):** explanations come only from solver and model outputs; anomalies are reviewable and evaluated; the assistant answers the five example prompts with citations, refuses unsupported ones, and cannot approve or alter anything. **Main risk:** the assistant states unsupported facts. Mitigation: citation verification against records returned in the same turn, and the insufficient-evidence fallback.

### Phase 10 - Reports and administration (weeks 17-21)

| ID | Task | Stream | Output |
| --- | --- | --- | --- |
| P10-1 | Report job pipeline: permission-scoped queries, Jinja2 templates, WeasyPrint PDF, streamed CSV, MinIO storage, signed download URLs | A | Report engine |
| P10-2 | The eight reports with headers (window, scenario, dataset version, model versions, plan version, data kind per metric) | A, C | Report set |
| P10-3 | Reports page: tabs, filters, KPI cards, charts, underlying records, generation status, exports | D | Reports UI |
| P10-4 | User and role management endpoints with last-admin protection | A, E | User admin |
| P10-5 | Model registry view with promote and rollback; objective-weight configuration with validation and versioning; engine toggles with in-use blocking; data-source status and manual ingest; audit and environment tab | A, D | Settings |
| P10-6 | Notifications polish, global search, topbar freshness indicator | D | Shell polish |
| P10-7 | Tests: reports equal underlying scenario and version data; exports contain only permitted records; every configuration change audited | E | Passing suite |

**Exit gate:** all eight reports generate and export with correct headers; an Admin changes objective weights and promotes a model with both actions audited; non-Admin calls to those endpoints fail.

### Phase 11 - Hardening and release (weeks 20-24)

| ID | Task | Stream | Output |
| --- | --- | --- | --- |
| P11-1 | Full end-to-end suite covering the 10-step core outcome and every role | E | Playwright suite |
| P11-2 | Security pass: authorisation matrix tests, direct-API bypass tests, input fuzzing with Schemathesis, header and CORS review, dependency and image scans | E | Security report |
| P11-3 | Benchmark script and docs/performance.md: API latency, inference latency, solver runtime and timeout rate, simulation runtime, event-to-proposal time; set targets from measurements | E, B | Performance report |
| P11-4 | Observability: Prometheus metrics, Grafana dashboards, OpenTelemetry traces, log review | E | Dashboards |
| P11-5 | Accessibility audit (axe plus manual keyboard pass), responsive pass on tablet and mobile widths, contrast review | D, E | A11y report |
| P11-6 | Backup and restore script, migration rollback test, environment setup docs | E | Operability |
| P11-7 | scripts/demo.sh and a fixed demo dataset; rehearsal of the completion criterion end to end | All | Demo kit |
| P11-8 | Documentation: README, architecture, data dictionary, API contracts, model cards, testing, deployment, privacy policy, limitations | All | Docs set |
| P11-9 | Walk through the release checklist (file section 14), bug bash, freeze | All | Release candidate |

**Exit gate (milestone M4):** every item in the release checklist is ticked with evidence; the demo runs from a clean checkout with one script and gives the same results on repeat.

### 25.5 Requirement-to-phase map

| Requirement | Built in | Verified in |
| --- | --- | --- |
| FR-01 Data ingestion | 2 | 2, 11 |
| FR-02 Overview dashboard | 3 | 3 |
| FR-03 Resource and task management | 3 | 3 |
| FR-04 Maintenance management | 3, 6, 7 | 6, 7 |
| FR-05 Scheduling and optimisation | 4 | 4 |
| FR-06 Replanning and events | 6 | 6 |
| FR-07 Predictive ML | 7 | 7 |
| FR-08 Anomaly detection | 2 (rules), 9 | 9 |
| FR-09 Digital twin | 8 | 8 |
| FR-10 Explainability | 9 | 9 |
| FR-11 Assistant and RAG | 9 | 9 |
| FR-12 Approval and audit | 1 (audit core), 5 | 5 |
| FR-13 Reports | 10 | 10 |
| FR-14 Settings and administration | 10 (config, users, registry), 7 (promotion) | 10 |
| Non-functional (performance, reliability, security, accessibility) | 1 onward, 11 | 11 |

### 25.6 Risk register

| Risk | Impact | Mitigation | Owner |
| --- | --- | --- | --- |
| Solver too slow at target size | Schedule page unusable | Early benchmark (week 8), slot-size tuning, time limits with honest feasible status, decomposition only if needed | B |
| Contract drift between frontend and backend | Rework | Generated types and type-sync CI check | A, D |
| Synthetic data unrealistic or leaky | Misleading model results | Documented generator rules, leakage tests, held-out test, explicit limitation text | C |
| Scope too large for the timeline | Core demo at risk | Must-should-could tagging and the descoping ladder | All |
| Non-reproducible solver or simulation | Failed determinism tests | Single-worker seeded mode as default, seeded generators, manifests | B, C |
| Assistant produces unsupported claims | Trust loss | Tool-only facts, citation verification, insufficient-evidence fallback | A, E |
| Permissions only enforced in UI | Security failure | Server-side dependency on every route, bypass tests in CI | E |
| Replans too disruptive | Poor proposals | Frozen window, churn objective, churn metric shown | B |
| Late integration surprises | Slipped milestones | Vertical slice by week 14, integration demo at every phase gate | All |

### 25.7 Descoping ladder (cut in this order if time runs short)

1. PDF export polish (keep CSV) and report styling.
2. Resource-demand forecasting model and the autoencoder.
3. Drag-and-drop schedule editing (not planned by default).
4. Parallel simulation tuning and extra scenario presets beyond the four disruption types.
5. Self-hosted LLM option, RAG corpus beyond core documents.
6. Observability dashboards beyond latency and job metrics.
7. Never cut: constraint validator, honest solver statuses, approval and audit, human oversight, synthetic labelling, server-side permissions, reproducibility of the core demo.

### 25.8 First two weeks, concrete

- Week 1: run scope and dimension workshop (P0-1); start data dictionary and KPI sheet (P0-2); draft OpenAPI skeleton (P0-3); scaffold the repository and CI (P1-1, P1-2); settle design tokens (P0-8).
- Week 2: freeze contracts v0.1 (M0); write the constraint catalogue and generator spec (P0-5, P0-6); record ADRs (P0-7); bring up Docker Compose with postgres, redis and minio (P1-3); start auth, RBAC and the audit writer (P1-5, P1-6); begin the frontend shell (P1-9).

## 26. Amendment v1.1: additional critical components

A gap review of the requirements file against this architecture found components that the file does not specify but that the core demo, its reproducibility and its credibility depend on. This amendment adds them. Where wording here conflicts with sections 1 to 25, this section governs. Phase placement and task IDs are in the separate Implementation Plan document (section 9), which also supersedes section 25 of this document.

### 26.1 Summary and amended sections

| # | Component | Priority | Amends sections | Plan phases |
| --- | --- | --- | --- | --- |
| 1 | Clock and as-of service | Must | 3, 4, 5.2, 5.3, 6, 12 | 0, 1, 2, 8 |
| 2 | Task execution tracking and rolling horizon | Must | 5.1, 5.3, 9, 10, 16.4 | 2, 3, 6, 7 |
| 3 | Stale proposals and approval-time revalidation | Must | 8, 9, 15.1 | 5 |
| 4 | Plan rollback | Must | 9, 15.1 | 5 |
| 5 | Benchmark and evidence suite | Must | 12, 15.3, 20 | 4, 6, 8, 11 |
| 6 | Usage-driven maintenance and spares logistics | Must | 5.1, 8.2, 9, 10 | 2, 3, 4, 6, 7 |
| 7 | Alert rules and lifecycle | Should | 5.1, 16.4 | 6, 10 |
| 8 | Solver fallback chain | Should | 8.5 | 4 |
| 9 | Constraint registry management | Should | 8.2, 15.4 | 4, 5, 10 |
| 10 | Guided demo mode and limitations page | Should | 16, 21 | 2, 3, 10, 11 |
| 11 | Job concurrency rules | Should | 3, 8 | 1, 4, 8 |
| 12 | Alternative proposals, prediction-versus-outcome view, reproducibility bundle | Could | 8, 10, 15, 21 | 5, 7, 11 |

### 26.2 Clock and as-of service (item 1)

Problem: overdue maintenance, availability, frozen windows and replanning all depend on what now means. A real clock makes repeated demos differ, which breaks the reproducibility principle.

- **Clock Protocol** in core/clock.py with three implementations: SystemClock, FixedClock (demo time pinned) and SimulatedClock (advanceable). Mode and demo as-of timestamp are configuration; the effective state is stored in a system\_clock\_state table and cached in Redis so the API and every worker read the same time.
- **Rule:** no service, engine or worker calls datetime.now or utcnow directly. A lint rule and a test enforce this; everything receives a Clock by injection.
- **Stored as\_of:** dataset\_versions, plan\_versions, predictions, simulation\_runs, benchmark\_runs and reports carry the as\_of timestamp used to produce them. KPI endpoints accept an as\_of parameter that defaults to the clock.
- **Generator:** synthetic data uses offsets relative to as\_of, so the same seed plus the same as\_of gives the same dataset hash (the hash covers as\_of).
- **Digital twin:** the SimPy clock is a SimulatedClock; trial time never touches the system clock.
- **API:** GET /system/clock; PUT /system/clock (set, advance, reset; Admin; audited).
- **UI:** the topbar shows a Demo time badge whenever the clock is not the system clock; Settings gets a clock control with advance buttons.

### 26.3 Task execution tracking and rolling horizon (item 2)

Problem: tasks are planned but nothing records that they started or finished. That breaks the completed-tasks KPI, the delay-model labels and the frozen-window logic, because the system cannot tell what has already happened.

- **Task lifecycle:** pending, scheduled, in\_progress, completed, cancelled, blocked. Transitions go through task\_executions (task\_id, assignment\_id, plan\_version\_id, actual\_start, actual\_end, actual resources, delay\_minutes derived, recorded\_by, source, version).
- **Endpoints:** POST /tasks/{id}/start, /complete, /cancel; GET /tasks/{id}/executions. Planner and Admin only; validated and audited. A task\_progress event type lets feeds report the same facts.
- **Locked assignments:** any assignment with an actual\_start at or before as\_of is locked. The optimiser and replanner treat locked assignments as fixed intervals; only unstarted work can move. This replaces the frozen window as the first line of preservation; the configurable frozen window still protects imminent unstarted work.
- **Rolling horizon job:** horizon\_roll (manual or Beat) advances the horizon to as\_of plus H, carries unfinished tasks forward, flags overdue work and creates a proposal. It never approves anything.
- **KPIs:** tasks completed come from task\_executions; the delay model label is actual\_end minus planned\_end from observed (synthetic-feed) executions; usage counters (26.6) accrue only from completed executions.
- **Twin:** simulated executions are written to simulation tables only, never to task\_executions.
- **UI:** status chips and Start and Complete actions in the Schedule task panel; execution history in task details.

### 26.4 Plan lifecycle v2: staleness, revalidation, rollback (items 3 and 4)

The version check in section 15.1 compares plan versions only. It does not catch data that changed after a proposal was built, or two proposals built on the same approved plan.

**Plan fields:** kind (baseline, optimised, replan, fallback, rollback, alternative), status (proposed, stale, approved, rejected, superseded, invalid, withdrawn), based\_on\_version, snapshot\_hash, constraint\_set\_version, weight\_set\_version, stale\_reason, refreshed\_from, rollback\_target, proposal\_group\_id.

| From | To | Trigger | Actor |
| --- | --- | --- | --- |
| proposed | approved | Approve, revalidation passes, versions match | Reviewer |
| proposed | rejected | Reject with reason | Reviewer |
| proposed | stale | Another plan approved, constraint set activated, or relevant data changed | System |
| proposed | invalid | Validator fails at creation | System |
| proposed | withdrawn | Creator withdraws, or a sibling alternative is chosen | Planner or system |
| approved | superseded | A newer plan is approved | System |

- **Snapshot fingerprint:** snapshot\_hash covers the dataset version, latest updates of the entities the plan uses, constraint set version and weight set version. A background staleness check marks a proposal stale when changes touch entities it assigns; unrelated changes only raise a soft warning. Stale proposals stay as records.
- **Sibling staleness:** approving a plan marks every other proposed plan with a different based\_on\_version stale in the same transaction.
- **Approval-time revalidation:** the approve endpoint runs the independent validator against the current snapshot, inside the transaction, not the snapshot used at proposal time. Violations return 409 revalidation\_failed with the violation list and mark the proposal stale. Nothing is approved on failure.
- **Refresh:** POST /plans/{id}/refresh creates a new proposal (warm-started re-solve on the current snapshot) with refreshed\_from set.
- **Rollback:** POST /plans/{id}/rollback-proposal targets any earlier approved or superseded version and creates a proposal of kind rollback with a required reason. It is revalidated against current data; if it fails, diagnostics are returned and a re-optimise-from-target option is offered. It then follows the normal Reviewer approval; an approved plan is never replaced silently. Planners request, Reviewers approve.
- **Endpoints added:** POST /plans/{id}/refresh, POST /plans/{id}/rollback-proposal, POST /plans/{id}/withdraw, GET /plans/{id}/staleness.
- **UI:** a Stale badge and reason on proposals, a Refresh action, a Rollback action in plan history, and the revalidation result shown in the approve dialog.

### 26.5 Solver fallback chain and job concurrency (items 8 and 11)

**Fallback chain (labelled, never silent):**

1. CP-SAT within the time limit. Optimal or feasible results become a proposal as before.
2. If CP-SAT times out without a solution or errors, run the baseline heuristic on the same snapshot. The result is a proposal of kind fallback with plan\_source heuristic\_fallback; the solver status stays timeout or error and a banner explains why. It still passes the validator.
3. If the heuristic cannot produce a valid plan either, no proposal is created. The UI shows diagnostics: the conflict set, unscheduled reasons and suggested relaxations.

Plans carry two separate fields: solver\_status and plan\_source (cpsat, heuristic\_fallback, rollback, manual).

**Concurrency rules:**

- One active optimisation per scope (horizon plus zone, or all) through a Redis lock keyed opt:{scope}; a second request is queued with a visible position or rejected with 409 job\_in\_progress, by configuration.
- Identical requests (same snapshot\_hash, configuration hash and seed) return the existing result idempotently.
- Per-user limit of two active jobs; global worker concurrency limits; priority replan over optimise over benchmark.
- Heartbeats with a reaper that fails stuck jobs and releases their locks; cancel always releases the lock.
- Same pattern for simulation (maximum parallel runs) and training (one per model).

### 26.6 Usage-driven maintenance and spares logistics (item 6)

Problem: the file lists next maintenance and inventory but not what generates due dates or what consumes and resupplies stock. All of this stays abstract and synthetic.

**New entities:** asset\_usage\_counters (asset, counter type such as hours, cycles or calendar days, value, as\_of), maintenance\_rules (category, trigger type usage, calendar or condition, threshold or interval, tolerance, lead time, duration estimate, required parts and skills), maintenance\_due (derived due items), parts\_catalog, spares\_inventory (part, zone, on\_hand, reserved, minimum level), maintenance\_part\_requirements, spares\_movements (consumption and receipt), resupply\_orders (part, quantity, ordered\_at, ETA, status).

- **Maintenance planner service:** evaluates rules against counters and as\_of and creates due items. Due items are treated by the optimiser as maintenance tasks with a hard deadline (threshold plus tolerance) and a soft target.
- **Usage accrual:** completed task executions add usage to the counters of the assets used; this couples the schedule to future maintenance demand.
- **Two new hard constraints (added to section 8.2):** (a) usage budget: planned usage within the horizon must not exceed the remaining allowance (limit minus counter) unless a maintenance task that resets the counter is scheduled earlier; the first release implements the horizon-budget form; (b) spares availability: on\_hand plus receipts by ETA minus consumption stays non-negative over time, encoded with a CP-SAT reservoir constraint, with the validator checking the running balance.
- **Events:** a resupply\_delay event type triggers impact assessment like any other disruption.
- **ML link:** usage counters become features for the downtime model; leakage tests require the value as of prediction time.
- **Endpoints:** GET /spares, GET /parts, GET and POST /resupply-orders, GET and PUT /maintenance-rules (PUT Admin), GET /maintenance/due, GET and POST /assets/{id}/usage.
- **UI:** a Due soon tab on Maintenance, usage counters on the asset detail, spares and resupply views, and a spares-shortage input to the Overview KPI.

### 26.7 Alert rules and lifecycle (item 7)

Events are inputs and facts; alerts are derived conditions that need attention. The Overview and Operations pages show alerts, so their production must be defined.

- **Entities:** alert\_rules (name, scope, condition type and parameters, severity, enabled, dedup window, clear threshold, version) and alerts (rule, entity reference, severity, status new, acknowledged, resolved or suppressed, first\_seen, last\_seen, count, dedup\_key, acknowledged and resolved by and at, reason, linked event, plan or scenario).
- **Rule catalogue (initial):** KPI threshold breach (for example availability or crew below a limit), stale data source, overdue maintenance, usage near limit, spares below minimum or resupply late, optimisation timeout or job failure, model drift or model failure, high-severity anomaly, proposal stale, proposal pending longer than a set time.
- **Evaluator:** a Celery Beat job every minute plus event-driven triggers. Deduplication by dedup\_key within the window; hysteresis through a separate clear threshold so alerts do not flap; automatic resolution when the condition clears. All times come from the Clock.
- **Delivery:** role-scoped notifications over SSE.
- **Endpoints:** GET /alerts, PATCH /alerts/{id}/acknowledge, PATCH /alerts/{id}/resolve, GET and PUT /alert-rules (PUT Admin), POST /alert-rules/{id}/test (dry run).
- **UI:** the Overview alert feed reads alerts; Operations gets an Alerts tab with acknowledge and resolve actions; Settings, System Configuration gets an Alert rules editor. Acknowledge, resolve and rule edits are audited.

### 26.8 Constraint registry management (item 9)

Only objective weights were configurable before. Hard-constraint parameters need the same governance.

- **Versioned constraint\_sets** (status draft, active or archived) containing constraint\_definitions with parameter values, units and allowed bounds. Hard constraints can never be switched off; only parameters within schema bounds can change.
- **Workflow:** clone the active set to a draft, edit parameters, run an impact preview, activate. Activation requires Admin confirmation (an optional two-person rule is a configuration setting).
- **Impact preview:** POST /constraints/sets/{id}/impact-preview revalidates the approved plan and all pending proposals under the draft with the validator (no solver run) and reports violations and newly infeasible tasks; an optional dry-run optimisation runs as a job.
- **On activation:** pending proposals become stale (they were built on the previous set); every plan stores its constraint\_set\_version.
- **Endpoints:** GET /constraints/sets, POST /constraints/sets (clone), PUT /constraints/sets/{id}/definitions/{def\_id}, POST /constraints/sets/{id}/impact-preview, POST /constraints/sets/{id}/activate, GET /constraints/definitions.
- **UI:** Settings, System Configuration, Constraints tab beside the objective-weights tab, with the same preview-then-activate pattern. All edits are audited with before and after values.

### 26.9 Benchmark and evidence suite (item 5)

Problem: nothing defined how the project shows that the optimiser actually improves on simpler approaches.

- **Scenario library:** versioned JSON scenarios with fixed seeds and as\_of values: nominal week, single asset outage, maintenance delay, capacity reduction, resupply delay, multiple disruptions, dense week, stale data, and a larger instance for scaling.
- **Strategies compared:** do nothing with right-shift delay propagation, baseline heuristic replanning, CP-SAT replanning in reproducible mode, and CP-SAT with the predicted-downtime buffer switched on and off (ablation).
- **Metrics:** total delay, weighted completion, unscheduled count, churn, utilisation, solver time and status, validator pass rate, and P95 delay under Monte Carlo.
- **Pass criteria:** thresholds are set from the first measured results after Phase 4 and then versioned; they are deliberately not invented in advance. The expected comparison is that CP-SAT is never worse than the heuristic on the objective and never produces a plan the validator rejects.
- **Storage and use:** benchmark\_runs and benchmark\_results with a full manifest. A nightly CI job runs a reduced set and fails on regression beyond tolerance. Results appear in the Scenario comparison report and in a Benchmarks tab on the Scenarios page.
- **Endpoints:** POST /benchmarks/runs (async), GET /benchmarks/runs/{id}, GET /benchmarks/scenarios. Planner, Analyst and Admin can run them.
- **Limit:** all evidence is synthetic and is labelled as such.

### 26.10 Guided demo mode and limitations page (item 10)

- **Demo controller:** POST /demo/reset (Admin; resets runtime data to a chosen seed and as\_of, keeps users, needs a typed confirmation, audited), GET /demo/script (the 10 core steps with completion state), POST /demo/steps/{id}/run (safe automatable steps such as injecting a preset event). Enabled only by the DEMO\_MODE environment flag.
- **Guided tour:** a Demo guide panel in the app shell shows the current step, links to the right page, states the expected result and ticks a step when the API state proves it (for example baseline approved). A quick role switch for the four demo roles exists in demo mode only.
- **Limitations page:** route /about/limitations, linked from the Topbar help menu and the footer. It states the synthetic-data scope, the not-certified status, the scope boundary, the meaning of each data kind and solver status, and known model limitations. Content comes from the versioned file docs/limitations.md and is also reproduced in report footers.
- **Presets:** named demo seeds and as\_of values are stored so every rehearsal starts from the same state.

### 26.11 Optional items (item 12, Could)

- **Alternative proposals:** an optimisation job may request up to three proposals with different emphasis (minimum delay, minimum churn, balanced), grouped by proposal\_group\_id. The Reviewer compares them side by side; approving one withdraws the others.
- **Prediction versus outcome:** a prediction\_outcomes table links stored predictions to realised values from task\_executions and maintenance actuals as the clock advances. It powers a Predicted versus observed (synthetic outcomes) view in Intelligence and feeds performance drift.
- **Reproducibility bundle:** export of a run as a zip with manifest.json (seed, as\_of, dataset hash, generator version, code SHA, solver and model versions, configuration hashes), the dataset, scenario configuration and outputs, plus scripts/reproduce.sh, which re-runs and compares output hashes.

### 26.12 Consolidated model, API and quality changes

**New tables:** system\_clock\_state, task\_executions, asset\_usage\_counters, maintenance\_rules, maintenance\_due, parts\_catalog, spares\_inventory, maintenance\_part\_requirements, spares\_movements, resupply\_orders, alert\_rules, alerts, constraint\_sets, benchmark\_runs, benchmark\_results, prediction\_outcomes (optional). **Changed tables:** plans (kind, status, snapshot\_hash, based\_on\_version, constraint\_set\_version, weight\_set\_version, stale\_reason, refreshed\_from, rollback\_target, proposal\_group\_id, plan\_source), and as\_of on dataset\_versions, plan\_versions, predictions, simulation\_runs and reports.

**Updated enums:** plan status (proposed, stale, approved, rejected, superseded, invalid, withdrawn), plan kind, plan\_source, task status (pending, scheduled, in\_progress, completed, cancelled, blocked), alert status, event types (adds task\_progress and resupply\_delay).

**KPI changes (section 5.3):** tasks completed come from task\_executions; open alerts by severity; spares shortage count; all KPIs accept as\_of.

**Hard constraints (section 8.2):** now ten: the original eight plus usage budget and spares availability, plus locked assignments treated as fixed intervals.

**Permission additions:**

| Capability | Planner | Reviewer | Analyst | Admin |
| --- | --- | --- | --- | --- |
| Start, complete or cancel tasks; record usage; manage resupply orders | Yes | No | No | Yes |
| Request plan rollback or refresh | Yes | Yes | No | Yes |
| Acknowledge or resolve alerts | Yes | Yes | Yes | Yes |
| Edit alert rules, constraint sets, maintenance rules | No | No | No | Yes |
| Set the clock, reset the demo | No | No | No | Yes |
| Run benchmarks | Yes | No | Yes | Yes |

**Tech flow changes (section 17):** step 1 also fixes the clock and as\_of; step 3 includes locked assignments and the constraint set version; step 4 can use task\_progress and resupply\_delay events; step 6 can end in the labelled fallback; step 9 now includes revalidation against current data and sibling staleness; step 10 also covers rollback history; evidence for steps 3 and 6 can be shown from the benchmark suite.

**New tests (section 20):** no direct datetime.now use; same seed and as\_of give the same dataset hash; locked assignments never move; sibling proposals become stale on approval; approval fails with revalidation\_failed when data changed; rollback follows the approval path; fallback plans are labelled and validated; concurrent optimisation requests respect locks and idempotent dedupe; stuck jobs are reaped; alerts deduplicate and do not flap; impact preview matches post-activation validation; spares and usage constraints agree between solver and validator; benchmark regression gate; demo reset is deterministic; reproducibility bundle verifies.

**Traceability additions (section 23):** FR-04 and FR-05 extended by 26.6 and 26.8; FR-06 by 26.3 and 26.4; FR-12 by 26.4; FR-02 by 26.7 and 26.2; FR-09 and the test section by 26.9; non-functional reliability by 26.5; usability and the completion criterion by 26.10.
