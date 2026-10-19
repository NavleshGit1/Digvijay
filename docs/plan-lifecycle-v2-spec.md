# AirOps Nexus — Plan Lifecycle v2: Governance, Staleness, and Rollback

**Status:** Approved Specification (Phase 0, Task P0-12 & Amendment v1.1)  
**Version:** 2.0  
**References:** Architecture Section 26.4 & 26.5

---

## 1. Plan State Machine (v2)

```
                     ┌───────────────┐
                     │    PROPOSED   │◄──────────────┐
                     └──┬───┬───┬─┬──┘               │
       Reject Reason    │   │   │ │ Validator Error  │ Refresh (Re-solve)
    ┌───────────────────┘   │   │ └─────────┐        │
┌───▼──────┐                │   │      ┌────▼────┐   │
│ REJECTED │   Sibling/Data │   │      │ INVALID │   │
└──────────┘   Changes      │   │      └─────────┘   │
             ┌──────────────┘   │                    │
        ┌────▼──┐   Withdrawal  │                    │
        │ STALE ├───────────────┼────────────────────┘
        └───┬───┘          ┌────▼──────┐
            │              │ WITHDRAWN │
            │              └───────────┘
            │ Approve + Revalidation Passes
       ┌────▼─────┐
       │ APPROVED │
       └────┬─────┘
            │ Newer Plan Approved
       ┌────▼───────┐
       │ SUPERSEDED │
       └────────────┘
```

---

## 2. Core Governance Invariants

### 2.1 Snapshot Fingerprinting (`snapshot_hash`)
Every proposed plan calculates and stores a SHA-256 fingerprint computed across:
- Active `dataset_version` hash.
- Max `updated_at` timestamp of all assigned assets, crew, and tasks.
- Active `constraint_set_version`.
- Active `objective_weight_set_version`.

### 2.2 Sibling Staleness
When a Reviewer approves Proposal $P_A$ (built on Base Plan $V_0$), any other existing proposals built on $V_0$ ($P_B, P_C$) are marked `stale` with `stale_reason = "Sibling proposal approved"` within the exact same database transaction.

### 2.3 Approval-Time Revalidation
Before committing an approval, `POST /plans/{id}/approve` invokes the pure-Python validator on the plan against the **current** operational state in the database:
- If unassigned resource downtime, maintenance delays, or constraint changes occurred while the proposal was awaiting review, revalidation fails.
- The transaction aborts with HTTP 409 `revalidation_failed`, returns detailed conflict diagnostics, and automatically transitions the proposal to `stale`.
- Under no circumstances is a broken plan approved.

### 2.4 Plan Rollback Workflow
1. A Planner or Reviewer initiates `POST /plans/{target_id}/rollback-proposal` with a mandatory reason.
2. The engine creates a new plan version of kind `rollback` referencing `rollback_target = target_id`.
3. The proposed rollback is revalidated against current operational reality.
4. If valid, the proposal enters the Reviewer approval queue. Once approved by a Reviewer, it supersedes the active plan and writes a full audit log entry.

### 2.5 Refresh Endpoint
Planners can call `POST /plans/{id}/refresh` on any stale proposal to trigger a warm-started re-solve against the current live snapshot, linking `refreshed_from = id`.

---

## 3. Concurrency & Fallback Rules

1. **Redis Scope Locking:** Only one CP-SAT solver job may run per operational scope (`opt:{scope}`) at any given time. Concurrent requests are queued with visible positions or returned with HTTP 409 `job_in_progress`.
2. **Idempotent Job Requests:** Repetitive requests matching the same `(snapshot_hash, config_hash, seed)` return the existing job result immediately.
3. **Solver Fallback Chain:**
   - **Tier 1:** CP-SAT within time limit $\to$ `status = optimal` or `feasible`.
   - **Tier 2:** If timeout or solver error occurs, run baseline earliest-due-date heuristic $\to$ `kind = fallback`, `plan_source = heuristic_fallback`, preserving honest `status = timeout`.
   - **Tier 3:** If heuristic fails validator, return no plan and provide full conflict diagnostics and relaxation advice.
