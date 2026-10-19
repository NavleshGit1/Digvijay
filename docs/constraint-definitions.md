# AirOps Nexus — Constraint Catalogue & Mathematical Formulations

**Status:** Approved Specification (Phase 0, Task P0-5 & P4-11)  
**Version:** 1.1 (Includes Constraints 1–10 and Section 26 Extensions)  
**Engines:** OR-Tools CP-SAT (Solver) & Pure-Python Validator (`app/engines/optimisation/validator.py`)

---

## 1. Dual-Verification Architecture

Every proposed plan must satisfy all active hard constraints. The system verifies this through two independent mechanisms:
1. **Solver Formulation (CP-SAT):** Mathematical constraints encoded using optional intervals and presence literals.
2. **Independent Pure-Python Validator:** An isolated verification pass that evaluates the serialized schedule independently. If any hard constraint fails validation, the plan is marked `invalid` and cannot be proposed or approved.

---

## 2. Hard Constraint Catalogue (The 10 Operational Invariants)

| # | Code | Name | CP-SAT Representation | Pure-Python Validator Check |
| :-: | :--- | :--- | :--- | :--- |
| **1** | `HC_RESOURCE_AVAIL` | Resource Availability Windows | Restrict task interval start and end within active working shifts. | Assert: $\text{start}(T) \ge \text{shift\_start}(R) \land \text{end}(T) \le \text{shift\_end}(R)$. |
| **2** | `HC_NO_OVERLAP` | No Incompatible Simultaneous Assignments | `model.AddNoOverlap(intervals_per_asset)` & `model.AddNoOverlap(intervals_per_person)`. | Pairwise interval intersection check: $\forall i \ne j, [\text{start}_i, \text{end}_i) \cap [\text{start}_j, \text{end}_j) = \emptyset$. |
| **3** | `HC_QUALIFICATIONS` | Crew Capability & Certification | Prune interval variables: only instantiate interval $I_{t, p}$ if crew $p$ holds all required certifications for task $t$. | Membership validation: $\text{required\_quals}(T) \subseteq \text{active\_quals}(P, \text{start}(T))$. |
| **4** | `HC_MAINT_WINDOWS` | Maintenance & Downtime Windows | Add confirmed maintenance work orders as fixed non-optional intervals into asset `NoOverlap`. | Assert no operational task overlaps with confirmed maintenance windows. |
| **5** | `HC_CAPACITY_LIMITS`| Zone & Equipment Capacity | `model.AddCumulative(intervals, demands, capacity_limit)` per bay or apron zone. | Compute slot-by-slot running concurrency; assert $\le \text{zone\_capacity}$. |
| **6** | `HC_TIME_BOUNDS` | Task Durations & Deadlines | Fixed interval duration ($d = \text{duration}$); bounds $\text{start} \ge \text{release\_date} \land \text{end} \le \text{deadline}$. | Verify $\text{end}(T) - \text{start}(T) = \text{duration}(T)$, $\text{start} \ge \text{earliest}$, $\text{end} \le \text{due}$. |
| **7** | `HC_PRECEDENCE` | Task Precedence & Dependencies | `model.Add(start(B) >= end(A) + lag_minutes).OnlyEnforceIf([pres(A), pres(B)])`. | Verify topological ordering across the NetworkX precedence DAG. |
| **8** | `HC_SAFETY_DUTY` | Abstract Safety & Rest Rules | Rest windows between shifts: interval distance $\ge \text{min\_rest\_hours}$; maximum duty limit per rolling 24 hours. | Check accumulated duty hours $\le \text{max\_duty}$ and rest between consecutive sorties $\ge \text{min\_rest}$. |
| **9** | `HC_USAGE_BUDGET` | Asset Usage Allowance (v1.1) | Total planned usage within planning horizon must not exceed $(\text{counter\_limit} - \text{current\_counter})$ unless reset maintenance is scheduled. | Sum scheduled task flight-hours per asset; assert $\sum \text{hours} \le \text{remaining\_allowance}$. |
| **10**| `HC_SPARES_RESERVOIR`| Spares & Part Availability (v1.1) | `model.AddReservoirConstraint(...)` over initial on-hand, resupply deliveries, and consumption demands. | Trace chronological running balance; assert $\text{balance}(t) \ge 0$ at all discrete time slots. |

---

## 3. Fixed Commitment Rules (Locked Assignments & Frozen Window)

1. **Task Execution Locking:** Any task assignment where `actual_start <= as_of` is marked **locked**. In CP-SAT, locked tasks are represented as fixed, non-optional intervals ($start = actual\_start, end = actual\_end, asset = assigned\_asset$) and cannot be moved or unassigned.
2. **Frozen Window:** Any unstarted task scheduled to begin within the configured frozen horizon ($[t_{\text{as\_of}}, t_{\text{as\_of}} + \text{lead\_time}]$) is penalized heavily against movement to prevent operational thrash.

---

## 4. Soft Objectives & Versioned Weights

The multi-objective function is optimized as an integer linear sum:

$$\min Z = w_{\text{delay}} \cdot \sum \text{Delay}_i + w_{\text{unassigned}} \cdot \sum \text{UnscheduledPenalty}_i + w_{\text{churn}} \cdot \sum \text{ChurnCost}_i + w_{\text{buffer}} \cdot \sum \text{BufferPenalty}_i$$

- **`delay_weight` ($w_{\text{delay}}$):** Penalizes tasks completing past their due date.
- **`completion_weight` ($w_{\text{unassigned}}$):** High penalty for leaving eligible tasks unplaced (using optional intervals with presence literals).
- **`churn_weight` ($w_{\text{churn}}$):** Penalizes moving tasks that were already assigned in the base approved plan.
- **`buffer_weight` ($w_{\text{buffer}}$):** Soft penalty for placing flight tasks within the predicted maintenance downtime buffer zone (ADR 0005).
- **Governance:** All weights are defined in versioned `objective_weight_sets` and require Admin privileges to update.
