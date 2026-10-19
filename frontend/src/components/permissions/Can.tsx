import React from "react";
import { UserRole } from "../../types/api";

interface CanProps {
  roles: UserRole[];
  userRoles: UserRole[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const Can: React.FC<CanProps> = ({
  roles,
  userRoles,
  children,
  fallback = null,
}) => {
  // Admin has superuser access across all UI controls
  if (userRoles.includes("admin")) {
    return <>{children}</>;
  }

  const hasPermission = roles.some((r) => userRoles.includes(r));

  if (!hasPermission) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
};
