import React, { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { api } from "./services/api";
import { wsClient } from "./services/websocket";
import { JobProgress, UserProfile, UserRole } from "./types/api";
import { AppShell } from "./layouts/AppShell";
import { LoginPage } from "./pages/LoginPage";
import { OverviewPage } from "./pages/OverviewPage";
import { OperationsPage } from "./pages/OperationsPage";
import { SchedulePage } from "./pages/SchedulePage";
import { AssetsPage } from "./pages/AssetsPage";
import { PersonnelPage } from "./pages/PersonnelPage";
import { MaintenancePage } from "./pages/MaintenancePage";
import { IntelligencePage } from "./pages/IntelligencePage";
import { ScenariosPage } from "./pages/ScenariosPage";
import { AssistantPage } from "./pages/AssistantPage";
import { ReportsPage } from "./pages/ReportsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { LimitationsPage } from "./pages/LimitationsPage";
import { NotFoundPage } from "./pages/NotFoundPage";

export const App: React.FC = () => {
  const [user, setUser] = useState<UserProfile | null>(() => {
    return {
      id: "demo-planner-id",
      username: "planner",
      email: "planner@airops.local",
      is_active: true,
      roles: ["planner"],
    };
  });
  const [clockTime, setClockTime] = useState<string>("2026-10-19 12:00:00 UTC");
  const [isClockSimulated, setIsClockSimulated] = useState<boolean>(false);
  const [isLiveStreaming, setIsLiveStreaming] = useState<boolean>(false);
  const [isWsConnected, setIsWsConnected] = useState<boolean>(false);
  const [lastJobProgress, setLastJobProgress] = useState<JobProgress | null>(null);

  // Sync virtual clock periodically
  useEffect(() => {
    const fetchClock = async () => {
      try {
        const state = await api.getClock();
        const dateObj = new Date(state.current_as_of);
        setClockTime(dateObj.toUTCString().replace("GMT", "UTC"));
        setIsClockSimulated(state.mode !== "system");
      } catch {
        // In local mode fallback to formatted UTC
        setClockTime("2026-10-19 12:00 UTC");
      }
    };

    fetchClock();
    const interval = setInterval(fetchClock, 10000);
    return () => clearInterval(interval);
  }, []);

  // Connect full-duplex WebSocket client
  useEffect(() => {
    wsClient.connect();
    const unsubStatus = wsClient.onStatusChange((status) => {
      setIsWsConnected(status === "connected");
    });

    const unsubJobs = wsClient.subscribe<JobProgress>("jobs:progress", (data) => {
      if (data) {
        setLastJobProgress(data);
      }
    });

    return () => {
      unsubJobs();
      unsubStatus();
      wsClient.disconnect();
    };
  }, []);

  // Connect to SSE stream as complementary / fallback channel
  useEffect(() => {
    let eventSource: EventSource | null = null;
    try {
      eventSource = new EventSource("/api/v1/stream");
      eventSource.onopen = () => setIsLiveStreaming(true);
      eventSource.onerror = () => setIsLiveStreaming(false);

      eventSource.addEventListener("jobs:progress", (e) => {
        try {
          const data = JSON.parse(e.data);
          setLastJobProgress(data);
        } catch {}
      });
    } catch {
      setIsLiveStreaming(false);
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, []);

  // Ensure JWT token is set on initial mount
  useEffect(() => {
    if (!api.getToken()) {
      api.login("planner@airops.local", "PlannerSecurePass2026!").catch(() => {});
    }
  }, []);

  const handleRoleSwitch = async (role: UserRole) => {
    if (!user) return;
    try {
      const passMap: Record<string, string> = {
        planner: "PlannerSecurePass2026!",
        reviewer: "ReviewerSecurePass2026!",
        analyst: "AnalystSecurePass2026!",
        admin: "AdminSecurePass2026!",
      };
      const password = passMap[role] || "PlannerSecurePass2026!";
      await api.login(`${role}@airops.local`, password);
    } catch (e) {
      console.warn("Could not login via API, continuing in demo state", e);
    }
    setUser({
      ...user,
      username: role,
      email: `${role}@airops.local`,
      roles: [role],
    });
  };

  const handleLogin = async (roleName: string) => {
    try {
      const passMap: Record<string, string> = {
        planner: "PlannerSecurePass2026!",
        reviewer: "ReviewerSecurePass2026!",
        analyst: "AnalystSecurePass2026!",
        admin: "AdminSecurePass2026!",
      };
      const password = passMap[roleName] || "PlannerSecurePass2026!";
      await api.login(`${roleName}@airops.local`, password);
    } catch (e) {
      console.warn("Could not login via API, continuing in demo state", e);
    }
    setUser({
      id: `demo-${roleName}-id`,
      username: roleName,
      email: `${roleName}@airops.local`,
      is_active: true,
      roles: [roleName as UserRole],
    });
  };

  const handleLogout = async () => {
    await api.logout();
    setUser(null);
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            user ? <Navigate to="/" replace /> : <LoginPage onLogin={handleLogin} />
          }
        />

        {/* Protected AppShell Routes */}
        <Route
          element={
            user ? (
              <AppShell
                user={user}
                onRoleSwitch={handleRoleSwitch}
                onLogout={handleLogout}
                clockTime={clockTime}
                isClockSimulated={isClockSimulated}
                isLiveStreaming={isLiveStreaming}
                isWsConnected={isWsConnected}
              />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        >
          <Route index element={<OverviewPage lastJobProgress={lastJobProgress} />} />
          <Route path="operations" element={<OperationsPage />} />
          <Route path="schedule" element={<SchedulePage />} />
          <Route path="schedule/proposals/:planId" element={<SchedulePage />} />
          <Route path="assets" element={<AssetsPage />} />
          <Route path="assets/:id" element={<AssetsPage />} />
          <Route path="personnel" element={<PersonnelPage />} />
          <Route path="maintenance" element={<MaintenancePage />} />
          <Route path="intelligence" element={<Navigate to="/intelligence/maintenance-risk" replace />} />
          <Route path="intelligence/:tab" element={<IntelligencePage />} />
          <Route path="scenarios" element={<ScenariosPage />} />
          <Route path="scenarios/:id" element={<ScenariosPage />} />
          <Route path="assistant" element={<AssistantPage />} />
          <Route path="reports" element={<Navigate to="/reports/operational" replace />} />
          <Route path="reports/:type" element={<ReportsPage />} />
          <Route path="settings" element={<Navigate to="/settings/clock" replace />} />
          <Route path="settings/:tab" element={<SettingsPage />} />
          <Route path="about/limitations" element={<LimitationsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
};
