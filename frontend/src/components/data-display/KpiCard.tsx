import React from "react";
import { DataKind } from "../../types/api";
import { DataKindBadge } from "./DataKindBadge";

interface KpiCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  dataKind?: DataKind;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  className?: string;
  onClick?: () => void;
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  subtitle,
  dataKind,
  trend,
  className = "",
  onClick,
}) => {
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-lg border border-slate-200 p-5 shadow-sm hover:shadow transition-shadow ${onClick ? 'cursor-pointer' : ''} ${className}`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">{title}</span>
        {dataKind && <DataKindBadge kind={dataKind} />}
      </div>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-2xl font-bold text-slate-900 tracking-tight">{value}</span>
        {trend && (
          <span
            className={`text-xs font-medium ${trend.isPositive ? 'text-emerald-600' : 'text-rose-600'}`}
          >
            {trend.value}
          </span>
        )}
      </div>
      {subtitle && <p className="text-xs text-slate-500 mt-1.5">{subtitle}</p>}
    </div>
  );
};
