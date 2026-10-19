import React from "react";
import { Play } from "lucide-react";
import { Button } from "../components/ui/Button";
import { DataKindBadge } from "../components/data-display/DataKindBadge";

export const ScenariosPage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Digital Twin & What-If Scenarios</h2>
          <p className="text-sm text-slate-500">
            SimPy discrete-event simulation and paired Monte Carlo trials using common random numbers.
          </p>
        </div>
        <Button variant="primary" size="sm">
          <Play className="w-3.5 h-3.5 mr-1.5" />
          Launch 50 Monte Carlo Trials
        </Button>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
          <h3 className="text-sm font-bold text-slate-800">Paired Scenario Evaluation: Nominal vs. Delayed</h3>
          <DataKindBadge kind="simulated" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-center">
          <div className="p-4 rounded-lg bg-slate-50 border border-slate-100">
            <p className="text-xs text-slate-500 uppercase">Baseline Mean Delay</p>
            <p className="text-2xl font-bold text-slate-800 mt-1">114.2 min</p>
            <p className="text-[10px] text-slate-400 mt-0.5">P95: 185 min</p>
          </div>
          <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200">
            <p className="text-xs text-emerald-700 uppercase">Replanned Mean Delay</p>
            <p className="text-2xl font-bold text-emerald-800 mt-1">42.8 min</p>
            <p className="text-[10px] text-emerald-600 mt-0.5">P95: 78 min (-57.8%)</p>
          </div>
          <div className="p-4 rounded-lg bg-slate-50 border border-slate-100">
            <p className="text-xs text-slate-500 uppercase">Infeasible Trial Rate</p>
            <p className="text-2xl font-bold text-slate-800 mt-1">0.0%</p>
            <p className="text-[10px] text-emerald-600 mt-0.5">50/50 trials valid</p>
          </div>
        </div>
      </div>
    </div>
  );
};
