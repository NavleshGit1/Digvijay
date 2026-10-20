# AirOps Nexus — Security Framework

Agent-ready spec v2.0. Concise rewrite that replaces v1.0 (still in the version history) and adds signed source manifests, Redis fail-closed behaviour and per-phase verification. Synthetic data only; not a certification. Phase numbers follow the Implementation Plan v1.1.

## 1. How a coding agent uses this spec

1. Every requirement has an ID (SEC-nn), a MUST statement, a location and an acceptance test. Build only what is due in the current phase (section 8). Do not start the next phase until the gate passes.
2. Write the acceptance test first. Name it tests/security/test\_sec\_NN\_slug.py (or a Playwright spec for the frontend) and register it in tests/security/sec\_registry.yaml with id, phase, test paths and status. make sec-registry-check fails if a requirement due in the current or an earlier phase has no passing test.
3. Fail closed. If a security dependency (Redis, database, key, signature check, hash check) errors or is missing, deny the action and return the matching error code. Never fall back to allow.
4. Never weaken a control to make a test or demo pass. If a requirement blocks a task, stop and record the question in docs/security/decisions.md, using the default from section 9.
5. Do not use the forbidden patterns in 1.1; CI blocks them.
6. Changes under the paths in 1.2 need human review (CODEOWNERS).
7. Finish each phase with make sec-verify PHASE=n and commit the generated docs/security/evidence/phase-n.md.

### 1.1 Forbidden patterns

- datetime.now or utcnow outside core/clock.py (use the injected Clock; audit uses the wall-clock helper in audit/writer.py).
- pickle, marshal, joblib.load or yaml.load on untrusted input; eval or exec; torch.load without weights\_only=True.
- subprocess with shell=True; HTTP calls without a timeout; TLS verification disabled.
- SQL built from strings or f-strings; raw text() with interpolated values.
- dangerouslySetInnerHTML; tokens in localStorage or sessionStorage.
- Logging request bodies, Authorization headers, passwords, tokens or keys.
- Hard-coded secrets, default passwords, DEBUG on outside development, CORS origin \*.
- Bare except or pass inside security, audit, governance or ingest modules.

### 1.2 Security-critical paths (CODEOWNERS)

backend/app/security/, backend/app/audit/, backend/app/governance/, backend/app/ingest/manifest.py, backend/app/ml/artifact\_guard.py, backend/app/assistant/, backend/app/engines/optimisation/validator.py, deploy/, migrations/ (audit and plan state files), .github/workflows/, tests/security/.

### 1.3 Error codes (problem+json type values)

forbidden, sod\_violation, step\_up\_required, revalidation\_failed, conflict\_version, rate\_limited, quota\_exceeded, job\_in\_progress, manifest\_invalid, quarantined, engine\_unavailable, dependency\_unavailable (HTTP 503), security\_freeze, validation\_error.

## 2. Scope and trust zones

Priorities: decision integrity, then audit accountability, then confidentiality, then availability. All data is synthetic and no real system is connected, but controls are built as if the data were sensitive.

| Zone | Components | Network rule (docker compose) |
| --- | --- | --- |
| Edge | caddy | Only service with a published port (443) |
| Application | api (and SSE) | Networks frontend and backend |
| Workers | optimise, ml, simulate, report, ingest | Network backend; no inbound from the edge |
| Data | postgres, redis, minio | Network data with internal: true; no published ports |
| ML operations | mlflow | Network mlops with internal: true |
| Assistant egress | llm-gateway | Network egress; destination allow-list; the only outbound path |
| Observability | otel, prometheus, grafana, loki | Network obs, admin access only |

Postgres roles: app\_rw, simulator\_ro, audit\_insert, migration, reporting\_ro. Each service has its own Redis, MinIO and MLflow credentials.

## 3. Security requirements

Columns: requirement ID, what the code MUST do, where it lives, the acceptance test (file test\_sec\_NN under tests/security unless noted), and the phase it is due.

### 3.1 Identity and access

