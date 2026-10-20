import React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ComponentType<{ className?: string }>;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  icon: Icon,
  className = "",
  id,
  ...props
}) => {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

  return (
    <div className="space-y-1 w-full">
      {label && (
        <label htmlFor={inputId} className="block text-xs font-medium text-slate-700">
          {label}
        </label>
      )}
      <div className="relative">
        {Icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
            <Icon className="w-4 h-4" />
          </div>
        )}
        <input
          id={inputId}
          className={`w-full ${
            Icon ? "pl-9" : "pl-3"
          } pr-3 py-2 text-xs bg-white border rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors ${
            error ? "border-red-400 focus:border-red-500 focus:ring-red-500/20" : "border-slate-300"
          } ${className}`}
          {...props}
        />
      </div>
      {error && <p className="text-[11px] text-red-600">{error}</p>}
    </div>
  );
};
