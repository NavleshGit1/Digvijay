# AirOps Nexus — Phased Implementation Plan

Companion to the AirOps Nexus System Architecture, Tech Flow and Technology Stack document. Section references such as 5.3, 7 and 8.4 point to that architecture document. Synthetic data only · Plan v1.0

## 1. Planning assumptions

- **Team (assumption, adjust to reality):** five people, one per workstream. A = Platform and data, B = Optimisation and replanning, C = ML and simulation, D = Frontend, E = Security, QA and DevOps. The calendar below is 24 weeks of two-week sprints. With a smaller team keep the phase order and exit gates and stretch the calendar; use the descoping ladder in section 7 to protect the core demo.
- **Prototype dimensions (proposed defaults, configurable, to be confirmed by benchmarking in Phase 4):** about 40 fictional assets, 120 personnel, 300 tasks, a 7-day planning horizon, 15-minute slots, 6 fictional zones. These are not from the problem statement; they exist so that the solver and UI can be sized and tested.
- **Working rules:** contracts first; every phase ends with a demo against a phase exit gate; nothing is marked done without tests, audit coverage where it applies, and the loading, empty, error and stale states for any new view; no hard-coded KPI values; every merged change passes CI.
- **Definition of Done (every task):** code reviewed; unit and integration tests pass; OpenAPI and generated types in sync; permissions enforced server-side and tested; audit entry for protected actions; documentation updated; demo data labelled synthetic.

## 2. Phase overview

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
| 11 | Hardening and release | 20-24 | Tests, security, performance, demo | Release checklist (requirements file section 14) fully ticked |

**Milestones:** M0 contracts frozen (end week 2); M1 vertical slice, full core outcome without ML (end week 14); M2 intelligence complete (end week 20); M3 release candidate (end week 22); M4 demo-ready and documented (end week 24).

## 3. Critical path and parallelism

Critical path: Phase 0 contracts, Phase 2 schema and generator, Phase 4 scheduler, Phase 5 plan versions and approval, Phase 6 replanning, which delivers M1. Parallel tracks: the frontend shell and design system run alongside Phases 1 and 2 using the generated API client and mocks (tests only); ML data work starts as soon as the generator exists (week 6) using stubbed prediction endpoints until models are promoted; the twin starts once plans and events exist (week 14); reports and settings can start as soon as their source data exists.

## 4. Detailed phase plans

### Phase 0 - Foundations and contracts (weeks 1-2)

| ID | Task | Stream | Output |
| --- | --- | --- | --- |
| P0-1 | Confirm scope, MVP versus stretch list, roles, display time zone, prototype dimensions | All | Signed-off scope note |
| P0-2 | Data dictionary v1, ERD, shared enum registry, KPI definitions from architecture section 5.3 | A | docs/data-dictionary.md |
| P0-3 | OpenAPI skeleton for all endpoints in architecture section 7 (stubs), problem+json error model, pagination and filter conventions | A | Frozen OpenAPI v0.1, generated TypeScript types |
| P0-4 | Permission matrix finalised, demo account policy (credentials from environment) | E | Permission table and seed policy |
| P0-5 | Constraint catalogue: the synthetic abstract hard constraints with parameters | B | constraint\_definitions spec |
| P0-6 | Synthetic data generation spec: entities, distributions, injected anomalies, label rules for ML targets, seeds | A, C | Generator spec |
| P0-7 | Architecture decision records: modular monolith, Celery over Kafka, pgvector, CP-SAT reproducible mode, prediction-to-optimiser rule | All | docs/adr/ |
| P0-8 | Design tokens, page-state matrix, wireframe review against the reference image | D | Token file, wireframes |
| P0-9 | Repository, branching, review and CI conventions | E | CONTRIBUTING and templates |

**Exit gate:** contracts reviewed by all streams; a change-request process is agreed so contract edits are visible and versioned.

**Main risk:** contracts drift later. Mitigation: type generation in CI fails when frontend and backend disagree.

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

**Exit gate:** four demo roles log in; every sidebar link opens a page; a dummy job reports queued, running and completed over SSE; its audit record exists and cannot be altered; CI is green.

**Main risk:** over-building infrastructure. Mitigation: only what later phases use; the observability stack waits for Phase 11.

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

**Exit gate:** the same seed and generator version produce the same dataset hash; injected invalid records are flagged; re-ingesting is a no-op; conflicting values appear as review items.

