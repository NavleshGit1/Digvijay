import React from "react";
import { StatusBadge } from "../components/data-display/StatusBadge";
import { Badge } from "../components/ui/Badge";

export const PersonnelPage: React.FC = () => {
  const crew = [
    { callsign: "VIPER-1", name: "Capt. Marcus Vance", role: "Fighter Pilot", quals: ["QUAL_NIGHT_OPS", "QUAL_INSTRUMENT"], status: "available", duty: "4.5 / 12 hrs" },
    { callsign: "WRENCH-LEAD", name: "Tech Sgt. Sarah Chen", role: "Avionics Specialist", quals: ["QUAL_AVIONICS_LV3", "QUAL_ENGINE_OVERHAUL"], status: "on_duty", duty: "6.0 / 12 hrs" },
    { callsign: "CARGO-CHIEF", name: "Maj. David Miller", role: "Transport Commander", quals: ["QUAL_HEAVY_AIRLIFT", "QUAL_INSTRUMENT"], status: "available", duty: "2.0 / 12 hrs" },
    { callsign: "RECON-OPS", name: "Lt. Elena Rostova", role: "Sensor Operator", quals: ["QUAL_SENSOR_PAYLOAD", "QUAL_ELECTRONIC_WARFARE"], status: "rest_period", duty: "0.0 / 12 hrs" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Personnel & Qualifications</h2>
          <p className="text-sm text-slate-500">
            Crew shift management, synthetic qualification certifications, and rest duty constraints.
          </p>
        </div>
        <Badge variant="default">120 Total Crew</Badge>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 overflow-hidden shadow-sm">
        <table className="w-full text-left text-sm text-slate-600">
          <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-500 border-b border-slate-200">
            <tr>
              <th className="px-5 py-3">Callsign / Name</th>
              <th className="px-5 py-3">Specialization</th>
              <th className="px-5 py-3">Status</th>
              <th className="px-5 py-3">Duty Hours (Rolling 24h)</th>
              <th className="px-5 py-3">Active Qualifications</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-mono text-xs">
            {crew.map((c) => (
              <tr key={c.callsign} className="hover:bg-slate-50/80">
                <td className="px-5 py-3">
                  <div className="font-bold text-slate-900">{c.callsign}</div>
                  <div className="text-[11px] text-slate-400 font-sans">{c.name}</div>
                </td>
                <td className="px-5 py-3 text-slate-700">{c.role}</td>
                <td className="px-5 py-3"><StatusBadge status={c.status} /></td>
                <td className="px-5 py-3 text-slate-800">{c.duty}</td>
                <td className="px-5 py-3">
                  <div className="flex flex-wrap gap-1">
                    {c.quals.map((q) => (
                      <span key={q} className="bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded text-[10px]">
                        {q}
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