| ID | MUST | Where | Acceptance test | Ph |
| --- | --- | --- | --- | --- |
| SEC-01 | Hash passwords with Argon2id; minimum length 12; reject entries on the weak list | security/auth.py | Policy and hash tests | 1 |
| SEC-02 | Login throttling: progressive delay, lockout after 5 failures per 15 minutes per account and per address; identical response for unknown user and wrong password | security/auth.py, rate\_limit.py | Response and timing equality | 1 |
| SEC-03 | TOTP MFA required for Reviewer and Admin unless DEMO\_MODE | security/auth.py, table user\_mfa | Login without MFA refused | 1 |
| SEC-04 | JWT with EdDSA or RS256, algorithm pinned in the verifier, 15-minute expiry, kid header; reject alg none, wrong kid, expired, tampered | security/auth.py | Token tamper suite | 1 |
| SEC-05 | Refresh token opaque, httpOnly Secure SameSite=Strict cookie on the auth path, rotated on every use; reuse revokes the session family; CSRF token on refresh and logout | security/sessions.py | Reuse and CSRF tests | 1 |
| SEC-06 | Revoke sessions on logout, password change and role change; idle 30 minutes, absolute 12 hours | security/sessions.py, Redis denylist | Revocation tests | 1 |
| SEC-07 | Every route declares a permission through require(); build fails if one does not | security/permissions.py | Route-permission test over OpenAPI | 1 |
| SEC-08 | Services check object-level access (ownership, scope, state) on every id-based read and write | services/ | Cross-user attempt tests | 3 |
| SEC-09 | Separate database roles; applications never use a superuser | deploy/postgres/roles.sql | Privilege matrix query | 1, 8 |
| SEC-10 | Step-up (password or TOTP within 5 minutes) for: approve or reject, model promote or rollback, constraint activation, weight or alert-rule change, clock set, demo reset, role change, user disable | security/stepup.py | Each action refused without step-up | 5 |
| SEC-11 | Separation of duties: requester differs from approver; Planner and Reviewer roles cannot co-exist on one user; Admin cannot approve | security/sod.py | sod\_violation tests | 5 |
| SEC-12 | The last Admin cannot be removed or disabled | services/users.py | Unit test | 10 |
| SEC-13 | No default or hard-coded credentials; demo accounts only when DEMO\_MODE; passwords from environment or generated once | scripts/seed\_users.py | Repository scan and production-mode start test | 1 |

### 3.2 API and web application

| ID | MUST | Where | Acceptance test | Ph |
| --- | --- | --- | --- | --- |
| SEC-14 | Pydantic models with extra forbidden, bounded strings, lists and numbers, JSON depth at most 10, body at most 1 MB | schemas/base.py | Fuzz and unit tests | 1 |
| SEC-15 | Sort and filter fields only from an allow-list; ORM or bound parameters only | repositories/ | Injection tests plus Semgrep rule | 2 |
| SEC-16 | Errors as problem+json with stable codes; no stack traces, SQL or paths | api/errors.py | Error-shape tests | 1 |
| SEC-17 | Rate limits: login 5 per minute, default 100 per minute per user, stricter on optimise, simulate, report, benchmark, assistant | security/rate\_limit.py | Limit tests | 1, 4 |
| SEC-18 | Idempotency-Key required on approve, reject, optimisation job and event creation; replay returns the original result | api/idempotency.py | Replay tests | 5 |
| SEC-19 | Uploads: CSV or JSON only, at most 20 MB, signature check, parsed in a worker with row and time limits, failures go to quarantine | ingest/uploads.py | Malformed and oversize tests | 2 |
| SEC-20 | CSV export neutralises cells starting with =, +, -, @, tab or carriage return | reports/csv\_safe.py | Payload tests | 10 |
| SEC-21 | PDF rendering with auto-escaping and external fetching disabled | reports/pdf.py | Template injection and fetch tests | 10 |
| SEC-22 | Edge headers: CSP (default-src self; script-src self; object-src none; base-uri self; form-action self; frame-ancestors none), HSTS, nosniff, Referrer-Policy no-referrer | deploy/caddy/Caddyfile | Header test and ZAP baseline | 1 |
| SEC-23 | dangerouslySetInnerHTML banned by lint; assistant markdown and SVG sanitised or shown as text | frontend lint, components/SafeHtml | Playwright XSS payloads in names and events | 1, 9 |
| SEC-24 | Access token held in memory only | frontend auth module | Playwright storage check | 1 |

