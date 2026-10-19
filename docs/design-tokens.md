# AirOps Nexus — Design Tokens Specification

**Status:** Approved Specification (Phase 0, Task P0-8)  
**Version:** 1.0  
**Implementation:** `frontend/src/styles/tokens.css`

---

## 1. Color Palette & Token Definitions

All colors comply with WCAG 2.1 Level AA contrast standards ($\ge 4.5:1$ for normal text, $\ge 3:1$ for large text/UI components).

```css
:root {
  /* Brand & Shell Colors */
  --color-sidebar-bg: #0b132b;          /* Deep Obsidian Navy */
  --color-sidebar-hover: #1c2541;       /* Dark Indigo Navy */
  --color-sidebar-text: #e2e8f0;        /* Slate 200 */
  --color-sidebar-muted: #94a3b8;       /* Slate 400 */
  --color-sidebar-border: #1e293b;      /* Slate 800 */

  /* Surface & Workspace */
  --color-workspace-bg: #f8fafc;        /* Slate 50 Neutral Surface */
  --color-card-bg: #ffffff;             /* Pure White Container */
  --color-card-border: #e2e8f0;         /* Slate 200 Border */
  --color-card-muted: #f1f5f9;          /* Slate 100 Alternate */

  /* Typography */
  --color-text-primary: #0f172a;        /* Slate 900 High Contrast Text */
  --color-text-secondary: #475569;      /* Slate 600 Body & Label Text */
  --color-text-muted: #64748b;          /* Slate 500 Subtle Captions */
  --color-text-disabled: #94a3b8;       /* Slate 400 Inactive Text */

  /* Brand Primary Accent */
  --color-primary-50: #eff6ff;
  --color-primary-100: #dbeafe;
  --color-primary-500: #3b82f6;
  --color-primary-600: #2563eb;         /* Core Interaction Blue */
  --color-primary-700: #1d4ed8;         /* Primary Hover */
  --color-primary-contrast: #ffffff;

  /* Semantic Status - Success / Healthy */
  --color-success-bg: #f0fdf4;
  --color-success-border: #bbf7d0;
  --color-success-text: #166534;
  --color-success-icon: #16a34a;

  /* Semantic Status - Warning / Degraded */
  --color-warning-bg: #fffbeb;
  --color-warning-border: #fde68a;
  --color-warning-text: #92400e;
  --color-warning-icon: #d97706;

  /* Semantic Status - Critical / Infeasible / Error */
  --color-critical-bg: #fef2f2;
  --color-critical-border: #fecaca;
  --color-critical-text: #991b1b;
  --color-critical-icon: #dc2626;

  /* Data Kind Provenance Badges */
  --badge-observed-bg: #e0f2fe;   --badge-observed-text: #0369a1;
  --badge-predicted-bg: #f3e8ff;  --badge-predicted-text: #6b21a8;
  --badge-simulated-bg: #ecfdf5;  --badge-simulated-text: #047857;
  --badge-synthetic-bg: #f1f5f9;  --badge-synthetic-text: #334155;
  --badge-stale-bg: #fff7ed;      --badge-stale-text: #c2410c;
}
```

---

## 2. Typography & Spatial System
- **Font Family:** `Inter`, `-apple-system`, `BlinkMacSystemFont`, `"Segoe UI"`, `Roboto`, `sans-serif`.
- **Code / Monospace:** `"JetBrains Mono"`, `"Fira Code"`, `Consolas`, `monospace`.
- **Base Grid:** 4px incremental scaling:
  - `space-1`: 4px | `space-2`: 8px | `space-3`: 12px | `space-4`: 16px | `space-6`: 24px | `space-8`: 32px
- **Border Radius:**
  - Standard cards: `8px` (`rounded-lg`)
  - Badges & chips: `9999px` (`rounded-full`)
  - Modals: `12px` (`rounded-xl`)
- **Elevation Shadows:**
  - Card default: `0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)`
  - Hover elevation: `0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)`