**Main risk:** unrealistic synthetic data. Mitigation: documented rules with variation, and a disclosure in the data dictionary and UI.

### Phase 3 - Resources and overview (weeks 5-8)

| ID | Task | Stream | Output |
| --- | --- | --- | --- |
| P3-1 | Asset, personnel, task, inventory, zone and maintenance endpoints with server-side validation, role checks, audit | A | Resource APIs |
| P3-2 | Maintenance rule: reject incompatible assignments inside maintenance windows | A | Validation rule |
| P3-3 | GET /overview with all KPIs per architecture section 5.3, GET /search, events list | A | Overview API |
| P3-4 | Reusable table (search, filter, sort, pagination, empty and error states) | D | Table component |
| P3-5 | Overview page: KPI cards, MapLibre map of fictional zones, alert feed, objectives and task status, data-source health, KPI click-through | D | Overview page |
| P3-6 | Assets page with detail drawer; Personnel page with qualifications, availability, eligibility; Maintenance page with tabs and detail panel (predicted column shown as not available yet) | D | Resource pages |
| P3-7 | Operations page v1: event table and timeline with filters | D | Event centre v1 |
| P3-8 | Tests: KPI values equal database, table behaviour, permission checks on edits | E | Passing suite |

**Exit gate:** every Overview number matches a direct database query; edits require permission and appear in the audit log; synthetic labels are visible.

**Main risk:** KPI definitions disagree between pages. Mitigation: one server-side KPI service.

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

**Exit gate:** baseline and optimised plans pass the validator; every status type is reproducible in a test (optimal, feasible, infeasible, timeout); the Schedule page shows solver status and runtime honestly.

**Main risk:** solver runtime at realistic size. Mitigation: early benchmarks in P4-9 (start in week 8), slot-size tuning, time limits with honest feasible status, decomposition by horizon or zone only if needed.

### Phase 5 - Governance (weeks 10-12)

| ID | Task | Stream | Output |
| --- | --- | --- | --- |
| P5-1 | Plan state machine, based\_on\_version, plan\_diffs service | A, B | Plan lifecycle |
| P5-2 | Approve and reject endpoints: Reviewer permission, reason, If-Match, Idempotency-Key, one-transaction supersede, approval\_records | A, E | Approval API |
| P5-3 | Audit log endpoint with filters and CSV export | A | Audit API |
| P5-4 | Proposal review page (route /schedule/proposals/:planId) with diff view, validation result, approve and reject dialog; Proposals tab in Schedule | D | Approval UI |
| P5-5 | Audit history view and filters | D | Audit UI |
| P5-6 | Tests: stale proposal returns 409, non-Reviewer blocked on direct API calls, optimiser cannot modify the approved plan, double submit is idempotent | E | Passing suite |

**Exit gate:** a baseline is approved and becomes the current plan; a second proposal is approved and supersedes it; a stale proposal and an unauthorised call are both refused; every step is in the audit log.

### Phase 6 - Events and replanning (weeks 11-14)

| ID | Task | Stream | Output |
| --- | --- | --- | --- |
| P6-1 | Event service: POST /events, idempotency key, validation status, audit | A | Event ingestion |
| P6-2 | POST /maintenance/{id}/simulate-delay and PATCH maintenance; event types: asset unavailability, maintenance delay, capacity reduction, stale data, abstract environmental restriction | A | Disruption inputs |
| P6-3 | Impact detector (NetworkX graph over assets, personnel, inventory, assignments, dependencies) and GET /maintenance/{id}/impact | B | Impact assessment |
| P6-4 | Feasibility re-check of the approved plan with the validator; degradation threshold; replan recommendation | B | Trigger logic |
| P6-5 | Replan mode in the optimiser: frozen window, churn term, warm start from the approved plan; replan\_triggers with reason | B | Replanning |
| P6-6 | Controlled workflow: auto-create a proposal job only (debounced, rate-limited), never approve; notifications to Reviewers | A, B | Event workflow |
| P6-7 | Plan diff and GET /plans/{id}/diff, objective-difference summary, unresolved tasks | B | Diff API |
| P6-8 | UI: Maintenance impact panel and Replan action; Operations page complete (inspect, mark reviewed, open impacted records, see resulting plan change); baseline-versus-proposal comparison in Schedule; clickable alerts on Overview | D | Disruption UI |
| P6-9 | Tests: duplicate events create no second effect; unaffected commitments preserved inside the frozen window; each disruption type produces an impact list | E | Passing suite |

