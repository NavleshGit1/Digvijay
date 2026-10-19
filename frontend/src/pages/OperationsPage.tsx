import React, { useEffect, useState } from "react";
import { AlertTriangle, RefreshCw, Plus, ShieldAlert } from "lucide-react";
import { api } from "../services/api";
import { OperationalEvent, Task } from "../types/api";
import { DataTable, Column } from "../components/data-display/DataTable";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { StatusBadge } from "../components/data-display/StatusBadge";

export const OperationsPage: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [events, setEvents] = useState<OperationalEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter
  const [activeTab, setActiveTab] = useState<"tasks" | "events">("events");

  // Inject disruption modal state
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
      const [taskList, eventList] = await Promise.all([
        api.getTasks({ limit: 100 }),
        api.getEvents({ limit: 100 }),
      ]);
      setTasks(taskList);
      setEvents(eventList);
    } catch (err: any) {
      setError(err?.detail || "Failed to load operations data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

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
          injected_by: "Demo Simulation Orchestrator",
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
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">Operations & Event Stream</h2>
            <Badge variant="default">{events.length} Events Logged</Badge>
          </div>
          <p className="text-sm text-slate-500">
            Live operational disruption feed, flight work orders, and deterministic perturbation injects.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Stream
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowInjectModal(true)}
          >
            <Plus className="w-3.5 h-3.5 mr-1.5" />
            Inject Disruption Event
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 space-x-6 text-sm font-semibold">
        <button
          onClick={() => setActiveTab("events")}
          className={`pb-3 flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === "events"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <span>Disruption Events Stream</span>
          <Badge variant="default" className="text-[10px]">{events.length}</Badge>
        </button>
        <button
          onClick={() => setActiveTab("tasks")}
          className={`pb-3 flex items-center gap-2 border-b-2 transition-colors ${
            activeTab === "tasks"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <span>Operational Tasks & Sorties</span>
          <Badge variant="default" className="text-[10px]">{tasks.length}</Badge>
        </button>
      </div>

      {/* Content based on Tab */}
      {activeTab === "events" ? (
        <DataTable
          data={events}
          columns={eventColumns}
          keyField="id"
          loading={loading}
          error={error}
          onRetry={fetchData}
          searchPlaceholder="Search disruption events by code or target..."
        />
      ) : (
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

      {/* Inject Disruption Event Modal */}
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
