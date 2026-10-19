# ADR 0004: CP-SAT Deterministic Configuration and Reproducibility Mode

- **Status:** Accepted
- **Date:** 2026-10-19
- **Deciders:** Optimisation & QA Team (Stream B, E)

---

## Context and Problem Statement
OR-Tools CP-SAT multi-threaded search is non-deterministic across different hardware thread counts and OS thread schedulers. A core requirement is that running the demo script or test suite with an identical random seed, dataset snapshot, and configuration produces identical plan assignments and objective values.
How do we balance multi-threaded solver performance against reproducibility?

## Considered Options
1. **Multi-threaded solver by default:** Fast execution, but variable search paths that cause non-reproducible plans.
2. **Explicit Reproducible Mode:** Single worker thread (`num_search_workers = 1`) with fixed random seed by default for automated tests, demonstrations, and baseline reproducibility, with an optional fast mode explicitly flagged and labelled `non-reproducible`.

## Decision Outcome
Chosen option: **Explicit Reproducible Mode by Default** (Option 2).

### Implementation Rules
- Default CP-SAT solver parameters: `num_search_workers: 1`, `random_seed: <seed>`, `cp_model_presolve: True`.
- Every generated plan stores its `solver_config` (including thread count, seed, time limit, and bound) in its run manifest.
- If parallel mode is activated (`num_search_workers > 1`), the API and UI must tag the result with `reproducible: false` to maintain transparency.
- Optimization time limits are enforced cleanly with honest `timeout` status mapping (never misreported as `infeasible`).