### 3.3 Data and ingestion

| ID | MUST | Where | Acceptance test | Ph |
| --- | --- | --- | --- | --- |
| SEC-25 | Every record has is\_synthetic; sources need a synthetic attestation; values outside the fictional namespace (reserved ID prefixes and name pools) are quarantined; persistent banner | ingest/guard.py | Real-looking value quarantined | 2 |
| SEC-71 | **Source authenticity (new):** every import and connector payload carries a signed manifest (Ed25519) with source\_id, file SHA-256, row count, generator version, synthetic attestation, issued\_at, expires\_at and nonce. Verify the signature against the key registered for that source, the file hash, expiry, and that the nonce is unused (store it). Otherwise reject with manifest\_invalid and log. Public keys are registered by an Admin with step-up; the generator signs with a key from the secret store | ingest/manifest.py, tables data\_source\_keys and manifest\_nonces | Forged signature, altered file, expired, replayed nonce, unknown key | 2 |
| SEC-26 | TLS at the edge; encrypted volumes; encrypted backups | deploy/, scripts/backup.sh | Config check | 1, 11 |
| SEC-27 | Secrets only from Docker secrets or environment at runtime; only .env.example in the repository; logs scrubbed | core/settings.py, core/logging.py | gitleaks plus log scrub test | 1 |
| SEC-28 | Rotation runbook for JWT, database, Redis, MinIO, MLflow and LLM keys, exercised each release | docs/security/runbooks/rotation.md | Drill record | 11 |
| SEC-29 | Retention settings for security logs, assistant text (off by default) and backups; minimal account data | core/retention.py | Retention tests | 10 |

### 3.4 Decision and audit integrity

| ID | MUST | Where | Acceptance test | Ph |
| --- | --- | --- | --- | --- |
| SEC-30 | Database trigger rejects illegal plan transitions; status approved only with an approval\_record in the same transaction | migrations/plan\_state.sql | Direct SQL attempts fail | 5 |
| SEC-31 | content\_hash on every plan version, copied into the approval record; a job recomputes and compares | governance/plan\_hash.py | Tamper detection | 5 |
| SEC-32 | Approve locks the current-approved row, revalidates on the current snapshot, marks sibling proposals stale, writes approval and audit in one transaction | governance/approval.py | Concurrent approvals; data change returns revalidation\_failed | 5 |
| SEC-33 | audit\_logs is append-only: insert-only role and triggers blocking UPDATE, DELETE, TRUNCATE | migrations/audit.sql | Direct SQL attempts fail | 1 |
| SEC-34 | Hash chain (SHA-256 of previous hash plus canonical JSON); nightly verification; nightly anchor of the chain head to a MinIO bucket with object lock | audit/chain.py, anchor.py, verify.py | Tampered row detected; anchor written | 1, 5 |
| SEC-35 | Audit entries store recorded\_at (real wall clock) and as\_of | audit/writer.py | Entry with both fields under a fixed clock | 1 |
| SEC-36 | Config changes (constraints, weights, rules, toggles) are Admin-only, bounded by schema, versioned, impact-previewed, step-up, audited; hard constraints, validator, auth and audit cannot be disabled | governance/config.py | Out-of-bounds and disable attempts refused | 4, 5, 10 |
| SEC-37 | Clock set is Admin-only, step-up, audited and alerts; FixedClock and SimulatedClock only in DEMO\_MODE; cannot move earlier than the latest approved plan as\_of except through reset | core/clock.py | Rewind refused | 1 |
| SEC-38 | Demo reset needs DEMO\_MODE, Admin, step-up and a typed phrase; writes a snapshot first; seals and chains the audit segment, never truncates it | demo/reset.py | Reset keeps chain valid; refused outside DEMO\_MODE | 2 |
| SEC-39 | Only the approve path creates approved plans; the replan workflow, simulator, benchmark runner and assistant cannot approve or write plans | tests/security/test\_oversight.py | Each component attempts and fails | 5, 6, 8, 9 |

