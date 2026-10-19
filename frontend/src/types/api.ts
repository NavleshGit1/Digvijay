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
