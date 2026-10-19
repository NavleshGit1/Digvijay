import React from "react";
import { Badge } from "../ui/Badge";

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = "" }) => {
  const normalized = status.toLowerCase();

  let variant: "default" | "success" | "warning" | "danger" | "info" = "default";

  if (["available", "completed", "approved", "optimal", "passed", "healthy", "nominal"].includes(normalized)) {
    variant = "success";
  } else if (["in_use", "in_progress", "scheduled", "feasible", "queued"].includes(normalized)) {
    variant = "info";
  } else if (["maintenance", "stale", "warning", "needs_review", "timeout", "degraded"].includes(normalized)) {
    variant = "warning";
  } else if (["grounded", "cancelled", "rejected", "infeasible", "error", "failed", "critical"].includes(normalized)) {
    variant = "danger";
  }

  return (
    <Badge variant={variant} className={`capitalize ${className}`}>
      {status.replace(/_/g, " ")}
    </Badge>
  );
};
