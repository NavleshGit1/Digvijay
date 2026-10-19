import React from "react";
import { StatusBadge } from "../components/data-display/StatusBadge";
import { Badge } from "../components/ui/Badge";

export const AssetsPage: React.FC = () => {
  const assets = [
    { id: "A-01", name: "F-16C Viper #01", type: "FIGHTER_MULTIROLE", status: "available", health: "94%", hours: "412.5 hrs", zone: "ZONE-A" },
    { id: "A-02", name: "F-16C Viper #02", type: "FIGHTER_MULTIROLE", status: "in_use", health: "88%", hours: "520.1 hrs", zone: "ZONE-A" },
    { id: "A-03", name: "C-130J Hercules #01", type: "TRANSPORT_CARGO", status: "maintenance", health: "65%", hours: "1140.0 hrs", zone: "ZONE-C" },
    { id: "A-04", name: "MQ-9 Reaper #01", type: "RECON_SURVEILLANCE", status: "available", health: "91%", hours: "340.2 hrs", zone: "ZONE-B" },
    { id: "A-05", name: "KC-135 Stratotanker #01", type: "REFUELER_TANKER", status: "available", health: "82%", hours: "980.4 hrs", zone: "ZONE-D" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Fleet Assets</h2>
          <p className="text-sm text-slate-500">
            Fictional equipment tracking, recorded vs. predicted readiness scores, and usage accruals.
          </p>
        </div>
        <Badge variant="default">40 Total Assets</Badge>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm">
        <table className="w-full text-left text-sm text-slate-600">
          <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-500 border-b border-slate-200">
            <tr>
              <th className="px-5 py-3">Asset ID</th>
              <th className="px-5 py-3">Type</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Health Score</th>
              <th className="px-5 py-3">Usage Hours</th>
              <th className="px-5 py-3">Sector</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-mono text-xs">
            {assets.map((a) => (
              <tr key={a.id} className="hover:bg-slate-50/80">
                <td className="px-5 py-3 font-bold text-slate-900">{a.id} · {a.name}</td>
                <td className="px-5 py-3 text-slate-600">{a.type}</td>
                <td className="px-5 py-3"><StatusBadge status={a.status} /></td>
                <td className="px-5 py-3 text-emerald-600 font-bold">{a.health}</td>
                <td className="px-5 py-3 text-slate-700">{a.hours}</td>
                <td className="px-5 py-3 text-blue-700">{a.zone}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
