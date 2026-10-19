import React from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Radio,
  CalendarDays,
  Plane,
  Users,
  Wrench,
  BrainCircuit,
  Boxes,
  BotMessageSquare,
  FileSpreadsheet,
  Settings,
  ShieldCheck,
} from "lucide-react";
import { UserRole } from "../types/api";

interface SidebarProps {
  userRoles: UserRole[];
  isOpen: boolean;
  onClose?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ userRoles, isOpen, onClose }) => {
  const navItems = [
    { name: "Overview", to: "/", icon: LayoutDashboard },
    { name: "Operations", to: "/operations", icon: Radio },
    { name: "Schedule", to: "/schedule", icon: CalendarDays },
    { name: "Fleet Assets", to: "/assets", icon: Plane },
    { name: "Personnel", to: "/personnel", icon: Users },
    { name: "Maintenance", to: "/maintenance", icon: Wrench },
    { name: "Intelligence", to: "/intelligence/maintenance-risk", icon: BrainCircuit },
    { name: "Digital Twin", to: "/scenarios", icon: Boxes },
    { name: "AI Assistant", to: "/assistant", icon: BotMessageSquare },
    { name: "Reports", to: "/reports/operational", icon: FileSpreadsheet },
    { name: "Settings", to: "/settings/users", icon: Settings, adminOnly: true },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 md:hidden backdrop-blur-sm"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-[#0b132b] border-r border-[#1e293b] flex flex-col transition-transform duration-200 ease-in-out md:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 px-6 flex items-center gap-3 border-b border-[#1e293b]">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
            <Plane className="w-5 h-5 -rotate-45" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-wide">AirOps Nexus</h1>
            <p className="text-[10px] text-blue-400 font-mono tracking-wider uppercase">Synthetic Ops v1.0</p>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            if (item.adminOnly && !userRoles.includes("admin")) {
              return null;
            }

            const Icon = item.icon;

            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onClose}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-blue-600 text-white shadow-sm shadow-blue-600/30"
                      : "text-slate-300 hover:text-white hover:bg-[#1c2541]"
                  }`
                }
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Footer Guardrail Badge */}
        <div className="p-4 border-t border-[#1e293b] bg-[#080d1d]">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Human-In-The-Loop</span>
          </div>
          <p className="text-[10px] text-slate-500 mt-1">Constraint Safety Verified</p>
        </div>
      </aside>
    </>
  );
};
