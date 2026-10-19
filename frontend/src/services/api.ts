import { ClockState, OverviewKPIs, UserProfile } from "../types/api";

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
  async login(username: string, password: string):Promise<{ access_token: string; roles: string[] }> {
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

  // Demo reset
  async resetDemo(seed: number = 42): Promise<any> {
    return this.request("/demo/reset", {
      method: "POST",
      body: JSON.stringify({ confirmation: "RESET", seed }),
    });
  }
}

export const api = new ApiClient();
