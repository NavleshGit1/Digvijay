export type UserRole = "planner" | "reviewer" | "analyst" | "admin";

export type AssetStatus = "available" | "in_use" | "maintenance" | "grounded" | "transit";

export type TaskStatus = "pending" | "scheduled" | "in_progress" | "completed" | "cancelled" | "blocked";

export type PlanKind = "baseline" | "optimised" | "replan" | "fallback" | "rollback" | "alternative";

export type PlanStatus = "proposed" | "stale" | "approved" | "rejected" | "superseded" | "invalid" | "withdrawn";

export type PlanSource = "cpsat" | "heuristic_fallback" | "rollback" | "manual";

export type SolverStatus = "optimal" | "feasible" | "infeasible" | "timeout" | "unknown" | "error";

export type DataKind = "observed" | "predicted" | "simulated" | "generated" | "synthetic" | "demo";

export type SeverityLevel = "informational" | "low" | "medium" | "high" | "critical";

export type AlertStatus = "new" | "acknowledged" | "resolved" | "suppressed";

export type JobState = "queued" | "running" | "completed" | "failed" | "cancelled";

export type ClockMode = "system" | "fixed" | "simulated";

export interface DataKindEnvelope<T = any> {
  value: T;
  data_kind: DataKind;
  as_of: string;
  model_version?: string;
  confidence_interval?: [number, number];
}

export interface ClockState {
  mode: ClockMode;
  current_as_of: string;
  time_scale: number;
}

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  roles: UserRole[];
}

export interface OverviewKPIs {
  asset_availability: DataKindEnvelope<number>;
  serviceability: DataKindEnvelope<number>;
  eligible_tasks: number;
  tasks_scheduled: number;
  maintenance_workload: DataKindEnvelope<number>;
  overdue_maintenance: number;
  crew_availability: DataKindEnvelope<number>;
  total_delay: number;
  spares_shortage: number;
  as_of: string;
}

export interface JobProgress {
  job_id: string;
  state: JobState;
  progress_percent: number;
  message: string;
}

export interface Zone {
  id: string;
  name: string;
  code: string;
  capacity_limit: number;
  coordinates_geojson?: {
    type: string;
    coordinates: [number, number];
  };
}

export interface Asset {
  id: string;
  identifier: string;
  asset_type: string;
  model_name: string;
  status: AssetStatus;
  health_score: number;
  zone_id: string;
  zone_code: string;
  zone_name: string;
  current_location?: string;
  flight_hours: number;
  cycles: number;
  has_active_maintenance: boolean;
}

export interface AssetDetail extends Asset {
  recent_maintenance: MaintenanceRecord[];
  usage_summary: {
    flight_hours_since_last_service: number;
    cycles_since_last_service: number;
    next_scheduled_inspection: string;
  };
}

export interface PersonnelQualification {
  qualification_code: string;
  qualification_name: string;
  acquired_at: string;
  expires_at: string;
  is_expired: boolean;
}

export interface Personnel {
  id: string;
  name: string;
  callsign?: string;
  role_type: string;
  status: string;
  duty_hours_accumulated: number;
  home_zone_id: string;
  home_zone_name: string;
  qualifications: string[];
}

export interface PersonnelDetail extends Personnel {
  qualification_details: PersonnelQualification[];
}

export interface TaskRequirement {
  asset_type_required: string;
  crew_headcount: number;
  required_qualification_code?: string;
}

export interface Task {
  id: string;
  code: string;
  category: string;
  zone_id: string;
  zone_name: string;
  earliest_start: string;
  latest_end: string;
  duration_minutes: number;
  priority: string;
  weight: number;
  status: TaskStatus;
  requirements: TaskRequirement[];
}

export interface SparesInventory {
  id: string;
  part_id: string;
  part_number: string;
  part_name: string;
  category: string;
  zone_id: string;
  zone_name: string;
  on_hand: number;
  reserved: number;
  minimum_safety_level: number;
  is_shortage: boolean;
}

