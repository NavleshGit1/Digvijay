import React, { useState } from "react";
import { Clock, RotateCcw, Sliders, ShieldAlert } from "lucide-react";
import { api } from "../services/api";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";

export const SettingsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState("clock");
  const [resetConfirm, setResetConfirm] = useState("");
  const [resetStatus, setResetStatus] = useState<string | null>(null);
  const [clockStatus, setClockStatus] = useState<string | null>(null);

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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">System Settings & Administration</h2>
          <p className="text-sm text-slate-500">
            Virtual clock manipulation, deterministic demo reset, objective weight sets, and engine circuit breakers.
          </p>
        </div>
        <Badge variant="warning">Administrator Privileges Required</Badge>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200">
        {[
          { id: "clock", label: "Virtual Clock Control", icon: Clock },
          { id: "reset", label: "Demo Reset & Presets", icon: RotateCcw },
          { id: "weights", label: "Objective Weights", icon: Sliders },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
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
        <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm max-w-xl">
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

      {/* Demo Reset Tab */}
      {activeTab === "reset" && (
        <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm max-w-xl">
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
        <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm max-w-xl">
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
    </div>
  );
};
