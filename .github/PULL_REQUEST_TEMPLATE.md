## AirOps Nexus — Pull Request

### Summary of Changes
<!-- Describe what changes are introduced and the architectural motivation -->

### Phase & Task Reference
- **Phase:** <!-- e.g., Phase 4 (Scheduling), Phase 5 (Governance) -->
- **Task ID:** <!-- e.g., P4-4, P5-2 -->
- **Requirement:** <!-- e.g., FR-05, FR-12 -->

### Quality & Governance Checklist
- [ ] **Deterministic Clock:** All new timestamps respect `get_clock().now()`. Passed `python scripts/lint_clock.py`.
- [ ] **Contract Alignment:** OpenAPI schema and frontend types are in sync (`docs/openapi.json`).
- [ ] **Server-Side Enforcement:** Permissions verified via `@require_permission()` on all protected endpoints.
- [ ] **Cryptographic Audit:** Sensitive state alterations logged via `@audited`.
- [ ] **Frontend Compliance:** `npm run lint` passes with 0 warnings (`--max-warnings 0`) and `npm run type-check` succeeds.
- [ ] **Test Coverage:** Unit and integration tests added under `backend/tests` or `frontend/src`.
- [ ] **Synthetic Disclosures:** All sample datasets labelled as synthetic.
