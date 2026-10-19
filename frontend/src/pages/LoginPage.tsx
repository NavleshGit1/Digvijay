import React, { useState } from "react";
import { Plane, Lock, ShieldCheck } from "lucide-react";

interface LoginPageProps {
  onLogin: (role: string) => Promise<void>;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLogin }) => {
  const [loadingRole, setLoadingRole] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const demoRoles = [
    {
      role: "planner",
      title: "Operational Planner",
      desc: "Creates baseline plans, runs replanning, injects disruptions",
      badge: "ROLE_PLANNER",
    },
    {
      role: "reviewer",
      title: "Reviewer & Approver",
      desc: "Sole authority to approve or reject proposed plan changes",
      badge: "ROLE_REVIEWER",
    },
    {
      role: "analyst",
      title: "Operational Analyst",
      desc: "Inspects model drift, anomalies, and digital twin distributions",
      badge: "ROLE_ANALYST",
    },
    {
      role: "admin",
      title: "System Administrator",
      desc: "Configures weights, manages users, advances virtual clock",
      badge: "ROLE_ADMIN",
    },
  ];

  const handleQuickLogin = async (role: string) => {
    try {
      setLoadingRole(role);
      setError(null);
      await onLogin(role);
    } catch (err: any) {
      setError(err?.detail || "Authentication failed");
    } finally {
      setLoadingRole(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center items-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="w-12 h-12 bg-blue-600 rounded-xl mx-auto flex items-center justify-center text-white shadow-xl shadow-blue-500/30 mb-4">
            <Plane className="w-7 h-7 -rotate-45" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">AirOps Nexus</h1>
          <p className="text-sm text-slate-400 mt-1">
            Dynamic Air Operations & Resource Optimisation
          </p>
          <div className="inline-block mt-3 px-3 py-1 rounded-full bg-blue-950/80 border border-blue-800 text-[11px] text-blue-300 font-mono">
            Phase 1 Platform Skeleton Active
          </div>
        </div>

        {/* Card */}
        <div className="bg-slate-800/90 border border-slate-700/80 rounded-2xl p-6 shadow-2xl backdrop-blur-xl">
          <div className="flex items-center gap-2 mb-4 pb-3 border-b border-slate-700/60 text-slate-300 text-xs font-semibold uppercase tracking-wider">
            <Lock className="w-4 h-4 text-blue-400" />
            <span>Select Demonstration Account</span>
          </div>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-950/80 border border-red-800 text-red-300 text-xs">
              {error}
            </div>
          )}

          <div className="space-y-3">
            {demoRoles.map((item) => (
              <button
                key={item.role}
                onClick={() => handleQuickLogin(item.role)}
                disabled={loadingRole !== null}
                className="w-full text-left p-3.5 rounded-xl border border-slate-700 bg-slate-900/60 hover:bg-slate-700/70 hover:border-blue-500 transition-all flex items-center justify-between group disabled:opacity-50"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white group-hover:text-blue-400 transition-colors">
                      {item.title}
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                      {item.badge}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">{item.desc}</p>
                </div>
                <div className="text-slate-500 group-hover:text-blue-400 font-bold ml-2">
                  →
                </div>
              </button>
            ))}
          </div>

          <div className="mt-6 pt-4 border-t border-slate-700/60 text-center">
            <div className="flex items-center justify-center gap-1.5 text-xs text-slate-400">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Strict Role-Based Authorization Enforced</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