### 3.5 Dependency failure behaviour

| ID | MUST | Where | Acceptance test | Ph |
| --- | --- | --- | --- | --- |
| SEC-72 | **Redis fail-closed (new):** if Redis is unreachable, every authenticated route except /health returns 503 dependency\_unavailable, because revocation, rate limits, idempotency and locks cannot be checked; no cached allow, no in-memory fallback; log and alert. REDIS\_FAIL\_MODE accepts only closed outside DEMO\_MODE | security/redis\_guard.py wrapping denylist, limiter, idempotency, locks | Stop Redis: expect 503 everywhere, no bypass, clean recovery | 1 |
| SEC-73 | PostgreSQL unavailable returns 503; no fallback for auth, audit or approvals; an audit write failure aborts the action | core/db.py | Stop database test | 1 |
| SEC-74 | MinIO unavailable: model loads, report downloads and anchoring fail visibly; an anchor failure raises a High alert | ml/artifact\_guard.py, audit/anchor.py | Stop MinIO test | 5, 7 |
| SEC-75 | Queue or lock unavailable: new optimisation and simulation jobs rejected with 503; never run without the lock | jobs/lock.py | Stop broker test | 4 |

### 3.6 AI and ML

| ID | MUST | Where | Acceptance test | Ph |
| --- | --- | --- | --- | --- |
| SEC-40 | Datasets content-hashed; training reads only dataset versions with status approved | ml/train.py | Unapproved dataset refused | 2, 7 |
| SEC-41 | Model artefacts in safe formats (native LightGBM or XGBoost, ONNX); any joblib artefact signed by the training worker; SHA-256 stored in model\_versions and verified before load; loading in a restricted process (no network, read-only file system, limits) | ml/artifact\_guard.py | Tampered and unsigned artefacts refused with alert | 7 |
| SEC-42 | MLflow requires authentication, is internal only, and accepts registry writes only from the training identity | deploy/mlflow | Write from another identity refused | 7 |
| SEC-43 | Promotion gate: beats baseline, calibration, leakage tests, artefact scan, hash recorded, model card, Admin step-up | ml/promotion.py | Failing any check blocks promotion | 7 |
| SEC-44 | Prediction endpoints enforce input bounds, out-of-distribution warnings and per-user rate limits; no bulk endpoint | api/predictions.py | Bounds and limit tests | 7 |
| SEC-45 | Explanations only from stored evidence; a content scan fails the build on claims of real-world accuracy | explain/, tests/security/test\_claims.py | Claims scan | 9, 11 |

### 3.7 Assistant

| ID | MUST | Where | Acceptance test | Ph |
| --- | --- | --- | --- | --- |
| SEC-46 | Tool registry read-only; a test fails if any tool name contains approve, reject, promote, activate, reset, set, create, update or delete; tools run with the caller's permissions | assistant/tools.py | Denylist test | 9 |
| SEC-47 | Retrieved text, tool results and user text delimited as data; tool arguments validated; red-team set in tests/security/redteam run in CI | assistant/guard.py | Injection and jailbreak set | 9 |
| SEC-48 | Output shown as plain text or sanitised markdown; every cited id was returned in the same turn, otherwise answer insufficient evidence | assistant/compose.py | Citation check tests | 9 |
| SEC-49 | The gateway is the only egress, with a destination allow-list; synthetic data only; requests for tactical or weapons planning are refused and logged | assistant/egress.py, compose network | Blocked-egress and refusal tests | 9 |
| SEC-50 | Token, context, timeout and per-user quotas; at most 5 tool calls per turn | assistant/limits.py | Limit tests | 9 |

