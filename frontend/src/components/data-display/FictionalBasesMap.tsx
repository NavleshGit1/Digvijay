import React, { useState } from "react";
import { Shield, Radio, Navigation, Wind } from "lucide-react";
import { Badge } from "../ui/Badge";
import { Zone } from "../../types/api";

interface FictionalBasesMapProps {
  zones: Zone[];
  selectedZoneId?: string | null;
  onSelectZone?: (zoneId: string | null) => void;
}

export const FictionalBasesMap: React.FC<FictionalBasesMapProps> = ({
  zones,
  selectedZoneId,
  onSelectZone,
}) => {
  const [activeBase, setActiveBase] = useState<string | null>(selectedZoneId || null);

  // Fictional base metadata with visual map placements
  const baseCoordinates: Record<string, { x: number; y: number; sector: string; fleet: string; wind: string }> = {
    "BASE_ALPHA": { x: 260, y: 130, sector: "Northern Operating Sector", fleet: "Su-30MKI, Rafale", wind: "080° / 12kt" },
    "BASE_BRAVO": { x: 190, y: 220, sector: "Central Operating Sector", fleet: "Tejas LCA, Rafale", wind: "240° / 08kt" },
    "BASE_CHARLIE": { x: 440, y: 270, sector: "Eastern Forward Sector", fleet: "C-130J, Il-78 MKI", wind: "110° / 15kt" },
    "BASE-ALPHA": { x: 260, y: 130, sector: "Northern Operating Sector", fleet: "Su-30MKI, Rafale", wind: "080° / 12kt" },
    "BASE-BRAVO": { x: 190, y: 220, sector: "Central Operating Sector", fleet: "Tejas LCA, Rafale", wind: "240° / 08kt" },
    "BASE-CHARLIE": { x: 440, y: 270, sector: "Eastern Forward Sector", fleet: "C-130J, Il-78 MKI", wind: "110° / 15kt" },
  };

  const handleBaseClick = (zoneId: string) => {
    const next = activeBase === zoneId ? null : zoneId;
    setActiveBase(next);
    if (onSelectZone) onSelectZone(next);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg relative text-slate-100">
      {/* Top Map Header */}
      <div className="p-4 bg-slate-950/80 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Radio className="w-4 h-4 text-emerald-400 animate-pulse" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Fictional Operating Sector Map (Unclassified Demo Grid)
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="border-amber-500/40 text-amber-400 bg-amber-950/30 text-[10px]">
            SYNTHETIC GRID · NO CLASSIFIED SITES
          </Badge>
          <span className="text-[11px] font-mono text-slate-400">
            DATUM: WGS-84 GRID-REF
          </span>
        </div>
      </div>

      {/* Visual Tactical Canvas */}
      <div className="relative w-full h-[360px] bg-[#0b1329] overflow-hidden select-none">
        {/* Tactical Grid Background */}
        <svg className="absolute inset-0 w-full h-full opacity-20 pointer-events-none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="tactical-grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#38bdf8" strokeWidth="0.5" strokeDasharray="2,2" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#tactical-grid)" />
          {/* Latitude & Longitude Guidelines */}
          <line x1="0" y1="180" x2="100%" y2="180" stroke="#38bdf8" strokeWidth="1" strokeDasharray="4,6" opacity="0.4" />
          <line x1="300" y1="0" x2="300" y2="100%" stroke="#38bdf8" strokeWidth="1" strokeDasharray="4,6" opacity="0.4" />
        </svg>

        {/* Tactical Flight Paths / Connecting Air Corridors */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" xmlns="http://www.w3.org/2000/svg">
          <line x1="260" y1="130" x2="190" y2="220" stroke="#0ea5e9" strokeWidth="1.5" strokeDasharray="4,4" opacity="0.5" />
          <line x1="260" y1="130" x2="440" y2="270" stroke="#0ea5e9" strokeWidth="1.5" strokeDasharray="4,4" opacity="0.5" />
          <line x1="190" y1="220" x2="440" y2="270" stroke="#0ea5e9" strokeWidth="1.5" strokeDasharray="4,4" opacity="0.3" />
        </svg>

        {/* Fictional Airbase Markers */}
        {zones.map((zone) => {
          const coords = baseCoordinates[zone.code] || { x: 300, y: 180, sector: "Operating Sector", fleet: "Airframes", wind: "Calm" };
          const isSelected = activeBase === zone.id;

          return (
            <div
              key={zone.id}
              style={{ left: `${coords.x}px`, top: `${coords.y}px` }}
              onClick={() => handleBaseClick(zone.id)}
              className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group transition-transform hover:scale-105"
            >
              {/* Radar Pulse Animation */}
              <div className={`absolute -inset-4 rounded-full border border-sky-400/30 animate-ping pointer-events-none ${isSelected ? 'opacity-100' : 'opacity-40'}`}></div>
              <div className="absolute -inset-8 rounded-full border border-sky-500/15 pointer-events-none"></div>

              {/* Central Node Badge */}
              <div className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg border shadow-xl backdrop-blur-md transition-colors ${
                isSelected
                  ? 'bg-blue-600/90 border-blue-400 text-white'
                  : 'bg-slate-900/90 border-slate-700 text-slate-200 group-hover:border-sky-400 group-hover:bg-slate-800'
              }`}>
                <Shield className={`w-3.5 h-3.5 ${isSelected ? 'text-amber-300' : 'text-sky-400'}`} />
                <div className="text-left">
                  <div className="text-[11px] font-bold leading-none tracking-tight font-mono">{zone.code}</div>
                  <div className="text-[9px] text-slate-300 font-sans truncate max-w-[110px]">{zone.name.split("-")[0]}</div>
                </div>
              </div>
            </div>
          );
        })}

        {/* Selected Base Tactical Inspector Overlay */}
        {activeBase && (
          <div className="absolute bottom-3 left-3 bg-slate-950/90 border border-slate-700 rounded-lg p-3 text-xs w-72 backdrop-blur-md shadow-2xl animate-fade-in">
            {(() => {
              const selectedZone = zones.find((z) => z.id === activeBase);
              if (!selectedZone) return null;
              const meta = baseCoordinates[selectedZone.code] || { sector: "Operating Sector", fleet: "Aircraft", wind: "Calm" };
              return (
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between border-b border-slate-800 pb-1">
                    <span className="font-bold text-sky-400 font-mono text-[11px]">{selectedZone.code} · {selectedZone.name}</span>
                    <Badge variant="success" className="text-[9px] py-0 px-1.5">OPERATIONAL</Badge>
                  </div>
                  <div className="text-[10px] text-slate-300 space-y-0.5">
                    <div><span className="text-slate-400">Sector:</span> {meta.sector}</div>
                    <div><span className="text-slate-400">Assigned Wings:</span> {meta.fleet}</div>
                    <div className="flex items-center gap-1.5">
                      <Wind className="w-3 h-3 text-slate-400" />
                      <span className="text-slate-400">Runway Wind:</span> {meta.wind}
                    </div>
                    <div><span className="text-slate-400">Apron Capacity:</span> {selectedZone.capacity_limit} Aircraft Bays</div>
                  </div>
                </div>
              );
            })()}
          </div>
        )}

        {/* Tactical Map Compass & Legend */}
        <div className="absolute top-3 right-3 bg-slate-950/80 border border-slate-800 rounded p-2 text-[10px] text-slate-400 font-mono flex items-center gap-2">
          <Navigation className="w-3.5 h-3.5 text-sky-400 rotate-45" />
          <span>TRUE NORTH 000°</span>
        </div>
      </div>
    </div>
  );
};