**Exit gate (milestone M1):** a Planner loads a seeded dataset, generates and gets an approved baseline, injects a maintenance delay, sees affected tasks, runs replanning and compares the diff, and a Reviewer approves; the audit trail retrieves the whole decision. ML is not required yet; predictions show as not available.

**Main risk:** replans shuffle too many assignments. Mitigation: tune the churn weight and frozen-window length with benchmarks, and show churn as a metric.

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
| P7-8 | Integration: predicted downtime as soft buffer in the optimiser (architecture section 8.4); re-prediction step inside replanning | B, C | Predictions in planning |
| P7-9 | Optional, behind a flag: resource-demand forecast versus seasonal naive and ETS | C | Optional model |
| P7-10 | Frontend: Intelligence tabs (Maintenance Risk, Task Delay, Resource Demand, Model Performance), predicted-versus-observed chart only with valid test data, risk table, feature-contribution chart, metadata panel, prediction columns on Maintenance, synthetic-data disclaimer | D | Intelligence UI v1 |
| P7-11 | Tests: held-out evaluation exists for each model, training reproducible from configuration, leakage checks, model version on every prediction, missing and out-of-range input handling | E | Passing suite |

**Exit gate:** each promoted model beats its baseline on held-out synthetic data, with metrics reproducible from configuration; every prediction shows version, timestamp and interval; drift and failure status are visible; no UI text claims real-world accuracy.

**Main risk:** synthetic data yields overly good metrics. Mitigation: noise, covariate shift and per-category error analysis in the evaluation, and a standing limitation note.

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

**Exit gate:** a scenario run with a fixed seed gives identical results twice; baseline and revised plans are compared on the same trials with confidence intervals; cancelling a run works; results are labelled simulated everywhere.

**Main risk:** run time grows with run count. Mitigation: chunked fan-out, a default run count chosen from benchmarks, results streamed as chunks finish.

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

**Exit gate (milestone M2):** explanations come only from solver and model outputs; anomalies are reviewable and evaluated; the assistant answers the five example prompts with citations, refuses unsupported ones, and cannot approve or alter anything.

**Main risk:** the assistant states unsupported facts. Mitigation: citation verification against records returned in the same turn, and the insufficient-evidence fallback.

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
| P11-9 | Walk through the release checklist (requirements file section 14), bug bash, freeze | All | Release candidate |

**Exit gate (milestone M4):** every item in the release checklist is ticked with evidence; the demo runs from a clean checkout with one script and gives the same results on repeat.

## 5. Requirement-to-phase map

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

## 6. Risk register

| Risk | Impact | Mitigation | Owner |
| --- | --- | --- | --- |
| Solver too slow at target size | Schedule page unusable | Early benchmark (week 8), slot-size tuning, time limits with honest feasible status, decomposition only if needed | B |
| Contract drift between frontend and backend | Rework | Generated types and type-sync CI check | A, D |
| Synthetic data unrealistic or leaky | Misleading model results | Documented generator rules, leakage tests, held-out test, explicit limitation text | C |
| Scope too large for the timeline | Core demo at risk | Must, should and could tagging and the descoping ladder | All |
| Non-reproducible solver or simulation | Failed determinism tests | Single-worker seeded mode as default, seeded generators, manifests | B, C |
| Assistant produces unsupported claims | Trust loss | Tool-only facts, citation verification, insufficient-evidence fallback | A, E |
| Permissions only enforced in UI | Security failure | Server-side dependency on every route, bypass tests in CI | E |
| Replans too disruptive | Poor proposals | Frozen window, churn objective, churn metric shown | B |
| Late integration surprises | Slipped milestones | Vertical slice by week 14, integration demo at every phase gate | All |

## 7. Descoping ladder (cut in this order if time runs short)

1. PDF export polish (keep CSV) and report styling.
2. Resource-demand forecasting model and the autoencoder.
3. Drag-and-drop schedule editing (not planned by default).
4. Parallel simulation tuning and extra scenario presets beyond the four disruption types.
5. Self-hosted LLM option and a RAG corpus beyond the core documents.
6. Observability dashboards beyond latency and job metrics.
7. Never cut: constraint validator, honest solver statuses, approval and audit, human oversight, synthetic labelling, server-side permissions, reproducibility of the core demo.

## 8. First two weeks, concrete

