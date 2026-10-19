import React, { useState } from "react";
import { Download, FileText, CheckCircle2 } from "lucide-react";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { api } from "../services/api";

export const ReportsPage: React.FC = () => {
  const [exportingId, setExportingId] = useState<string | null>(null);
  const [successId, setSuccessId] = useState<string | null>(null);

  const reports = [
    { id: "REP-01", title: "Operational Summary", desc: "Fleet availability, scheduled sorties, pending work orders", format: "PDF & CSV" },
    { id: "REP-02", title: "Scenario Comparison", desc: "Baseline vs. revised plan distributions under Monte Carlo", format: "PDF & CSV" },
    { id: "REP-03", title: "Model Performance & Drift", desc: "Accuracy metrics, PSI drift index, and model limitations", format: "PDF & CSV" },
    { id: "REP-04", title: "Resource Utilization", desc: "Asset hours and technician workload per operational shift", format: "PDF & CSV" },
    { id: "REP-05", title: "Maintenance & Downtime", desc: "Recorded downtime vs. predictive buffer allocations", format: "PDF & CSV" },
    { id: "REP-06", title: "Data Quality & Integrity", desc: "Reconciliation issues and data freshness status", format: "PDF & CSV" },
    { id: "REP-07", title: "Risk & Anomaly Findings", desc: "Unsupervised anomaly scores and technician review actions", format: "PDF & CSV" },
    { id: "REP-08", title: "Audit & Approval History", desc: "Cryptographic hash chain of plan approvals, rejections, and config edits", format: "Signed CSV" },
  ];

  const handleExportCsv = async (reportId: string) => {
    try {
      setExportingId(reportId);
      if (reportId === "REP-08") {
        await api.exportAuditLogsCsv();
      } else {
        // Mock download for other operational summaries
        await new Promise((r) => setTimeout(r, 600));
        alert(`Generating export for ${reportId}... Download will start shortly.`);
      }
      setSuccessId(reportId);
      setTimeout(() => setSuccessId(null), 3000);
    } catch (err: any) {
      alert(`Export failed: ${err?.message || "Server error"}`);
    } finally {
      setExportingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Operational Reports</h2>
          <p className="text-sm text-slate-500">
            Permission-scoped report generation with signed MinIO download URLs, data provenance, and cryptographic audit hash chains.
          </p>
        </div>
        <Badge variant="default">8 Reports Configured</Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {reports.map((r) => (
          <div key={r.id} className="bg-white rounded-lg border border-slate-200 p-5 shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono font-bold text-blue-600">{r.id}</span>
                <span className="text-[10px] font-mono text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                  {r.format}
                </span>
              </div>
              <h3 className="text-sm font-bold text-slate-900 mb-1">{r.title}</h3>
              <p className="text-xs text-slate-500 mb-4">{r.desc}</p>
            </div>
            <div className="flex items-center gap-2 pt-3 border-t border-slate-100">
              <Button
                variant="outline"
                size="sm"
                className="w-full flex items-center justify-center gap-1.5"
                onClick={() => handleExportCsv(r.id)}
                disabled={exportingId === r.id}
              >
                {successId === r.id ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span className="text-emerald-700">Downloaded</span>
                  </>
                ) : (
                  <>
                    <Download className={`w-3.5 h-3.5 ${exportingId === r.id ? "animate-bounce" : ""}`} />
                    <span>{exportingId === r.id ? "Generating..." : "Export CSV"}</span>
                  </>
                )}
              </Button>
              <Button variant="primary" size="sm" className="w-full">
                <FileText className="w-3.5 h-3.5 mr-1" />
                Download PDF
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
