import React from "react";
import { CalendarDays } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";

export const SchedulePage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">Operational Schedule</h2>
            <Badge variant="success">Active Approved Plan (v1.0)</Badge>
          </div>
          <p className="text-sm text-slate-500">
            CP-SAT constraint-optimized 7-day schedule with locked assignment preservation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm">Compare Diff</Button>
          <Button variant="primary" size="sm">Run Replanning Job</Button>
        </div>
      </div>

      {/* Schedule Tabs Preview */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm text-center">
        <CalendarDays className="w-12 h-12 text-blue-500 mx-auto mb-3 opacity-80" />
        <h3 className="text-base font-semibold text-slate-800">Timeline, Gantt & Constraint Matrix</h3>
        <p className="text-sm text-slate-500 max-w-md mx-auto mt-1 mb-4">
          Visual Gantt chart displaying 300 operational tasks, shift intervals, maintenance buffers, and locked commitments.
        </p>
        <div className="inline-flex gap-2">
          <span className="text-xs font-mono bg-slate-100 text-slate-700 px-3 py-1.5 rounded-lg border border-slate-200">
            CP-SAT Solver Status: OPTIMAL (Gap 0.0%)
          </span>
          <span className="text-xs font-mono bg-emerald-50 text-emerald-800 px-3 py-1.5 rounded-lg border border-emerald-200">
            Validator Pass: 10/10 Hard Constraints OK
          </span>
        </div>
      </div>
    </div>
  );
};
