import React, { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { UserProfile, UserRole } from "../types/api";

interface AppShellProps {
  user: UserProfile | null;
  onRoleSwitch: (role: UserRole) => void;
  onLogout: () => void;
  clockTime: string;
  isClockSimulated: boolean;
  isLiveStreaming: boolean;
}

export const AppShell: React.FC<AppShellProps> = ({
  user,
  onRoleSwitch,
  onLogout,
  clockTime,
  isClockSimulated,
  isLiveStreaming,
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const userRoles = user?.roles || ["planner"];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Sidebar
        userRoles={userRoles}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <div className="md:pl-64 flex flex-col flex-1">
        <Topbar
          user={user}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          onRoleSwitch={onRoleSwitch}
          onLogout={onLogout}
          clockTime={clockTime}
          isClockSimulated={isClockSimulated}
          isLiveStreaming={isLiveStreaming}
        />

        <main className="flex-1 p-6 md:p-8 max-w-7xl w-full mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
