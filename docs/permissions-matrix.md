# AirOps Nexus — Role-Based Access Control (RBAC) & Security Policy

**Status:** Approved Specification (Phase 0, Task P0-4)  
**Version:** 1.0 (Phase 0 Baseline)  
**Enforcement:** Server-Side FastAPI Dependencies (`require_permission`)

---

## 1. Principles of Authorization
1. **Server-Side Authorization by Default:** The frontend UI may hide or disable action buttons for convenience, but every API route validates caller permissions at the controller layer. Any attempt to invoke an unauthorized endpoint returns an HTTP 403 `forbidden` status and triggers an audit log alert.
2. **Object-Level Permissions:** Modifications to work orders, plans, and config objects enforce row-level tenant/version validation.
3. **Least Privilege Database Roles:**
   - `api_app`: Read/write access to business entities, insert-only on `audit_logs`.
   - `digital_twin_sim`: Read-only access to domain tables; write access limited to `simulation_run_trials`.
   - `audit_writer`: Insert-only on `audit_logs`; no `UPDATE` or `DELETE` grants.

---

## 2. Comprehensive Capability Matrix

| Operational Capability | Planner (`ROLE_PLANNER`) | Reviewer (`ROLE_REVIEWER`) | Analyst (`ROLE_ANALYST`) | Admin (`ROLE_ADMIN`) |
| :--- | :---: | :---: | :---: | :---: |
| **View Resources & Schedules** | Yes | Yes | Yes | Yes |
| **Inspect Plan Diffs & Explanations** | Yes | Yes | Yes | Yes |
| **Create / Edit Baseline Schedules** | Yes | No | No | Yes |
| **Trigger CP-SAT Optimiser & Replanning**| Yes | No | No | Yes |
| **Inject Simulated Disruption Events** | Yes | No | No | Yes |
| **Start / Complete / Cancel Tasks** | Yes | No | No | Yes |
| **Manage Spares Resupply Orders** | Yes | No | No | Yes |
| **Approve / Reject Plan Proposals** | **NO** | **YES** | **NO** | **NO** |
| **Request Plan Rollback / Refresh** | Yes | Yes | No | Yes |
| **Run Digital Twin Scenarios & Benchmarks**| Yes | No | Yes | Yes |
| **Review Anomaly Findings** | No | No | Yes | Yes |
| **Train, Promote, or Rollback ML Models** | No | No | No | Yes |
| **Edit Constraint Registry & Objective Weights**| No | No | No | Yes |
| **Configure Alert Rules & Maintenance Rules**| No | No | No | Yes |
| **Manipulate Virtual Clock / Demo Reset**| No | No | No | Yes |
| **Manage Users & Role Assignments** | No | No | No | Yes |
| **Acknowledge & Resolve Live Alerts** | Yes | Yes | Yes | Yes |
| **Generate & Download PDF / CSV Reports** | Yes | Yes | Yes | Yes (Scoped) |
| **Inspect System Audit Logs** | Own actions | Full | Full | Full |
| **Interact with Grounded AI Assistant** | Yes | Yes | Yes | Yes |

*Note: As established in Architecture Principle 3 and Section 7.3, Plan Approval is reserved exclusively for `ROLE_REVIEWER` to enforce strict segregation of duties (Planners propose, Reviewers approve).*

---

## 3. Demo Account Policy & Environment Seeding

1. **Zero Hard-Coded Credentials:** No user passwords or secrets shall be committed to git.
2. **Environment Variable Configuration:** Initial demonstration accounts are seeded from environment variables with safe fallbacks during local development:
   - `DEMO_PLANNER_USER`: `planner@airops.local` / `DEMO_PLANNER_PASSWORD`
   - `DEMO_REVIEWER_USER`: `reviewer@airops.local` / `DEMO_REVIEWER_PASSWORD`
   - `DEMO_ANALYST_USER`: `analyst@airops.local` / `DEMO_ANALYST_PASSWORD`
   - `DEMO_ADMIN_USER`: `admin@airops.local` / `DEMO_ADMIN_PASSWORD`
3. **Password Hashing:** Passwords are hashed using `argon2id` (memory cost: 65536 KiB, time cost: 3 iterations, parallelism: 4).
4. **Token Security:** Short-lived JWT access tokens (15-minute expiration) paired with rotating refresh tokens stored in `httpOnly`, `Secure`, `SameSite=Strict` cookies.
