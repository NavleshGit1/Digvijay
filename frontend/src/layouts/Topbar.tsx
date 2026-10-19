import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Menu,
  Clock as ClockIcon,
  Activity,
  User as UserIcon,
  LogOut,
  ChevronDown,
  Search,
  Plane,
  Users,
  Calendar,
  Package,
  X,
} from "lucide-react";
import { api } from "../services/api";
import { SearchResultItem, UserProfile, UserRole } from "../types/api";

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
  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  // Global search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResultItem[]>([]);
  const [searchOpen, setSearchOpen] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const res = await api.search(searchQuery.trim());
        setSearchResults(res.results);
        setSearchOpen(true);
      } catch (err) {
        console.error("Search failed:", err);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Click outside listener for search results
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleResultClick = (url: string) => {
    setSearchOpen(false);
    setSearchQuery("");
    navigate(url);
  };

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

        {/* Center: Global Unified Search (Task P3-3) */}
        <div ref={searchRef} className="flex-1 max-w-md relative hidden md:block">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => searchResults.length > 0 && setSearchOpen(true)}
              placeholder="Global search (assets, crew, tasks, spares)..."
              className="w-full pl-9 pr-8 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
            />
            {searchQuery && (
              <button
                onClick={() => {
                  setSearchQuery("");
                  setSearchResults([]);
                  setSearchOpen(false);
                }}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Dropdown Results */}
          {searchOpen && searchResults.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1.5 bg-white border border-slate-200 rounded-xl shadow-xl overflow-hidden z-50 max-h-80 overflow-y-auto">
              <div className="p-2 bg-slate-50 border-b border-slate-100 text-[10px] font-bold uppercase text-slate-400 tracking-wider">
                Matching System Entities ({searchResults.length})
              </div>
              <div className="divide-y divide-slate-100">
                {searchResults.map((item) => (
                  <div
                    key={`${item.category}-${item.id}`}
                    onClick={() => handleResultClick(item.url)}
                    className="p-2.5 hover:bg-blue-50/60 cursor-pointer flex items-center justify-between transition-colors text-xs"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="p-1.5 bg-slate-100 rounded text-slate-600">
                        {item.category === "asset" && <Plane className="w-3.5 h-3.5" />}
                        {item.category === "personnel" && <Users className="w-3.5 h-3.5" />}
                        {item.category === "task" && <Calendar className="w-3.5 h-3.5" />}
                        {item.category === "spare" && <Package className="w-3.5 h-3.5" />}
                      </div>
                      <div>
                        <div className="font-semibold text-slate-900">{item.title}</div>
                        <div className="text-[10px] text-slate-400 font-mono">{item.subtitle}</div>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono font-bold bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded border border-slate-200">
                      {item.badge}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
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
              <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-lg border border-slate-200 py-1 z-50 text-xs">
                <div className="px-3 py-2 border-b border-slate-100">
                  <p className="font-semibold text-slate-900">{user?.email || "user@airops.local"}</p>
                  <p className="text-[10px] text-slate-400">Authenticated Demo Session</p>
                </div>

                <div className="py-1">
                  <div className="px-3 py-1 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                    Switch Role (Demo Mode)
                  </div>
                  {(["planner", "reviewer", "analyst", "admin"] as UserRole[]).map((role) => (
                    <button
                      key={role}
                      onClick={() => {
                        onRoleSwitch(role);
                        setDropdownOpen(false);
                      }}
                      className={`w-full text-left px-3 py-1.5 hover:bg-slate-50 flex items-center justify-between capitalize ${
                        user?.roles?.[0] === role ? "font-bold text-blue-600 bg-blue-50/50" : "text-slate-700"
                      }`}
                    >
                      <span>{role}</span>
                      {user?.roles?.[0] === role && <span className="w-1.5 h-1.5 rounded-full bg-blue-600"></span>}
                    </button>
                  ))}
                </div>

                <div className="border-t border-slate-100 pt-1">
                  <button
                    onClick={() => {
                      setDropdownOpen(false);
                      onLogout();
                    }}
                    className="w-full text-left px-3 py-1.5 hover:bg-rose-50 text-rose-600 flex items-center gap-2"
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
