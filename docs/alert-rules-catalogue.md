# AirOps Nexus — Alert Rules Catalogue & Lifecycle Specification

**Status:** Approved Specification (Phase 0, Task P0-13 & Amendment v1.1)  
**Version:** 1.0  
**References:** Architecture Section 26.7

---

## 1. Alert Architecture & Lifecycle

Alerts represent actionable operational conditions evaluated by a periodic Celery Beat background job (default: 60-second evaluation loop) and event-driven triggers.

```
[System Condition] ──► [Evaluate Alert Rule] ──► [Deduplication & Hysteresis]
                                                            │
                                                     ┌──────▼──────┐
                                                     │ STATUS: NEW │
                                                     └──────┬──────┘
                                          Acknowledge Action│
                                                     ┌──────▼──────────┐
                                                     │  ACKNOWLEDGED   │
                                                     └──────┬──────────┘
                                        Condition Cleared / │ Resolve Action
                                                     ┌──────▼──────────┐
                                                     │    RESOLVED     │
                                                     └─────────────────┘
```

---

## 2. Seeded Alert Rules Catalogue

| Rule Code | Alert Name | Severity | Condition Threshold | Hysteresis / Clear Rule | Scope |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `ALERT_AVAIL_CRITICAL` | Asset Availability Below Threshold | `critical` | Fleet availability $< 60\%$ | Clears when availability $\ge 65\%$ | Global |
| `ALERT_CREW_SHORTAGE` | Crew Availability Deficit | `high` | Scheduled crew demand $>$ available crew | Clears when crew demand $\le$ availability | Zone |
| `ALERT_MAINT_OVERDUE` | Overdue Asset Maintenance | `high` | Planned maintenance end $< t_{\text{as\_of}}$ | Clears when work order status is `completed` | Asset |
| `ALERT_USAGE_LIMIT` | Asset Usage Exceeds Threshold | `medium` | Accumulated flight hours $\ge 90\%$ of service limit | Clears upon resetting maintenance overhaul | Asset |
| `ALERT_SPARES_STOCKOUT` | Critical Spare Parts Shortage | `high` | Part inventory on hand $<$ safety stock level | Clears when on-hand inventory $\ge$ safety level | Part/Zone |
| `ALERT_RESUPPLY_DELAY` | Late Resupply Delivery | `medium` | Resupply order ETA $< t_{\text{as\_of}}$ and not received | Clears when order arrives | Logistics |
| `ALERT_PROPOSAL_STALE` | Pending Proposal Outdated | `medium` | Underlying asset/task data updated since proposal build | Clears when proposal refreshed or withdrawn | Plan |
| `ALERT_SOLVER_TIMEOUT` | Optimisation Solver Timeout | `medium` | CP-SAT job hit time limit without optimal proof | Informational acknowledgment | Job |
| `ALERT_MODEL_DRIFT` | Predictive Model Drift Detected | `high` | Population Stability Index (PSI) $> 0.25$ or KS test $p < 0.01$ | Clears upon champion model retraining/promotion | ML |
| `ALERT_DATA_QUALITY` | High-Severity Anomaly Detected | `critical` | Unsupervised anomaly score $> 0.85$ or integrity error | Clears upon Analyst review | Quality |

---

## 3. Anti-Flapping & Deduplication Rules
1. **Deduplication Key (`dedup_key`):** Formed by hashing `(rule_code, entity_type, entity_id)`.
2. **Deduplication Window:** An active alert matching an existing `dedup_key` within a 15-minute window increments the occurrence `count` and updates `last_seen` rather than creating a duplicate notification.
3. **Hysteresis Buffer:** Quantitative threshold rules require values to recover beyond a delta buffer before triggering automatic resolution, preventing notification noise.
