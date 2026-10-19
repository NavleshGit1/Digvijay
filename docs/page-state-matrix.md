# AirOps Nexus — UI Page-State & Behavior Matrix

**Status:** Approved Specification (Phase 0, Task P0-8)  
**Version:** 1.0  
**References:** Architecture Section 16.3 & 16.5

---

## 1. Universal Page-State Contract

Every page, data table, and visualization component must cleanly handle six distinct states without breaking layout or fabricating defaults:

| State | Visual Treatment | User Interaction |
| :--- | :--- | :--- |
| **`Loading`** | Animated pulse skeletons matching the exact geometry of cards/tables. | Interactive inputs disabled; no layout shift upon data resolution. |
| **`Empty`** | `EmptyState` component with custom illustration, clear explanation, and primary action. | Action button routes to creation flow (e.g., "Seed Dataset", "Generate Plan"). |
| **`Partial Data`** | Inline warning banner with icon; available cards render with amber badges. | Explains what data sources are missing or degraded; displays available records. |
| **`Stale Data`** | Subtle warning banner (`StaleBanner`) indicating last successful sync timestamp. | "Refresh Now" button; data remains visible with stale indicator. |
| **`Error`** | RFC 7807 Problem Details card with error code, human message, and request ID. | "Retry Action" button and link to system health status. Never leaks stack traces. |
| **`Success`** | High-contrast data presentation with appropriate `DataKindBadge`. | Full table sorting, filtering, row inspection drawers, and action buttons active. |

---

## 2. Page-by-Page Implementation Matrix

| Route | Page Name | Primary View | Empty State Action | Error Fallback |
| :--- | :--- | :--- | :--- | :--- |
| `/` | **Overview** | KPI cards, MapLibre map, alert feed | "Seed Initial Demo Data" | Render offline shell with cache or service error |
| `/operations` | **Operations** | Event table, timeline, blast radius | "No Active Events (System Nominal)" | Show retry button on event stream connection |
| `/schedule` | **Schedule** | SVG Gantt, timeline, table tabs | "Generate Baseline Schedule" | Infeasible dialog with diagnostic conflict set |
| `/schedule/proposals/:id` | **Proposal Review** | Side-by-side diff, validation badge | "No Pending Proposals" | Revalidation failure banner with rollback link |
| `/assets` | **Fleet Assets** | Searchable table, asset drawer | "No Assets Found in Active Fleet" | Card boundary error with retry button |
| `/personnel` | **Personnel** | Crew table, qualifications chips | "No Personnel Registered" | Card boundary error with retry button |
| `/maintenance` | **Maintenance** | Work orders table, delay simulation | "No Open Maintenance Items" | Disruption simulation failure toast |
| `/intelligence/:tab` | **Intelligence** | Risk tables, SHAP feature charts | "No Models Trained Yet" | Engine unavailable alert (Principle 7) |
| `/scenarios` | **Digital Twin** | Run config, outcome distributions | "Configure First Scenario Run" | Simulation failure modal with seed capture |
| `/assistant` | **AI Assistant** | Chat transcript, source references | Prompt suggestions starter buttons | Graceful disabled state if LLM service down |
| `/reports` | **Reports** | 8 report tabs, PDF/CSV download | "Generate First Operational Report"| Async job failed banner with log reference |
| `/settings/:tab` | **Settings** | Admin configuration tabs | "No Custom Config Sets Defined" | Validation error highlight on form inputs |
