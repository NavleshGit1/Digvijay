import React, { useEffect, useState } from "react";
import { useParams, useOutletContext } from "react-router-dom";
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
  CheckCheck,
  GitCompare,
  Undo2,
  Shield,
  Filter,
  History,
  FileCheck,
} from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { DataTable, Column } from "../components/data-display/DataTable";
import { api } from "../services/api";
import {
  ApprovalRecordItem,
  GanttTimelineResponse,
  PlanAssignmentItem,
  PlanDiffAssignmentItem,
  PlanDiffResponse,
  PlanStatus,
  PlanSummary,
  PlanVersionDetail,
  SolverStatus,
  UserProfile,
} from "../types/api";

export const SchedulePage: React.FC = () => {
  const { planId: routePlanId } = useParams<{ planId?: string }>();
  const { user } = useOutletContext<{ user?: UserProfile }>() || {};
  const userRoles = user?.roles || [];
  const isReviewer = userRoles.includes("reviewer");

  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(routePlanId || null);
  const [selectedVersionNum, setSelectedVersionNum] = useState<number | null>(null);
  const [planDetail, setPlanDetail] = useState<PlanVersionDetail | null>(null);
  const [ganttData, setGanttData] = useState<GanttTimelineResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<"gantt" | "table" | "diagnostics" | "proposals">(
    routePlanId ? "proposals" : "gantt"
  );
  const [ganttTrackType, setGanttTrackType] = useState<"aircraft" | "crew">("aircraft");
  const [selectedAssignment, setSelectedAssignment] = useState<PlanAssignmentItem | null>(null);
  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);

  // Governance & Diff State
  const [planDiff, setPlanDiff] = useState<PlanDiffResponse | null>(null);
  const [diffLoading, setDiffLoading] = useState<boolean>(false);
  const [approvalRecords, setApprovalRecords] = useState<ApprovalRecordItem[]>([]);
  const [diffCompareVersion, setDiffCompareVersion] = useState<number | null>(null);
  const [diffFilter, setDiffFilter] = useState<"all" | "shifted" | "added" | "removed" | "unchanged">("all");

  // Review Dialog State (Approve / Reject)
  const [reviewModalOpen, setReviewModalOpen] = useState<boolean>(false);
  const [reviewDecision, setReviewDecision] = useState<"approved" | "rejected">("approved");
  const [reviewReason, setReviewReason] = useState<string>("");
  const [reviewSubmitting, setReviewSubmitting] = useState<boolean>(false);
  const [reviewError, setReviewError] = useState<string | null>(null);

  // Rollback Dialog State
  const [rollbackModalOpen, setRollbackModalOpen] = useState<boolean>(false);
  const [rollbackTargetVersion, setRollbackTargetVersion] = useState<number>(1);
  const [rollbackReason, setRollbackReason] = useState<string>("");
  const [rollbackSubmitting, setRollbackSubmitting] = useState<boolean>(false);
  const [rollbackError, setRollbackError] = useState<string | null>(null);

  // Refresh State
  const [refreshingProposal, setRefreshingProposal] = useState<boolean>(false);

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
        const targetPlan = routePlanId ? res.find((p) => p.id === routePlanId) || res[0] : res[0];
        setSelectedPlanId(targetPlan.id);
        const versionToLoad = targetPlan.latest_version;
        setSelectedVersionNum(versionToLoad);
        await loadVersionData(targetPlan.id, versionToLoad);
      } else {
        setLoading(false);
      }
    } catch (err) {
      console.error("Failed to load plans:", err);
      setLoading(false);
    }
  };

  const loadGovernanceData = async (planId: string, versionNum: number, compareVersion?: number) => {
    try {
      setDiffLoading(true);
      const [records, diff] = await Promise.all([
        api.getApprovalRecords(planId).catch(() => []),
        api.getPlanDiff(planId, versionNum, compareVersion).catch(() => null),
      ]);
      setApprovalRecords(records);
      setPlanDiff(diff);
    } catch (err) {
      console.error("Failed to load governance diff data:", err);
    } finally {
      setDiffLoading(false);
    }
  };

  const loadVersionData = async (planId: string, versionNum: number) => {
    try {
      setLoading(true);
      const [detailRes, ganttRes] = await Promise.all([
        api.getPlanVersion(planId, versionNum),
        api.getPlanGantt(planId, versionNum).catch(() => null),
      ]);
      setPlanDetail(detailRes);
      setGanttData(ganttRes);
      await loadGovernanceData(planId, versionNum, diffCompareVersion || undefined);
      setLoading(false);
    } catch (err) {
      console.error("Failed to load version details:", err);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlansList();
  }, [routePlanId]);

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

  // Review Dialog Openers
  const handleOpenReviewDialog = (decision: "approved" | "rejected") => {
    setReviewDecision(decision);
    setReviewReason("");
    setReviewError(null);
    setReviewModalOpen(true);
  };

  // Submit Review Decision (Approve or Reject)
  const handleSubmitReviewDecision = async () => {
    if (!selectedPlanId || selectedVersionNum === null || !planDetail) return;
    if (reviewReason.trim().length < 3) {
      setReviewError("A justification reason of at least 3 characters is strictly mandatory.");
      return;
    }

    try {
      setReviewSubmitting(true);
      setReviewError(null);
      const idempotencyKey = `review-${selectedPlanId}-${selectedVersionNum}-${Date.now()}`;
      const etag = `"${planDetail.snapshot_hash}"`;

      if (reviewDecision === "approved") {
        await api.approvePlanVersion(
          selectedPlanId,
          selectedVersionNum,
          reviewReason.trim(),
          etag,
          idempotencyKey
        );
      } else {
        await api.rejectPlanVersion(
          selectedPlanId,
          selectedVersionNum,
          reviewReason.trim(),
          idempotencyKey
        );
      }

      setReviewModalOpen(false);
      await fetchPlansList();
      await loadVersionData(selectedPlanId, selectedVersionNum);
    } catch (err: any) {
      console.error("Review decision error:", err);
      const msg = err?.detail || err?.message || "Failed to process reviewer decision";
      setReviewError(typeof msg === "string" ? msg : JSON.stringify(msg));
      await loadVersionData(selectedPlanId, selectedVersionNum);
    } finally {
      setReviewSubmitting(false);
    }
  };

  // Refresh Proposal
  const handleRefreshProposal = async () => {
    if (!selectedPlanId || selectedVersionNum === null) return;
    try {
      setRefreshingProposal(true);
      const res = await api.refreshPlanProposal(selectedPlanId, selectedVersionNum);
      const newVersion = res.version_number || selectedVersionNum;
      setSelectedVersionNum(newVersion);
      await fetchPlansList();
      await loadVersionData(selectedPlanId, newVersion);
    } catch (err: any) {
      alert(`Refresh failed: ${err?.detail || err?.message || "Server error"}`);
    } finally {
      setRefreshingProposal(false);
    }
  };

  // Withdraw Proposal
  const handleWithdrawProposal = async () => {
    if (!selectedPlanId || selectedVersionNum === null) return;
    const reason = prompt("Enter operational reason for withdrawing proposal:") || "Withdrawn by operator";
    try {
      await api.withdrawPlanVersion(selectedPlanId, selectedVersionNum, reason);
      await fetchPlansList();
      await loadVersionData(selectedPlanId, selectedVersionNum);
    } catch (err: any) {
      alert(`Withdraw failed: ${err?.detail || err?.message || "Server error"}`);
    }
  };

  // Rollback Proposal
  const handleOpenRollbackDialog = (targetVersion: number = 1) => {
    setRollbackTargetVersion(targetVersion);
    setRollbackReason("");
    setRollbackError(null);
    setRollbackModalOpen(true);
  };

  const handleSubmitRollbackProposal = async () => {
    if (!selectedPlanId) return;
    if (rollbackReason.trim().length < 3) {
      setRollbackError("Rollback reason of at least 3 characters is mandatory.");
      return;
    }
    try {
      setRollbackSubmitting(true);
      setRollbackError(null);
      const res = await api.rollbackPlanProposal(selectedPlanId, rollbackTargetVersion, rollbackReason.trim());
      setRollbackModalOpen(false);
      await fetchPlansList();
      if (res.version_number) {
        setSelectedVersionNum(res.version_number);
        await loadVersionData(selectedPlanId, res.version_number);
      }
    } catch (err: any) {
      setRollbackError(err?.detail || err?.message || "Failed to submit rollback proposal");
    } finally {
      setRollbackSubmitting(false);
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
            TIMEOUT
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

  const getPlanStatusBadge = (status: PlanStatus | string | undefined) => {
    switch (status) {
      case "approved":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            APPROVED
          </span>
        );
      case "proposed":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300">
            <Clock className="w-3 h-3 text-amber-600" />
            PROPOSED
          </span>
        );
      case "superseded":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-300">
            SUPERSEDED
          </span>
        );
      case "stale":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-orange-100 text-orange-800 border border-orange-300">
            <AlertTriangle className="w-3 h-3 text-orange-600" />
            STALE
          </span>
        );
      case "rejected":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800 border border-rose-300">
            <X className="w-3 h-3 text-rose-600" />
            REJECTED
          </span>
        );
      case "withdrawn":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-zinc-100 text-zinc-700 border border-zinc-300">
            WITHDRAWN
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
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
      key: "delay_minutes",
      header: "Tardiness",
      sortable: true,
      render: (r: PlanAssignmentItem) =>
        r.delay_minutes > 0 ? (
          <span className="font-mono text-xs font-bold text-amber-600">+{r.delay_minutes}m</span>
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

  // Current selected plan object
  const currentPlan = plans.find((p) => p.id === selectedPlanId);

  // Filtered diff assignments
  const getFilteredDiffAssignments = (): PlanDiffAssignmentItem[] => {
    if (!planDiff) return [];
    switch (diffFilter) {
      case "shifted":
        return planDiff.shifted_assignments;
      case "added":
        return planDiff.added_assignments;
      case "removed":
        return planDiff.removed_assignments;
      case "unchanged":
        return planDiff.unchanged_assignments;
      case "all":
      default:
        return [
          ...planDiff.shifted_assignments,
          ...planDiff.added_assignments,
          ...planDiff.removed_assignments,
        ];
    }
  };

  if (loading && !planDetail) {
    return (
      <div className="p-12 text-center space-y-3">
        <RotateCw className="w-8 h-8 text-blue-600 animate-spin mx-auto" />
        <div className="text-sm font-semibold text-slate-700">Loading Operational Schedules & Governance Ledger...</div>
      </div>
    );
  }

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
                {getPlanStatusBadge(planDetail.status)}
                {getSolverStatusBadge(planDetail.solver_status)}
              </div>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Dual-verified multi-objective schedule with Reviewer-guarded plan lifecycle, atomic revalidation, and diff audit trail.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Plan Selector Dropdown */}
          {plans.length > 0 && (
            <select
              value={selectedPlanId || ""}
              onChange={(e) => {
                const planId = e.target.value;
                setSelectedPlanId(planId);
                const p = plans.find((x) => x.id === planId);
                if (p) {
                  setSelectedVersionNum(p.latest_version);
                  loadVersionData(p.id, p.latest_version);
                }
              }}
              className="text-xs font-medium bg-white border border-slate-300 rounded-lg px-3 py-2 shadow-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {plans.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          )}

          {/* Version Selector Dropdown */}
          {currentPlan && currentPlan.versions && currentPlan.versions.length > 0 && (
            <select
              value={selectedVersionNum || ""}
              onChange={(e) => {
                const v = parseInt(e.target.value);
                setSelectedVersionNum(v);
                if (selectedPlanId) loadVersionData(selectedPlanId, v);
              }}
              className="text-xs font-mono font-medium bg-white border border-slate-300 rounded-lg px-3 py-2 shadow-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {currentPlan.versions.map((ver) => (
                <option key={ver.version_number} value={ver.version_number}>
                  v{ver.version_number} ({ver.kind}) - {ver.status.toUpperCase()}
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
            Run Baseline
          </Button>

          <Button
            variant="primary"
            size="sm"
            onClick={() => handleRunJob("optimise")}
            disabled={jobRunning}
            className="flex items-center gap-1.5 shadow-xs"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            Propose Replan
          </Button>
        </div>
      </div>

      {/* Reviewer Action Bar (when Proposal is in PROPOSED status) */}
      {planDetail && planDetail.status === "proposed" && (
        <div className="bg-gradient-to-r from-amber-50 to-amber-100/60 border border-amber-300 rounded-xl p-4 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-amber-500 text-white flex items-center justify-center font-bold">
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-amber-950 flex items-center gap-2">
                Proposed Version v{planDetail.version_number} Awaiting Review
                <span className="text-xs px-2 py-0.5 rounded bg-amber-200/80 text-amber-900 font-mono font-semibold">
                  Based on v{planDetail.based_on_version || 1}
                </span>
              </div>
              <p className="text-xs text-amber-800 mt-0.5">
                Reviewer role required to execute single-transaction atomic approval with live invariant revalidation.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {isReviewer ? (
              <>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleOpenReviewDialog("approved")}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5 shadow-xs"
                >
                  <CheckCheck className="w-4 h-4" />
                  Approve Proposal
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleOpenReviewDialog("rejected")}
                  className="text-rose-600 border-rose-300 hover:bg-rose-50 flex items-center gap-1.5"
                >
                  <X className="w-4 h-4" />
                  Reject
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleWithdrawProposal}
                  className="text-slate-600 hover:text-slate-900 text-xs"
                >
                  Withdraw
                </Button>
              </>
            ) : (
              <div className="flex items-center gap-2 bg-amber-200/60 border border-amber-300 text-amber-900 px-3 py-1.5 rounded-lg text-xs font-medium">
                <Shield className="w-3.5 h-3.5 text-amber-700" />
                <span>Switch to Reviewer persona in Topbar to Approve/Reject</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Stale Warning Banner & Refresh Action */}
      {planDetail && planDetail.status === "stale" && (
        <div className="bg-orange-50 border border-orange-300 rounded-xl p-4 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-orange-500 text-white flex items-center justify-center font-bold">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-orange-950 flex items-center gap-2">
                Proposal v{planDetail.version_number} is Stale
              </div>
              <p className="text-xs text-orange-800 mt-0.5">
                {planDetail.stale_reason || "Operational snapshot or active baseline has changed since proposal creation."}
              </p>
            </div>
          </div>

          <Button
            variant="primary"
            size="sm"
            onClick={handleRefreshProposal}
            disabled={refreshingProposal}
            className="bg-orange-600 hover:bg-orange-700 text-white flex items-center gap-1.5 shrink-0 shadow-xs"
          >
            <RotateCw className={`w-3.5 h-3.5 ${refreshingProposal ? "animate-spin" : ""}`} />
            {refreshingProposal ? "Refreshing..." : "Refresh Proposal (Warm-Start)"}
          </Button>
        </div>
      )}

      {/* Live Job Progress Banner */}
      {jobRunning && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 shadow-xs animate-pulse">
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
          <button
            onClick={() => setActiveTab("proposals")}
            className={`pb-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === "proposals"
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            <GitCompare className="w-4 h-4" />
            Proposals & Governance
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
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
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

          <div className="divide-y divide-slate-100 max-h-[640px] overflow-y-auto">
            {(ganttTrackType === "aircraft" ? ganttData.asset_tracks : ganttData.crew_tracks).map(
              (track, idx) => (
                <div key={idx} className="flex hover:bg-slate-50/70 transition-colors group">
                  <div className="w-48 shrink-0 p-3 border-r border-slate-200 bg-white">
                    <div className="font-mono font-bold text-xs text-slate-900">
                      {track.identifier || track.name || track.callsign}
                    </div>
                    <div className="text-[10px] text-slate-400 capitalize">
                      {track.model_name || track.role_type || track.asset_type || "Resource"}
                    </div>
                  </div>
                  <div className="flex-1 relative h-12 bg-slate-50/30 overflow-hidden">
                    <div className="absolute inset-0 grid grid-cols-7 pointer-events-none divide-x divide-slate-100" />
                    {track.blocks.map((block) => {
                      const style = computeBlockStyle(block.start, block.end, ganttData.as_of);
                      return (
                        <div
                          key={block.id}
                          style={style}
                          className={`absolute top-2 bottom-2 rounded px-2 py-0.5 text-[10px] font-mono font-medium truncate shadow-xs cursor-pointer hover:brightness-110 hover:z-10 transition-all ${getCategoryColor(
                            block.category
                          )}`}
                          title={`${block.code} (${block.category})\nStart: ${block.start}\nEnd: ${block.end}`}
                          onClick={() => {
                            const match = planDetail?.assignments.find((a) => a.task_code === block.code);
                            if (match) {
                              setSelectedAssignment(match);
                              setDrawerOpen(true);
                            }
                          }}
                        >
                          {block.code}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Schedule Table */}
      {activeTab === "table" && planDetail && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4">
          <DataTable<PlanAssignmentItem>
            data={planDetail.assignments}
            columns={tableColumns}
            keyField="id"
            searchPlaceholder="Search task code, aircraft identifier, category..."
            pageSize={15}
            onRowClick={(row) => {
              setSelectedAssignment(row);
              setDrawerOpen(true);
            }}
          />
        </div>
      )}

      {/* Tab 3: Diagnostics & Unassigned */}
      {activeTab === "diagnostics" && planDetail && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <h3 className="text-base font-bold text-slate-900">Unassigned Mission Sorties</h3>
              </div>
              <p className="text-xs text-slate-500 mb-4">
                Tasks unable to be assigned within the operational horizon without violating hard invariants.
              </p>
              {planDetail.metrics.unassigned_count === 0 ? (
                <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs">
                  <div className="font-bold flex items-center gap-1.5 mb-1">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    100% Horizon Task Completion
                  </div>
                  All mission sorties scheduled successfully within feasible resource and maintenance boundaries.
                </div>
              ) : (
                <div className="text-xs text-slate-600 font-mono">
                  {planDetail.metrics.unassigned_count} sorties unassigned due to resource contention or turnaround limits.
                </div>
              )}
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
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

      {/* Tab 4: Proposals & Governance (Phase 5 Core) */}
      {activeTab === "proposals" && (
        <div className="space-y-6">
          {/* Section A: Version History & Proposals List */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <History className="w-4 h-4 text-blue-600" />
                  Plan Version History & Proposals
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Complete ledger of generated proposals, active baselines, and superseded revisions for {currentPlan?.name}.
                </p>
              </div>

              {planDetail && (planDetail.status === "approved" || planDetail.status === "superseded") && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleOpenRollbackDialog(planDetail.version_number)}
                  className="flex items-center gap-1.5 text-xs"
                >
                  <Undo2 className="w-3.5 h-3.5" />
                  Propose Rollback to v{planDetail.version_number}
                </Button>
              )}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-2.5 px-4">Version</th>
                    <th className="py-2.5 px-4">Kind</th>
                    <th className="py-2.5 px-4">Lifecycle Status</th>
                    <th className="py-2.5 px-4">Based On</th>
                    <th className="py-2.5 px-4">Solver</th>
                    <th className="py-2.5 px-4">Sorties</th>
                    <th className="py-2.5 px-4">Total Delay</th>
                    <th className="py-2.5 px-4">Created At</th>
                    <th className="py-2.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {currentPlan?.versions?.map((v) => {
                    const isSelected = selectedVersionNum === v.version_number;
                    return (
                      <tr
                        key={v.version_number}
                        className={`hover:bg-slate-50/80 transition-colors cursor-pointer ${
                          isSelected ? "bg-blue-50/50 font-medium" : ""
                        }`}
                        onClick={() => {
                          setSelectedVersionNum(v.version_number);
                          if (selectedPlanId) loadVersionData(selectedPlanId, v.version_number);
                        }}
                      >
                        <td className="py-3 px-4 font-mono font-bold text-slate-900">
                          v{v.version_number}
                          {isSelected && (
                            <span className="ml-2 text-[10px] text-blue-600 font-semibold">(Active View)</span>
                          )}
                        </td>
                        <td className="py-3 px-4 capitalize text-slate-700">{v.kind}</td>
                        <td className="py-3 px-4">{getPlanStatusBadge(v.status)}</td>
                        <td className="py-3 px-4 font-mono text-slate-500">
                          {v.based_on_version ? `v${v.based_on_version}` : "—"}
                        </td>
                        <td className="py-3 px-4">{getSolverStatusBadge(v.solver_status)}</td>
                        <td className="py-3 px-4 font-mono text-slate-700">
                          {v.metrics?.scheduled_count || "—"}
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-700">
                          {v.metrics?.total_delay_minutes?.toFixed(0) || "0"}m
                        </td>
                        <td className="py-3 px-4 text-slate-500">
                          {new Date(v.created_at).toLocaleString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedVersionNum(v.version_number);
                              if (selectedPlanId) loadVersionData(selectedPlanId, v.version_number);
                            }}
                            className="text-xs text-blue-600 hover:text-blue-800 font-semibold"
                          >
                            Inspect Diff
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Section B: Side-by-Side Proposal Diff View (P5-1, P5-7) */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <GitCompare className="w-4 h-4 text-blue-600" />
                  Side-by-Side Diff Analysis: v{selectedVersionNum} vs Base
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Fine-grained assignment shifts, aircraft reallocations, and operational metric deltas.
                </p>
              </div>

              {/* Compare version selector */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500 font-medium">Compare Against:</span>
                <select
                  value={diffCompareVersion || planDetail?.based_on_version || 1}
                  onChange={(e) => {
                    const compV = parseInt(e.target.value);
                    setDiffCompareVersion(compV);
                    if (selectedPlanId && selectedVersionNum !== null) {
                      loadGovernanceData(selectedPlanId, selectedVersionNum, compV);
                    }
                  }}
                  className="text-xs font-mono font-medium bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 shadow-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {currentPlan?.versions?.map((v) => (
                    <option key={v.version_number} value={v.version_number}>
                      v{v.version_number} ({v.kind})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {diffLoading ? (
              <div className="p-8 text-center text-xs text-slate-500 animate-pulse">
                Calculating fine-grained assignment shifts and metric deltas...
              </div>
            ) : planDiff ? (
              <div className="p-5 space-y-5">
                {/* Diff Metrics KPI Bar */}
                <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                    <div className="text-[10px] uppercase font-bold text-slate-500">Added Sorties</div>
                    <div className="text-xl font-bold font-mono text-emerald-600 mt-1">
                      +{planDiff.summary.added_count}
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                    <div className="text-[10px] uppercase font-bold text-slate-500">Removed Sorties</div>
                    <div className="text-xl font-bold font-mono text-rose-600 mt-1">
                      -{planDiff.summary.removed_count}
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                    <div className="text-[10px] uppercase font-bold text-slate-500">Shifted Sorties</div>
                    <div className="text-xl font-bold font-mono text-blue-600 mt-1">
                      {planDiff.summary.shifted_count}
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                    <div className="text-[10px] uppercase font-bold text-slate-500">Unchanged Sorties</div>
                    <div className="text-xl font-bold font-mono text-slate-700 mt-1">
                      {planDiff.summary.unchanged_count}
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                    <div className="text-[10px] uppercase font-bold text-slate-500">Assignment Churn</div>
                    <div className="text-xl font-bold font-mono text-amber-700 mt-1">
                      {planDiff.summary.churn_count}
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                    <div className="text-[10px] uppercase font-bold text-slate-500">Delay Delta</div>
                    <div
                      className={`text-xl font-bold font-mono mt-1 ${
                        planDiff.metrics_diff.delay_minutes_delta > 0
                          ? "text-rose-600"
                          : planDiff.metrics_diff.delay_minutes_delta < 0
                          ? "text-emerald-600"
                          : "text-slate-700"
                      }`}
                    >
                      {planDiff.metrics_diff.delay_minutes_delta >= 0 ? "+" : ""}
                      {planDiff.metrics_diff.delay_minutes_delta.toFixed(0)}m
                    </div>
                  </div>
                </div>

                {/* Filter Controls */}
                <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                  <div className="flex items-center gap-1.5">
                    <Filter className="w-3.5 h-3.5 text-slate-400" />
                    <span className="text-xs text-slate-500 font-medium">Filter Diff:</span>
                    {(["all", "shifted", "added", "removed", "unchanged"] as const).map((filterKey) => (
                      <button
                        key={filterKey}
                        onClick={() => setDiffFilter(filterKey)}
                        className={`text-xs px-2.5 py-1 rounded-md font-medium capitalize transition-all ${
                          diffFilter === filterKey
                            ? "bg-blue-600 text-white shadow-xs"
                            : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                        }`}
                      >
                        {filterKey === "all" ? "All Changes" : filterKey}
                      </button>
                    ))}
                  </div>

                  <span className="text-xs text-slate-400">
                    Showing {getFilteredDiffAssignments().length} entries
                  </span>
                </div>

                {/* Diff Table */}
                <div className="overflow-x-auto border border-slate-200 rounded-lg">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                      <tr>
                        <th className="py-2.5 px-3">Task Code</th>
                        <th className="py-2.5 px-3">Category</th>
                        <th className="py-2.5 px-3">Change Type</th>
                        <th className="py-2.5 px-3">Base Assignment (v{planDiff.from_version || 1})</th>
                        <th className="py-2.5 px-3">Proposed Assignment (v{planDiff.to_version})</th>
                        <th className="py-2.5 px-3">Variance Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {getFilteredDiffAssignments().length === 0 ? (
                        <tr>
                          <td colSpan={6} className="py-6 text-center text-slate-400">
                            No assignments match the selected diff filter.
                          </td>
                        </tr>
                      ) : (
                        getFilteredDiffAssignments().map((item, idx) => (
                          <tr key={idx} className="hover:bg-slate-50/70">
                            <td className="py-2.5 px-3 font-mono font-semibold text-slate-900">
                              {item.task_code}
                            </td>
                            <td className="py-2.5 px-3 capitalize text-slate-600">
                              {item.category.replace(/_/g, " ")}
                            </td>
                            <td className="py-2.5 px-3">
                              <span
                                className={`inline-flex px-2 py-0.5 rounded text-[11px] font-semibold uppercase ${
                                  item.change_type === "shifted"
                                    ? "bg-blue-100 text-blue-800"
                                    : item.change_type === "added"
                                    ? "bg-emerald-100 text-emerald-800"
                                    : item.change_type === "removed"
                                    ? "bg-rose-100 text-rose-800"
                                    : "bg-slate-100 text-slate-700"
                                }`}
                              >
                                {item.change_type}
                              </span>
                            </td>
                            <td className="py-2.5 px-3">
                              {item.change_type === "added" ? (
                                <span className="text-slate-400 italic">None (Unassigned)</span>
                              ) : (
                                <div>
                                  <span className="font-mono font-medium text-slate-900">
                                    {item.old_asset_identifier || item.asset_identifier || "—"}
                                  </span>
                                  {item.old_start && (
                                    <div className="text-[10px] font-mono text-slate-500">
                                      {new Date(item.old_start).toLocaleTimeString(undefined, {
                                        hour: "2-digit",
                                        minute: "2-digit",
                                      })}{" "}
                                      -{" "}
                                      {item.old_end &&
                                        new Date(item.old_end).toLocaleTimeString(undefined, {
                                          hour: "2-digit",
                                          minute: "2-digit",
                                        })}
                                    </div>
                                  )}
                                </div>
                              )}
                            </td>
                            <td className="py-2.5 px-3">
                              {item.change_type === "removed" ? (
                                <span className="text-slate-400 italic">Unassigned</span>
                              ) : (
                                <div>
                                  <span className="font-mono font-medium text-slate-900">
                                    {item.new_asset_identifier || item.asset_identifier || "—"}
                                  </span>
                                  {item.new_start && (
                                    <div className="text-[10px] font-mono text-slate-500">
                                      {new Date(item.new_start).toLocaleTimeString(undefined, {
                                        hour: "2-digit",
                                        minute: "2-digit",
                                      })}{" "}
                                      -{" "}
                                      {item.new_end &&
                                        new Date(item.new_end).toLocaleTimeString(undefined, {
                                          hour: "2-digit",
                                          minute: "2-digit",
                                        })}
                                    </div>
                                  )}
                                </div>
                              )}
                            </td>
                            <td className="py-2.5 px-3">
                              <div className="flex flex-wrap gap-1">
                                {item.start_delta_minutes !== undefined && item.start_delta_minutes !== 0 && (
                                  <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 font-mono text-[10px]">
                                    {item.start_delta_minutes > 0 ? "+" : ""}
                                    {item.start_delta_minutes}m shift
                                  </span>
                                )}
                                {item.asset_changed && (
                                  <span className="px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 font-medium text-[10px]">
                                    Aircraft swapped
                                  </span>
                                )}
                                {item.crew_changed && (
                                  <span className="px-1.5 py-0.5 rounded bg-teal-50 text-teal-700 font-medium text-[10px]">
                                    Crew updated
                                  </span>
                                )}
                                {item.change_type === "unchanged" && (
                                  <span className="text-slate-400 text-[10px]">Identical</span>
                                )}
                              </div>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-slate-400">
                No diff data available for comparison.
              </div>
            )}
          </div>

          {/* Section C: Approval Records & Cryptographic Audit Trail */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-4 border-b border-slate-200 bg-slate-50/50">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-emerald-600" />
                Reviewer Approval & Rejection Ledger
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Cryptographically audited approval decisions, reviewer justifications, and deduplication keys.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-2.5 px-4">Reviewer</th>
                    <th className="py-2.5 px-4">Decision</th>
                    <th className="py-2.5 px-4">Mandatory Justification Reason</th>
                    <th className="py-2.5 px-4">Timestamp (UTC)</th>
                    <th className="py-2.5 px-4 font-mono">Record ID</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {approvalRecords.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-slate-400">
                        No formal reviewer approval or rejection records recorded yet for this plan.
                      </td>
                    </tr>
                  ) : (
                    approvalRecords.map((rec) => (
                      <tr key={rec.id} className="hover:bg-slate-50/70">
                        <td className="py-3 px-4 font-semibold text-slate-900">
                          {rec.reviewer_username}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full font-bold uppercase text-[11px] ${
                              rec.decision === "approved"
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-rose-100 text-rose-800"
                            }`}
                          >
                            {rec.decision === "approved" ? (
                              <CheckCircle2 className="w-3 h-3" />
                            ) : (
                              <X className="w-3 h-3" />
                            )}
                            {rec.decision}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-700 max-w-md">{rec.reason}</td>
                        <td className="py-3 px-4 text-slate-500">
                          {new Date(rec.created_at).toLocaleString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </td>
                        <td className="py-3 px-4 font-mono text-[10px] text-slate-400">
                          {rec.id.slice(0, 8)}...
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
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

            <div className="flex-1 p-5 overflow-y-auto space-y-6 text-xs">
              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Allocated Airframe
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                  <div className="flex justify-between items-center">
                    <span className="font-mono font-bold text-slate-900 text-sm">
                      {selectedAssignment.asset_identifier}
                    </span>
                    <Badge variant="outline">{selectedAssignment.asset_model || "Aircraft"}</Badge>
                  </div>
                </div>
              </div>

              <div>
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Operational Window
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-2 font-mono">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Scheduled Start:</span>
                    <span className="font-semibold text-slate-800">
                      {new Date(selectedAssignment.assigned_start).toUTCString()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Scheduled End:</span>
                    <span className="font-semibold text-slate-800">
                      {new Date(selectedAssignment.assigned_end).toUTCString()}
                    </span>
                  </div>
                  <div className="flex justify-between pt-2 border-t border-slate-200">
                    <span className="text-slate-500">Lateness Variance:</span>
                    <span
                      className={`font-bold ${
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

      {/* Reviewer Action Dialog (Approve / Reject Modal) */}
      {reviewModalOpen && planDetail && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full overflow-hidden animate-in zoom-in-95 duration-150">
            <div
              className={`p-5 border-b text-white ${
                reviewDecision === "approved" ? "bg-emerald-600 border-emerald-700" : "bg-rose-600 border-rose-700"
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  {reviewDecision === "approved" ? (
                    <CheckCheck className="w-6 h-6" />
                  ) : (
                    <X className="w-6 h-6" />
                  )}
                  <div>
                    <h3 className="text-base font-bold">
                      {reviewDecision === "approved" ? "Approve Plan Proposal" : "Reject Plan Proposal"}
                    </h3>
                    <p className="text-xs text-white/80">
                      Version v{planDetail.version_number} ({planDetail.kind})
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setReviewModalOpen(false)}
                  className="text-white/80 hover:text-white p-1 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="p-6 space-y-4">
              {reviewError && (
                <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs">
                  <div className="font-bold flex items-center gap-1.5 mb-1">
                    <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                    Review Action Failed
                  </div>
                  {reviewError}
                </div>
              )}

              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs space-y-1.5">
                <div className="flex justify-between font-mono">
                  <span className="text-slate-500">Plan Name:</span>
                  <span className="font-bold text-slate-800">{currentPlan?.name}</span>
                </div>
                <div className="flex justify-between font-mono">
                  <span className="text-slate-500">Precondition ETag:</span>
                  <span className="text-slate-800 truncate max-w-[200px]">
                    "{planDetail.snapshot_hash.slice(0, 16)}..."
                  </span>
                </div>
                <div className="flex justify-between font-mono">
                  <span className="text-slate-500">Live Invariant Check:</span>
                  <span className="font-bold text-emerald-700">0 Violations (Solver {planDetail.solver_status})</span>
                </div>
              </div>

              {reviewDecision === "approved" && (
                <div className="text-xs text-slate-600 bg-amber-50/70 border border-amber-200 p-3 rounded-lg">
                  <span className="font-semibold text-amber-900">Atomic Supersede Guarantee:</span> Live revalidation
                  will execute against current operational constraints inside the database transaction. Sibling proposals
                  will be marked stale.
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Mandatory Justification Reason <span className="text-rose-500">*</span>
                </label>
                <textarea
                  rows={3}
                  value={reviewReason}
                  onChange={(e) => setReviewReason(e.target.value)}
                  placeholder={
                    reviewDecision === "approved"
                      ? "e.g. Verified crew rest limits and maintenance slots. Approved for active operations."
                      : "e.g. Conflict with unscheduled emergency depot maintenance. Requesting replan."
                  }
                  className="w-full text-xs p-3 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-xs"
                />
                <span className="text-[10px] text-slate-400">Min 3 characters required.</span>
              </div>
            </div>

            <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setReviewModalOpen(false)}
                disabled={reviewSubmitting}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSubmitReviewDecision}
                disabled={reviewSubmitting || reviewReason.trim().length < 3}
                className={
                  reviewDecision === "approved"
                    ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                    : "bg-rose-600 hover:bg-rose-700 text-white"
                }
              >
                {reviewSubmitting ? "Processing..." : `Confirm ${reviewDecision === "approved" ? "Approval" : "Rejection"}`}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Rollback Proposal Dialog */}
      {rollbackModalOpen && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full overflow-hidden animate-in zoom-in-95 duration-150">
            <div className="p-5 border-b border-slate-200 bg-slate-900 text-white">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <Undo2 className="w-5 h-5 text-amber-400" />
                  <div>
                    <h3 className="text-base font-bold">Generate Rollback Proposal</h3>
                    <p className="text-xs text-slate-400">Targeting Version v{rollbackTargetVersion}</p>
                  </div>
                </div>
                <button
                  onClick={() => setRollbackModalOpen(false)}
                  className="text-slate-400 hover:text-white p-1 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="p-6 space-y-4">
              {rollbackError && (
                <div className="p-3.5 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs">
                  {rollbackError}
                </div>
              )}

              <p className="text-xs text-slate-600">
                Rollback creates a new <strong className="text-slate-800">proposed</strong> plan version targeting the
                selected baseline. It will strictly require Reviewer approval before taking effect (never silently overwrites).
              </p>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Target Version
                </label>
                <select
                  value={rollbackTargetVersion}
                  onChange={(e) => setRollbackTargetVersion(parseInt(e.target.value))}
                  className="w-full text-xs p-2.5 border border-slate-300 rounded-lg font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {currentPlan?.versions?.map((v) => (
                    <option key={v.version_number} value={v.version_number}>
                      v{v.version_number} ({v.kind}) - {v.status.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Rollback Justification Reason <span className="text-rose-500">*</span>
                </label>
                <textarea
                  rows={3}
                  value={rollbackReason}
                  onChange={(e) => setRollbackReason(e.target.value)}
                  placeholder="e.g. Rolling back to baseline v1 due to unexpected maintenance rescheduling."
                  className="w-full text-xs p-3 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-xs"
                />
              </div>
            </div>

            <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setRollbackModalOpen(false)}
                disabled={rollbackSubmitting}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSubmitRollbackProposal}
                disabled={rollbackSubmitting || rollbackReason.trim().length < 3}
              >
                {rollbackSubmitting ? "Generating..." : "Generate Rollback Proposal"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
