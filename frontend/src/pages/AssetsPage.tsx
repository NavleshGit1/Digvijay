import React, { useEffect, useState } from "react";
import { Plane, Wrench, RefreshCw, X, Edit3 } from "lucide-react";
import { api } from "../services/api";
import { Asset, AssetDetail, Zone } from "../types/api";
import { DataTable, Column } from "../components/data-display/DataTable";
import { StatusBadge } from "../components/data-display/StatusBadge";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";

export const AssetsPage: React.FC = () => {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [typeFilter, setTypeFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [zoneFilter, setZoneFilter] = useState<string>("ALL");

  // Detail drawer & edit modal
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);
  const [assetDetail, setAssetDetail] = useState<AssetDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Edit status state
  const [isEditing, setIsEditing] = useState(false);
  const [newStatus, setNewStatus] = useState<string>("");
  const [auditReason, setAuditReason] = useState<string>("");
  const [editError, setEditError] = useState<string | null>(null);
  const [editSaving, setEditSaving] = useState(false);

  const fetchAssets = async () => {
    try {
      setLoading(true);
      setError(null);
      const [assetList, zoneList] = await Promise.all([
        api.getAssets(),
        api.getZones(),
      ]);
      setAssets(assetList);
      setZones(zoneList);
    } catch (err: any) {
      setError(err?.detail || "Failed to load fleet assets");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssets();
  }, []);

  const handleOpenDetail = async (assetId: string) => {
    setSelectedAssetId(assetId);
    setIsEditing(false);
    setEditError(null);
    try {
      setDetailLoading(true);
      const detail = await api.getAssetDetail(assetId);
      setAssetDetail(detail);
      setNewStatus(detail.status);
    } catch (err: any) {
      console.error("Failed to load asset detail:", err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleSaveStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAssetId) return;
    if (!auditReason.trim()) {
      setEditError("Audit reason is required for operational state updates.");
      return;
    }

    try {
      setEditSaving(true);
      setEditError(null);
      await api.updateAsset(selectedAssetId, {
        status: newStatus,
        reason: auditReason,
      });
      // Refresh detail and list
      const updated = await api.getAssetDetail(selectedAssetId);
      setAssetDetail(updated);
      setIsEditing(false);
      setAuditReason("");
      fetchAssets();
    } catch (err: any) {
      setEditError(err?.detail || "Failed to update asset status.");
    } finally {
      setEditSaving(false);
    }
  };

  // Filtered rows for DataTable
  const filteredAssets = assets.filter((a) => {
    if (typeFilter !== "ALL" && a.asset_type !== typeFilter) return false;
    if (statusFilter !== "ALL" && a.status !== statusFilter) return false;
    if (zoneFilter !== "ALL" && a.zone_id !== zoneFilter) return false;
    return true;
  });

  const columns: Column<Asset>[] = [
    {
      key: "identifier",
      header: "Identifier & Airframe",
      sortable: true,
      render: (a) => (
        <div className="flex items-center gap-2">
          <Plane className="w-3.5 h-3.5 text-blue-600" />
          <div>
            <span className="font-mono font-bold text-slate-900">{a.identifier}</span>
            <span className="text-[11px] text-slate-400 block">{a.model_name}</span>
          </div>
        </div>
      ),
    },
    {
      key: "asset_type",
      header: "Type",
      sortable: true,
      render: (a) => (
        <span className="text-slate-600 font-mono text-[11px]">
          {a.asset_type.replace(/_/g, " ")}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      sortable: true,
      render: (a) => <StatusBadge status={a.status} />,
    },
    {
      key: "health_score",
      header: "Health Score",
      sortable: true,
      render: (a) => {
        const pct = Math.round(a.health_score * 100);
        const color =
          pct >= 85 ? "bg-emerald-500 text-emerald-700" : pct >= 70 ? "bg-amber-500 text-amber-700" : "bg-rose-500 text-rose-700";
        return (
          <div className="w-28 space-y-1">
            <div className="flex justify-between text-[11px] font-mono">
              <span className="font-bold">{pct}%</span>
              {a.has_active_maintenance && (
                <span className="text-[9px] text-amber-600 flex items-center gap-0.5">
                  <Wrench className="w-2.5 h-2.5" /> Servicing
                </span>
              )}
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
              <div
                className={`h-full ${color.split(" ")[0]} transition-all`}
                style={{ width: `${pct}%` }}
              ></div>
            </div>
          </div>
        );
      },
    },
    {
      key: "flight_hours",
      header: "Flight Hours",
      sortable: true,
      align: "right",
      render: (a) => <span className="font-mono">{a.flight_hours.toFixed(1)} hrs</span>,
    },
    {
      key: "cycles",
      header: "Cycles",
      sortable: true,
      align: "right",
      render: (a) => <span className="font-mono">{a.cycles}</span>,
    },
    {
      key: "zone_name",
      header: "Home Base",
      sortable: true,
      render: (a) => (
        <div>
          <span className="font-mono font-bold text-blue-700 text-[11px]">{a.zone_code}</span>
          <span className="text-[10px] text-slate-400 block truncate max-w-[120px]">{a.zone_name.split("-")[0]}</span>
        </div>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      align: "right",
      render: (a) => (
        <Button
          variant="outline"
          size="sm"
          onClick={() => handleOpenDetail(a.id)}
          className="text-[11px] py-1 px-2.5 h-auto"
        >
          Inspect
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">Fleet Asset Inventory</h2>
            <Badge variant="default">{assets.length} Aircraft Tracked</Badge>
          </div>
          <p className="text-sm text-slate-500">
            Real-time equipment readiness scores, accrued wear counters, and maintenance window scheduling.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchAssets} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Fleet
          </Button>
        </div>
      </div>

      {/* Filter Dropdowns Bar */}
      <DataTable
        data={filteredAssets}
        columns={columns}
        keyField="id"
        loading={loading}
        error={error}
        onRetry={fetchAssets}
        searchPlaceholder="Search by aircraft ID (e.g. SB-001) or model..."
        filters={
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="ALL">All Aircraft Types</option>
              <option value="FIGHTER_MULTIROLE">Fighter Multirole</option>
              <option value="TRANSPORT_CARGO">Transport Cargo</option>
              <option value="REFUELER_TANKER">Refueler Tanker</option>
              <option value="RECON_SURVEILLANCE">Reconnaissance</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="available">Available</option>
              <option value="in_use">In Use / Sortie</option>
              <option value="maintenance">Maintenance</option>
              <option value="grounded">Grounded</option>
            </select>

            <select
              value={zoneFilter}
              onChange={(e) => setZoneFilter(e.target.value)}
              className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="ALL">All Bases</option>
              {zones.map((z) => (
                <option key={z.id} value={z.id}>
                  {z.code} - {z.name.split("-")[0]}
                </option>
              ))}
            </select>
          </div>
        }
      />

      {/* Detail Slide-over Drawer */}
      {selectedAssetId && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end animate-fade-in">
          <div className="w-full max-w-lg bg-white h-full shadow-2xl flex flex-col justify-between overflow-y-auto">
            {/* Drawer Header */}
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-blue-100 rounded-lg text-blue-700">
                  <Plane className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-base font-mono">
                    {assetDetail?.identifier || "Asset Dossier"}
                  </h3>
                  <p className="text-xs text-slate-500">
                    {assetDetail?.model_name} · {assetDetail?.zone_name}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedAssetId(null)}
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-200/60"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Drawer Body */}
            <div className="p-6 space-y-6 flex-1">
              {detailLoading ? (
                <div className="py-20 text-center text-slate-400 text-xs animate-pulse">
                  Loading comprehensive asset dossier...
                </div>
              ) : assetDetail ? (
                <>
                  {/* Status & Health Gauge Banner */}
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider">
                        Operational State
                      </span>
                      <StatusBadge status={assetDetail.status} />
                    </div>

                    <div className="space-y-1.5">
                      <div className="flex justify-between text-xs font-mono">
                        <span className="text-slate-600">Recorded Health Score</span>
                        <strong className="text-slate-900">
                          {Math.round(assetDetail.health_score * 100)}%
                        </strong>
                      </div>
                      <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-full ${
                            assetDetail.health_score >= 0.85
                              ? "bg-emerald-500"
                              : assetDetail.health_score >= 0.70
                              ? "bg-amber-500"
                              : "bg-rose-500"
                          }`}
                          style={{ width: `${Math.round(assetDetail.health_score * 100)}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>

                  {/* Accrued Usage Telemetry */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Usage Accruals & Counters
                    </h4>
                    <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                        <div className="text-slate-400 text-[10px]">TOTAL FLIGHT HOURS</div>
                        <div className="text-base font-bold text-slate-900 mt-0.5">
                          {assetDetail.flight_hours.toFixed(1)} hrs
                        </div>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                        <div className="text-slate-400 text-[10px]">TOTAL CYCLES</div>
                        <div className="text-base font-bold text-slate-900 mt-0.5">
                          {assetDetail.cycles} landings
                        </div>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                        <div className="text-slate-400 text-[10px]">SINCE LAST SERVICE</div>
                        <div className="text-sm font-bold text-slate-700 mt-0.5">
                          {assetDetail.usage_summary.flight_hours_since_last_service} hrs
                        </div>
                      </div>
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-100">
                        <div className="text-slate-400 text-[10px]">BAY PARKING LOCATION</div>
                        <div className="text-sm font-bold text-blue-700 mt-0.5">
                          {assetDetail.current_location || "Ramp-01"}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Recent Maintenance Work Orders */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                        Recent & Scheduled Maintenance
                      </h4>
                      <Badge variant="outline" className="text-[10px]">
                        {assetDetail.recent_maintenance.length} Records
                      </Badge>
                    </div>

                    {assetDetail.recent_maintenance.length === 0 ? (
                      <p className="text-xs text-slate-400 p-4 border border-dashed rounded-lg text-center">
                        No maintenance work orders recorded for this airframe.
                      </p>
                    ) : (
                      <div className="space-y-2 max-h-48 overflow-y-auto">
                        {assetDetail.recent_maintenance.map((m) => (
                          <div
                            key={m.id}
                            className="p-2.5 rounded-lg border border-slate-200 bg-white text-xs space-y-1"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-slate-800">
                                {m.category.replace(/_/g, " ").toUpperCase()}
                              </span>
                              <Badge
                                variant={
                                  m.status === "completed"
                                    ? "success"
                                    : m.status === "in_progress"
                                    ? "warning"
                                    : "info"
                                }
                              >
                                {m.status.toUpperCase()}
                              </Badge>
                            </div>
                            <div className="flex justify-between text-[11px] text-slate-500 font-mono">
                              <span>Window:</span>
                              <span>
                                {new Date(m.start_time).toLocaleDateString()} -{" "}
                                {new Date(m.end_time).toLocaleDateString()}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Status Edit Modal / Form (Audited Action) */}
                  <div className="border-t border-slate-200 pt-4 space-y-3">
                    {!isEditing ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setIsEditing(true)}
                        className="w-full text-xs"
                      >
                        <Edit3 className="w-3.5 h-3.5 mr-1.5" />
                        Update Operational Status (Audited)
                      </Button>
                    ) : (
                      <form onSubmit={handleSaveStatus} className="bg-blue-50/60 p-4 rounded-xl border border-blue-200 space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-blue-900">
                            Update Asset Readiness
                          </span>
                          <button
                            type="button"
                            onClick={() => setIsEditing(false)}
                            className="text-xs text-slate-400 hover:text-slate-600"
                          >
                            Cancel
                          </button>
                        </div>

                        {editError && (
                          <div className="p-2 bg-rose-50 border border-rose-200 rounded text-rose-700 text-[11px]">
                            {editError}
                          </div>
                        )}

                        <div className="space-y-1">
                          <label className="text-[11px] font-semibold text-slate-700">New Status</label>
                          <select
                            value={newStatus}
                            onChange={(e) => setNewStatus(e.target.value)}
                            className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white"
                          >
                            <option value="available">Available (Flight Ready)</option>
                            <option value="in_use">In Use (Sortie Assigned)</option>
                            <option value="maintenance">Maintenance (Grounded for Servicing)</option>
                            <option value="grounded">Grounded (AOG / Unfit)</option>
                          </select>
                        </div>

                        <div className="space-y-1">
                          <label className="text-[11px] font-semibold text-slate-700">
                            Justification / Reason (Mandatory Audit Requirement)
                          </label>
                          <textarea
                            value={auditReason}
                            onChange={(e) => setAuditReason(e.target.value)}
                            placeholder="State reason for operational state change..."
                            rows={2}
                            className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white"
                          />
                        </div>

                        <Button
                          variant="primary"
                          size="sm"
                          type="submit"
                          loading={editSaving}
                          className="w-full text-xs"
                        >
                          Save & Record Immutable Audit Log
                        </Button>
                      </form>
                    )}
                  </div>
                </>
              ) : null}
            </div>

            {/* Drawer Footer */}
            <div className="p-4 bg-slate-50 border-t border-slate-200 text-right">
              <Button variant="outline" size="sm" onClick={() => setSelectedAssetId(null)}>
                Close Dossier
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
