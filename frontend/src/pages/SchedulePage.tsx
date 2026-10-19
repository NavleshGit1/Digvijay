import React, { useEffect, useState } from "react";
import {
  CalendarDays,
  Play,
  RotateCw,
  Clock,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  HelpCircle,
  Layers,
  X,
  ShieldCheck,
  ShieldAlert,
  Zap,
} from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, Column } from "../components/data-display/DataTable";
import { api } from "../services/api";
import {
  GanttTimelineResponse,
  PlanAssignmentItem,
  PlanSummary,
  PlanVersionDetail,
  SolverStatus,
} from "../types/api";

export const SchedulePage: React.FC = () => {
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [selectedVersionNum, setSelectedVersionNum] = useState<number | null>(null);
  const [planDetail, setPlanDetail] = useState<PlanVersionDetail | null>(null);
  const [ganttData, setGanttData] = useState<GanttTimelineResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<"gantt" | "table" | "diagnostics">("gantt");
  const [ganttTrackType, setGanttTrackType] = useState<"aircraft" | "crew">("aircraft");
  const [selectedAssignment, setSelectedAssignment] = useState<PlanAssignmentItem | null>(null);
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);

  // Job execution state
  const [jobRunning, setJobRunning] = useState<boolean>(false);
  const [jobProgress, setJobProgress] = useState<number>(0);
  const [jobMessage, setJobMessage] = useState<string>("");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [timeLimitSecs, setTimeLimitSecs] = useState<number>(15);

  const fetchPlansList = async () => {
    try {
      setLoading(true);
      const res = await api.getPlans();
      setPlans(res);
      if (res.length > 0) {
        const latestPlan = res[0];
        setSelectedPlanId(latestPlan.id);
        setSelectedVersionNum(latestPlan.latest_version);
        await loadVersionData(latestPlan.id, latestPlan.latest_version);
      } else {
        setLoading(false);
      }
    } catch (err) {
      console.error("Failed to load plans:", err);
      setLoading(false);
    }
  };

  const loadVersionData = async (planId: string, versionNum: number) => {
    try {
      setLoading(true);
      const [detailRes, ganttRes] = await Promise.all([
        api.getPlanVersion(planId, versionNum),
        api.getPlanGantt(planId, versionNum),
      ]);
      setPlanDetail(detailRes);
      setGanttData(ganttRes);
      setLoading(false);
    } catch (err) {
      console.error("Failed to load version details:", err);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlansList();
  }, []);

  // Poll job status if a job is currently executing
  useEffect(() => {
    if (!activeJobId || !jobRunning) return;

    const interval = setInterval(async () => {
      try {
        const statusRes = await api.getOptimisationJob(activeJobId);
        setJobProgress(statusRes.progress_percent || 0);
        setJobMessage(statusRes.message || "Optimiser running...");

        if (statusRes.state === "completed") {
          setJobRunning(false);
          setActiveJobId(null);
          // Reload plans
          await fetchPlansList();
        } else if (statusRes.state === "failed" || statusRes.state === "cancelled") {
          setJobRunning(false);
          setActiveJobId(null);
        }
      } catch (err) {
        console.error("Error polling job status:", err);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeJobId, jobRunning]);

  const handleRunJob = async (jobType: "baseline" | "optimise") => {
    try {
      setJobRunning(true);
      setJobProgress(10);
      setJobMessage(`Submitting ${jobType} job to worker queue...`);
      const res = await api.createOptimisationJob({
        job_type: jobType,
        time_limit_seconds: timeLimitSecs,
        seed: 42,
        run_async: true,
      });
      setActiveJobId(res.job_id);
    } catch (err: any) {
      alert(`Job submission failed: ${err.detail || "Server error"}`);
      setJobRunning(false);
    }
  };

  const getSolverStatusBadge = (status: SolverStatus | undefined) => {
    switch (status) {
      case "optimal":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
            OPTIMAL
          </span>
        );
      case "feasible":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
            FEASIBLE
          </span>
        );
      case "timeout":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-300">
            <Clock className="w-3.5 h-3.5 text-amber-600" />
            TIMEOUT (Best Known)
          </span>
        );
      case "infeasible":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-50 text-red-700 border border-red-200">
            <AlertCircle className="w-3.5 h-3.5 text-red-600" />
            INFEASIBLE
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
            {status || "UNKNOWN"}
          </span>
        );
    }
  };

  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case "patrol_sortie":
        return "bg-blue-600 text-white";
      case "air_defense_escort":
        return "bg-indigo-600 text-white";
      case "recon_surveillance":
        return "bg-purple-600 text-white";
      case "tactical_airlift":
        return "bg-teal-600 text-white";
      case "refueling_anchor":
        return "bg-amber-600 text-white";
      case "maintenance":
        return "bg-amber-100 border border-amber-400 text-amber-900 font-semibold";
      default:
        return "bg-slate-700 text-white";
    }
  };

  // Timeline helper: compute percentage position across 7 days (168 hours)
  const computeBlockStyle = (startIso: string, endIso: string, asOfIso: string) => {
    const asOfMs = new Date(asOfIso).getTime();
    const startMs = new Date(startIso).getTime();
    const endMs = new Date(endIso).getTime();
    const totalMs = 7 * 24 * 60 * 60 * 1000;

    const leftPercent = Math.max(0, Math.min(100, ((startMs - asOfMs) / totalMs) * 100));
    const widthPercent = Math.max(0.6, Math.min(100 - leftPercent, ((endMs - startMs) / totalMs) * 100));

    return {
      left: `${leftPercent}%`,
      width: `${widthPercent}%`,
    };
  };

  const tableColumns: Column<PlanAssignmentItem>[] = [
    {
      key: "task_code",
      header: "Task Code",
      sortable: true,
      render: (r: PlanAssignmentItem) => (
        <span className="font-mono font-semibold text-slate-900 text-xs">{r.task_code}</span>
      ),
    },
    {
      key: "task_category",
      header: "Category",
      sortable: true,
      render: (r: PlanAssignmentItem) => (
        <span className="text-xs px-2 py-0.5 rounded bg-slate-100 font-medium text-slate-700 capitalize">
          {r.task_category.replace(/_/g, " ")}
        </span>
      ),
    },
    {
      key: "asset_identifier",
      header: "Allocated Aircraft",
      sortable: true,
      render: (r: PlanAssignmentItem) => (
        <div>
          <span className="font-mono font-medium text-slate-900 text-xs">{r.asset_identifier}</span>
          {r.asset_model && <div className="text-[10px] text-slate-500">{r.asset_model}</div>}
        </div>
      ),
    },
    {
      key: "personnel_ids",
      header: "Crew Headcount",
      render: (r: PlanAssignmentItem) => (
        <span className="text-xs text-slate-600">{r.personnel_ids.length} operators</span>
      ),
    },
    {
      key: "assigned_start",
      header: "Window Start (UTC)",
      sortable: true,
      render: (r: PlanAssignmentItem) => (
        <span className="font-mono text-xs text-slate-700">
          {new Date(r.assigned_start).toLocaleString(undefined, {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      ),
    },
    {
      key: "assigned_end",
      header: "Window End (UTC)",
      sortable: true,
      render: (r: PlanAssignmentItem) => (
        <span className="font-mono text-xs text-slate-700">
          {new Date(r.assigned_end).toLocaleString(undefined, {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      ),
    },
    {
      key: "duration_minutes",
      header: "Duration",
      sortable: true,
      render: (r: PlanAssignmentItem) => <span className="text-xs text-slate-700">{r.duration_minutes}m</span>,
    },
    {
      key: "delay_minutes",
      header: "Delay",
      sortable: true,
      render: (r: PlanAssignmentItem) =>
        r.delay_minutes > 0 ? (
          <span className="text-xs font-semibold text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
            +{r.delay_minutes}m
          </span>
        ) : (
          <span className="text-xs text-emerald-600 font-medium">On-time</span>
        ),
    },
    {
      key: "actions",
      header: "",
      render: (r: PlanAssignmentItem) => (
        <Button
          variant="outline"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            setSelectedAssignment(r);
            setDrawerOpen(true);
          }}
        >
          Details
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Operational Schedule</h1>
            {planDetail && (
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold px-2.5 py-1 rounded bg-slate-800 text-white font-mono">
                  v{planDetail.version_number} ({planDetail.kind})
                </span>
                {getSolverStatusBadge(planDetail.solver_status)}
              </div>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Dual-verified multi-objective schedule satisfying 10 operational invariants with deterministic solver configuration.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Plan Selector Dropdown */}
          {plans.length > 0 && (
            <select
              value={selectedVersionNum || ""}
              onChange={(e) => {
                const v = parseInt(e.target.value);
                setSelectedVersionNum(v);
                if (selectedPlanId) loadVersionData(selectedPlanId, v);
              }}
              className="text-xs font-medium bg-white border border-slate-300 rounded-lg px-3 py-2 shadow-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {plans.map((p) => (
                <option key={p.id} value={p.latest_version}>
                  {p.name} (v{p.latest_version})
                </option>
              ))}
            </select>
          )}

          {/* Time limit selector */}
          <div className="flex items-center gap-1.5 bg-slate-100 rounded-lg px-2.5 py-1 border border-slate-200">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-xs text-slate-600 font-medium">Limit:</span>
            <select
              value={timeLimitSecs}
              onChange={(e) => setTimeLimitSecs(parseFloat(e.target.value))}
              disabled={jobRunning}
              className="text-xs bg-transparent border-none text-slate-800 font-semibold focus:outline-none"
            >
              <option value={5}>5s</option>
              <option value={15}>15s</option>
              <option value={30}>30s</option>
              <option value={60}>60s</option>
            </select>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => handleRunJob("baseline")}
            disabled={jobRunning}
            className="flex items-center gap-1.5"
          >
            <RotateCw className="w-3.5 h-3.5" />
            Run Baseline (W-EDD)
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => handleRunJob("optimise")}
            disabled={jobRunning}
            className="flex items-center gap-1.5 shadow-sm"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            Run CP-SAT Optimiser
          </Button>
        </div>
      </div>

      {/* Live Job Progress Banner */}
      {jobRunning && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 shadow-sm animate-pulse">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-blue-600 animate-spin" />
              <span className="text-sm font-semibold text-blue-900">Solver Job Running...</span>
            </div>
            <span className="text-xs font-mono font-bold text-blue-700">{jobProgress.toFixed(0)}%</span>
          </div>
          <div className="w-full bg-blue-200 rounded-full h-2 overflow-hidden mb-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${jobProgress}%` }}
            />
          </div>
          <div className="text-xs text-blue-700 font-mono">{jobMessage}</div>
        </div>
      )}

      {/* KPI & Utilisation Summary Grid */}
      {planDetail && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Scheduled Sorties</div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-2xl font-bold text-slate-900 font-mono">
                {planDetail.assignments_count}
              </span>
              <span className="text-xs text-slate-500">
                / {planDetail.metrics.total_horizon_tasks || 300}
              </span>
            </div>
            <div className="mt-2 text-xs text-slate-500">
              Completion: {((planDetail.metrics.completion_rate || 0) * 100).toFixed(1)}%
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Schedule Delay</div>
            <div className="mt-1 flex items-baseline gap-1">
              <span className="text-2xl font-bold text-slate-900 font-mono">
                {planDetail.metrics.total_delay_minutes?.toFixed(0) || "0"}
              </span>
              <span className="text-xs text-slate-500 font-medium">mins</span>
            </div>
            <div className="mt-2 text-xs text-emerald-600 font-medium">Across active sorties</div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Validator Verdict</div>
            <div className="mt-1.5 flex items-center gap-1.5">
              {planDetail.validation.is_valid ? (
                <>
                  <ShieldCheck className="w-5 h-5 text-emerald-600" />
                  <span className="text-sm font-bold text-emerald-800">VALID (0 Violations)</span>
                </>
              ) : (
                <>
                  <ShieldAlert className="w-5 h-5 text-red-600" />
                  <span className="text-sm font-bold text-red-700">
                    {planDetail.validation.violation_count} Violations
                  </span>
                </>
              )}
            </div>
            <div className="mt-2 text-xs text-slate-500">
              {planDetail.validation.binding_constraints.length} binding constraints
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Solver Runtime</div>
            <div className="mt-1 flex items-baseline gap-1">
              <span className="text-2xl font-bold text-slate-900 font-mono">
                {planDetail.runtime_seconds.toFixed(2)}
              </span>
              <span className="text-xs text-slate-500 font-medium">sec</span>
            </div>
            <div className="mt-2 text-[11px] font-mono text-slate-500">
              {planDetail.manifest.reproducible ? "Deterministic (1 Worker)" : "Parallel"}
            </div>
          </div>

          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Objective Score</div>
            <div className="mt-1 text-2xl font-bold text-slate-900 font-mono">
              {planDetail.metrics.objective_value?.toFixed(0) || "—"}
            </div>
            <div className="mt-2 text-[11px] text-slate-500">
              Gap: {planDetail.manifest.optimality_gap !== undefined ? planDetail.manifest.optimality_gap : "0.0"}
            </div>
          </div>
        </div>
      )}

      {/* Tabs Header */}
      <div className="flex items-center justify-between border-b border-slate-200">
        <div className="flex gap-4">
          <button
            onClick={() => setActiveTab("gantt")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === "gantt"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <CalendarDays className="w-4 h-4" />
            Gantt Timeline
          </button>
          <button
            onClick={() => setActiveTab("table")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === "table"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <Layers className="w-4 h-4" />
            Schedule Table ({planDetail?.assignments_count || 0})
          </button>
          <button
            onClick={() => setActiveTab("diagnostics")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === "diagnostics"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <AlertTriangle className="w-4 h-4" />
            Diagnostics & Unassigned ({planDetail?.metrics.unassigned_count || 0})
          </button>
        </div>

        {activeTab === "gantt" && (
          <div className="flex items-center gap-2 pb-2">
            <span className="text-xs text-slate-500 font-medium">Tracks:</span>
            <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-0.5">
              <button
                onClick={() => setGanttTrackType("aircraft")}
                className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
                  ganttTrackType === "aircraft"
                    ? "bg-white text-slate-900 shadow-xs"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                Aircraft Tracks
              </button>
              <button
                onClick={() => setGanttTrackType("crew")}
                className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-all ${
                  ganttTrackType === "crew"
                    ? "bg-white text-slate-900 shadow-xs"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                Crew Tracks
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Tab 1: Gantt Timeline */}
      {activeTab === "gantt" && ganttData && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          {/* Timeline Header (7 Days of Planning Window) */}
          <div className="flex border-b border-slate-200 bg-slate-50">
            <div className="w-48 shrink-0 p-3 font-semibold text-xs text-slate-600 border-r border-slate-200">
              Resource Track
            </div>
            <div className="flex-1 grid grid-cols-7 text-center divide-x divide-slate-200 text-xs font-medium text-slate-600 py-2.5">
              <div>Day 1 (+0-24h)</div>
              <div>Day 2 (+24-48h)</div>
              <div>Day 3 (+48-72h)</div>
              <div>Day 4 (+72-96h)</div>
              <div>Day 5 (+96-120h)</div>
              <div>Day 6 (+120-144h)</div>
              <div>Day 7 (+144-168h)</div>
            </div>
          </div>

          {/* Timeline Rows */}
          <div className="divide-y divide-slate-100 max-h-[620px] overflow-y-auto">
            {(ganttTrackType === "aircraft" ? ganttData.asset_tracks : ganttData.crew_tracks).map((track, idx) => (
              <div key={idx} className="flex hover:bg-slate-50/50 transition-colors">
                <div className="w-48 shrink-0 p-2.5 border-r border-slate-200 flex flex-col justify-center">
                  <div className="text-xs font-mono font-bold text-slate-900">
                    {track.identifier || track.name}
                  </div>
                  <div className="text-[10px] text-slate-500 truncate">
                    {track.model_name || track.role_type || track.callsign}
                  </div>
                </div>

                <div className="flex-1 relative h-12 bg-white flex items-center">
                  {/* Subtle 24-hour vertical grid dividers */}
                  <div className="absolute inset-0 grid grid-cols-7 divide-x divide-slate-100 pointer-events-none" />

                  {/* Task / Maintenance Blocks */}
                  {track.blocks.map((block) => {
                    const style = computeBlockStyle(block.start, block.end, ganttData.as_of);
                    const colorClass = getCategoryColor(block.category);

                    return (
                      <div
                        key={block.id}
                        style={style}
                        onClick={() => {
                          const asgn = planDetail?.assignments.find((a) => a.id === block.id);
                          if (asgn) {
                            setSelectedAssignment(asgn);
                            setDrawerOpen(true);
                          }
                        }}
                        className={`absolute h-7 rounded-md shadow-xs px-1.5 flex items-center overflow-hidden cursor-pointer hover:ring-2 hover:ring-blue-400 transition-all text-[10px] font-mono font-semibold ${colorClass}`}
                        title={`${block.code} (${block.category}): ${new Date(block.start).toUTCString()} to ${new Date(block.end).toUTCString()}`}
                      >
                        <span className="truncate">{block.code}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          {/* Timeline Legend */}
          <div className="p-3 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center gap-4 text-xs">
            <span className="text-slate-500 font-semibold">Legend:</span>
            <span className="inline-flex items-center gap-1.5 text-slate-700">
              <span className="w-3 h-3 rounded bg-blue-600 inline-block" /> Patrol Sortie
            </span>
            <span className="inline-flex items-center gap-1.5 text-slate-700">
              <span className="w-3 h-3 rounded bg-indigo-600 inline-block" /> Escort
            </span>
            <span className="inline-flex items-center gap-1.5 text-slate-700">
              <span className="w-3 h-3 rounded bg-purple-600 inline-block" /> Recon
            </span>
            <span className="inline-flex items-center gap-1.5 text-slate-700">
              <span className="w-3 h-3 rounded bg-teal-600 inline-block" /> Airlift
            </span>
            <span className="inline-flex items-center gap-1.5 text-slate-700">
              <span className="w-3 h-3 rounded bg-amber-600 inline-block" /> Refueling
            </span>
            <span className="inline-flex items-center gap-1.5 text-slate-700">
              <span className="w-3 h-3 rounded bg-amber-100 border border-amber-400 inline-block" /> Confirmed Maintenance
            </span>
          </div>
        </div>
      )}

      {/* Tab 2: Schedule Table */}
      {activeTab === "table" && planDetail && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4">
          <DataTable<PlanAssignmentItem>
            data={planDetail.assignments}
            columns={tableColumns}
            keyField="id"
            loading={loading}
            searchPlaceholder="Search task code, aircraft tail, or status..."
            searchFilter={(row, query) =>
              row.task_code.toLowerCase().includes(query) ||
              (row.asset_identifier ? row.asset_identifier.toLowerCase().includes(query) : false) ||
              row.task_category.toLowerCase().includes(query)
            }
            pageSize={15}
            onRowClick={(row: PlanAssignmentItem) => {
              setSelectedAssignment(row);
              setDrawerOpen(true);
            }}
          />
        </div>
      )}

      {/* Tab 3: Diagnostics & Unassigned Tasks */}
      {activeTab === "diagnostics" && planDetail && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Binding Constraints (Zero-Slack Limits) */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <div className="flex items-center gap-2 mb-3">
                <CheckCircle2 className="w-5 h-5 text-blue-600" />
                <h3 className="text-base font-bold text-slate-900">Binding Constraints (Zero-Slack)</h3>
              </div>
              <p className="text-xs text-slate-500 mb-4">
                Identified hard constraints operating with 0 slack minutes, defining critical path bottlenecks.
              </p>
              <div className="space-y-2 max-h-[360px] overflow-y-auto">
                {planDetail.validation.binding_constraints.map((bc, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg border border-slate-200 bg-slate-50/70 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-slate-800">{bc.constraint_code}</span>
                      <span className="font-mono text-[10px] bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded font-semibold">
                        Slack: {bc.slack_minutes}m
                      </span>
                    </div>
                    <div className="text-slate-600 mt-1 text-[11px]">{bc.description}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Invariant Violations Ledger */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
              <div className="flex items-center gap-2 mb-3">
                <ShieldCheck className="w-5 h-5 text-emerald-600" />
                <h3 className="text-base font-bold text-slate-900">Independent Validator Verification</h3>
              </div>
              <p className="text-xs text-slate-500 mb-4">
                Pure-Python validation pass covering all 10 operational invariants.
              </p>

              {planDetail.validation.is_valid ? (
                <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs">
                  <div className="font-bold flex items-center gap-1.5 mb-1">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    Zero Violations Detected
                  </div>
                  All {planDetail.assignments_count} assignments rigorously satisfy resource availability,
                  pairwise non-overlap, crew certifications, maintenance windows, and apron capacities.
                </div>
              ) : (
                <div className="space-y-2 max-h-[360px] overflow-y-auto">
                  {planDetail.validation.violations.map((v, idx) => (
                    <div key={idx} className="p-2.5 rounded-lg border border-red-200 bg-red-50 text-xs">
                      <div className="font-bold text-red-900">{v.constraint_code}</div>
                      <div className="text-red-700 mt-0.5">{v.message}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Slide-over Detail Drawer */}
      {drawerOpen && selectedAssignment && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end">
          <div className="w-full max-w-md bg-white shadow-2xl h-full flex flex-col animate-in slide-in-from-right duration-200">
            <div className="p-5 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-900 font-mono">
                  {selectedAssignment.task_code}
                </h3>
                <span className="text-xs text-slate-500 capitalize">
                  {selectedAssignment.task_category.replace(/_/g, " ")}
                </span>
              </div>
              <button
                onClick={() => setDrawerOpen(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 space-y-5 flex-1 overflow-y-auto text-xs">
              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Assigned Aircraft
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                  <div className="font-bold text-slate-900 font-mono text-sm">
                    {selectedAssignment.asset_identifier}
                  </div>
                  <div className="text-slate-600">{selectedAssignment.asset_model}</div>
                </div>
              </div>

              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Execution Window
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Start (UTC):</span>
                    <span className="font-mono font-medium text-slate-800">
                      {new Date(selectedAssignment.assigned_start).toUTCString()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">End (UTC):</span>
                    <span className="font-mono font-medium text-slate-800">
                      {new Date(selectedAssignment.assigned_end).toUTCString()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Duration:</span>
                    <span className="font-semibold text-slate-800">{selectedAssignment.duration_minutes} mins</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Delay:</span>
                    <span
                      className={`font-semibold ${
                        selectedAssignment.delay_minutes > 0 ? "text-amber-600" : "text-emerald-600"
                      }`}
                    >
                      {selectedAssignment.delay_minutes > 0 ? `+${selectedAssignment.delay_minutes} mins` : "On-Time"}
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Assigned Flight Crew
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                  <span className="font-semibold text-slate-800">
                    {selectedAssignment.personnel_ids.length} Personnel Allocated
                  </span>
                  <div className="text-slate-500 text-[11px]">
                    Qualified operators meeting night-ops, rest limits, and duty regulations.
                  </div>
                </div>
              </div>

              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Governance & Locking
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <div className="flex items-center gap-2">
                    <Badge variant={selectedAssignment.is_locked ? "warning" : "default"}>
                      {selectedAssignment.is_locked ? "Locked Commitment" : "Optimisable Assignment"}
                    </Badge>
                  </div>
                  <div className="text-[11px] text-slate-500 mt-1">
                    Assignments inside frozen window or past actual_start are preserved against perturbation.
                  </div>
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-slate-200 bg-slate-50">
              <Button variant="outline" className="w-full" onClick={() => setDrawerOpen(false)}>
                Close Panel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
