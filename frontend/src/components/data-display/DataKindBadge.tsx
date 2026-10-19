import React from "react";
import { DataKind } from "../../types/api";

interface DataKindBadgeProps {
  kind: DataKind;
  className?: string;
}

export const DataKindBadge: React.FC<DataKindBadgeProps> = ({ kind, className = "" }) => {
  const kindStyles: Record<DataKind, { bg: string; text: string; label: string }> = {
    observed: { bg: "bg-sky-50 border-sky-200", text: "text-sky-700", label: "Observed" },
    predicted: { bg: "bg-purple-50 border-purple-200", text: "text-purple-700", label: "Predicted" },
    simulated: { bg: "bg-emerald-50 border-emerald-200", text: "text-emerald-700", label: "Simulated" },
    generated: { bg: "bg-indigo-50 border-indigo-200", text: "text-indigo-700", label: "Generated" },
    synthetic: { bg: "bg-slate-100 border-slate-200", text: "text-slate-700", label: "Synthetic" },
    demo: { bg: "bg-amber-50 border-amber-200", text: "text-amber-700", label: "Demo" },
  };

  const style = kindStyles[kind] || kindStyles.synthetic;

  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold border tracking-wide uppercase ${style.bg} ${style.text} ${className}`}
      title={`Data Provenance: ${style.label}`}
    >
      {style.label}
    </span>
  );
};