### 3.8 Engines, infrastructure and supply chain

| ID | MUST | Where | Acceptance test | Ph |
| --- | --- | --- | --- | --- |
| SEC-51 | Limits on model size, solver time, memory, Monte Carlo runs and horizon; per-user quotas | engines/limits.py | Oversize and flood tests | 4, 8 |
| SEC-52 | Simulator uses simulator\_ro; no writes to plans, approvals or task executions | engines/digital\_twin | Write attempts fail | 8 |
| SEC-53 | Workers: non-root, read-only root file system, no inbound access, cgroup limits | deploy/compose | Compose config test | 1, 4 |
| SEC-54 | Only caddy publishes a port; data and mlops networks are internal | docker-compose.yml | Parse compose config | 1 |
| SEC-55 | Containers: cap\_drop ALL, no-new-privileges, read\_only, images pinned by digest | compose, Dockerfiles | Trivy, hadolint, config test | 1, 11 |
| SEC-56 | Redis ACL user per service; Celery accepts JSON only; messages signed; no pickle | deploy/redis/users.acl, celery config | Unauthenticated and pickle messages rejected | 1 |
| SEC-57 | MinIO private buckets, per-service policies, signed URLs of at most 5 minutes, object lock on the audit-anchor bucket | deploy/minio | Policy and expiry tests | 1, 5 |
| SEC-58 | Grafana, Flower, MinIO console and MLflow UI are not published | compose | Network test | 1 |
| SEC-59 | Lockfiles with hashes (uv, pnpm); CI installs with hash checking | CI | Pipeline check | 1 |
| SEC-60 | CI runs ruff security rules, Bandit, Semgrep, CodeQL, gitleaks, pip-audit, npm audit, Trivy, hadolint | .github/workflows/security.yml | Pipeline fails on findings | 1 |
| SEC-61 | SBOM (CycloneDX) and cosign-signed images, verified at deploy | CI | Pipeline check | 11 |
| SEC-62 | Actions pinned by SHA, minimal token permissions, CODEOWNERS on 1.2 paths | .github/, CODEOWNERS | Config test | 1 |
| SEC-63 | Nightly OWASP ZAP baseline and Schemathesis against an ephemeral stack | nightly workflow | Report archived | 6 |

### 3.9 Detection and response

| ID | MUST | Where | Acceptance test | Ph |
| --- | --- | --- | --- | --- |
| SEC-64 | Security events written as JSON to a separate stream with secrets and personal data scrubbed | core/logging.py | Scrub tests | 1 |
| SEC-65 | Seed the alert rules in section 7 | alerts/security\_rules.py | Rule trigger tests | 6, 10 |
| SEC-66 | Nightly canary: forbidden call returns 403, audit UPDATE fails, chain verifies, headers present, unsigned model refused, Redis-down returns 503 in staging | scripts/sec\_canary.py | Canary job result | 11 |
| SEC-67 | SECURITY\_FREEZE blocks approvals, optimisation, configuration, imports, simulation and the assistant; enable by one Admin, disable by two | core/freeze.py | Freeze tests | 10 |
| SEC-68 | Break-glass Admin: disabled by default, offline credentials, MFA, alert on use, rotated after use | runbooks | Drill record | 10, 11 |
| SEC-69 | Daily encrypted backups; monthly restore drill verifying audit chain, plan hashes, model hashes | scripts/backup.sh, restore\_verify.sh | Drill record | 11 |
| SEC-70 | Incident playbook (severity, contain, recover, review) published and rehearsed | docs/security/runbooks/incident.md | Tabletop record | 11 |

## 4. Dependency failure matrix

| Dependency down | Required behaviour |
| --- | --- |
| Redis | 503 on all authenticated routes except /health (SEC-72) |
| PostgreSQL | 503; actions and audit never separate (SEC-73) |
| MinIO | Reports, downloads, model loads and anchoring fail visibly (SEC-74) |
| Broker or locks | New jobs rejected (SEC-75); running jobs keep their state |
| MLflow or model hash failure | Predictions return engine\_unavailable; no fallback numbers |
| LLM gateway | Assistant shows a disabled state; the rest of the system continues |
| Clock state | Clock endpoints and as\_of-dependent writes fail; audit still uses wall clock |

