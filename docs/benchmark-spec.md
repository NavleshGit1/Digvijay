# AirOps Nexus — Benchmark & Evidence Suite Specification

**Status:** Approved Specification (Phase 0, Task P0-13 & Amendment v1.1)  
**Version:** 1.0  
**References:** Architecture Section 26.9

---

## 1. Purpose & Empirical Approach

To prevent unsubstantiated marketing claims, AirOps Nexus incorporates an automated benchmarking framework. Rather than pre-inventing arbitrary target percentages, the benchmark suite empirically compares CP-SAT against simpler dispatch heuristics across standardized scenario profiles. Pass/fail regression thresholds are established from baseline Phase 4 measurements and recorded in an Architecture Decision Record.

---

## 2. Standardized Scenario Library (JSON Presets)

1. **`SCEN_NOMINAL_WEEK`:** 7-day schedule, 40 assets, 300 tasks, nominal weather, zero unexpected breakdowns.
2. **`SCEN_SINGLE_OUTAGE`:** Abrupt unserviceability of a primary multirole asset at hour 24.
3. **`SCEN_MAINT_DELAY`:** A 6-hour delay injected into a heavy inspection window of a transport aircraft.
4. **`SCEN_CAPACITY_REDUCTION`:** Fictional Zone Alpha runway capacity cut by 50% due to adverse weather.
5. **`SCEN_RESUPPLY_DELAY`:** Critical spare actuators delayed by 48 hours, blocking scheduled overhauls.
6. **`SCEN_MULTI_DISRUPT`:** Cascading disruptions: asset outage + maintenance delay + resupply delay.
7. **`SCEN_DENSE_SURGE`:** 600 tasks over 7 days to stress-test capacity and solver limits.

---

## 3. Compared Strategies

Every scenario is evaluated under four distinct dispatch and replanning strategies:
1. **`STRAT_DO_NOTHING` (Right-Shift):** Inflexible right-shift of disrupted tasks with linear delay propagation.
2. **`STRAT_BASELINE_HEURISTIC`:** Earliest-due-date dispatch on earliest feasible resource slots.
3. **`STRAT_CPSAT_STANDARD`:** OR-Tools CP-SAT in reproducible single-threaded mode.
4. **`STRAT_CPSAT_ABLATION`:** CP-SAT with the predicted maintenance downtime buffer turned ON vs. OFF to measure whether predictive ML reduces realised disruptions in the digital twin.

---

## 4. Benchmark Metrics
- **Total Delay Minutes:** Cumulative tardiness beyond due dates.
- **Weighted Task Completion Rate:** Percentage of eligible tasks successfully assigned.
- **Plan Churn:** Ratio of moved assignments relative to base plan.
- **Resource Utilization:** Average active working time across assets and crew.
- **Solver Runtime & Gap:** CP-SAT execution wall-clock time and proven optimality gap.
- **Digital Twin P95 Delay:** 95th percentile delay observed across 100 SimPy Monte Carlo runs.
- **Validator Pass Rate:** Must be 100% for CP-SAT and heuristic plans.