- **Week 1:** run the scope and dimension workshop (P0-1); start the data dictionary and KPI sheet (P0-2); draft the OpenAPI skeleton (P0-3); scaffold the repository and CI (P1-1, P1-2); settle design tokens (P0-8).
- **Week 2:** freeze contracts v0.1 (M0); write the constraint catalogue and generator spec (P0-5, P0-6); record ADRs (P0-7); bring up Docker Compose with postgres, redis and minio (P1-3); start auth, RBAC and the audit writer (P1-5, P1-6); begin the frontend shell (P1-9).

## 9. Plan amendments v1.1: additional critical components

This section adds the work for the components described in architecture section 26 (clock, task execution, plan lifecycle v2, rollback, benchmarks, usage and spares, alerts, fallback chain, constraint registry management, guided demo, job concurrency, and the optional items). Where it conflicts with sections 1 to 8, this section governs. The architecture document is the source for what each component is; this section says when and by whom it is built.

Item numbers used below: 1 clock, 2 task execution, 3 stale proposals and revalidation, 4 rollback, 5 benchmarks, 6 usage and spares, 7 alerts, 8 fallback chain, 9 constraint registry, 10 demo mode and limitations, 11 job concurrency, 12 optional items.

### 9.1 Revised calendar

The added scope extends the plan from 24 to 26 weeks (same five-person assumption). Phases keep their order; later phases shift.

| Phase | Name | Weeks (v1.1) | Was | Main additions |
| --- | --- | --- | --- | --- |
| 0 | Foundations and contracts | 1-2 | 1-2 | Specs and contracts for items 1 to 11 |
| 1 | Platform skeleton | 2-4 | 2-4 | Clock service, concurrency primitives |
| 2 | Data foundation | 3-7 | 3-6 | Execution, usage and spares schema; generator v1.1; demo reset |
| 3 | Resources and overview | 6-9 | 5-8 | Task execution APIs and UI; usage and spares views; limitations page |
| 4 | Scheduling | 8-13 | 7-11 | New constraints, fallback chain, locks, constraint versions, benchmark v1 |
| 5 | Governance | 11-14 | 10-12 | Plan lifecycle v2, revalidation, rollback, impact preview |
| 6 | Events and replanning | 12-16 | 11-14 | Rolling horizon, alerts, new event types |
| 7 | ML platform | 13-19 | 12-17 | Execution-based labels, usage features, ablation |
| 8 | Digital twin | 15-20 | 14-18 | Simulated clock, robustness benchmark |
| 9 | Intelligence layer | 17-22 | 16-20 | Alert rules for anomalies and drift |
| 10 | Reports and administration | 18-23 | 17-21 | Guided demo, constraint and alert editors, benchmarks tab |
| 11 | Hardening and release | 22-26 | 20-24 | Nightly benchmark gate, extended end-to-end suite |

**Updated milestones:** M0 contracts frozen (end week 2); M1 vertical slice with the full core outcome including rollback and revalidation, without ML (end week 16); M2 intelligence complete (end week 22); M3 release candidate (end week 24); M4 demo-ready and documented (end week 26).

**Critical path update:** contracts, then the clock and schema and generator (the clock must exist before the generator), then the scheduler with its fallback chain, then plan lifecycle v2, then replanning with execution locking, giving M1. Task execution tracking must land before replanning because locked assignments depend on it.

### 9.2 Added tasks by phase

Columns: ID, task, stream (A Platform and data, B Optimisation and replanning, C ML and simulation, D Frontend, E Security, QA and DevOps), output, item number.

### Phase 0 additions

| ID | Task | Stream | Output | Item |
| --- | --- | --- | --- | --- |
| P0-10 | ADR for the clock: modes, injection rule, as\_of stored on outputs, lint rule specification | A, E | ADR | 1 |
| P0-11 | Specify task lifecycle, usage counters, maintenance rules, spares and resupply model; extend generator spec | A, B, C | Specs | 2, 6 |
| P0-12 | Specify plan lifecycle v2 (states, staleness rules, revalidation, rollback, fallback chain, locks); add all new endpoints and enums to OpenAPI v0.1 | A, B | Updated contracts | 3, 4, 8, 9, 11 |
| P0-13 | Alert rule catalogue and thresholds, benchmark metrics and scenario list, demo script outline, limitations text | A, D, E | Docs | 5, 7, 10 |

### Phase 1 additions