## 5. Abuse-case tests

| # | Abuse case | Expected result | SEC |
| --- | --- | --- | --- |
| A1 | Planner or Analyst calls approve | 403 and audit entry | 07, 39 |
| A2 | Reviewer approves own request | 403 sod\_violation | 11 |
| A3 | Approve request replayed | Original result, no second effect | 18 |
| A4 | Approve after relevant data changed | 409 revalidation\_failed | 32 |
| A5 | UPDATE or DELETE on audit\_logs | Database error | 33, 34 |
| A6 | Forged, expired or wrong-algorithm token | 401 | 04 |
| A7 | Oversize, malformed, formula-laden or unsigned upload | Rejected or quarantined | 19, 71 |
| A8 | Unapproved dataset used for training | Refused | 40 |
| A9 | Tampered or unsigned model artefact | Load refused, alert | 41 |
| A10 | Injection text in event description or document | Instruction ignored, no tool misuse | 47 |
| A11 | Assistant asked to approve or configure | No such tool; refusal | 46 |
| A12 | Job flood | 429 or 409; limits hold | 17, 51, 75 |
| A13 | Clock set backwards | Refused | 37 |
| A14 | Demo reset outside DEMO\_MODE | Refused | 38 |
| A15 | Script payload in asset name or event text | Rendered inert | 23 |
| A16 | Formula payload in exported CSV | Neutralised | 20 |
| A17 | Dependency with a Critical vulnerability | CI fails | 60 |
| A18 | Secret in commit or log | CI fails or value scrubbed | 27, 64 |
| A19 | Unauthenticated or pickled queue message | Rejected | 56 |
| A20 | Out-of-bounds weight or constraint parameter | 422 validation\_error | 36 |
| A21 | Redis stopped | 503 everywhere, no bypass | 72 |
| A22 | Replayed or forged source manifest | manifest\_invalid | 71 |

## 6. Seeded security alert rules

| Rule | Condition | Severity |
| --- | --- | --- |
| Brute force | More than 10 failed logins in 10 minutes per account, or 50 per address | High |
| Refresh token reuse | Rotated token presented again | High |
| Permission denial spike | More than 20 denials per minute per user | Medium |
| Audit chain failure or missing anchor | Verification fails or nightly anchor absent | Critical or High |
| Model integrity failure | Hash mismatch or unsigned artefact | Critical |
| Clock changed | Any change; backwards change | Medium; High |
| Demo reset or role elevation | Any occurrence | High |
| Quota or lock abuse | Repeated job\_in\_progress or quota hits | Low to Medium |
| Assistant abuse | Spike in injection flags or scope refusals | Medium |
| Source rejected | manifest\_invalid or quarantine for attestation | Medium |
| Redis, database or MinIO unavailable | Dependency check fails | High |
| Blocked egress | Outbound attempt outside the allow-list | High |

## 7. Verification commands (create these Makefile targets in Phase 0)

| Target | Does |
| --- | --- |
| make sec-test | Runs pytest tests/security for requirements due up to the current phase |
| make sec-scan | Ruff security rules, Bandit, Semgrep, gitleaks, pip-audit, pnpm audit, Trivy, hadolint |
| make sec-registry-check | Fails if a requirement due in this or an earlier phase lacks a passing test in sec\_registry.yaml |
| make sec-canary | Runs scripts/sec\_canary.py against the running stack |
| make sec-nightly | ZAP baseline, Schemathesis, audit chain verification, anchor check |
| make sec-verify PHASE=n | Runs all of the above for phase n and writes docs/security/evidence/phase-n.md (SEC id, test, result, commit, time) |

## 8. Phase gates

