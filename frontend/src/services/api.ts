import {
  Asset,
  AssetDetail,
  ClockState,
  MaintenanceRecord,
  OperationalEvent,
  OverviewKPIs,
  Personnel,
  PersonnelDetail,
  SearchResponse,
  SparesInventory,
  Task,
  UserProfile,
  Zone,
  PlanSummary,
  PlanVersionDetail,
  GanttTimelineResponse,
  ObjectiveWeightSet,
} from "../types/api";

const API_BASE = "/api/v1";

class ApiClient {
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem("airops_access_token");
  }

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem("airops_access_token", token);
    } else {
      localStorage.removeItem("airops_access_token");
    }
  }

  getToken(): string | null {
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const errorJson = await response.json().catch(() => ({}));
      throw {
        status: response.status,
        detail: errorJson.detail || "An unexpected error occurred",
        code: errorJson.code || "unknown_error",
        title: errorJson.title || "Request Failed",
      };
    }

    return response.json();
  }

  // Auth endpoints
  async login(username: string, password: string): Promise<{ access_token: string; roles: string[] }> {
    const res = await this.request<{ access_token: string; roles: string[] }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    this.setToken(res.access_token);
    return res;
  }

  async logout(): Promise<void> {
    try {
      await this.request("/auth/logout", { method: "POST" });
    } finally {
      this.setToken(null);
    }
  }

  async getMe(): Promise<UserProfile> {
    return this.request<UserProfile>("/auth/me");
  }

  // System endpoints
  async getClock(): Promise<ClockState> {
    return this.request<ClockState>("/system/clock");
  }

  async updateClock(params: Partial<ClockState>): Promise<ClockState> {
    return this.request<ClockState>("/system/clock", {
      method: "PUT",
      body: JSON.stringify(params),
    });
  }

  async getHealth(): Promise<any> {
    return this.request("/system/health");
  }

  // Overview endpoint
  async getOverview(as_of?: string): Promise<OverviewKPIs> {
    const query = as_of ? `?as_of=${encodeURIComponent(as_of)}` : "";
    return this.request<OverviewKPIs>(`/overview${query}`);
  }

  // Jobs endpoint
  async createJob(job_type: string, duration_seconds: number = 5): Promise<any> {
    return this.request("/jobs", {
      method: "POST",
      body: JSON.stringify({ job_type, duration_seconds }),
    });
  }

  async getJobs(): Promise<any[]> {
    return this.request("/jobs");
  }

  // Zones & Resources
  async getZones(): Promise<Zone[]> {
    return this.request<Zone[]>("/zones");
  }

  async getAssets(params?: Record<string, any>): Promise<Asset[]> {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<Asset[]>(`/assets${qs}`);
  }

  async getAssetDetail(assetId: string): Promise<AssetDetail> {
    return this.request<AssetDetail>(`/assets/${assetId}`);
  }

  async updateAsset(
    assetId: string,
    data: { status?: string; current_location?: string; zone_id?: string; health_score?: number; reason: string }
  ): Promise<Asset> {
    return this.request<Asset>(`/assets/${assetId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async getPersonnel(params?: Record<string, any>): Promise<Personnel[]> {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<Personnel[]>(`/personnel${qs}`);
  }

  async getPersonnelDetail(personnelId: string): Promise<PersonnelDetail> {
    return this.request<PersonnelDetail>(`/personnel/${personnelId}`);
  }

  async updatePersonnel(
    personnelId: string,
    data: { status?: string; duty_hours_accumulated?: number; home_zone_id?: string; reason: string }
  ): Promise<Personnel> {
    return this.request<Personnel>(`/personnel/${personnelId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async getTasks(params?: Record<string, any>): Promise<Task[]> {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<Task[]>(`/tasks${qs}`);
  }

  async getTaskDetail(taskId: string): Promise<any> {
    return this.request<any>(`/tasks/${taskId}`);
  }

  async updateTask(taskId: string, data: { status?: string; reason: string }): Promise<Task> {
    return this.request<Task>(`/tasks/${taskId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async getSpares(params?: Record<string, any>): Promise<SparesInventory[]> {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<SparesInventory[]>(`/inventory/spares${qs}`);
  }

  async orderSpares(data: { part_id: string; zone_id: string; quantity: number; reason: string }): Promise<any> {
    return this.request("/inventory/orders", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async getMaintenanceRecords(params?: Record<string, any>): Promise<MaintenanceRecord[]> {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<MaintenanceRecord[]>(`/maintenance/records${qs}`);
  }

  async scheduleMaintenance(data: {
    asset_id: string;
    category: string;
    start_time: string;
    end_time: string;
    is_unplanned?: boolean;
    reason: string;
  }): Promise<MaintenanceRecord> {
    return this.request<MaintenanceRecord>("/maintenance/records", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async validateMaintenanceWindow(data: {
    asset_id: string;
    start_time: string;
    end_time: string;
  }): Promise<{ is_compatible: boolean; conflict_details: string | null; conflicting_record_id: string | null }> {
    return this.request("/maintenance/validate-window", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Search
  async search(query: string): Promise<SearchResponse> {
    return this.request<SearchResponse>(`/search?q=${encodeURIComponent(query)}`);
  }

  // Events & Disruption
  async getEvents(params?: Record<string, any>): Promise<OperationalEvent[]> {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<OperationalEvent[]>(`/events${qs}`);
  }

  async injectEvent(data: {
    event_type: string;
    affected_entity_type: string;
    affected_entity_id: string;
    severity?: string;
    payload_json?: Record<string, any>;
    reason: string;
  }): Promise<OperationalEvent> {
    return this.request<OperationalEvent>("/events", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Audit
  async getAuditLogs(params?: Record<string, any>): Promise<any[]> {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<any[]>(`/admin/audit-logs${qs}`);
  }

  // Demo reset
  async resetDemo(seed: number = 42): Promise<any> {
    return this.request("/demo/reset", {
      method: "POST",
      body: JSON.stringify({ confirmation: "RESET", seed }),
    });
  }

  // Phase 4: Optimisation & Plans
  async getPlans(): Promise<PlanSummary[]> {
    return this.request<PlanSummary[]>("/plans");
  }

  async getPlanVersion(planId: string, versionNumber: number): Promise<PlanVersionDetail> {
    return this.request<PlanVersionDetail>(`/plans/${planId}/versions/${versionNumber}`);
  }

  async getPlanGantt(planId: string, versionNumber: number): Promise<GanttTimelineResponse> {
    return this.request<GanttTimelineResponse>(`/plans/${planId}/versions/${versionNumber}/gantt`);
  }

  async createOptimisationJob(params: {
    job_type: "baseline" | "optimise";
    plan_name?: string;
    time_limit_seconds?: number;
    seed?: number;
    weight_set_version?: number;
    run_async?: boolean;
  }): Promise<{ job_id: string; job_type: string; state: string; result?: any }> {
    return this.request("/optimisation/jobs", {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  async getOptimisationJob(jobId: string): Promise<any> {
    return this.request(`/optimisation/jobs/${jobId}`);
  }

  async cancelOptimisationJob(jobId: string): Promise<any> {
    return this.request(`/optimisation/jobs/${jobId}/cancel`, {
      method: "POST",
    });
  }

  async getWeightSets(): Promise<ObjectiveWeightSet[]> {
    return this.request<ObjectiveWeightSet[]>("/optimisation/weight-sets");
  }

  async createWeightSet(data: {
    name: string;
    delay_weight: number;
    completion_weight: number;
    churn_weight: number;
    balance_weight: number;
    buffer_weight: number;
  }): Promise<ObjectiveWeightSet> {
    return this.request<ObjectiveWeightSet>("/optimisation/weight-sets", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }
}

export const api = new ApiClient();
