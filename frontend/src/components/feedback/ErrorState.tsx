import React from "react";
import { Button } from "../ui/Button";

interface ErrorStateProps {
  title?: string;
  detail?: string;
  code?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = "Service Error",
  detail = "An unexpected error occurred while processing the operational request.",
  code,
  onRetry,
}) => {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-6 my-4">
      <div className="flex items-start">
        <div className="flex-shrink-0 text-red-500 text-xl font-bold mr-3">⚠</div>
        <div className="flex-1">
          <h3 className="text-sm font-semibold text-red-800">{title}</h3>
          <p className="text-sm text-red-700 mt-1">{detail}</p>
          {code && (
            <p className="text-xs font-mono text-red-600 mt-2 bg-red-100 inline-block px-2 py-0.5 rounded">
              Code: {code}
            </p>
          )}
          {onRetry && (
            <div className="mt-4">
              <Button variant="danger" size="sm" onClick={onRetry}>
                Retry Action
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
