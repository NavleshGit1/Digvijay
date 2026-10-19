# AirOps Nexus — Data Dictionary & Entity Relationship Specification

**Status:** Approved Specification (Phase 0, Task P0-2 & P0-11)  
**Version:** 1.1 (Comprehensive Baseline including Section 26 Extensions)  
**Database Engine:** PostgreSQL 16 with `pgvector`

---

## 1. Schema Conventions & System Rules

1. **Primary Keys:** UUID v4 (`UUID`) across all primary and foreign key references.
2. **Timestamps:** ISO 8601 UTC timestamps (`TIMESTAMPTZ`), stored in UTC.
3. **Synthetic Data Flag:** Every domain row carries `is_synthetic: BOOLEAN DEFAULT TRUE`.
4. **Audit & Metadata:** Domain entities include `created_at`, `updated_at`, `version: INT DEFAULT 1`, and nullable `source_record_id`.
5. **Provenance:** Ingested entities track `source_id`, `source_record_id`, `ingestion_time`, `source_update_time`, and `validation_status`.
6. **Immutable Snapshots:** Plan versions, audit logs, and benchmark runs are immutable once committed.
7. **Time Standard:** The `as_of: TIMESTAMPTZ` field is mandatory on generated outputs, predictions, simulations, and benchmark runs.

---

## 2. Shared Enums Registry

| Enum Type | Allowed Values | Description |
| :--- | :--- | :--- |
| `UserRole` | `planner`, `reviewer`, `analyst`, `admin` | User authorization roles |
| `AssetStatus` | `available`, `in_use`, `maintenance`, `grounded`, `transit` | Operational state of equipment/airframe |
| `PersonnelStatus` | `available`, `on_duty`, `rest_period`, `leave`, `training` | Crew operational readiness |
| `TaskStatus` | `pending`, `scheduled`, `in_progress`, `completed`, `cancelled`, `blocked` | Lifecycle state of a work assignment |
| `TaskPriority` | `low`, `routine`, `high`, `critical`, `flash` | Operational importance for scheduling |
| `PlanKind` | `baseline`, `optimised`, `replan`, `fallback`, `rollback`, `alternative` | Generation intent of the schedule |
| `PlanStatus` | `proposed`, `stale`, `approved`, `rejected`, `superseded`, `invalid`, `withdrawn` | Plan lifecycle state machine |
| `PlanSource` | `cpsat`, `heuristic_fallback`, `rollback`, `manual` | Generating engine or origin |
| `SolverStatus` | `optimal`, `feasible`, `infeasible`, `timeout`, `unknown`, `error` | Transparent CP-SAT solver status |
| `ValidationStatus`| `passed`, `failed`, `needs_review`, `unvalidated` | Independent validator outcome |
| `DataKind` | `observed`, `predicted`, `simulated`, `generated`, `synthetic`, `demo` | Data provenance display envelope |
| `SeverityLevel` | `informational`, `low`, `medium`, `high`, `critical` | Event, alert, and anomaly severity |
| `AlertStatus` | `new`, `acknowledged`, `resolved`, `suppressed` | Operational alert lifecycle |
| `JobState` | `queued`, `running`, `completed`, `failed`, `cancelled` | Async background job lifecycle |
| `EventType` | `asset_unavailability`, `maintenance_delay`, `capacity_reduction`, `stale_data`, `environmental_restriction`, `task_progress`, `resupply_delay` | Ingested disruption types |

---

## 3. Entity Catalog

### 3.1 Identity & Access Control
- **`users`**: User identity, password hash (`argon2id`), active status, last login.
- **`roles`**: System role definitions (`name`, `description`).
- **`user_roles`**: Many-to-many relationship mapping users to roles.

### 3.2 Sources, Provenance & Clock
- **`system_clock_state`**: Single-row virtual clock tracking `mode` (`system`, `fixed`, `simulated`), `current_as_of`, `time_scale`, `last_updated_at`.
- **`data_sources`**: External connector registrations (`name`, `adapter_type`, `expected_interval_seconds`, `is_active`).
- **`ingestion_runs`**: Ingestion batches (`source_id`, `records_processed`, `records_failed`, `as_of`, `content_hash`).
- **`source_records`**: Immutable raw landing payloads (`payload_json`, `source_id`, `ingested_at`).
- **`dataset_versions`**: Seeded synthetic dataset snapshots (`version_tag`, `generator_version`, `seed`, `as_of`, `content_hash`).
- **`data_source_freshness`**: Heartbeat and SLA compliance (`source_id`, `last_successful_sync`, `is_stale`).

