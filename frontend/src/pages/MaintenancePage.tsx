import React, { useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "../components/ui/Button";
import { StatusBadge } from "../components/data-display/StatusBadge";
import { DataKindBadge } from "../components/data-display/DataKindBadge";

export const MaintenancePage: React.FC = () => {
  const [simulating, setSimulating] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const handleSimulateDelay = () => {
    setSimulating(true);
    setTimeout(() => {
      setSimulating(false);
      setFeedback("Disruption injected: ASSET-F16-04 delayed +4.5 hours. Downstream tasks flagged.");
    }, 1200);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Maintenance & Work Orders</h2>
          <p className="text-sm text-slate-500">
            Recorded downtime vs. ML predicted buffer zones and disruption delay injection.
          </p>
        </div>
        <Button
          variant="danger"
          size="sm"
          onClick={handleSimulateDelay}
          loading={simulating}
        >
          <AlertTriangle className="w-3.5 h-3.5 mr-1.5" />
          Simulate Maintenance Delay (+4.5h)
        </Button>
      </div>

      {feedback && (
        <div className="p-4 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-center justify-between">
          <span>{feedback}</span>
          <Button variant="outline" size="sm" onClick={() => setFeedback(null)}>Dismiss</Button>
        </div>
      )}

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm">
        <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-800">Open Work Orders</h3>
          <span className="text-xs text-slate-500">3 Open Items</span>
        </div>
        <div className="divide-y divide-slate-100 font-mono text-xs">
          {[
            { id: "WO-991", asset: "ASSET-F16-04", cat: "Turbine Seal Overhaul", planned: "08:00 - 14:00 UTC", predicted: "18:30 UTC (+4.5h)", status: "in_progress" },
            { id: "WO-992", asset: "ASSET-C130-01", cat: "Avionics Radar Calibration", planned: "10:00 - 16:00 UTC", predicted: "16:15 UTC (Nominal)", status: "scheduled" },
            { id: "WO-993", asset: "ASSET-MQ9-02", cat: "Optical Sensor Pod Clean", planned: "13:00 - 15:00 UTC", predicted: "15:00 UTC (Nominal)", status: "scheduled" },
          ].map((wo) => (
            <div key={wo.id} className="p-4 hover:bg-slate-50/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-900">{wo.id}</span>
                  <span className="text-slate-500">· {wo.asset}</span>
                  <StatusBadge status={wo.status} />
                </div>
                <p className="text-xs font-sans text-slate-600 mt-0.5">{wo.cat}</p>
                <p className="text-[11px] text-slate-400 mt-1">Confirmed Window: {wo.planned}</p>
              </div>
              <div className="text-right">
                <div className="flex items-center gap-1.5 justify-end mb-1">
                  <span className="text-xs font-bold text-purple-700">{wo.predicted}</span>
                  <DataKindBadge kind="predicted" />
                </div>
                <span className="text-[10px] text-slate-400">Soft Buffer Model v1.2</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