| ID | Task | Stream | Output | Item |
| --- | --- | --- | --- | --- |
| P1-10 | Clock service: Protocol, three implementations, system\_clock\_state with Redis cache, GET and PUT /system/clock, lint rule banning direct datetime.now, tests | A, E | Clock | 1 |
| P1-11 | Topbar Demo time badge | D | Shell badge | 1 |
| P1-12 | Concurrency primitives: scope locks, heartbeats and reaper, idempotent dedupe keys, per-user limits, queue position | A | Job safety | 11 |

### Phase 2 additions

| ID | Task | Stream | Output | Item |
| --- | --- | --- | --- | --- |
| P2-9 | Schema: task\_executions, asset\_usage\_counters, maintenance\_rules, maintenance\_due, parts\_catalog, spares\_inventory, maintenance\_part\_requirements, spares\_movements, resupply\_orders, as\_of columns | A | Schema v1.1 | 1, 2, 6 |
| P2-10 | Generator v1.1: times relative to as\_of, historical executions, usage accrual, part consumption, resupply lead times; dataset hash covers as\_of | A | Dataset v1.1 | 1, 2, 6 |
| P2-11 | Demo presets and POST /demo/reset (Admin, typed confirmation, deterministic, audited) | A | Reset | 10 |
| P2-12 | Tests: same seed and as\_of give the same hash; reset is deterministic; no direct clock access anywhere | E | Passing suite | 1, 10 |

### Phase 3 additions

| ID | Task | Stream | Output | Item |
| --- | --- | --- | --- | --- |
| P3-9 | Task execution service and endpoints (start, complete, cancel), validation, audit, locked-assignment flag | A | Execution API | 2 |
| P3-10 | KPI service reads task\_executions, accepts as\_of, adds spares-shortage input | A | KPI update | 2, 6 |
| P3-11 | Usage, spares, parts, resupply orders and due-list endpoints | A | Logistics API | 6 |
| P3-12 | UI: task status chips and actions, asset usage counters, spares and resupply views, Due soon tab on Maintenance | D | Logistics UI | 2, 6 |
| P3-13 | Help menu and /about/limitations page from docs/limitations.md | D | Limitations page | 10 |
| P3-14 | Tests: KPIs equal database with as\_of; execution transitions; permission checks | E | Passing suite | 2, 6 |

### Phase 4 additions

| ID | Task | Stream | Output | Item |
| --- | --- | --- | --- | --- |
| P4-10 | Maintenance planner service: rules evaluated against counters give due items; usage accrues from completed executions | B | Due generation | 6 |
| P4-11 | Two new hard constraints (usage budget in horizon form, spares reservoir) with validator counterparts; locked assignments as fixed intervals | B | Constraints 9 and 10 | 2, 6 |
| P4-12 | Versioned constraint\_sets; active set; every plan stores constraint\_set\_version | A, B | Constraint versions | 9 |
| P4-13 | Fallback chain with solver\_status and plan\_source, banner data, tests of all three tiers | B | Labelled fallback | 8 |
| P4-14 | Optimisation concurrency: scope lock, dedupe by snapshot hash, configuration hash and seed, queue position, priorities | A, B | Safe concurrency | 11 |
| P4-15 | Benchmark module v1: scenarios (nominal, outage, maintenance delay, capacity reduction), strategies (right-shift, heuristic, CP-SAT), metrics, benchmark\_runs; set pass thresholds from first measurements and record them in an ADR | B, C | Evidence v1 | 5 |
| P4-16 | Tests: solver and validator agree on the new constraints; fallback labelling; lock behaviour | E | Passing suite | 6, 8, 11 |

### Phase 5 additions

| ID | Task | Stream | Output | Item |
| --- | --- | --- | --- | --- |
| P5-7 | Plan lifecycle v2: statuses, kinds, snapshot\_hash, sibling staleness on approval | A, B | Lifecycle | 3 |
| P5-8 | Approval-time revalidation against the current snapshot inside the transaction; 409 revalidation\_failed | A, B | Safe approval | 3 |
| P5-9 | Staleness checker and GET /plans/{id}/staleness (hard and soft cases) | B | Staleness | 3 |
| P5-10 | Refresh (warm-started re-solve) and withdraw endpoints | A, B | Refresh | 3 |
| P5-11 | Rollback proposal endpoint and flow, diagnostics, re-optimise-from-target option | A, B | Rollback | 4 |
| P5-12 | Constraint set impact preview and activation (marks proposals stale) | B | Registry governance | 9 |
| P5-13 | UI: stale badge and reason, refresh, rollback and history, revalidation result in the approve dialog | D | Lifecycle UI | 3, 4 |
| P5-14 | Optional: alternative proposals (up to three, grouped) with side-by-side compare | B, D | Alternatives | 12 |
| P5-15 | Tests: sibling staleness, revalidation failure, rollback through approval, impact preview equals post-activation validation, no silent replacement | E | Passing suite | 3, 4, 9 |

