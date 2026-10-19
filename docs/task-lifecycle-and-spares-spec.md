# AirOps Nexus — Task Execution Lifecycle, Usage Accrual, and Spares Logistics

**Status:** Approved Specification (Phase 0, Task P0-11 & Amendment v1.1)  
**Version:** 1.0  
**References:** Architecture Section 26.3 & 26.6

---

## 1. Task Execution State Machine

```
               ┌──────────┐
               │ PENDING  │
               └────┬─────┘
                    │ Assigned in Approved Plan
               ┌────▼─────┐
               │SCHEDULED │◄────────┐
               └────┬─────┘         │
                    │ POST /tasks/{id}/start
               ┌────▼────────┐      │
               │ IN_PROGRESS │      │
               └────┬────────┘      │
     ┌──────────────┴──────────────┐│
     │ POST .../complete           ││ POST .../cancel
┌────▼──────┐                 ┌────▼▼────┐
│ COMPLETED │                 │CANCELLED │
└───────────┘                 └──────────┘
```

### 1.1 State Definitions
- **`PENDING`:** Task created, not yet placed in an approved schedule.
- **`SCHEDULED`:** Task has an active assignment in the current approved plan version.
- **`IN_PROGRESS`:** Execution has started (`actual_start <= as_of`). Transition writes a row into `task_executions`.
- **`COMPLETED`:** Task finished successfully. `actual_end` is recorded, delay minutes are computed, and asset wear is accrued.
- **`CANCELLED`:** Task aborted before completion. Unlocks assigned resources.
- **`BLOCKED`:** Operational constraint violation or predecessor disruption prevents execution.

### 1.2 Execution Locking Rule
- **Rule:** If a task in an approved plan has `actual_start <= as_of`, its assignment is **locked**.
- **Constraint Enforcement:** When replanning runs, locked assignments are treated by CP-SAT as immovable fixed intervals. The replanner can only reassign or shift unstarted tasks.

---

## 2. Usage Accrual & Wear Accounting

Operational assets accrue usage from completed executions:
1. **Accrual Trigger:** When a task transition moves to `COMPLETED`, the system calculates actual duration:
   $$\Delta t = \text{actual\_end} - \text{actual\_start}$$
2. **Counter Updates:**
   - `flight_hours` increments by $\Delta t$ (for flight sortie categories).
   - `cycles` increments by 1 (takeoff/landing event).
   - `calendar_days` advances with clock updates.
3. **Coupling to Maintenance:**
   - `maintenance_rules` define service intervals (e.g., *Check A at 100 flight hours, Check B at 500 hours*).
   - If an asset counter approaches the threshold within lead time $\tau_{\text{lead}}$, the maintenance planner creates a `maintenance_due` record.

---

## 3. Spares Logistics & Resupply Pipeline

1. **Reservoir Invariant:**
   For every tracked spare part $p$ at zone $z$ across all time slots $t \in [t_{\text{now}}, t_{\text{now}} + H]$:
   $$\text{Stock}(p, z, t) = \text{InitialOnHand}(p, z) + \sum_{\text{Orders } o: \text{ETA}_o \le t} \text{Qty}_o - \sum_{\text{Maint } m: \text{Start}_m \le t} \text{RequiredParts}_{m, p} \ge 0$$
2. **Consumption:** Maintenance work orders deduct reserved stock upon start and permanently ledger changes in `spares_movements`.
3. **Resupply Ingestion:** New shipments ingested via `POST /resupply-orders` or `resupply_delay` events trigger dynamic inventory recalculation and impact assessment.