export interface MaintenanceRecord {
  id: string;
  asset_id: string;
  asset_identifier: string;
  category: string;
  start_time: string;
  end_time: string;
  predicted_completion?: string;
  is_unplanned: boolean;
  status: string;
  is_overdue: boolean;
}

export interface SearchResultItem {
  category: "asset" | "personnel" | "task" | "spare";
  id: string;
  title: string;
  subtitle: string;
  badge: string;
  url: string;
}

export interface SearchResponse {
  query: string;
  total: number;
  results: SearchResultItem[];
}

export interface OperationalEvent {
  id: string;
  idempotency_key: string;
  event_type: string;
  source: string;
  affected_entity_type: string;
  affected_entity_id: string;
  severity: SeverityLevel;
  payload_json: Record<string, any>;
  timestamp: string;
}

export interface PlanSummary {
  id: string;
  name: string;
  current_approved_version_id: string | null;
  current_approved_version?: number | null;
  versions_count: number;
  latest_version: number;
  latest_solver_status: SolverStatus | null;
  latest_kind?: PlanKind | null;
  latest_status?: PlanStatus | null;
  versions?: Array<{
    version_number: number;
    kind: PlanKind;
    status: PlanStatus;
    solver_status: SolverStatus;
    plan_source: PlanSource;
    based_on_version?: number | null;
    stale_reason?: string | null;
    refreshed_from?: number | null;
    rollback_target?: number | null;
    metrics?: Record<string, any>;
    runtime_seconds?: number | null;
    created_at: string;
  }>;
  created_at: string;
}

export interface PlanAssignmentItem {
  id: string;
  task_id: string;
  task_code: string;
  task_category: string;
  priority: string;
  asset_id: string | null;
  asset_identifier: string;
  asset_model: string | null;
  personnel_ids: string[];
  assigned_start: string;
  assigned_end: string;
  duration_minutes: number;
  delay_minutes: number;
  is_locked: boolean;
}

export interface PlanValidationReport {
  is_valid: boolean;
  violation_count: number;
  violations: Array<{
    constraint_code: string;
    message: string;
    entity_type: string;
    entity_id: string;
    conflicting_task_id?: string;
    details?: Record<string, any>;
  }>;
  binding_constraints: Array<{
    constraint_code: string;
    entity_type: string;
    entity_id: string;
    slack_minutes: number;
    description: string;
  }>;
  validated_at: string | null;
}

export interface PlanVersionDetail {
  plan_id: string;
  version_number: number;
  kind: PlanKind;
  status: PlanStatus;
  solver_status: SolverStatus;
  plan_source: PlanSource;
  based_on_version?: number | null;
  stale_reason?: string | null;
  refreshed_from?: number | null;
  rollback_target?: number | null;
  proposal_group_id?: string | null;
  rejection_reason?: string | null;
  created_by?: string | null;
  as_of: string;
  snapshot_hash: string;
  runtime_seconds: number;
  metrics: {
    total_horizon_tasks?: number;
    scheduled_count?: number;
    unassigned_count?: number;
    total_delay_minutes?: number;
    completion_rate?: number;
    objective_value?: number;
    best_bound?: number;
    churn?: ReplanChurnMetrics;
    disruption_reason?: string;
    frozen_window_minutes?: number;
    [key: string]: any;
  };
  manifest: Record<string, any>;
  validation: PlanValidationReport;
  assignments_count: number;
  assignments: PlanAssignmentItem[];
}

export interface ApprovalRecordItem {
  id: string;
  plan_id: string;
  plan_version_id: string;
  reviewer_id: string;
  reviewer_username: string;
  decision: "approved" | "rejected";
  reason: string;
  idempotency_key?: string | null;
  created_at: string;
}

export interface PlanDiffAssignmentItem {
  task_id: string;
  task_code: string;
  category: string;
  change_type: "added" | "removed" | "shifted" | "unchanged";
  assigned_start?: string;
  assigned_end?: string;
  old_start?: string;
  new_start?: string;
  start_delta_minutes?: number;
  old_end?: string;
  new_end?: string;
  end_delta_minutes?: number;
  asset_id?: string | null;
  asset_identifier?: string | null;
  old_asset_id?: string | null;
  old_asset_identifier?: string | null;
  new_asset_id?: string | null;
  new_asset_identifier?: string | null;
  asset_changed?: boolean;
  crew_changed?: boolean;
  personnel_ids?: string[];
}

