import React from "react";
import { ChevronDown } from "lucide-react";

export interface Option {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: Option[];
  error?: string;
}

export const Select: React.FC<SelectProps> = ({
  label,
  options,
  error,
  className = "",
  id,
  ...props
}) => {
  const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

  return (
    <div className="space-y-1 w-full">
      {label && (
        <label htmlFor={selectId} className="block text-xs font-medium text-slate-700">
          {label}
        </label>
      )}
      <div className="relative">
        <select
          id={selectId}
          className={`w-full appearance-none pl-3 pr-8 py-2 text-xs bg-white border rounded-lg text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors ${
            error ? "border-red-400 focus:border-red-500 focus:ring-red-500/20" : "border-slate-300"
          } ${className}`}
          {...props}
        >
          {options.map((opt) => (
            <option key={opt.value} value={opt.value} disabled={opt.disabled}>
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown className="w-4 h-4 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
      </div>
      {error && <p className="text-[11px] text-red-600">{error}</p>}
    </div>
  );
};
