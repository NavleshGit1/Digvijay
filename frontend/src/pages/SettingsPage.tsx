import React, { useEffect, useState } from "react";
import {
  Clock,
  RotateCcw,
  Sliders,
  ShieldAlert,
  ShieldCheck,
  FileSpreadsheet,
  Download,
  Copy,
  Layers,
  X,
} from "lucide-react";
import { api } from "../services/api";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";
import { ConstraintSetItem } from "../types/api";

export const SettingsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState("clock");
  const [resetConfirm, setResetConfirm] = useState("");
  const [resetStatus, setResetStatus] = useState<string | null>(null);
  const [clockStatus, setClockStatus] = useState<string | null>(null);

  // Constraint Sets State
  const [constraintSets, setConstraintSets] = useState<ConstraintSetItem[]>([]);
  const [loadingSets, setLoadingSets] = useState(false);
  const [impactModal, setImpactModal] = useState<any | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [activationStatus, setActivationStatus] = useState<string | null>(null);

  // Audit Logs State
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loadingAudit, setLoadingAudit] = useState(false);
  const [exportingAudit, setExportingAudit] = useState(false);

  const handleAdvanceClock = async (seconds: number) => {
    try {
      setClockStatus("Advancing virtual clock...");
      const res = await api.updateClock({
        mode: "simulated",
        advance_seconds: seconds,
      } as any);
      setClockStatus(`Clock advanced to ${res.current_as_of}`);
    } catch (err: any) {
      setClockStatus(`Error: ${err?.detail || "Failed to update clock"}`);
    }
  };

  const handleResetDemo = async () => {
    if (resetConfirm !== "RESET") {
      setResetStatus("Error: Must type 'RESET' exactly.");
      return;
    }
    try {
      setResetStatus("Executing deterministic reset...");
      const res = await api.resetDemo(42);
      setResetStatus(`Success: ${res.message}`);
      setResetConfirm("");
    } catch (err: any) {
      setResetStatus(`Error: ${err?.detail || "Failed to reset demo"}`);
    }
  };

  // Load Constraint Sets
  const fetchConstraintSets = async () => {
    try {
      setLoadingSets(true);
      const data = await api.getConstraintSets();
      setConstraintSets(data);
    } catch (err) {
      console.error("Failed to load constraint sets:", err);
    } finally {
      setLoadingSets(false);
    }
  };

  // Preview Impact
  const handlePreviewImpact = async (setId: string) => {
    try {
      setPreviewLoading(true);
      const res = await api.previewConstraintSetImpact(setId);
      setImpactModal(res);
    } catch (err: any) {
      alert(`Impact preview failed: ${err?.detail || err?.message || "Server error"}`);
    } finally {
      setPreviewLoading(false);
    }
  };

  // Activate Constraint Set
  const handleActivateSet = async (setId: string) => {
    try {
      setActivationStatus("Activating constraint set...");
      const res = await api.activateConstraintSet(setId);
      setActivationStatus(`Successfully activated ${res.version}. Sibling proposals marked stale: ${res.affected_pending_proposals || 0}`);
      setImpactModal(null);
      await fetchConstraintSets();
    } catch (err: any) {
      setActivationStatus(`Activation failed: ${err?.detail || err?.message || "Server error"}`);
    }
  };

  // Clone Constraint Set
  const handleCloneSet = async (fromSet: ConstraintSetItem) => {
    const newName = prompt(`Enter name for draft cloned from ${fromSet.name}:`, `${fromSet.name} (Draft)`);
    if (!newName) return;
    try {
      await api.cloneConstraintSet(newName, fromSet.version);
      await fetchConstraintSets();
    } catch (err: any) {
      alert(`Clone failed: ${err?.detail || err?.message || "Server error"}`);
    }
  };

  // Load Audit Logs
  const fetchAuditLogs = async () => {
    try {
      setLoadingAudit(true);
      const data = await api.getAuditLogs({ limit: 50 });
      setAuditLogs(data);
    } catch (err) {
      console.error("Failed to load audit logs:", err);
    } finally {
      setLoadingAudit(false);
    }
  };

  // Export Signed Audit CSV
  const handleExportAuditCsv = async () => {
    try {
      setExportingAudit(true);
      await api.exportAuditLogsCsv();
    } catch (err: any) {
      alert(`Failed to export audit logs: ${err?.message || "Server error"}`);
    } finally {
      setExportingAudit(false);
    }
  };

  useEffect(() => {
    if (activeTab === "constraints") {
      fetchConstraintSets();
    } else if (activeTab === "audit") {
      fetchAuditLogs();
    }
  }, [activeTab]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">System Settings & Governance</h2>
          <p className="text-sm text-slate-500">
            Virtual clock manipulation, constraint registry governance, deterministic presets, and signed tamper-evident audit logs.
          </p>
        </div>
        <Badge variant="warning">Administrator Privileges Required</Badge>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200 overflow-x-auto">
        {[
          { id: "clock", label: "Virtual Clock Control", icon: Clock },
          { id: "constraints", label: "Constraint Registry (Governance)", icon: ShieldCheck },
          { id: "audit", label: "Cryptographic Audit Ledger", icon: FileSpreadsheet },
          { id: "reset", label: "Demo Reset & Presets", icon: RotateCcw },
          { id: "weights", label: "Objective Weights", icon: Sliders },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-slate-500 hover:text-slate-700"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Clock Control Tab */}
      {activeTab === "clock" && (
        <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-xs max-w-xl">
          <h3 className="text-sm font-bold text-slate-900 mb-1">Advance Virtual Operational Time</h3>
          <p className="text-xs text-slate-500 mb-4">
            Advances the system clock without altering the server host time. Synced across API and Celery workers via Redis.
          </p>

          {clockStatus && (
            <div className="mb-4 p-3 rounded bg-blue-50 text-blue-800 text-xs font-mono">
              {clockStatus}
            </div>
          )}

          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={() => handleAdvanceClock(3600)}>
              +1 Hour
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleAdvanceClock(14400)}>
              +4 Hours
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleAdvanceClock(86400)}>
              +1 Day (Roll Horizon)
            </Button>
          </div>
        </div>
      )}

      {/* Constraint Registry Tab (Phase 5 - P4-12, P5-12) */}
      {activeTab === "constraints" && (
        <div className="space-y-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div>
              <h3 className="text-sm font-bold text-slate-900">Versioned Operational Constraint Sets</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Parameters governing solver turnarounds, duty time limits, and rest rules. Activating a set automatically
                stales pending proposals across affected horizons.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={fetchConstraintSets}
              className="flex items-center gap-1.5 self-start md:self-auto"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Refresh Registry
            </Button>
          </div>

          {activationStatus && (
            <div className="p-3.5 rounded-xl bg-blue-50 border border-blue-200 text-blue-900 text-xs font-mono">
              {activationStatus}
            </div>
          )}

          {loadingSets ? (
            <div className="p-8 text-center text-xs text-slate-400">Loading constraint sets...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {constraintSets.map((cSet) => {
                const isActive = cSet.status === "active";
                return (
                  <div
                    key={cSet.id}
                    className={`bg-white rounded-xl border p-5 shadow-xs flex flex-col justify-between ${
                      isActive ? "border-emerald-300 ring-1 ring-emerald-300/50" : "border-slate-200"
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-mono font-bold text-sm text-slate-900">{cSet.version}</span>
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                            isActive
                              ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                              : cSet.status === "draft"
                              ? "bg-amber-100 text-amber-800 border border-amber-200"
                              : "bg-slate-100 text-slate-600"
                          }`}
                        >
                          {cSet.status}
                        </span>
                      </div>
                      <h4 className="text-xs font-bold text-slate-800 mb-3">{cSet.name}</h4>

                      <div className="space-y-1.5 font-mono text-[11px] bg-slate-50 p-3 rounded-lg border border-slate-100">
                        {Object.entries(cSet.parameters || {}).map(([k, val]) => (
                          <div key={k} className="flex justify-between">
                            <span className="text-slate-500 capitalize">{k.replace(/_/g, " ")}:</span>
                            <span className="font-semibold text-slate-800">{String(val)}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 pt-4 border-t border-slate-100 mt-4">
                      {!isActive && (
                        <>
                          <Button
                            variant="primary"
                            size="sm"
                            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white text-xs"
                            onClick={() => handleActivateSet(cSet.id)}
                          >
                            Activate Set
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full text-xs"
                            onClick={() => handlePreviewImpact(cSet.id)}
                            disabled={previewLoading}
                          >
                            Preview Impact
                          </Button>
                        </>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs text-slate-600 flex items-center gap-1"
                        onClick={() => handleCloneSet(cSet)}
                      >
                        <Copy className="w-3.5 h-3.5" />
                        Clone
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Audit Ledger Tab (Phase 5 - P5-3, P5-5) */}
      {activeTab === "audit" && (
        <div className="space-y-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div>
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <FileSpreadsheet className="w-4 h-4 text-blue-600" />
                Tamper-Evident SHA-256 Chained Audit Ledger
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Every state transition, approval, rejection, and configuration change is cryptographically chained.
              </p>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={handleExportAuditCsv}
              disabled={exportingAudit}
              className="flex items-center gap-1.5 self-start md:self-auto bg-blue-600 hover:bg-blue-700 text-white shadow-xs"
            >
              <Download className={`w-3.5 h-3.5 ${exportingAudit ? "animate-bounce" : ""}`} />
              {exportingAudit ? "Exporting Signed CSV..." : "Export Signed Audit CSV"}
            </Button>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-3 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-700">Recent Audit Records ({auditLogs.length})</span>
              <span className="text-[10px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 font-mono">
                X-Audit-Tamper-Proof: SHA256-Merkle-Chained
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="py-2.5 px-4">Timestamp (UTC)</th>
                    <th className="py-2.5 px-4">Actor</th>
                    <th className="py-2.5 px-4">Action</th>
                    <th className="py-2.5 px-4">Entity</th>
                    <th className="py-2.5 px-4 font-mono">Chain Hash</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {loadingAudit ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-400">
                        Loading audit ledger...
                      </td>
                    </tr>
                  ) : auditLogs.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-slate-400">
                        No audit records found.
                      </td>
                    </tr>
                  ) : (
                    auditLogs.map((entry: any) => (
                      <tr key={entry.id} className="hover:bg-slate-50/70">
                        <td className="py-2.5 px-4 text-slate-500 font-mono text-[11px]">
                          {new Date(entry.timestamp).toLocaleString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                            second: "2-digit",
                          })}
                        </td>
                        <td className="py-2.5 px-4 font-semibold text-slate-800">
                          {entry.actor_role ? `${entry.actor_role} (${entry.actor_id?.slice(0, 8)})` : entry.actor_id}
                        </td>
                        <td className="py-2.5 px-4">
                          <span className="px-2 py-0.5 rounded bg-slate-100 font-mono text-[11px] font-bold text-slate-800">
                            {entry.action}
                          </span>
                        </td>
                        <td className="py-2.5 px-4 text-slate-600">
                          {entry.entity_type} {entry.entity_id ? `(${entry.entity_id.slice(0, 8)})` : ""}
                        </td>
                        <td className="py-2.5 px-4 font-mono text-[10px] text-slate-400">
                          {entry.chain_hash ? `${entry.chain_hash.slice(0, 16)}...` : "—"}
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

      {/* Demo Reset Tab */}
      {activeTab === "reset" && (
        <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-xs max-w-xl">
          <div className="flex items-center gap-2 text-rose-600 mb-2">
            <ShieldAlert className="w-5 h-5" />
            <h3 className="text-sm font-bold text-slate-900">Deterministic Demonstration Reset</h3>
          </div>
          <p className="text-xs text-slate-500 mb-4">
            Resets all schedules, work orders, and events back to the initial deterministic seed (seed=42). Requires typing <strong className="text-slate-800">RESET</strong> to confirm.
          </p>

          {resetStatus && (
            <div className="mb-4 p-3 rounded bg-slate-100 text-slate-800 text-xs font-mono">
              {resetStatus}
            </div>
          )}

          <div className="flex gap-2">
            <input
              type="text"
              value={resetConfirm}
              onChange={(e) => setResetConfirm(e.target.value)}
              placeholder="Type RESET to confirm"
              className="flex-1 px-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 font-mono"
            />
            <Button variant="danger" size="sm" onClick={handleResetDemo}>
              Confirm Reset
            </Button>
          </div>
        </div>
      )}

      {/* Weights Tab */}
      {activeTab === "weights" && (
        <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-xs max-w-xl">
          <h3 className="text-sm font-bold text-slate-900 mb-1">CP-SAT Multi-Objective Weight Sets</h3>
          <p className="text-xs text-slate-500 mb-4">
            Versioned integer weights balancing operational tardiness against assignment churn and soft buffers.
          </p>
          <div className="space-y-3 font-mono text-xs">
            {[
              { name: "Delay Penalty (w_delay)", val: "100" },
              { name: "Unscheduled Task Penalty (w_unassigned)", val: "10,000" },
              { name: "Replanning Churn Weight (w_churn)", val: "50" },
              { name: "Predicted Downtime Buffer Penalty (w_buffer)", val: "30" },
            ].map((w, idx) => (
              <div key={idx} className="flex justify-between p-2 rounded bg-slate-50 border border-slate-100">
                <span className="text-slate-600">{w.name}</span>
                <span className="font-bold text-blue-700">{w.val}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Impact Preview Modal Dialog */}
      {impactModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-md w-full overflow-hidden animate-in zoom-in-95 duration-150">
            <div className="p-5 border-b border-slate-200 bg-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-amber-400" />
                <h3 className="text-sm font-bold">Constraint Activation Impact Preview</h3>
              </div>
              <button onClick={() => setImpactModal(null)} className="text-slate-400 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-amber-900">
                <div className="font-bold mb-1">Impact Warning</div>
                Activating this constraint set will automatically mark all pending proposals as{" "}
                <strong className="underline">stale</strong> to guarantee no un-revalidated proposals are approved.
              </div>

              <div className="space-y-2 font-mono">
                <div className="flex justify-between p-2 rounded bg-slate-50">
                  <span className="text-slate-500">Constraint Set Version:</span>
                  <span className="font-bold text-slate-800">{impactModal.constraint_set_version}</span>
                </div>
                <div className="flex justify-between p-2 rounded bg-slate-50">
                  <span className="text-slate-500">Active Plans Evaluated:</span>
                  <span className="font-bold text-slate-800">{impactModal.active_plans_checked}</span>
                </div>
                <div className="flex justify-between p-2 rounded bg-slate-50">
                  <span className="text-slate-500">Proposals Becoming Stale:</span>
                  <span className="font-bold text-rose-600">{impactModal.pending_proposals_will_be_staled}</span>
                </div>
              </div>
            </div>

            <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setImpactModal(null)}>
                Dismiss
              </Button>
              <Button
                variant="primary"
                size="sm"
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
                onClick={() => handleActivateSet(impactModal.constraint_set_id)}
              >
                Confirm & Activate
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