export interface PlanDiffResponse {
  from_version: number | null;
  from_kind?: PlanKind | null;
  from_status?: PlanStatus | null;
  to_version: number;
  to_kind: PlanKind;
  to_status: PlanStatus;
  summary: {
    added_count: number;
    removed_count: number;
    shifted_count: number;
    unchanged_count: number;
    total_assignments_new: number;
    total_assignments_old: number;
    churn_count: number;
  };
  metrics_diff: {
    delay_minutes_delta: number;
    completion_count_delta: number;
    runtime_seconds_delta: number;
    new_total_delay_minutes: number;
    old_total_delay_minutes: number;
  };
  added_assignments: PlanDiffAssignmentItem[];
  removed_assignments: PlanDiffAssignmentItem[];
  shifted_assignments: PlanDiffAssignmentItem[];
  unchanged_assignments: PlanDiffAssignmentItem[];
}

export interface StalenessCheckResponse {
  plan_id: string;
  version_number: number;
  is_stale: boolean;
  status: PlanStatus;
  reason: string | null;
  hard_conflict: boolean;
  violation_count?: number;
  violations?: any[];
}

export interface ConstraintSetItem {
  id: string;
  version: string;
  name: string;
  status: "draft" | "active" | "archived";
  parameters: Record<string, any>;
  created_by?: string | null;
  created_at: string;
}


export interface GanttBlock {
  id: string;
  type: "task" | "maintenance" | "sortie";
  code: string;
  category: string;
  priority?: string;
  start: string;
  end: string;
  duration_minutes?: number;
}

export interface GanttTrack {
  asset_id?: string;
  identifier?: string;
  model_name?: string;
  asset_type?: string;
  status?: string;
  personnel_id?: string;
  name?: string;
  callsign?: string;
  role_type?: string;
  blocks: GanttBlock[];
}

export interface GanttTimelineResponse {
  plan_id: string;
  version_number: number;
  as_of: string;
  asset_tracks: GanttTrack[];
  crew_tracks: GanttTrack[];
}

export interface ObjectiveWeightSet {
  id: string;
  version: number;
  name: string;
  delay_weight: number;
  completion_weight: number;
  churn_weight: number;
  balance_weight: number;
  buffer_weight: number;
  is_active: boolean;
  created_by?: string;
  created_at: string;
}

export interface AlertItem {
  id: string;
  rule_code: string;
  title: string;
  message: string;
  severity: SeverityLevel;
  status: AlertStatus;
  dedup_key: string;
  entity_type: string;
  entity_id: string;
  payload_json: Record<string, any>;
  count: number;
  first_seen: string;
  last_seen: string;
  acknowledged_by?: string | null;
  acknowledged_at?: string | null;
  resolved_by?: string | null;
  resolved_at?: string | null;
}

export interface AlertSummary {
  total_active: number;
  new_count: number;
  acknowledged_count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
}

export interface DisruptionAffectedTask {
  task_id: string;
  code: string;
  title: string;
  category: string;
  assigned_start: string;
  assigned_end: string;
  overlap_minutes?: number;
  ripple_depth?: number;
  crew_ids?: string[];
  conflict_reason?: string;
}

export interface DisruptionImpactResponse {
  record_id: string;
  asset_id: string;
  asset_identifier: string;
  delay_minutes: number;
  extended_scheduled_end: string;
  directly_affected_count: number;
  cascading_affected_count: number;
  crew_conflicts_count: number;
  plan_invalidated: boolean;
  affected_tasks: DisruptionAffectedTask[];
}

export interface ReplanChurnMetrics {
  tasks_shifted: number;
  total_shift_minutes: number;
  assets_reassigned: number;
  frozen_tasks_preserved: number;
  total_scheduled: number;
  churn_index: number;
}

