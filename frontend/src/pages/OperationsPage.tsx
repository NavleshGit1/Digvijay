import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  RefreshCw,
  Plus,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  Play,
  Clock,
  Zap,
  Check,
  Eye,
  GitBranch,
  Bell,
  Activity,
  Layers,
  Wrench,
} from "lucide-react";
import { api } from "../services/api";
import {
  AlertItem,
  AlertSummary,
  DisruptionImpactResponse,
  MaintenanceRecord,
  OperationalEvent,
  Task,
} from "../types/api";
import { DataTable, Column } from "../components/data-display/DataTable";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { StatusBadge } from "../components/data-display/StatusBadge";

export const OperationsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const tabParam = searchParams.get("tab") as "alerts" | "disruptions" | "events" | "tasks" | null;
  const [activeTab, setActiveTab] = useState<"alerts" | "disruptions" | "events" | "tasks">(
    tabParam || "alerts"
  );

  // Data states
  const [tasks, setTasks] = useState<Task[]>([]);
  const [events, setEvents] = useState<OperationalEvent[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [alertSummary, setAlertSummary] = useState<AlertSummary | null>(null);
  const [maintRecords, setMaintRecords] = useState<MaintenanceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Alerts filters
  const [alertStatusFilter, setAlertStatusFilter] = useState<string>("all");
  const [alertSeverityFilter, setAlertSeverityFilter] = useState<string>("all");
  const [evaluatingAlerts, setEvaluatingAlerts] = useState(false);
  const [evalFeedback, setEvalFeedback] = useState<string | null>(null);

  // Resolve Alert Modal
  const [resolveModalAlert, setResolveModalAlert] = useState<AlertItem | null>(null);
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [resolvingAlert, setResolvingAlert] = useState(false);

  // Disruption Simulator State (Phase 6 M1 Core)
  const [selectedMaintRecordId, setSelectedMaintRecordId] = useState<string>("");
  const [delayMinutes, setDelayMinutes] = useState<number>(60);
  const [disruptionReason, setDisruptionReason] = useState<string>(
    "Hydraulic pump inspection overrun - extended maintenance grounding"
  );
  const [impactAnalysis, setImpactAnalysis] = useState<DisruptionImpactResponse | null>(null);
  const [analyzingImpact, setAnalyzingImpact] = useState(false);
  const [injectingDelay, setInjectingDelay] = useState(false);
  const [disruptionFeedback, setDisruptionFeedback] = useState<string | null>(null);

  // Replanning State
  const [frozenWindowMinutes, setFrozenWindowMinutes] = useState<number>(120);
  const [replanRunning, setReplanRunning] = useState(false);
  const [replanFeedback, setReplanFeedback] = useState<string | null>(null);

  // Rolling Horizon State
  const [advanceMinutes, setAdvanceMinutes] = useState<number>(60);
  const [advancingHorizon, setAdvancingHorizon] = useState(false);

  // Generic Event Injection Modal State
  const [showInjectModal, setShowInjectModal] = useState(false);
  const [injectType, setInjectType] = useState("asset_unavailability");
  const [injectTargetType, setInjectTargetType] = useState("asset");
  const [injectTargetId, setInjectTargetId] = useState("SB-001");
  const [injectSeverity, setInjectSeverity] = useState("high");
  const [injectDescription, setInjectDescription] = useState("");
  const [injectReason, setInjectReason] = useState("");
  const [injectError, setInjectError] = useState<string | null>(null);
  const [injectSaving, setInjectSaving] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [taskList, eventList, alertsList, summaryRes, recordsList] = await Promise.all([
        api.getTasks({ limit: 100 }),
        api.getEvents({ limit: 100 }),
        api.getAlerts({ limit: 100 }),
        api.getAlertSummary().catch(() => null),
        api.getMaintenanceRecords().catch(() => []),
      ]);
      setTasks(taskList);
      setEvents(eventList);
      setAlerts(alertsList);
      setAlertSummary(summaryRes);
      setMaintRecords(recordsList);

      if (recordsList.length > 0 && !selectedMaintRecordId) {
        setSelectedMaintRecordId(recordsList[0].id);
      }
    } catch (err: any) {
      setError(err?.detail || "Failed to load operations data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleTabChange = (tab: "alerts" | "disruptions" | "events" | "tasks") => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  // Evaluate alerts rule engine on demand
  const handleEvaluateAlerts = async () => {
    try {
      setEvaluatingAlerts(true);
      setEvalFeedback(null);
      const res = await api.evaluateAlerts();
      setEvalFeedback(`Rules evaluated at ${new Date(res.evaluated_at).toLocaleTimeString()}: ${res.created} new alerts, ${res.updated} anti-flapping updates.`);
      const [alertsList, summaryRes] = await Promise.all([
        api.getAlerts({ limit: 100 }),
        api.getAlertSummary().catch(() => null),
      ]);
      setAlerts(alertsList);
      setAlertSummary(summaryRes);
    } catch (err: any) {
      setEvalFeedback(`Alert evaluation error: ${err?.detail || "Service error"}`);
    } finally {
      setEvaluatingAlerts(false);
    }
  };

  // Acknowledge alert
  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await api.acknowledgeAlert(alertId);
      const [alertsList, summaryRes] = await Promise.all([
        api.getAlerts({ limit: 100 }),
        api.getAlertSummary().catch(() => null),
      ]);
      setAlerts(alertsList);
      setAlertSummary(summaryRes);
    } catch (err: any) {
      alert(`Failed to acknowledge alert: ${err?.detail || "Error"}`);
    }
  };

  // Resolve alert modal submit
  const handleResolveAlertSubmit = async () => {
    if (!resolveModalAlert) return;
    try {
      setResolvingAlert(true);
      await api.resolveAlert(resolveModalAlert.id, resolutionNotes || undefined);
      setResolveModalAlert(null);
      setResolutionNotes("");
      const [alertsList, summaryRes] = await Promise.all([
        api.getAlerts({ limit: 100 }),
        api.getAlertSummary().catch(() => null),
      ]);
      setAlerts(alertsList);
      setAlertSummary(summaryRes);
    } catch (err: any) {
      alert(`Failed to resolve alert: ${err?.detail || "Error"}`);
    } finally {
      setResolvingAlert(false);
    }
  };

  // Preview NetworkX graph impact without mutating
  const handlePreviewImpact = async () => {
    if (!selectedMaintRecordId) return;
    try {
      setAnalyzingImpact(true);
      setDisruptionFeedback(null);
      const impact = await api.getMaintenanceImpact(selectedMaintRecordId, delayMinutes);
      setImpactAnalysis(impact);
      setDisruptionFeedback(`Impact detector traced ${impact.directly_affected_count} directly overlapping sorties and ${impact.cascading_affected_count} cascading downstream ripple tasks.`);
    } catch (err: any) {
      setDisruptionFeedback(`Impact preview failed: ${err?.detail || "Network error"}`);
    } finally {
      setAnalyzingImpact(false);
    }
  };

  // Inject maintenance delay and apply to DB (Milestone M1 Step 4)
  const handleInjectMaintenanceDelay = async () => {
    if (!selectedMaintRecordId) return;
    try {
      setInjectingDelay(true);
      setDisruptionFeedback(null);
      const res = await api.simulateMaintenanceDelay(
        selectedMaintRecordId,
        delayMinutes,
        disruptionReason || "Maintenance overrun simulated"
      );
      setImpactAnalysis(res.impact);
      setDisruptionFeedback(
        `Disruption injected! Maintenance extended to ${new Date(res.extended_scheduled_end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}. Active schedule flagged invalid. Ready for replanning.`
      );
      // Refresh events and alerts
      const [eventList, alertsList, summaryRes] = await Promise.all([
        api.getEvents({ limit: 100 }),
        api.getAlerts({ limit: 100 }),
        api.getAlertSummary().catch(() => null),
      ]);
      setEvents(eventList);
      setAlerts(alertsList);
      setAlertSummary(summaryRes);
    } catch (err: any) {
      setDisruptionFeedback(`Simulation failed: ${err?.detail || "Server error"}`);
    } finally {
      setInjectingDelay(false);
    }
  };

  // Trigger constrained replan (Milestone M1 Step 6)
  const handleTriggerReplan = async () => {
    try {
      setReplanRunning(true);
      setReplanFeedback(null);
      const res = await api.triggerReplan({
        frozen_window_minutes: frozenWindowMinutes,
        disruption_reason: disruptionReason || "Maintenance delay replanning",
        time_limit_seconds: 15.0,
        seed: 42,
        weight_set_version: 1,
        run_async: true,
      });
      setReplanFeedback(
        `Replanning solver job ${res.job_id.slice(0, 8)} queued! Warm start hints and frozen window enforced. Redirecting to review proposal...`
      );
      setTimeout(() => {
        navigate("/schedule");
      }, 1500);
    } catch (err: any) {
      setReplanFeedback(`Replanning trigger error: ${err?.detail || "Execution failed"}`);
      setReplanRunning(false);
    }
  };

  // Trigger rolling-horizon advance
  const handleRollingHorizon = async () => {
    try {
      setAdvancingHorizon(true);
      setReplanFeedback(null);
      const res = await api.triggerRollingHorizon({
        advance_minutes: advanceMinutes,
        frozen_window_minutes: frozenWindowMinutes,
        run_async: true,
      });
      setReplanFeedback(
        `Operational clock advanced by +${res.advance_minutes}m to ${new Date(res.new_as_of).toLocaleTimeString()}. Rolling horizon replan dispatched.`
      );
      setTimeout(() => {
        navigate("/schedule");
      }, 1500);
    } catch (err: any) {
      setReplanFeedback(`Rolling horizon advance error: ${err?.detail || "Failed"}`);
    } finally {
      setAdvancingHorizon(false);
    }
  };

  // Submit generic disruption event modal
  const handleInjectSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!injectDescription.trim() || !injectReason.trim()) {
      setInjectError("Description and mandatory audit justification are required.");
      return;
    }

    try {
      setInjectSaving(true);
      setInjectError(null);
      await api.injectEvent({
        event_type: injectType,
        affected_entity_type: injectTargetType,
        affected_entity_id: injectTargetId,
        severity: injectSeverity,
        payload_json: {
          description: injectDescription,
          injected_by: "Operations Orchestrator",
        },
        reason: injectReason,
      });
      setShowInjectModal(false);
      setInjectDescription("");
      setInjectReason("");
      fetchData();
    } catch (err: any) {
      setInjectError(err?.detail || "Failed to inject operational disruption event.");
    } finally {
      setInjectSaving(false);
    }
  };

  // Filtered alerts
  const filteredAlerts = alerts.filter((a) => {
    if (alertStatusFilter !== "all" && a.status !== alertStatusFilter) return false;
    if (alertSeverityFilter !== "all" && a.severity !== alertSeverityFilter) return false;
    return true;
  });

  // Table Columns
  const alertColumns: Column<AlertItem>[] = [
    {
      key: "severity",
      header: "Severity",
      sortable: true,
      render: (a) => (
        <Badge
          variant={
            a.severity === "critical"
              ? "danger"
              : a.severity === "high"
              ? "warning"
              : a.severity === "medium"
              ? "info"
              : "default"
          }
        >
          {a.severity.toUpperCase()}
        </Badge>
      ),
    },
    {
      key: "title",
      header: "Alert Title & Message",
      render: (a) => (
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-900 text-xs">{a.title}</span>
            {a.count > 1 && (
              <span className="text-[10px] bg-slate-200 text-slate-700 px-1.5 py-0.2 rounded font-mono font-bold">
                ×{a.count}
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-600 max-w-md line-clamp-1">{a.message}</p>
        </div>
      ),
    },
    {
      key: "rule_code",
      header: "Rule Code",
      sortable: true,
      render: (a) => <span className="font-mono text-xs font-semibold text-slate-700">{a.rule_code}</span>,
    },
    {
      key: "entity_id",
      header: "Affected Entity",
      sortable: true,
      render: (a) => (
        <span className="font-mono text-xs text-blue-800 font-semibold">
          {a.entity_type.toUpperCase()}: {a.entity_id}
        </span>
      ),
    },
    {
      key: "last_seen",
      header: "Last Seen",
      sortable: true,
      render: (a) => (
        <span className="font-mono text-xs text-slate-500">
          {new Date(a.last_seen).toLocaleDateString()} {new Date(a.last_seen).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      sortable: true,
      render: (a) => (
        <Badge
          variant={
            a.status === "new"
              ? "danger"
              : a.status === "acknowledged"
              ? "warning"
              : "success"
          }
        >
          {a.status.toUpperCase()}
        </Badge>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      render: (a) => (
        <div className="flex items-center gap-1.5">
          {a.status === "new" && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleAcknowledgeAlert(a.id)}
              className="text-amber-700 border-amber-300 hover:bg-amber-50 text-[11px] py-0.5 px-2"
            >
              <Check className="w-3 h-3 mr-1" />
              Ack
            </Button>
          )}
          {a.status !== "resolved" && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setResolveModalAlert(a);
                setResolutionNotes("");
              }}
              className="text-emerald-700 border-emerald-300 hover:bg-emerald-50 text-[11px] py-0.5 px-2"
            >
              Resolve
            </Button>
          )}
        </div>
      ),
    },
  ];

  const taskColumns: Column<Task>[] = [
    {
      key: "code",
      header: "Task Code & Category",
      sortable: true,
      render: (t) => (
        <div>
          <span className="font-mono font-bold text-slate-900">{t.code}</span>
          <span className="text-[11px] text-slate-500 block">
            {t.category.replace(/_/g, " ").toUpperCase()}
          </span>
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      sortable: true,
      render: (t) => <StatusBadge status={t.status} />,
    },
    {
      key: "priority",
      header: "Priority",
      sortable: true,
      render: (t) => (
        <Badge
          variant={
            t.priority === "critical"
              ? "danger"
              : t.priority === "high"
              ? "warning"
              : "default"
          }
        >
          {t.priority.toUpperCase()}
        </Badge>
      ),
    },
    {
      key: "duration_minutes",
      header: "Duration",
      sortable: true,
      align: "right",
      render: (t) => <span className="font-mono text-xs">{t.duration_minutes} min</span>,
    },
    {
      key: "zone_name",
      header: "Operating Base",
      sortable: true,
      render: (t) => <span className="font-mono text-xs text-blue-700">{t.zone_name.split("-")[0]}</span>,
    },
    {
      key: "earliest_start",
      header: "Planning Window",
      sortable: true,
      render: (t) => (
        <span className="font-mono text-xs text-slate-600">
          {new Date(t.earliest_start).toLocaleDateString()} {new Date(t.earliest_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} →{" "}
          {new Date(t.latest_end).toLocaleDateString()} {new Date(t.latest_end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      ),
    },
  ];

  const eventColumns: Column<OperationalEvent>[] = [
    {
      key: "event_type",
      header: "Disruption Code",
      sortable: true,
      render: (e) => (
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-500" />
          <span className="font-mono font-bold text-slate-900">
            {e.event_type.replace(/_/g, " ").toUpperCase()}
          </span>
        </div>
      ),
    },
    {
      key: "severity",
      header: "Severity",
      sortable: true,
      render: (e) => (
        <Badge
          variant={
            e.severity === "critical"
              ? "danger"
              : e.severity === "high"
              ? "warning"
              : "default"
          }
        >
          {e.severity.toUpperCase()}
        </Badge>
      ),
    },
    {
      key: "affected_entity",
      header: "Impact Target",
      sortable: true,
      render: (e) => (
        <span className="font-mono text-xs text-blue-800 font-semibold">
          {e.affected_entity_type.toUpperCase()}: {e.affected_entity_id}
        </span>
      ),
    },
    {
      key: "description",
      header: "Operational Blast Details",
      render: (e) => (
        <p className="text-xs text-slate-600 max-w-md truncate">
          {e.payload_json?.description || "Simulated operational disturbance."}
        </p>
      ),
    },
    {
      key: "timestamp",
      header: "Logged At",
      sortable: true,
      render: (e) => (
        <span className="font-mono text-xs text-slate-500">
          {new Date(e.timestamp).toLocaleDateString()} {new Date(e.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} UTC
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">Operations, Alerts & Disruption Sandbox</h2>
            <Badge variant="outline" className="border-blue-300 text-blue-700 bg-blue-50 text-[10px]">
              PHASE 6 (MILESTONE M1)
            </Badge>
          </div>
          <p className="text-sm text-slate-500">
            Anti-flapping alert subsystem, NetworkX graph impact detection, and frozen-window constrained replanning.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh All
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleEvaluateAlerts}
            disabled={evaluatingAlerts}
            className="text-blue-700 border-blue-300 hover:bg-blue-50"
          >
            <Activity className={`w-3.5 h-3.5 mr-1.5 ${evaluatingAlerts ? 'animate-spin' : ''}`} />
            Evaluate Rules Now
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowInjectModal(true)}
          >
            <Plus className="w-3.5 h-3.5 mr-1.5" />
            Inject Generic Disruption
          </Button>
        </div>
      </div>

      {evalFeedback && (
        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-800 text-xs flex items-center justify-between">
          <span>{evalFeedback}</span>
          <button onClick={() => setEvalFeedback(null)} className="text-blue-500 hover:text-blue-700">✕</button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-slate-200 space-x-6 text-sm font-semibold">
        <button
          onClick={() => handleTabChange("alerts")}
          className={`pb-3 flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === "alerts"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <Bell className="w-4 h-4" />
          <span>Operational Alerts</span>
          {alertSummary && (
            <Badge
              variant={alertSummary.critical_count > 0 ? "danger" : "default"}
              className="text-[10px]"
            >
              {alertSummary.total_active}
            </Badge>
          )}
        </button>

        <button
          onClick={() => handleTabChange("disruptions")}
          className={`pb-3 flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === "disruptions"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <GitBranch className="w-4 h-4" />
          <span>Disruption Sandbox & Replanning (M1)</span>
          {impactAnalysis && impactAnalysis.plan_invalidated && (
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
          )}
        </button>

        <button
          onClick={() => handleTabChange("events")}
          className={`pb-3 flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === "events"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          <span>Disruption Events Stream</span>
          <Badge variant="default" className="text-[10px]">{events.length}</Badge>
        </button>

        <button
          onClick={() => handleTabChange("tasks")}
          className={`pb-3 flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === "tasks"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Operational Tasks & Sorties</span>
          <Badge variant="default" className="text-[10px]">{tasks.length}</Badge>
        </button>
      </div>

      {/* Tab 1: Operational Alerts */}
      {activeTab === "alerts" && (
        <div className="space-y-4">
          {/* Alert KPI Summary Grid */}
          {alertSummary && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs">
                <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Active Alerts</div>
                <div className="mt-1 text-2xl font-bold text-slate-900 font-mono">
                  {alertSummary.total_active}
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {alertSummary.new_count} new · {alertSummary.acknowledged_count} acknowledged
                </div>
              </div>

              <div className="bg-white p-3.5 rounded-xl border border-rose-200 bg-rose-50/30 shadow-xs">
                <div className="text-[11px] font-semibold text-rose-700 uppercase tracking-wider">Critical Severity</div>
                <div className="mt-1 text-2xl font-bold text-rose-700 font-mono">
                  {alertSummary.critical_count}
                </div>
                <div className="mt-1 text-xs text-rose-600">Immediate recovery action required</div>
              </div>

              <div className="bg-white p-3.5 rounded-xl border border-amber-200 bg-amber-50/30 shadow-xs">
                <div className="text-[11px] font-semibold text-amber-700 uppercase tracking-wider">High Severity</div>
                <div className="mt-1 text-2xl font-bold text-amber-700 font-mono">
                  {alertSummary.high_count}
                </div>
                <div className="mt-1 text-xs text-amber-600">Operational readiness warning</div>
              </div>

              <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs">
                <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Anti-Flapping Filter</div>
                <div className="mt-1 flex items-center gap-1.5 text-sm font-bold text-emerald-700">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span>15-min Sliding Window</span>
                </div>
                <div className="mt-1 text-xs text-slate-500">Hysteresis deduplication active</div>
              </div>
            </div>
          )}

          {/* Alert Filters Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-white rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-slate-600">Status:</span>
              <div className="flex gap-1">
                {["all", "new", "acknowledged", "resolved"].map((st) => (
                  <button
                    key={st}
                    onClick={() => setAlertStatusFilter(st)}
                    className={`text-xs px-2.5 py-1 rounded-lg capitalize font-medium transition-colors ${
                      alertStatusFilter === st
                        ? "bg-slate-900 text-white font-semibold"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <span className="text-xs font-semibold text-slate-600">Severity:</span>
              <div className="flex gap-1">
                {["all", "critical", "high", "medium", "low"].map((sev) => (
                  <button
                    key={sev}
                    onClick={() => setAlertSeverityFilter(sev)}
                    className={`text-xs px-2.5 py-1 rounded-lg capitalize font-medium transition-colors ${
                      alertSeverityFilter === sev
                        ? "bg-blue-600 text-white font-semibold"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {sev}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Alerts Table */}
          <DataTable
            data={filteredAlerts}
            columns={alertColumns}
            keyField="id"
            loading={loading}
            error={error}
            onRetry={fetchData}
            searchPlaceholder="Search operational alerts by rule code, title, or target entity..."
          />
        </div>
      )}

      {/* Tab 2: Disruption Sandbox & Replanning (Milestone M1 Core) */}
      {activeTab === "disruptions" && (
        <div className="space-y-6">
          {/* Milestone M1 Flow Header Banner */}
          <div className="bg-gradient-to-r from-blue-900 to-indigo-900 text-white p-5 rounded-xl shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <GitBranch className="w-5 h-5 text-blue-300" />
                <h3 className="text-base font-bold tracking-tight">Milestone M1: End-to-End Operational Disruption Workflow</h3>
              </div>
              <Badge variant="outline" className="border-blue-400 text-blue-200 text-xs">
                Graph Traversal + CP-SAT Warm Start
              </Badge>
            </div>
            <p className="text-xs text-blue-200 max-w-3xl leading-relaxed">
              Inject a maintenance overrun delay $\rightarrow$ NetworkX graph impact detector traverses DAG descendants $\rightarrow$ active schedule invalidated $\rightarrow$ trigger constrained replan with frozen window & churn penalty minimization.
            </p>
          </div>

          {disruptionFeedback && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 text-xs space-y-1">
              <div className="font-bold flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <span>Simulation Status Update</span>
              </div>
              <p>{disruptionFeedback}</p>
            </div>
          )}

          {replanFeedback && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-900 text-xs space-y-1">
              <div className="font-bold flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Replanning Orchestrator</span>
              </div>
              <p>{replanFeedback}</p>
            </div>
          )}

          {/* Sandbox Two-Column Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Disruption Injector & Controls (5 cols) */}
            <div className="lg:col-span-5 space-y-5">
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <Wrench className="w-4 h-4 text-blue-600" />
                    <h4 className="font-bold text-slate-900 text-sm">Maintenance Delay Simulator</h4>
                  </div>
                  <Badge variant="default" className="text-[10px]">Step 4 Injector</Badge>
                </div>

                <div className="space-y-3 text-xs">
                  <div>
                    <label className="font-semibold text-slate-700 block mb-1">
                      Target Airframe Maintenance Work Order
                    </label>
                    <select
                      value={selectedMaintRecordId}
                      onChange={(e) => setSelectedMaintRecordId(e.target.value)}
                      className="w-full border border-slate-300 rounded-lg p-2.5 bg-white text-xs font-mono font-medium"
                    >
                      {maintRecords.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.asset_identifier} — {m.category.toUpperCase()} ({new Date(m.start_time).toLocaleDateString()})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="font-semibold text-slate-700">Simulated Delay Overrun</label>
                      <span className="font-mono font-bold text-blue-700">+{delayMinutes} minutes</span>
                    </div>
                    <input
                      type="range"
                      min={15}
                      max={240}
                      step={15}
                      value={delayMinutes}
                      onChange={(e) => setDelayMinutes(parseInt(e.target.value))}
                      className="w-full accent-blue-600"
                    />
                    <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-1">
                      <span>+15m</span>
                      <span>+60m</span>
                      <span>+120m</span>
                      <span>+240m</span>
                    </div>
                  </div>

                  <div>
                    <label className="font-semibold text-slate-700 block mb-1">Disruption Justification & Findings</label>
                    <textarea
                      value={disruptionReason}
                      onChange={(e) => setDisruptionReason(e.target.value)}
                      rows={2}
                      className="w-full border border-slate-300 rounded-lg p-2 bg-white text-xs"
                      placeholder="State mechanical finding or reason for delay..."
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2 pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handlePreviewImpact}
                      loading={analyzingImpact}
                      className="text-blue-700 border-blue-300 hover:bg-blue-50"
                    >
                      <Eye className="w-3.5 h-3.5 mr-1" />
                      Preview Impact
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleInjectMaintenanceDelay}
                      loading={injectingDelay}
                      className="bg-amber-600 hover:bg-amber-700 text-white"
                    >
                      <AlertTriangle className="w-3.5 h-3.5 mr-1" />
                      Inject & Invalidate
                    </Button>
                  </div>
                </div>
              </div>

              {/* Replanning Controls Panel */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
                <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-emerald-600" />
                    <h4 className="font-bold text-slate-900 text-sm">Constrained Replan Controls</h4>
                  </div>
                  <Badge variant="outline" className="border-emerald-300 text-emerald-700 text-[10px]">
                    Step 6 Solver
                  </Badge>
                </div>

                <div className="space-y-3 text-xs">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <label className="font-semibold text-slate-700">Frozen Window Lockout</label>
                      <span className="font-mono font-bold text-slate-800">{frozenWindowMinutes} minutes</span>
                    </div>
                    <p className="text-[11px] text-slate-500 mb-2">
                      Commitments starting within this window or marked locked are strictly preserved.
                    </p>
                    <div className="flex gap-2">
                      {[60, 120, 180, 240].map((mins) => (
                        <button
                          key={mins}
                          onClick={() => setFrozenWindowMinutes(mins)}
                          className={`flex-1 py-1 px-2 rounded-lg text-xs font-mono font-semibold transition-colors ${
                            frozenWindowMinutes === mins
                              ? "bg-slate-900 text-white"
                              : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                          }`}
                        >
                          {mins}m
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="pt-2 space-y-2">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleTriggerReplan}
                      loading={replanRunning}
                      className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2 shadow-xs"
                    >
                      <Play className="w-4 h-4 mr-1.5 fill-current" />
                      Trigger Constrained Replan (CP-SAT)
                    </Button>

                    <div className="pt-2 border-t border-slate-100 mt-2">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-slate-700">Horizon Advance Step</span>
                        <span className="font-mono font-bold text-slate-800">+{advanceMinutes}m</span>
                      </div>
                      <div className="flex gap-2 mb-2">
                        {[30, 60, 120].map((step) => (
                          <button
                            key={step}
                            onClick={() => setAdvanceMinutes(step)}
                            className={`flex-1 py-1 px-2 rounded-lg text-xs font-mono font-semibold transition-colors ${
                              advanceMinutes === step
                                ? "bg-slate-900 text-white"
                                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                            }`}
                          >
                            +{step}m
                          </button>
                        ))}
                      </div>
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleRollingHorizon}
                      loading={advancingHorizon}
                      className="w-full text-slate-700 border-slate-300 hover:bg-slate-50 font-medium py-1.5"
                    >
                      <Clock className="w-3.5 h-3.5 mr-1.5" />
                      Advance Operational Horizon (+{advanceMinutes}m)
                    </Button>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column: NetworkX Operational Impact Report (7 cols) */}
            <div className="lg:col-span-7">
              {impactAnalysis ? (
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                    <div>
                      <h4 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                        <GitBranch className="w-4 h-4 text-blue-600" />
                        NetworkX Operational Blast & DAG Ripple Report
                      </h4>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Airframe: <span className="font-mono font-bold text-slate-800">{impactAnalysis.asset_identifier}</span> · Delay: +{impactAnalysis.delay_minutes}m
                      </p>
                    </div>

                    {impactAnalysis.plan_invalidated ? (
                      <Badge variant="danger" className="text-xs font-mono font-bold animate-pulse">
                        PLAN INVALIDATED
                      </Badge>
                    ) : (
                      <Badge variant="success" className="text-xs font-mono">
                        NO SORTIE CONFLICT
                      </Badge>
                    )}
                  </div>

                  {/* Impact Summary Numbers */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="p-3 rounded-lg bg-rose-50 border border-rose-200">
                      <div className="text-[11px] font-semibold text-rose-700 uppercase">Directly Overlapping</div>
                      <div className="text-xl font-bold font-mono text-rose-900 mt-0.5">
                        {impactAnalysis.directly_affected_count} sorties
                      </div>
                    </div>
                    <div className="p-3 rounded-lg bg-amber-50 border border-amber-200">
                      <div className="text-[11px] font-semibold text-amber-700 uppercase">Cascading Ripples</div>
                      <div className="text-xl font-bold font-mono text-amber-900 mt-0.5">
                        {impactAnalysis.cascading_affected_count} tasks
                      </div>
                    </div>
                    <div className="p-3 rounded-lg bg-slate-50 border border-slate-200">
                      <div className="text-[11px] font-semibold text-slate-600 uppercase">Crew Conflicts</div>
                      <div className="text-xl font-bold font-mono text-slate-900 mt-0.5">
                        {impactAnalysis.crew_conflicts_count}
                      </div>
                    </div>
                  </div>

                  {/* Affected Tasks List */}
                  <div className="space-y-2">
                    <h5 className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                      Affected Downstream Operational Tasks ({impactAnalysis.affected_tasks.length})
                    </h5>

                    {impactAnalysis.affected_tasks.length === 0 ? (
                      <div className="p-6 text-center text-slate-400 text-xs border border-dashed border-slate-200 rounded-lg">
                        No downstream sorties or dependency DAG tasks affected by this maintenance extension.
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                        {impactAnalysis.affected_tasks.map((task) => (
                          <div
                            key={task.task_id}
                            className="p-3 rounded-lg border border-slate-200 bg-slate-50/50 hover:bg-white transition-colors flex items-start justify-between text-xs"
                          >
                            <div className="space-y-1">
                              <div className="flex items-center gap-2">
                                <span className="font-mono font-bold text-slate-900">{task.code}</span>
                                <Badge variant="outline" className="text-[10px]">
                                  {task.category.toUpperCase()}
                                </Badge>
                                {task.ripple_depth !== undefined && task.ripple_depth > 0 && (
                                  <Badge variant="warning" className="text-[10px]">
                                    Ripple Depth {task.ripple_depth}
                                  </Badge>
                                )}
                              </div>
                              <p className="text-slate-600 font-medium">{task.title}</p>
                              {task.conflict_reason && (
                                <p className="text-[11px] text-rose-600 font-semibold">{task.conflict_reason}</p>
                              )}
                            </div>

                            <div className="text-right text-[11px] font-mono text-slate-500 whitespace-nowrap ml-4">
                              <div>{new Date(task.assigned_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} → {new Date(task.assigned_end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                              {task.overlap_minutes ? (
                                <span className="text-rose-600 font-bold font-mono">Overlap: {task.overlap_minutes}m</span>
                              ) : null}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="bg-white p-12 rounded-xl border border-dashed border-slate-300 text-center space-y-3">
                  <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
                    <Eye className="w-6 h-6" />
                  </div>
                  <h4 className="text-sm font-bold text-slate-800">No Disruption Simulation Selected</h4>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                    Select a maintenance record on the left and click <b>Preview Impact</b> or <b>Inject & Invalidate</b> to run the NetworkX dependency graph traversal.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Events Stream */}
      {activeTab === "events" && (
        <DataTable
          data={events}
          columns={eventColumns}
          keyField="id"
          loading={loading}
          error={error}
          onRetry={fetchData}
          searchPlaceholder="Search disruption events by code or target..."
        />
      )}

      {/* Tab 4: Operational Tasks */}
      {activeTab === "tasks" && (
        <DataTable
          data={tasks}
          columns={taskColumns}
          keyField="id"
          loading={loading}
          error={error}
          onRetry={fetchData}
          searchPlaceholder="Search operational tasks by code or category..."
        />
      )}

      {/* Resolve Alert Modal */}
      {resolveModalAlert && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full shadow-2xl border border-slate-200 p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                <h3 className="font-bold text-slate-900">Resolve Operational Alert</h3>
              </div>
              <button onClick={() => setResolveModalAlert(null)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>

            <div className="text-xs space-y-2">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                <div className="font-bold text-slate-800">{resolveModalAlert.title}</div>
                <div className="text-slate-500 mt-1">{resolveModalAlert.message}</div>
                <div className="text-[10px] font-mono text-blue-700 mt-2">
                  Target: {resolveModalAlert.entity_type}/{resolveModalAlert.entity_id}
                </div>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Resolution Notes (Optional)</label>
                <textarea
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  placeholder="e.g. Parts arrived from central depot; inspection complete and certified airworthy."
                  rows={3}
                  className="w-full border border-slate-300 rounded-lg p-2.5 bg-white text-xs"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <Button variant="outline" size="sm" type="button" onClick={() => setResolveModalAlert(null)}>
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleResolveAlertSubmit}
                  loading={resolvingAlert}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                >
                  Mark Alert Resolved
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Inject Generic Disruption Event Modal */}
      {showInjectModal && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full shadow-2xl border border-slate-200 p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <h3 className="font-bold text-slate-900">Inject Simulated Disruption Event</h3>
              </div>
              <button onClick={() => setShowInjectModal(false)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>

            {injectError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs">
                {injectError}
              </div>
            )}

            <form onSubmit={handleInjectSubmit} className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Disruption Event Type</label>
                <select
                  value={injectType}
                  onChange={(e) => setInjectType(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2 bg-white"
                >
                  <option value="asset_unavailability">Asset Unavailability (Mechanical Grounding)</option>
                  <option value="maintenance_delay">Maintenance Delay (Inspection Overrun)</option>
                  <option value="environmental_restriction">Environmental Restriction (Weather Gate)</option>
                  <option value="resupply_delay">Resupply Delay (Spares Shipment Latency)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Affected Entity Type</label>
                  <select
                    value={injectTargetType}
                    onChange={(e) => setInjectTargetType(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg p-2 bg-white"
                  >
                    <option value="asset">Aircraft Asset</option>
                    <option value="zone">Airbase Zone</option>
                    <option value="task">Operational Task</option>
                  </select>
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Target Identifier</label>
                  <input
                    type="text"
                    value={injectTargetId}
                    onChange={(e) => setInjectTargetId(e.target.value)}
                    placeholder="e.g. SB-001 or BASE-ALPHA"
                    className="w-full border border-slate-300 rounded-lg p-2 bg-white font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Severity Level</label>
                <select
                  value={injectSeverity}
                  onChange={(e) => setInjectSeverity(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2 bg-white"
                >
                  <option value="critical">Critical (Immediate Replanning Required)</option>
                  <option value="high">High (Elevated Operational Impact)</option>
                  <option value="medium">Medium (Manageable Disruption)</option>
                  <option value="low">Low (Informational)</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Disruption Description</label>
                <textarea
                  value={injectDescription}
                  onChange={(e) => setInjectDescription(e.target.value)}
                  placeholder="e.g. Hydraulic pump seal leak detected during pre-flight check. Airframe grounded for unscheduled repair."
                  rows={2}
                  className="w-full border border-slate-300 rounded-lg p-2 bg-white"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Audit Justification (Mandatory)
                </label>
                <textarea
                  value={injectReason}
                  onChange={(e) => setInjectReason(e.target.value)}
                  placeholder="State reason for injecting simulation disruption..."
                  rows={2}
                  className="w-full border border-slate-300 rounded-lg p-2 bg-white"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <Button variant="outline" size="sm" type="button" onClick={() => setShowInjectModal(false)}>
                  Cancel
                </Button>
                <Button variant="primary" size="sm" type="submit" loading={injectSaving}>
                  Inject & Log Audit Record
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
