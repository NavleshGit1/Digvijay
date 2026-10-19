import React from "react";
import { Badge } from "../components/ui/Badge";
import { DataKindBadge } from "../components/data-display/DataKindBadge";

export const IntelligencePage: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Predictive Intelligence & SHAP Explanations</h2>
          <p className="text-sm text-slate-500">
            MLflow model registry, feature contributions, drift detection, and uncertainty intervals.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="info">3 Champion Models Promoted</Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { name: "Model 1: Maintenance Downtime", algo: "LightGBM Quantile (P80)", metric: "MAE 18.2 min", status: "Champion", target: "Downtime Hours" },
          { name: "Model 2: Task Delay Estimation", algo: "XGBoost Regressor", metric: "RMSE 24.5 min", status: "Champion", target: "Delay Minutes" },
          { name: "Model 3: Disruption Risk Classifier", algo: "Calibrated Logistic GBM", metric: "PR-AUC 0.89", status: "Champion", target: "Disruption Probability" },
        ].map((m, idx) => (
          <div key={idx} className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <Badge variant="success">{m.status}</Badge>
              <DataKindBadge kind="predicted" />
            </div>
            <h3 className="text-sm font-bold text-slate-900 mb-1">{m.name}</h3>
            <p className="text-xs text-slate-500 mb-3">{m.algo}</p>
            <div className="pt-3 border-t border-slate-100 flex justify-between text-xs font-mono">
              <span className="text-slate-400">Validation Metric:</span>
              <span className="font-bold text-blue-700">{m.metric}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
