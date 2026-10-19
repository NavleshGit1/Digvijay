# ADR 0002: Celery and Redis over Apache Kafka

- **Status:** Accepted
- **Date:** 2026-10-19
- **Deciders:** Platform & Architecture Team (Stream A, E)

---

## Context and Problem Statement
Long-running background tasks (CP-SAT solver execution, ML training/inference, SimPy Monte Carlo simulations, PDF report generation, and data ingestion) require asynchronous execution, progress tracking, and job cancellation.
Does the synthetic prototype justify an Apache Kafka event streaming cluster, or is Celery with Redis sufficient?

## Considered Options
1. **Apache Kafka + Kafka Connect + Custom Consumers**
2. **Celery 5 + Redis 7 Broker + Celery Beat**

## Decision Outcome
Chosen option: **Celery 5 + Redis 7** (Option 2).

### Rationale
- **Synthetic Prototype Throughput:** Event volumes in this decision-support prototype (hundreds of tasks, tens of disruption events per minute) are well within the capabilities of Redis and Celery.
- **Job State & Progress Semantics:** Celery natively supports task state machines (`QUEUED`, `RUNNING`, `SUCCESS`, `FAILURE`, `CANCELLED`), task revocation, soft/hard time limits, and progress reporting via Redis keys streamed directly over Server-Sent Events (SSE).
- **Lightweight Infrastructure:** Kafka introduces ZooKeeper/KRaft, JVM resource footprints, partition rebalancing complexity, and multi-broker configuration which impairs rapid developer iteration and single-command Docker Compose bring-up.

### Mitigation
- Background queues are segregated by priority: `optimise` (CP-SAT), `ml` (training/serving), `simulate` (Monte Carlo), `report` (PDF/CSV), `ingest` (fusion), and `default` (alerts/heartbeats).
