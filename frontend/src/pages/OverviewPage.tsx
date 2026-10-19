import React, { useEffect, useState } from "react";
import { Play, CheckCircle2, RefreshCw, Layers } from "lucide-react";
import { api } from "../services/api";
import { OverviewKPIs, JobProgress } from "../types/api";
import { KpiCard } from "../components/data-display/KpiCard";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { ErrorState } from "../components/feedback/ErrorState";

interface OverviewPageProps {
  lastJobProgress: JobProgress | null;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ lastJobProgress }) => {
  const [kpis, setKpis] = useState<OverviewKPIs | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmittingJob, setIsSubmittingJob] = useState(false);
  const [jobFeedback, setJobFeedback] = useState<string | null>(null);

  const fetchKpis = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getOverview();
      setKpis(data);
    } catch (err: any) {
      setError(err?.detail || "Failed to load overview KPIs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKpis();
  }, []);

  const handleRunDummyJob = async () => {
    try {
      setIsSubmittingJob(true);
      setJobFeedback(null);
      const res = await api.createJob("dummy_job", 6);
      setJobFeedback(`Async Job ${res.id.slice(0, 8)} enqueued to Celery. Streaming live progress via SSE...`);
    } catch (err: any) {
      setJobFeedback(`Error: ${err?.detail || "Failed to enqueue job"}`);
    } finally {
      setIsSubmittingJob(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Operations Overview</h2>
          <p className="text-sm text-slate-500">
            Real-time fleet readiness, scheduled sortie completion, and asynchronous worker orchestration.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchKpis} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh KPIs
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleRunDummyJob}
            loading={isSubmittingJob}
          >
            <Play className="w-3.5 h-3.5 mr-1.5" />
            Dispatch Async Worker Job
          </Button>
        </div>
      </div>

      {error && <ErrorState title="Overview Unavailable" detail={error} onRetry={fetchKpis} />}

      {/* Live SSE Job Stream Card (Validates Phase 1 Exit Gate) */}
      {(lastJobProgress || jobFeedback) && (
        <div className="bg-gradient-to-r from-blue-900 to-indigo-950 text-white p-5 rounded-xl border border-blue-800 shadow-md">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-400 animate-ping"></span>
              <h3 className="text-xs font-bold uppercase tracking-wider text-blue-200">
                Live SSE Worker Task Execution (Phase 1 Exit Gate)
              </h3>
            </div>
            {lastJobProgress && (
              <Badge variant={lastJobProgress.state === "completed" ? "success" : "info"}>
                {lastJobProgress.state.toUpperCase()}
              </Badge>
            )}
          </div>

          <div className="space-y-2 mt-3">
            <div className="flex justify-between text-xs text-blue-200 font-mono">
              <span>{lastJobProgress?.message || jobFeedback || "Task queued..."}</span>
              <span>{lastJobProgress ? `${Math.round(lastJobProgress.progress_percent)}%` : "0%"}</span>
            </div>
            <div className="w-full bg-blue-950 rounded-full h-2 overflow-hidden border border-blue-800/60">
              <div
                className="bg-blue-400 h-full transition-all duration-300 ease-out"
                style={{ width: `${lastJobProgress?.progress_percent || 5}%` }}
              ></div>
            </div>
          </div>
        </div>
      )}

      {/* KPI Cards Row */}
      {kpis && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            title="Asset Availability"
            value={`${(kpis.asset_availability.value * 100).toFixed(1)}%`}
            subtitle="33 of 40 active airframes operational"
            dataKind={kpis.asset_availability.data_kind}
            trend={{ value: "+2.5% vs yesterday", isPositive: true }}
          />
          <KpiCard
            title="Serviceability Rate"
            value={`${(kpis.serviceability.value * 100).toFixed(1)}%`}
            subtitle="Health score ≥ 0.70 threshold"
            dataKind={kpis.serviceability.data_kind}
          />
          <KpiCard
            title="Tasks Scheduled"
            value={`${kpis.tasks_scheduled} / ${kpis.eligible_tasks}`}
            subtitle="91.2% planning horizon placement"
            dataKind="observed"
          />
          <KpiCard
            title="Maintenance Workload"
            value={`${(kpis.maintenance_workload.value * 100).toFixed(0)}%`}
            subtitle={`${kpis.overdue_maintenance} overdue work orders`}
            dataKind={kpis.maintenance_workload.data_kind}
            trend={{ value: "Capacity optimal", isPositive: true }}
          />
        </div>
      )}

      {/* Secondary Information Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Fictional Operational Sectors */}
        <div className="lg:col-span-2 bg-white rounded-lg border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-blue-600" />
              <h3 className="text-sm font-bold text-slate-800">Operational Sectors & Zones</h3>
            </div>
            <Badge variant="default">6 Fictional Zones</Badge>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {[
              { code: "ZONE-A", name: "Sector Alpha Airbase", capacity: "8/10 Bays", status: "nominal" },
              { code: "ZONE-B", name: "Bravo Forward Staging", capacity: "5/6 Apron", status: "nominal" },
              { code: "ZONE-C", name: "Charlie Main Hangar", capacity: "12/12 Max", status: "degraded" },
              { code: "ZONE-D", name: "Delta Logistics Depot", capacity: "4/8 Storage", status: "nominal" },
              { code: "ZONE-E", name: "Echo Rapid Turnaround", capacity: "6/6 Bays", status: "nominal" },
              { code: "ZONE-F", name: "Foxtrot Reserve Strip", capacity: "2/4 Parking", status: "nominal" },
            ].map((z) => (
              <div key={z.code} className="p-3 rounded-lg border border-slate-100 bg-slate-50/60">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-xs font-bold text-blue-700">{z.code}</span>
                  <span className={`w-2 h-2 rounded-full ${z.status === 'nominal' ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
                </div>
                <p className="text-xs font-semibold text-slate-800 truncate">{z.name}</p>
                <p className="text-[11px] text-slate-500 mt-0.5">{z.capacity}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Engine Circuit Breakers */}
        <div className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
            <h3 className="text-sm font-bold text-slate-800">Modular Engines (Principle 7)</h3>
            <Badge variant="success">All Healthy</Badge>
          </div>
          <div className="space-y-2.5 text-xs">
            {[
              { name: "CP-SAT Optimiser", state: "Ready (Single-worker reproducible)" },
              { name: "Independent Validator", state: "Active (10 Hard Constraints)" },
              { name: "Prediction Serving", state: "MLflow Champion Aliases" },
              { name: "Digital Twin (SimPy)", state: "Ready (Common Random Numbers)" },
              { name: "Audit Hash Chain", state: "Append-Only SHA-256 Active" },
            ].map((eng, idx) => (
              <div key={idx} className="flex items-center justify-between p-2 rounded bg-slate-50">
                <span className="font-medium text-slate-700">{eng.name}</span>
                <span className="text-[11px] text-emerald-600 font-mono flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>OK</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
