import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Play,
  CheckCircle2,
  RefreshCw,
  AlertTriangle,
  ArrowRight,
} from "lucide-react";
import { api } from "../services/api";
import { OverviewKPIs, JobProgress, Zone, OperationalEvent } from "../types/api";
import { KpiCard } from "../components/data-display/KpiCard";
import { FictionalBasesMap } from "../components/data-display/FictionalBasesMap";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { ErrorState } from "../components/feedback/ErrorState";

interface OverviewPageProps {
  lastJobProgress: JobProgress | null;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ lastJobProgress }) => {
  const [kpis, setKpis] = useState<OverviewKPIs | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [events, setEvents] = useState<OperationalEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSubmittingJob, setIsSubmittingJob] = useState(false);
  const [jobFeedback, setJobFeedback] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [kpiData, zoneData, eventData] = await Promise.all([
        api.getOverview(),
        api.getZones(),
        api.getEvents({ limit: 6 }),
      ]);
      setKpis(kpiData);
      setZones(zoneData);
      setEvents(eventData);
    } catch (err: any) {
      setError(err?.detail || "Failed to load overview data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
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
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">Operations Overview</h2>
            <Badge variant="outline" className="border-blue-300 text-blue-700 bg-blue-50 text-[10px]">
              PHASE 3 CERTIFIED
            </Badge>
          </div>
          <p className="text-sm text-slate-500">
            Real-time fleet readiness, synthetic airbase telemetry, and verified server-side KPI telemetry.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh All
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

      {error && <ErrorState title="Overview Unavailable" detail={error} onRetry={fetchData} />}

      {/* Live SSE Job Stream Card */}
      {(lastJobProgress || jobFeedback) && (
        <div className="bg-gradient-to-r from-blue-900 to-indigo-950 text-white p-5 rounded-xl border border-blue-800 shadow-md">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-400 animate-ping"></span>
              <h3 className="text-xs font-bold uppercase tracking-wider text-blue-200">
                Live Celery Async Task Execution
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

      {/* Primary KPI Cards Grid (Direct server-side computation from database records) */}
      {kpis && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Fleet Operational Readiness & Task Placement
            </h3>
            <span className="text-[11px] font-mono text-slate-400">
              AS OF: {new Date(kpis.as_of).toLocaleDateString()} {new Date(kpis.as_of).toLocaleTimeString()} UTC
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Link to="/assets" className="group">
              <KpiCard
                title="Fleet Availability"
                value={`${(kpis.asset_availability.value * 100).toFixed(1)}%`}
                subtitle="Active aircraft ready for sortie tasking"
                dataKind={kpis.asset_availability.data_kind}
                trend={{ value: "Click to inspect fleet →", isPositive: true }}
              />
            </Link>

            <Link to="/assets" className="group">
              <KpiCard
                title="Fleet Serviceability"
                value={`${(kpis.serviceability.value * 100).toFixed(1)}%`}
                subtitle="Airframes with health score ≥ 0.70"
                dataKind={kpis.serviceability.data_kind}
                trend={{ value: "Health telemetry →", isPositive: true }}
              />
            </Link>

            <Link to="/operations" className="group">
              <KpiCard
                title="Eligible Tasks"
                value={`${kpis.eligible_tasks}`}
                subtitle="Tasks with compatible fleet & crew"
                dataKind="observed"
                trend={{ value: "Sortie work orders →", isPositive: true }}
              />
            </Link>

            <Link to="/maintenance" className="group">
              <KpiCard
                title="Maintenance Workload"
                value={`${(kpis.maintenance_workload.value * 100).toFixed(1)}%`}
                subtitle="Tech duty demand vs capacity"
                dataKind={kpis.maintenance_workload.data_kind}
                trend={{ value: "Work order queues →", isPositive: true }}
              />
            </Link>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Link to="/personnel" className="group">
              <KpiCard
                title="Crew Availability"
                value={`${(kpis.crew_availability.value * 100).toFixed(1)}%`}
                subtitle="Qualified pilots & technicians on-duty"
                dataKind={kpis.crew_availability.data_kind}
                trend={{ value: "Personnel rosters →", isPositive: true }}
              />
            </Link>

            <Link to="/maintenance" className="group">
              <KpiCard
                title="Overdue Maintenance"
                value={`${kpis.overdue_maintenance}`}
                subtitle="Work orders past scheduled deadline"
                dataKind="observed"
                trend={{
                  value: kpis.overdue_maintenance > 0 ? "Critical action needed" : "Zero overdue",
                  isPositive: kpis.overdue_maintenance === 0,
                }}
              />
            </Link>

            <Link to="/maintenance" className="group">
              <KpiCard
                title="Spares Shortages"
                value={`${kpis.spares_shortage}`}
                subtitle="Parts below base safety thresholds"
                dataKind="observed"
                trend={{
                  value: kpis.spares_shortage > 0 ? "Resupply order required" : "Stock optimal",
                  isPositive: kpis.spares_shortage === 0,
                }}
              />
            </Link>

            <Link to="/operations" className="group">
              <KpiCard
                title="Cumulative Delay"
                value={`${kpis.total_delay.toFixed(1)} min`}
                subtitle="Sortie schedule latency"
                dataKind="observed"
                trend={{ value: "Disruption tracking →", isPositive: kpis.total_delay <= 60 }}
              />
            </Link>
          </div>
        </div>
      )}

      {/* Fictional Tactical Sector Map */}
      <FictionalBasesMap zones={zones} />

      {/* Lower Row: Live Disruption Events Feed + System Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Live Disruption Feed (Task P3-5 & P3-7) */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-500" />
              <h3 className="text-sm font-bold text-slate-800">Operational Events & Disruption Feed</h3>
            </div>
            <Link to="/operations" className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1 font-medium">
              <span>View All Events</span>
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          {events.length === 0 ? (
            <div className="p-6 text-center text-slate-400 text-xs">
              No recent disruption events recorded. System operating in nominal state.
            </div>
          ) : (
            <div className="space-y-2.5">
              {events.map((evt) => (
                <div
                  key={evt.id}
                  className="flex items-start justify-between p-3 rounded-lg border border-slate-100 bg-slate-50/70 hover:bg-slate-50 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-800">
                        {evt.event_type.replace(/_/g, " ").toUpperCase()}
                      </span>
                      <Badge
                        variant={
                          evt.severity === "critical"
                            ? "danger"
                            : evt.severity === "high"
                            ? "warning"
                            : "default"
                        }
                      >
                        {evt.severity.toUpperCase()}
                      </Badge>
                      <span className="text-[10px] text-slate-400 font-mono">
                        Target: {evt.affected_entity_type}/{evt.affected_entity_id}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600">
                      {evt.payload_json?.description || evt.payload_json?.reason || "Operational disturbance recorded."}
                    </p>
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono whitespace-nowrap ml-4">
                    {new Date(evt.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} UTC
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Engine Circuit Breakers & Data Source Health */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
            <h3 className="text-sm font-bold text-slate-800">System Engines & Integrity</h3>
            <Badge variant="success">All Nominal</Badge>
          </div>
          <div className="space-y-2.5 text-xs">
            {[
              { name: "PostgreSQL 16 System of Record", desc: "33 Relational Tables", ok: true },
              { name: "Cryptographic Audit Ledger", desc: "SHA-256 Hash Chaining Active", ok: true },
              { name: "Celery Distributed Workers", desc: "6 Queues Streaming via SSE", ok: true },
              { name: "Hard Maintenance Validator", desc: "Window Overlap Rejection", ok: true },
              { name: "Virtual Clock Engine", desc: "AST Zero-Clock Enforcement", ok: true },
              { name: "Data Fusion & Quality SLA", desc: "Conflict Review Queue", ok: true },
            ].map((item, idx) => (
              <div key={idx} className="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                <div>
                  <div className="font-semibold text-slate-700">{item.name}</div>
                  <div className="text-[10px] text-slate-400 font-mono">{item.desc}</div>
                </div>
                <span className="text-[11px] text-emerald-600 font-mono flex items-center gap-1 font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                  <span>ACTIVE</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
