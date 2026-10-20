import React from "react";

export interface TabItem {
  id: string;
  label: React.ReactNode;
  icon?: React.ComponentType<{ className?: string }>;
  badge?: React.ReactNode;
}

export interface TabsProps {
  tabs: TabItem[];
  activeTab: string;
  onChange: (tabId: string) => void;
  className?: string;
}

export const Tabs: React.FC<TabsProps> = ({
  tabs,
  activeTab,
  onChange,
  className = "",
}) => {
  return (
    <div className={`flex items-center gap-1 border-b border-slate-200 overflow-x-auto ${className}`}>
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;

        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition-all whitespace-nowrap ${
              isActive
                ? "border-blue-600 text-blue-600 font-semibold"
                : "border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300"
            }`}
          >
            {Icon && <Icon className={`w-3.5 h-3.5 ${isActive ? "text-blue-600" : "text-slate-400"}`} />}
            <span>{tab.label}</span>
            {tab.badge && (
              <span className="ml-1 text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};
