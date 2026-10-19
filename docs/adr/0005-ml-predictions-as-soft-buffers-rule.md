# ADR 0005: ML Predictions as Soft Penalties and Buffer Zones Rule

- **Status:** Accepted
- **Date:** 2026-10-19
- **Deciders:** Optimisation, ML & Safety Team (Stream B, C, E)

---

## Context and Problem Statement
Machine learning models generate predictions for maintenance downtime, task delay, and disruption risk. If probabilistic ML predictions are injected directly as hard operational constraints, an inaccurate prediction could force the solver to reject valid schedules or make the model infeasible. Conversely, ignoring predictions risks scheduling tasks into imminent failure windows.
How should predictive ML outputs be interfaced with the CP-SAT solver?

## Considered Options
1. **Direct Hard Window Replacement:** Override confirmed maintenance windows with predicted completion dates.
2. **Soft Buffer Zones and Objective Penalties:** Preserve confirmed operational and maintenance windows as hard constraints; append a predicted downtime buffer (default P80 quantile) as an adjustable soft-penalty buffer.

## Decision Outcome
Chosen option: **Soft Buffer Zones and Objective Penalties** (Option 2).

### Architectural Rules
1. **Strict Hard Constraint Protection:** Hard constraints (availability windows, qualifications, no-overlap, capacity, safety rules) are derived **only** from verified, confirmed system of record data.
2. **Probabilistic Buffers:** Predicted downtime extensions are modeled as soft buffer intervals following the hard maintenance window. The solver penalizes scheduling high-priority tasks inside this buffer, balancing operational throughput against risk.
3. **Traceability:** Every plan created using predictive model inputs records the exact `prediction_id` and `model_version` in its manifest.
4. **Independent Validation:** The pure-Python validator checks only hard constraints. It never evaluates predictive buffers, ensuring solver safety even if models fail or degrade.