A phase is complete only when make sec-verify PHASE=n passes with no failing or missing requirement up to n, no open Critical or High finding, and the manual checks below are recorded.

| Phase | Requirements due | Manual checks at the gate |
| --- | --- | --- |
| 0 | Registry and Makefile targets created; section 9 decisions recorded; contract additions in section 9 added to OpenAPI | CODEOWNERS active; all SEC ids present in sec\_registry.yaml |
| 1 | 01-07, 09, 13, 14, 16, 17, 22, 23, 24, 26, 27, 33-35, 37, 53-60, 62, 64, 72, 73 | docker compose config shows one published port; curl -I shows the header set; tampered token returns 401; stop Redis and confirm 503; direct UPDATE on audit\_logs fails |
| 2 | 15, 19, 25, 38, 40, 71 | Upload a forged manifest, a replayed manifest and a real-looking value; all rejected |
| 3 | 08 | Cross-user and cross-role attempts on every new endpoint |
| 4 | 17, 36, 51, 53, 75 | Flood the optimise endpoint; stop the broker |
| 5 | 10, 11, 18, 30-32, 34, 36, 39, 57, 74 | Attempt approval as each role; change data then approve; run two approvals at once; confirm the anchor object is locked |
| 6 | 39, 63, 65 | Trigger each alert rule; confirm the replan workflow cannot approve |
| 7 | 40-44, 74 | Edit one byte of a model file; confirm refusal and alert |
| 8 | 09, 39, 51, 52 | Simulator write attempt fails |
| 9 | 23, 39, 45-50 | Run the red-team set against the real model; attempt egress to an unlisted host |
| 10 | 12, 20, 21, 29, 36, 65, 67, 68 | Admin actions without step-up fail; freeze and unfreeze rehearsed |
| 11 | 26, 28, 45, 55, 61, 66, 68-70 and a full regression | Internal red team, rotation drill, restore drill, canary green for 7 nights |

## 9. Contract additions and open decisions

**Add in Phase 0 (OpenAPI, migrations, configuration):**

- Endpoints: POST /auth/mfa/enroll, POST /auth/mfa/verify, POST /auth/step-up, POST /system/security-freeze, GET /audit-logs/verify, GET /security/events, POST and GET /system/source-keys.
- Tables: user\_mfa, auth\_sessions, security\_events, audit\_anchors, model\_signatures, upload\_quarantine, data\_source\_keys, manifest\_nonces.
- Fields: plan\_versions.content\_hash, approval\_records.plan\_hash, audit\_logs.recorded\_at, model\_versions.artefact\_sha256 and signature, data\_sources.attestation.
- Configuration: DEMO\_MODE, SECURITY\_FREEZE, REDIS\_FAIL\_MODE, STEPUP\_TTL\_SECONDS, EGRESS\_ALLOWLIST, retention settings.

**Defaults the agent uses until the owner decides:**

| Decision | Default |
| --- | --- |
| MFA | Required for Reviewer and Admin outside DEMO\_MODE |
| Step-up on approval | Yes |
| Two-person rule for model promotion and constraint activation | Off |
| Recovery targets and backups | RPO 24 hours, RTO 4 hours, 30-day retention (proposed, owner to confirm) |
| Retention | Security logs 90 days, audit permanent, assistant message text not stored |
| LLM | Hosted through the gateway; self-hosted option kept |
| Hosting | Docker Compose on one hardened host |

## 10. Limits

- Passing tests prove the listed controls work, not that the system is secure. Unknown dependency flaws, misconfiguration, a malicious insider and prompt injection through free text remain residual risks; the red team and nightly scans exist to find them.
- Not covered, and needed before any real use: security categorisation under the owning organisation's policy, privacy impact assessment, accreditation, hardware-backed key management, single sign-on, SIEM and monitored operations, external penetration test, formal disaster recovery, and assurance of models and libraries on real data.
- Reference checklists (OWASP ASVS Level 2, API Top 10, LLM Top 10, NIST SSDF, MITRE ATLAS, CIS benchmarks) guide the design; the project claims no certification.