### 3.3 Resources & Base Facilities
- **`assets`**: Equipment/aircraft (`identifier`, `type`, `status`, `health_score_recorded`, `zone_id`, `current_location`).
- **`personnel`**: Crew and technicians (`name`, `callsign`, `status`, `duty_hours_accumulated`, `home_zone_id`).
- **`qualifications`**: Skill and certification definitions (`code`, `name`, `validity_days`).
- **`personnel_qualifications`**: M2M certifications with expiration dates (`personnel_id`, `qualification_id`, `expires_at`).
- **`zones`**: Fictional sectors, airfields, and bays (`name`, `code`, `capacity_limit`, `coordinates_geojson`).
- **`resource_inventory`**: Base supplies (`item_code`, `zone_id`, `quantity_on_hand`, `reorder_threshold`).

### 3.4 Logistics, Usage & Spares Management (v1.1)
- **`asset_usage_counters`**: Accumulated wear metrics (`asset_id`, `counter_type` [flight_hours, cycles, calendar_days], `value`, `as_of`).
- **`maintenance_rules`**: Service triggers (`category`, `trigger_type`, `threshold`, `tolerance`, `estimated_duration_hours`, `required_parts`).
- **`maintenance_due`**: Derived due list (`asset_id`, `rule_id`, `due_at`, `deadline_at`, `status`).
- **`parts_catalog`**: Detailed component definitions (`part_number`, `name`, `category`, `unit_cost`).
- **`spares_inventory`**: Zone-level inventory (`part_id`, `zone_id`, `on_hand`, `reserved`, `minimum_safety_level`).
- **`maintenance_part_requirements`**: Parts needed per maintenance rule (`rule_id`, `part_id`, `quantity_required`).
- **`spares_movements`**: Inventory ledger (`part_id`, `zone_id`, `quantity_change`, `movement_type` [consumption, receipt, transfer], `reference_id`).
- **`resupply_orders`**: Logistics pipeline (`part_id`, `zone_id`, `quantity`, `ordered_at`, `estimated_arrival`, `status`).

### 3.5 Tasks & Operations Work
- **`tasks`**: Operational work items (`code`, `category`, `zone_id`, `earliest_start`, `latest_end`, `duration_minutes`, `priority`, `weight`).
- **`task_requirements`**: Resource requirements (`task_id`, `asset_type_required`, `crew_headcount`, `required_qualifications`).
- **`task_dependencies`**: Precedence graph (`predecessor_id`, `successor_id`, `min_lag_minutes`).
- **`task_executions`**: Realized execution records (`task_id`, `plan_version_id`, `assignment_id`, `actual_start`, `actual_end`, `delay_minutes`, `locked`).
- **`maintenance_records`**: Work orders (`asset_id`, `category`, `start_time`, `end_time`, `predicted_completion`, `is_unplanned`).

### 3.6 Plans, Constraints & Governance
- **`constraint_definitions`**: Parameterized constraint rules (`code`, `name`, `is_hard`, `parameter_schema`, `default_value`).
- **`constraint_sets`**: Versioned groupings of constraints (`version`, `status` [draft, active, archived], `created_by`, `activated_at`).
- **`objective_weight_sets`**: Integer weights for CP-SAT objective terms (`version`, `delay_weight`, `completion_weight`, `churn_weight`, `balance_weight`, `buffer_weight`).
- **`plans`**: Logical schedule entity (`name`, `current_approved_version_id`).
- **`plan_versions`**: Immutable schedules (`plan_id`, `version_number`, `kind`, `status`, `based_on_version`, `snapshot_hash`, `constraint_set_version`, `weight_set_version`, `solver_status`, `plan_source`, `as_of`).
- **`plan_assignments`**: Specific resource allocations (`plan_version_id`, `task_id`, `asset_id`, `personnel_ids`, `assigned_start`, `assigned_end`).
- **`plan_validations`**: Independent validation results (`plan_version_id`, `is_valid`, `violations_json`, `binding_constraints_json`).
- **`plan_diffs`**: Precomputed differences between plans (`base_version_id`, `target_version_id`, `added_tasks`, `removed_tasks`, `moved_tasks`, `churn_metric`).
- **`approval_records`**: Governance sign-offs (`plan_version_id`, `reviewer_id`, `action` [approved, rejected], `reason`, `snapshot_hash`, `timestamp`).

### 3.7 Events, Alerts & Quality
- **`events`**: Ingested disruptions (`idempotency_key`, `event_type`, `source`, `affected_entity_type`, `affected_entity_id`, `severity`, `payload_json`, `timestamp`).
- **`alerts`**: Live system alerts (`rule_id`, `entity_type`, `entity_id`, `severity`, `status`, `first_seen`, `last_seen`, `count`, `dedup_key`, `acknowledged_by`, `resolved_by`).
- **`alert_rules`**: Monitoring thresholds (`name`, `condition_type`, `threshold_value`, `hysteresis_value`, `dedup_window_minutes`, `severity`, `is_enabled`).
- **`data_quality_issues`**: Integrity and reconciliation conflicts (`source_id`, `entity_type`, `issue_class` [integrity_error, conflict, stale], `description`, `status`).

