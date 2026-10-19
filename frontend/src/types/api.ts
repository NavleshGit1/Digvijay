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