### Phase 6 additions

| ID | Task | Stream | Output | Item |
| --- | --- | --- | --- | --- |
| P6-10 | Rolling horizon job producing proposals; locked assignments respected in replanning | B | Roll-forward | 2 |
| P6-11 | Alert subsystem: tables, evaluator (Beat and event-driven), deduplication, hysteresis, auto-resolve, SSE notifications, endpoints | A | Alerting | 7 |
| P6-12 | Seed the alert rule catalogue; Overview feed reads alerts; Operations Alerts tab with acknowledge and resolve | D | Alert UI | 7 |
| P6-13 | task\_progress and resupply\_delay event types; impact detection covers spares and usage | A, B | New events | 2, 6 |
| P6-14 | Benchmark scenarios extended (resupply delay, multiple disruptions) and a no-replan strategy comparison | B, C | Evidence v2 | 5 |
| P6-15 | Tests: alerts deduplicate and do not flap; rolling horizon creates a proposal, never an approval; locked assignments never move | E | Passing suite | 2, 7 |

### Phase 7 additions

| ID | Task | Stream | Output | Item |
| --- | --- | --- | --- | --- |
| P7-12 | Delay labels from observed executions; usage counters as features with as-of leakage tests | C | Better labels | 2, 6 |
| P7-13 | Training concurrency: one run per model | C | Training lock | 11 |
| P7-14 | Ablation benchmark: predicted-downtime buffer on versus off | B, C | Ablation | 5 |
| P7-15 | Optional: prediction\_outcomes and the Predicted versus observed view | C, D | Outcome view | 12 |

### Phase 8 additions

| ID | Task | Stream | Output | Item |
| --- | --- | --- | --- | --- |
| P8-9 | Twin runs on a SimulatedClock; simulation concurrency limits | C | Clock-safe twin | 1, 11 |
| P8-10 | Robustness benchmark: Monte Carlo P95 delay across strategies | C | Evidence v3 | 5 |
| P8-11 | Optional: reproducibility bundle export and scripts/reproduce.sh | C, E | Bundle | 12 |

### Phase 9 additions

| ID | Task | Stream | Output | Item |
| --- | --- | --- | --- | --- |
| P9-9 | Alert rules for high-severity anomalies and model drift or failure | A | Alert rules | 7 |

### Phase 10 additions

| ID | Task | Stream | Output | Item |
| --- | --- | --- | --- | --- |
| P10-8 | Guided demo: demo controller (script and step run), Demo guide panel with proof-of-completion ticks, role quick-switch, DEMO\_MODE flag | A, D | Demo mode | 10 |
| P10-9 | Settings UI: alert rules editor, Constraints tab, maintenance rules editor, clock control | D | Admin UI | 1, 6, 7, 9 |
| P10-10 | Benchmarks tab on Scenarios; benchmark results in the Scenario comparison report | A, D | Evidence in UI | 5 |
| P10-11 | Tests: demo reset and guide; Admin-only enforcement on all new settings | E | Passing suite | 10 |

### Phase 11 additions

| ID | Task | Stream | Output | Item |
| --- | --- | --- | --- | --- |
| P11-10 | Nightly benchmark regression job in CI with tolerance | E | Regression gate | 5 |
| P11-11 | Extend end-to-end suite: stale proposal, revalidation failure, rollback, fallback banner, alert acknowledge, demo reset | E | E2E coverage | 3, 4, 7, 8, 10 |
| P11-12 | Rehearse the demo including clock control and rollback; finish clock policy, limitations and benchmark report documents | All | Demo kit | 1, 5, 10 |
| P11-13 | Performance tests include lock contention and reaper behaviour | E | Concurrency evidence | 11 |

### 9.3 Exit gate additions

