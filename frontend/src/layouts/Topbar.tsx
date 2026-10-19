import React from "react";
import { Menu, Clock as ClockIcon, Activity, User as UserIcon, LogOut, ChevronDown } from "lucide-react";
import { UserProfile, UserRole } from "../types/api";

interface TopbarProps {
  user: UserProfile | null;
  onToggleSidebar: () => void;
  onRoleSwitch: (role: UserRole) => void;
  onLogout: () => void;
  clockTime: string;
  isClockSimulated: boolean;
  isLiveStreaming: boolean;
}

export const Topbar: React.FC<TopbarProps> = ({
  user,
  onToggleSidebar,
  onRoleSwitch,
  onLogout,
  clockTime,
  isClockSimulated,
  isLiveStreaming,
}) => {
  const [dropdownOpen, setDropdownOpen] = React.useState(false);

  return (
    <header className="sticky top-0 z-30 bg-white border-b border-slate-200">
      {/* Persistent Synthetic Prototype Disclaimer Banner */}
      <div className="bg-slate-900 text-slate-300 px-4 py-1 text-[11px] text-center flex items-center justify-center gap-2 font-mono">
        <span className="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
        <span>SYNTHETIC ENVIRONMENT · STRICTLY FICTIONAL DATA · RESEARCH PROTOTYPE</span>
      </div>

      <div className="h-16 px-4 md:px-8 flex items-center justify-between gap-4">
        {/* Left: Mobile Toggle & Status */}
        <div className="flex items-center gap-3">
          <button
            onClick={onToggleSidebar}
            className="p-2 text-slate-600 hover:text-slate-900 md:hidden rounded-lg hover:bg-slate-100"
            aria-label="Toggle navigation"
          >
            <Menu className="w-5 h-5" />
          </button>

          {/* SSE Live Indicator */}
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 border border-slate-200 text-xs">
            <Activity className={`w-3.5 h-3.5 ${isLiveStreaming ? 'text-emerald-500 animate-pulse' : 'text-slate-400'}`} />
            <span className="font-medium text-slate-700">{isLiveStreaming ? "Stream Live" : "Stream Idle"}</span>
          </div>
        </div>

        {/* Right: Demo Clock Badge, Role Selector & User Profile */}
        <div className="flex items-center gap-3">
          {/* Demo Time Badge (Task P1-11) */}
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono ${
              isClockSimulated
                ? "bg-amber-50 border-amber-300 text-amber-900"
                : "bg-slate-50 border-slate-200 text-slate-700"
            }`}
            title="Operational System Virtual Clock"
          >
            <ClockIcon className="w-3.5 h-3.5 text-blue-600" />
            <span className="font-semibold">{clockTime || "2026-10-19 12:00 UTC"}</span>
            {isClockSimulated && (
              <span className="text-[10px] bg-amber-200 text-amber-900 px-1 rounded font-bold uppercase">
                Demo
              </span>
            )}
          </div>

          {/* User Profile & Role Switcher */}
          <div className="relative">
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors text-left"
            >
              <div className="w-7 h-7 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center font-semibold text-xs">
                {user?.username ? user.username[0].toUpperCase() : <UserIcon className="w-4 h-4" />}
              </div>
              <div className="hidden md:block">
                <p className="text-xs font-semibold text-slate-900">{user?.username || "Demo User"}</p>
                <p className="text-[10px] text-blue-600 font-medium capitalize">
                  {user?.roles?.[0] || "planner"}
                </p>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-slate-200 py-1 z-50 animate-in fade-in slide-in-from-top-1">
                <div className="px-4 py-2 border-b border-slate-100">
                  <p className="text-xs font-semibold text-slate-900">{user?.email || "user@airops.local"}</p>
                  <p className="text-[11px] text-slate-500">Demo Role Quick-Switch</p>
                </div>

                <div className="p-1 space-y-0.5">
                  {(["planner", "reviewer", "analyst", "admin"] as UserRole[]).map((role) => (
                    <button
                      key={role}
                      onClick={() => {
                        onRoleSwitch(role);
                        setDropdownOpen(false);
                      }}
                      className={`w-full text-left px-3 py-1.5 rounded text-xs capitalize font-medium flex items-center justify-between ${
                        user?.roles?.includes(role)
                          ? "bg-blue-50 text-blue-700 font-bold"
                          : "text-slate-700 hover:bg-slate-100"
                      }`}
                    >
                      <span>{role}</span>
                      {user?.roles?.includes(role) && <span className="text-blue-600">✓</span>}
                    </button>
                  ))}
                </div>

                <div className="border-t border-slate-100 p-1">
                  <button
                    onClick={() => {
                      setDropdownOpen(false);
                      onLogout();
                    }}
                    className="w-full text-left px-3 py-1.5 rounded text-xs text-rose-600 hover:bg-rose-50 flex items-center gap-2 font-medium"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Log Out</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
