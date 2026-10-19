# ADR 0001: Modular Monolith over Microservices Architecture

- **Status:** Accepted
- **Date:** 2026-10-19
- **Deciders:** Architecture Team (Stream A, B, C, D, E)
- **Consulted:** System Stakeholders

---

## Context and Problem Statement
The requirements demand a tightly integrated 10-step end-to-end workflow (data generation, inspection, baseline scheduling, disruption injection, impact analysis, predictive ML, replanning, digital twin simulation, explainability, human approval, and audit). 
Should the prototype be built as distributed microservices or as a modular monolith?

## Considered Options
1. **Distributed Microservices** (separate services for scheduler, ML inference, simulation, API, and auth).
2. **Modular Monolith** (single FastAPI codebase with strict internal engine protocols, distinct background Celery workers, and clean repository layering).

## Decision Outcome
Chosen option: **Modular Monolith** (Option 2).

### Positive Consequences
- **Transactional Integrity:** Approvals, plan superseding, and audit logging happen within a single atomic database transaction, preventing split-brain states.
- **Simplified Operational Complexity:** One unified Docker Compose stack for local development, CI testing, and live demonstrations without distributed tracing and consensus overhead.
- **Engine Protocol Decoupling:** Engines (`optimisation`, `prediction`, `digital_twin`, `explainability`) communicate via pure Python `Protocol` interfaces under `app/engines/`, enabling independent unit testing and future extraction if scale demands it.
- **Single Source of Truth:** A single schema repository and Pydantic models eliminate network serialization overhead and schema drift between internal services.

### Negative Consequences
- Team disciplines must strictly respect internal engine boundaries and forbid direct cross-engine database imports without service layer mediation.
- CI pipelines build and test the full monolith codebase.