- **Phase 1:** the clock can be fixed and advanced, every worker agrees on it, and a lint check fails on direct datetime.now use.
- **Phase 2:** the same seed and as\_of give the same dataset hash; reset to a preset gives an identical state.
- **Phase 3:** a task can be started and completed with audit, and the completed-tasks KPI follows task\_executions.
- **Phase 4:** the new constraints agree between solver and validator; each fallback tier is demonstrated and labelled; two simultaneous optimisation requests behave per the lock rules; first benchmark numbers exist and thresholds are recorded.
- **Phase 5:** approving one proposal marks siblings stale; approval fails with revalidation\_failed after relevant data changes; a rollback goes through approval; an impact preview matches the validation after activation.
- **Phase 6 (M1):** the full core outcome runs including a rolling-horizon step, locked assignments and the alert feed with acknowledge and resolve.
- **Phase 7:** delay labels come from executions; the ablation shows whether the downtime buffer helps, with the result reported either way.
- **Phase 10:** the guided demo walks the 10 steps with automatic completion ticks; Admin edits of constraints, alert rules and the clock are audited.
- **Phase 11:** the nightly benchmark gate is green and the extended end-to-end suite passes.

### 9.4 Additional risks

| Risk | Impact | Mitigation | Owner |
| --- | --- | --- | --- |
| Code bypasses the clock | Non-reproducible results | Lint rule, injection by default, determinism tests | A, E |
| Staleness triggers too often | Reviewers lose proposals needlessly | Hard versus soft staleness, tune from usage in Phases 5 and 6 | B |
| Spares reservoir constraint is complex | Solver slowdown | Start with the simple balance form; benchmark early; fall back to pre-filtering tasks by spare availability, with the validator still checking | B |
| Benchmark thresholds invented | Weak evidence | Set only from measured results and record them in an ADR | B, C |
| Alerts flap or flood | Alert fatigue | Hysteresis, deduplication windows, rule dry-run before enabling | A |
| Demo reset used by mistake | Lost demo state | Typed confirmation, Admin only, DEMO\_MODE only, audit entry | A, E |
| Two extra weeks slip further | M4 late | Descoping ladder below, phase gates, early benchmarks | All |

### 9.5 Updated descoping ladder

Cut in this order if time runs short:

1. Optional items: reproducibility bundle, prediction-versus-outcome view, alternative proposals.
2. Everything on the original ladder (PDF polish, demand forecast and autoencoder, extra presets, self-hosted LLM, extra dashboards).
3. Spares reservoir inside the solver: fall back to pre-filtering with validator-only checking.
4. Usage budget beyond the horizon form.
5. Guided tour polish (keep the reset and the limitations page).
6. Never cut: clock and as\_of, task execution tracking, approval-time revalidation, sibling staleness, rollback through approval, labelled fallback, honest solver statuses, the independent validator, audit, server-side permissions, synthetic labelling.

### 9.6 Requirement-to-phase additions

| Item | Built in | Verified in |
| --- | --- | --- |
| 1 Clock and as\_of | 0, 1, 2, 8 | 1, 2 |
| 2 Task execution and rolling horizon | 2, 3, 6, 7 | 3, 6 |
| 3 Stale proposals and revalidation | 5 | 5, 11 |
| 4 Plan rollback | 5 | 5, 11 |
| 5 Benchmark and evidence suite | 4, 6, 7, 8, 10, 11 | 4, 11 |
| 6 Usage and spares logistics | 2, 3, 4, 6, 7 | 4, 6 |
| 7 Alerts | 6, 9, 10 | 6, 11 |
| 8 Fallback chain | 4 | 4, 11 |
| 9 Constraint registry management | 4, 5, 10 | 5, 10 |
| 10 Demo mode and limitations | 2, 3, 10, 11 | 10, 11 |
| 11 Job concurrency | 1, 4, 7, 8 | 4, 11 |
| 12 Optional items | 5, 7, 8 | 11 |

### 9.7 Updated working rules and first two weeks

- **Definition of Done additions:** all time access goes through the Clock; any change that creates, approves, refreshes or rolls back a plan follows plan lifecycle v2; new settings are Admin-only, validated and audited.
- **Week 1 additions:** decide the clock modes and the as\_of convention (P0-10); agree the task lifecycle and the abstract usage and spares model (P0-11); draft the alert rule catalogue (P0-13).
- **Week 2 additions:** contracts v0.1 must already contain the new endpoints, enums and plan fields (P0-12); begin the clock service alongside auth and the audit writer (P1-10).
