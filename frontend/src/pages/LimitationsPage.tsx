import React from "react";
import { Link } from "react-router-dom";
import {
  ShieldAlert,
  Info,
  Database,
  Cpu,
  ArrowLeft,
  AlertTriangle,
} from "lucide-react";
import { DataKindBadge } from "../components/data-display/DataKindBadge";
import { StatusBadge } from "../components/data-display/StatusBadge";

export const LimitationsPage: React.FC = () => {
  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header Breadcrumb & Title */}
      <div className="flex flex-col gap-2">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-blue-600 transition-colors w-fit"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to Operational Overview
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
              <ShieldAlert className="w-7 h-7 text-amber-500" />
              System Limitations & Formal Disclaimers
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Problem Statement 26250 · Air Power: Dynamic Air Operations and Resource Optimisation · v1.0
            </p>
          </div>
          <span className="text-xs font-mono font-semibold px-2.5 py-1 bg-amber-50 border border-amber-200 text-amber-800 rounded-full">
            Synthetic Prototype
          </span>
        </div>
      </div>

      {/* Section 1: Prototype Status & Non-Certification */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <Info className="w-5 h-5 text-blue-600" />
          <h2 className="text-base font-semibold text-slate-900">
            1. Prototype Status & Non-Certification Scope
          </h2>
        </div>
        <div className="grid md:grid-cols-3 gap-4 text-xs text-slate-600">
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-100 space-y-1.5">
            <span className="font-semibold text-slate-900 block">Research Prototype Only</span>
            <p>
              AirOps Nexus is a prototype developed strictly for algorithmic research, decision-support exploration, and technical demonstrations.
            </p>
          </div>
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-100 space-y-1.5">
            <span className="font-semibold text-slate-900 block">No Live Defense Certification</span>
            <p>
              This platform has <strong>not</strong> been evaluated, accredited, or certified for live military flight dispatch, air defense missions, or classified command.
            </p>
          </div>
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-100 space-y-1.5">
            <span className="font-semibold text-slate-900 block">Human-in-the-Loop Authority</span>
            <p>
              The system functions strictly as a human-supervised decision-support utility. Automated solvers and AI assistants have <strong>no autonomous authority</strong> to execute actions.
            </p>
          </div>
        </div>
      </div>

      {/* Section 2: Synthetic Data Disclosure */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <Database className="w-5 h-5 text-indigo-600" />
          <h2 className="text-base font-semibold text-slate-900">
            2. 100% Synthetic Data & Zero Real Operational Feeds
          </h2>
        </div>
        <div className="space-y-3 text-xs text-slate-600 leading-relaxed">
          <p>
            All tail numbers, asset configurations, personnel names, flight qualifications, maintenance intervals, base coordinates, and disruption events within this platform are <strong>entirely fictitious and synthetically generated</strong>.
          </p>
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Synthetic Accuracy Warning:</span> Machine learning model metrics (e.g. $R^2$, MAE, Brier scores) reflect performance against synthetic distributions with injected anomalies. They must never be extrapolated to real-world avionics or aircraft reliability.
            </div>
          </div>
        </div>
      </div>

      {/* Section 3: Data Provenance & Solver Status Taxonomy */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-3">
          <Cpu className="w-5 h-5 text-emerald-600" />
          <h2 className="text-base font-semibold text-slate-900">
            3. Data Provenance & Honest Solver Status Taxonomy
          </h2>
        </div>

        {/* Provenance Envelopes */}
        <div className="space-y-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Data Provenance Envelopes
          </h3>
          <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
            <div className="border border-slate-100 p-3 rounded-lg flex items-start gap-2">
              <DataKindBadge kind="observed" />
              <span className="text-slate-600 text-[11px]">Directly recorded historical or operational reality.</span>
            </div>
            <div className="border border-slate-100 p-3 rounded-lg flex items-start gap-2">
              <DataKindBadge kind="predicted" />
              <span className="text-slate-600 text-[11px]">Statistical/ML inference with version & uncertainty interval.</span>
            </div>
            <div className="border border-slate-100 p-3 rounded-lg flex items-start gap-2">
              <DataKindBadge kind="simulated" />
              <span className="text-slate-600 text-[11px]">Stochastic discrete-event digital twin simulation run.</span>
            </div>
            <div className="border border-slate-100 p-3 rounded-lg flex items-start gap-2">
              <DataKindBadge kind="generated" />
              <span className="text-slate-600 text-[11px]">Synthesized by deterministic pseudo-random generator.</span>
            </div>
            <div className="border border-slate-100 p-3 rounded-lg flex items-start gap-2">
              <DataKindBadge kind="synthetic" />
              <span className="text-slate-600 text-[11px]">Baseline synthetic reference configuration.</span>
            </div>
            <div className="border border-slate-100 p-3 rounded-lg flex items-start gap-2">
              <DataKindBadge kind="demo" />
              <span className="text-slate-600 text-[11px]">Fictional demonstration persona or preset.</span>
            </div>
          </div>
        </div>

        {/* Honest Solver Statuses */}
        <div className="space-y-2 pt-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Honest Solver Status Mapping (CP-SAT)
          </h3>
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-3 p-2.5 rounded-lg border border-slate-100 bg-slate-50">
              <StatusBadge status="optimal" />
              <span className="text-slate-700"><strong>Optimal:</strong> Mathematically proven schedule within model bounds.</span>
            </div>
            <div className="flex items-center gap-3 p-2.5 rounded-lg border border-slate-100 bg-slate-50">
              <StatusBadge status="feasible" />
              <span className="text-slate-700"><strong>Feasible:</strong> Valid schedule satisfying all hard constraints before timeout.</span>
            </div>
            <div className="flex items-center gap-3 p-2.5 rounded-lg border border-slate-100 bg-slate-50">
              <StatusBadge status="timeout" />
              <span className="text-slate-700"><strong>Timeout:</strong> Solver hit configured time limit. Honestly reported—<strong>never</strong> conflated with infeasibility.</span>
            </div>
            <div className="flex items-center gap-3 p-2.5 rounded-lg border border-slate-100 bg-slate-50">
              <StatusBadge status="infeasible" />
              <span className="text-slate-700"><strong>Infeasible:</strong> Proven no combination satisfies constraints. Accompanied by diagnostic conflict sets.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