### 3.8 Machine Learning & Digital Twin
- **`models`**: ML model catalogue (`name`, `domain` [downtime, delay, disruption, demand], `target_variable`).
- **`model_versions`**: Model iterations (`model_id`, `mlflow_run_id`, `version_tag`, `status` [candidate, champion, archived], `metrics_json`).
- **`predictions`**: Stored inferences (`model_version_id`, `entity_id`, `input_features_hash`, `predicted_value`, `interval_lower`, `interval_upper`, `as_of`, `data_kind`).
- **`anomaly_findings`**: Unsupervised anomaly scores (`model_version_id`, `entity_id`, `anomaly_score`, `contributing_features_json`, `review_status`).
- **`drift_reports`**: Data and concept drift evaluations (`model_id`, `test_type` [PSI, KS], `metric_value`, `threshold`, `drift_detected`).
- **`simulation_scenarios`**: Digital twin scenario setups (`name`, `preset_type`, `config_json`, `seed`).
- **`simulation_runs`**: Executed simulation batches (`scenario_id`, `plan_version_id`, `run_count`, `seed_sequence_manifest`, `summary_statistics_json`).
- **`simulation_run_trials`**: Individual Monte Carlo trial records (`simulation_run_id`, `trial_index`, `child_seed`, `total_delay`, `completed_tasks`, `infeasible_flag`).
- **`benchmark_runs`**: Evaluation runs comparing strategies (`scenario_id`, `strategy` [right_shift, heuristic, cpsat], `metrics_json`, `as_of`).

### 3.9 Audit Trail
- **`audit_logs`**: Append-only tamper-evident ledger:
  - `id`: UUID primary key
  - `actor_id`: User identifier
  - `role`: Role at time of action
  - `action`: Protected action code (`APPROVE_PLAN`, `SEED_DATA`, `UPDATE_CONFIG`, etc.)
  - `entity_type`, `entity_id`: Target of action
  - `before_state_json`, `after_state_json`: Delta states
  - `plan_version_id`: Associated plan if applicable
  - `reason`: Mandatory text justification
  - `request_id`: Tracing identifier
  - `timestamp`: UTC timestamp
  - `previous_hash`: SHA-256 hash of previous audit row
  - `record_hash`: SHA-256 hash of this row including `previous_hash` (immutable hash chain).

---

## 4. Server-Side KPI Mathematical Formulations

| KPI Identifier | Formal Mathematical Definition | Inputs / Tables |
| :--- | :--- | :--- |
| **`kpi_asset_availability`** | $\frac{\sum \mathbb{I}(\text{status} = \text{'available'} \land \text{no active maintenance})}{\text{total active assets}}$ | `assets`, `maintenance_records` |
| **`kpi_serviceability`** | $\frac{\sum \mathbb{I}(\text{status} = \text{'available'} \land \text{recorded\_health} \ge \tau_{\text{ready}})}{\text{total active assets}}$ | `assets`, `system_config` |
| **`kpi_eligible_tasks`** | Tasks $T_i$ where $\text{status} \notin \{\text{cancelled}, \text{completed}\} \land \text{start}(T_i) \in [t_{\text{now}}, t_{\text{now}} + H] \land \exists \text{compatible asset} \land \exists \text{qualified crew}$ | `tasks`, `task_requirements`, `assets`, `personnel` |
| **`kpi_tasks_scheduled`** | $\frac{\text{Eligible Tasks Assigned in Active Approved Plan}}{\text{Total Eligible Tasks}}$ | `tasks`, `plan_assignments`, `plans` |
| **`kpi_maintenance_workload`**| $\frac{\sum \text{Planned Maintenance Duration in Window}}{\sum \text{Available Maintenance Technician Hours in Window}}$ | `maintenance_records`, `personnel` |
| **`kpi_overdue_maintenance`** | $\sum \mathbb{I}(\text{status} \ne \text{'completed'} \land \text{planned\_end} < t_{\text{as\_of}})$ | `maintenance_records`, `system_clock_state` |
| **`kpi_crew_availability`** | $\frac{\sum \text{Qualified On-Duty Personnel}}{\sum \text{Crew Headcount Demanded by Scheduled Tasks}}$ | `personnel`, `task_requirements`, `plan_assignments` |
| **`kpi_total_delay`** | $\sum_{T_i \in \text{Scheduled}} \max(0, \text{assigned\_end}(T_i) - \text{due\_date}(T_i))$ | `tasks`, `plan_assignments` |
| **`kpi_plan_churn`** | $\frac{\sum \mathbb{I}(\text{asset}(A_{\text{new}}) \ne \text{asset}(A_{\text{base}}) \lor |\text{start}_{\text{new}} - \text{start}_{\text{base}}| > \tau_{\text{tol}})}{\text{Total Assignments in Base Plan}}$ | `plan_assignments`, `plan_diffs` |
| **`kpi_spares_shortage`** | $\sum \mathbb{I}(\text{on\_hand} < \text{minimum\_safety\_level})$ | `spares_inventory` |
