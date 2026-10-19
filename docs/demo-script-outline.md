# AirOps Nexus — Guided Demonstration Script (The 10 Core Steps)

**Status:** Approved Specification (Phase 0, Task P0-13 & Amendment v1.1)  
**Version:** 1.0  
**References:** Architecture Section 17 & 26.10

---

## 1. Demo Mode Overview (`DEMO_MODE=true`)
When `DEMO_MODE=true` is enabled in the environment:
- The UI AppShell renders a persistent **Demo Guide Panel** tracking progress across the 10 steps.
- A quick role-switcher allows toggling between `Planner`, `Reviewer`, `Analyst`, and `Administrator`.
- The Topbar displays the **Demo Time Badge** reflecting the virtual system clock.
- An Administrator can trigger `POST /demo/reset` to reset the entire database to a deterministic preset seed and `as_of` baseline.

---

## 2. Step-by-Step Flow & Proof-of-Completion Criteria

| Step | User Action & Page | Underlying API Calls | Verification & Proof-of-Completion Tick |
| :-: | :--- | :--- | :--- |
| **1** | **Reset & Seed State**<br>Settings $\to$ Data Sources | `POST /demo/reset`<br>`POST /admin/seed` | `dataset_versions` record exists; virtual clock is pinned; synthetic data banner visible. |
| **2** | **Inspect Current State**<br>Overview, Assets, Personnel | `GET /overview`<br>`GET /assets` | Overview KPI cards populate with live computed numbers matching the database. |
| **3** | **Generate Baseline Plan**<br>Schedule $\to$ Run Baseline | `POST /optimisation/jobs`<br>(mode: `baseline`) | CP-SAT/Heuristic runs; validator passes; plan created as `baseline`; Reviewer approves to make it current. |
| **4** | **Inject Disruption Event**<br>Maintenance $\to$ Simulate Delay | `POST /maintenance/{id}/simulate-delay` | Maintenance work order extended; event logged in `events`; active alert generated. |
| **5** | **Assess Blast Radius**<br>Maintenance $\to$ Impact Panel | `GET /maintenance/{id}/impact` | NetworkX graph identifies directly conflicted tasks and downstream successor delays. |
| **6** | **Run Replanning**<br>Schedule $\to$ Replan | `POST /predictions/maintenance`<br>`POST /optimisation/jobs` (mode: `replan`) | Locked tasks preserved; CP-SAT generates proposal with based_on_version pointing to baseline. |
| **7** | **Digital Twin Comparison**<br>Scenarios $\to$ Digital Twin | `POST /scenarios/{id}/runs` | 50 paired Monte Carlo runs evaluate baseline vs. replanned proposal; intervals displayed. |
| **8** | **Examine Explanations**<br>Schedule $\to$ Explanation Panel | `GET /plans/{id}/explanation` | SHAP feature contribution charts and solver binding constraints rendered with evidence tags. |
| **9** | **Review & Approve Plan**<br>Proposal Review (`ROLE_REVIEWER`) | `POST /plans/{id}/approve` | Approval-time revalidation passes; old plan superseded; sibling proposals marked stale; audit logged. |
| **10**| **Audit & Decision Retrieval**<br>Reports & Audit History | `GET /audit-logs`<br>`POST /reports` | Complete decision history retrieved; cryptographic hash chain verified; PDF/CSV exported. |
