import React from "react";
import { Radio } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { StatusBadge } from "../components/data-display/StatusBadge";

export const OperationsPage: React.FC = () => {
  const events = [
    {
      id: "EVT-2026-081",
      timestamp: "12:15 UTC",
      type: "maintenance_delay",
      entity: "ASSET-F16-04",
      severity: "high",
      validation: "passed",
      summary: "Turbine seal inspection extended by 4.5 hours",
    },
    {
      id: "EVT-2026-080",
      timestamp: "11:40 UTC",
      type: "resupply_delay",
      entity: "PART-ACTUATOR-HYD",
      severity: "medium",
      validation: "passed",
      summary: "Inbound shipment delayed 24h due to transit weather",
    },
    {
      id: "EVT-2026-079",
      timestamp: "10:15 UTC",
      type: "task_progress",
      entity: "TASK-SORTIE-102",
      severity: "informational",
      validation: "passed",
      summary: "Patrol sortie returned to Sector Alpha; assignment locked",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Operations Event Centre</h2>
          <p className="text-sm text-slate-500">
            Ingested operational disruptions, telemetry updates, and automated blast-radius assessments.
          </p>
        </div>
        <Badge variant="info">Live Stream Active</Badge>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-800">Operational Events Stream</h3>
          <span className="text-xs text-slate-500">Showing last 3 ingested disruptions</span>
        </div>
        <div className="divide-y divide-slate-100">
          {events.map((evt) => (
            <div key={evt.id} className="p-4 hover:bg-slate-50 flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center font-mono text-xs">
                  <Radio className="w-4 h-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-900">{evt.id}</span>
                    <span className="text-xs text-slate-400">· {evt.timestamp}</span>
                    <StatusBadge status={evt.severity} />
                  </div>
                  <p className="text-sm text-slate-700 mt-0.5">{evt.summary}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-slate-500">{evt.entity}</span>
                <Badge variant="success">Validated</Badge>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
