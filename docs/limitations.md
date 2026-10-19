# AirOps Nexus — System Limitations & Formal Disclaimers

**Status:** Approved Public Disclosure (Phase 0, Task P0-13 & Section 26.10)  
**Version:** 1.0  
**Route:** Accessible in UI at `/about/limitations` and embedded in report footers.

---

## 1. Prototype Status & Non-Certification
- **Prototype Only:** AirOps Nexus is a research prototype developed for Problem Statement 26250 (*Air Power: Dynamic Air Operations and Resource Optimisation*).
- **No Operational Defense Certification:** This software has **not** been certified, evaluated, or accredited for live military operations, flight dispatch, weapon employment, or classified mission command.
- **Decision-Support Scope:** The system functions strictly as a human-supervised decision-support utility for logistics scheduling, base maintenance allocation, and resource deconfliction. It possesses no autonomous authority to execute real-world missions.

---

## 2. Synthetic Data Disclosure
- **100% Synthetic Data:** All assets, callsigns, tail numbers, personnel names, qualifications, maintenance procedures, coordinates, and operational tasks are entirely fictitious.
- **No Real Operational Feeds:** Any resemblance to real military airbases, defense units, or commercial airlines is purely coincidental.
- **Synthetic Accuracy Warning:** Machine learning model metrics (e.g., $R^2$, MAE, Brier score) reflect performance on synthetic data distributions and cannot be extrapolated to predict real-world equipment reliability or operational friction.

---

## 3. Data Provenance & Solver Status Taxonomy

Every derived number presented in the AirOps Nexus user interface is tagged with one of the following data provenance envelopes:
1. **`Observed`:** Directly recorded historical or operational reality (e.g., completed task timestamps).
2. **`Predicted`:** Output of a trained statistical or machine learning model. Always displayed with an associated model version, inference timestamp, and prediction uncertainty interval.
3. **`Simulated`:** Result of a stochastic discrete-event digital twin run (SimPy). Represents a hypothetical trajectory under randomized trials.
4. **`Generated`:** Synthetically synthesized by the deterministic scenario data generator.
5. **`Synthetic`:** General synthetic prototype baseline records.

### Solver Statuses
- **`Optimal`:** Mathematically proven to be the optimal schedule within the CP-SAT model and parameter bounds.
- **`Feasible`:** A valid schedule satisfying all hard constraints was identified, but search ended (e.g., due to timeout) before mathematical optimality could be established.
- **`Timeout`:** The solver hit its configured time limit without finding a feasible solution. This is an honest status indicating resource exhaustion—**never** misreported as proof of infeasibility.
- **`Infeasible`:** Mathematically proven that no combination of assignments can satisfy the combination of hard constraints. Accompanied by diagnostic conflict sets.
- **`Error`:** Internal computational exception. Logged safely with RFC 7807 problem details.
