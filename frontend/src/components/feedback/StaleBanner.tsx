import React from "react";
import { Button } from "../ui/Button";

interface StaleBannerProps {
  lastUpdated: string;
  onRefresh?: () => void;
}

export const StaleBanner: React.FC<StaleBannerProps> = ({ lastUpdated, onRefresh }) => {
  return (
    <div className="bg-amber-50 border-l-4 border-amber-500 p-4 mb-4 rounded-r-md flex items-center justify-between">
      <div className="flex items-center">
        <span className="text-amber-600 mr-2">⏱</span>
        <div>
          <p className="text-sm font-medium text-amber-800">
            Data Snapshot Stale
          </p>
          <p className="text-xs text-amber-700">
            Underlying operational records have updated since this view was generated ({lastUpdated}).
          </p>
        </div>
      </div>
      {onRefresh && (
        <Button variant="secondary" size="sm" onClick={onRefresh}>
          Refresh View
        </Button>
      )}
    </div>
  );
};
