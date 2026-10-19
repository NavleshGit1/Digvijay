# Contributing to AirOps Nexus

Thank you for contributing to AirOps Nexus. This document specifies the engineering conventions, code quality gates, Definition of Done, and the contract change process for all workstreams.

---

## 1. Workstream Ownership & Branching Model

- **Workstream A:** Platform & Data Engine (`app/api`, `app/db`, `app/services`, `app/engines/data_fusion`)
- **Workstream B:** Optimisation & Replanning (`app/engines/optimisation`, `app/engines/replanning`, validator)
- **Workstream C:** ML Platform & Digital Twin (`app/engines/prediction`, `app/engines/digital_twin`, `ml/`)
- **Workstream D:** Frontend Application (`frontend/`)
- **Workstream E:** Security, Governance, QA & DevOps (`app/audit`, `app/governance`, `.github/`, tests)

### Branch Naming Conventions
- `feature/<stream>-<task-id>-<short-description>` (e.g., `feature/A-P1-4-fastapi-app-factory`)
- `fix/<stream>-<issue-description>`
- `contract/<change-request-id>`

---

## 2. Code Quality & Pre-Commit Standards

Every merged change must pass automated linting and static analysis without errors or warnings:
- **Backend (Python 3.12):**
  - Formatter & Linter: `ruff check .` and `ruff format .`
  - Static Type Checking: `mypy . --strict`
  - Test Suite: `pytest --cov=app tests/`
  - **Forbidden Rule:** Direct use of `datetime.now()` or `utcnow()` is banned; all business logic must receive a `Clock` protocol instance.
- **Frontend (TypeScript 5 / React 18):**
  - Formatter & Linter: `eslint .` and `prettier --check .`
  - Type Check: `tsc --noEmit`
  - Tests: `vitest run` and `playwright test`
  - Accessibility: `axe-core` assertions on all rendered views.

---

## 3. Contract Change Request Process

The OpenAPI contract (`docs/openapi.json`) and Data Dictionary (`docs/data-dictionary.md`) serve as the single source of truth across streams.
- If an endpoint, schema, or enum must be modified, the change **must** be submitted via a `contract/` branch first.
- CI verifies that TypeScript types generated from `docs/openapi.json` remain in 100% synchronization with backend Pydantic schemas.
- Contract edits require review by Stream A (Backend) and Stream D (Frontend) before merging.

---

## 4. Definition of Done (DoD)

A task or feature cannot be marked complete unless:
1. All unit, property-based (`Hypothesis`), and integration tests pass.
2. Server-side authorization dependencies are applied to all modified endpoints.
3. Protected mutations (approvals, config edits, seed resets) produce an append-only audit log row.
4. UI components include `loading`, `empty`, `stale`, and `error` states without hard-coded numbers.
5. All generated and derived outputs display appropriate `DataKind` labels.
6. Documentation, schema dictionaries, and ADRs are updated.
