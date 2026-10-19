import React, { useEffect, useState } from "react";
import { Users, RefreshCw, X, Edit3, AlertTriangle } from "lucide-react";
import { api } from "../services/api";
import { Personnel, PersonnelDetail, Zone } from "../types/api";
import { DataTable, Column } from "../components/data-display/DataTable";
import { StatusBadge } from "../components/data-display/StatusBadge";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";

export const PersonnelPage: React.FC = () => {
  const [personnel, setPersonnel] = useState<Personnel[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [roleFilter, setRoleFilter] = useState<string>("ALL");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [zoneFilter, setZoneFilter] = useState<string>("ALL");

  // Detail drawer & edit modal
  const [selectedPersonnelId, setSelectedPersonnelId] = useState<string | null>(null);
  const [personnelDetail, setPersonnelDetail] = useState<PersonnelDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Edit status state
  const [isEditing, setIsEditing] = useState(false);
  const [newStatus, setNewStatus] = useState<string>("");
  const [newDutyHours, setNewDutyHours] = useState<number>(0);
  const [auditReason, setAuditReason] = useState<string>("");
  const [editError, setEditError] = useState<string | null>(null);
  const [editSaving, setEditSaving] = useState(false);

  const fetchPersonnel = async () => {
    try {
      setLoading(true);
      setError(null);
      const [personnelList, zoneList] = await Promise.all([
        api.getPersonnel({ limit: 200 }),
        api.getZones(),
      ]);
      setPersonnel(personnelList);
      setZones(zoneList);
    } catch (err: any) {
      setError(err?.detail || "Failed to load personnel roster");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPersonnel();
  }, []);

  const handleOpenDetail = async (pId: string) => {
    setSelectedPersonnelId(pId);
    setIsEditing(false);
    setEditError(null);
    try {
      setDetailLoading(true);
      const detail = await api.getPersonnelDetail(pId);
      setPersonnelDetail(detail);
      setNewStatus(detail.status);
      setNewDutyHours(detail.duty_hours_accumulated);
    } catch (err: any) {
      console.error("Failed to load personnel detail:", err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleSaveStatus = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPersonnelId) return;
    if (!auditReason.trim()) {
      setEditError("Audit reason is required for crew duty adjustments.");
      return;
    }

    try {
      setEditSaving(true);
      setEditError(null);
      await api.updatePersonnel(selectedPersonnelId, {
        status: newStatus,
        duty_hours_accumulated: Number(newDutyHours),
        reason: auditReason,
      });
      const updated = await api.getPersonnelDetail(selectedPersonnelId);
      setPersonnelDetail(updated);
      setIsEditing(false);
      setAuditReason("");
      fetchPersonnel();
    } catch (err: any) {
      setEditError(err?.detail || "Failed to update crew member.");
    } finally {
      setEditSaving(false);
    }
  };

  // Filtered rows for DataTable
  const filteredPersonnel = personnel.filter((p) => {
    if (roleFilter !== "ALL" && p.role_type !== roleFilter) return false;
    if (statusFilter !== "ALL" && p.status !== statusFilter) return false;
    if (zoneFilter !== "ALL" && p.home_zone_id !== zoneFilter) return false;
    return true;
  });

  const columns: Column<Personnel>[] = [
    {
      key: "name",
      header: "Operator & Callsign",
      sortable: true,
      render: (p) => (
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-slate-100 rounded text-slate-700">
            <Users className="w-3.5 h-3.5" />
          </div>
          <div>
            <div className="font-bold text-slate-900 font-mono text-xs">
              {p.name}
            </div>
            {p.callsign && (
              <span className="text-[10px] text-blue-600 font-mono font-semibold">
                "{p.callsign}"
              </span>
            )}
          </div>
        </div>
      ),
    },
    {
      key: "role_type",
      header: "Role Type",
      sortable: true,
      render: (p) => (
        <Badge
          variant={
            p.role_type === "pilot"
              ? "info"
              : p.role_type === "maintenance_tech"
              ? "warning"
              : "default"
          }
        >
          {p.role_type.replace(/_/g, " ").toUpperCase()}
        </Badge>
      ),
    },
    {
      key: "status",
      header: "Readiness Status",
      sortable: true,
      render: (p) => <StatusBadge status={p.status} />,
    },
    {
      key: "duty_hours_accumulated",
      header: "Duty Accumulation",
      sortable: true,
      render: (p) => {
        const hrs = p.duty_hours_accumulated;
        const maxDuty = 12.0;
        const pct = Math.min(100, Math.round((hrs / maxDuty) * 100));
        const isNearLimit = hrs >= 10.0;

        return (
          <div className="w-28 space-y-1">
            <div className="flex justify-between text-[11px] font-mono">
              <span className={isNearLimit ? "text-amber-600 font-bold" : "text-slate-700"}>
                {hrs.toFixed(1)} / 12h
              </span>
              {isNearLimit && (
                <span className="text-[9px] text-amber-600 flex items-center">
                  <AlertTriangle className="w-2.5 h-2.5" />
                </span>
              )}
            </div>
            <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
              <div
                className={`h-full ${
                  isNearLimit ? "bg-amber-500" : "bg-blue-500"
                } transition-all`}
                style={{ width: `${pct}%` }}
              ></div>
            </div>
          </div>
        );
      },
    },
    {
      key: "home_zone_name",
      header: "Assigned Airbase",
      sortable: true,
      render: (p) => (
        <span className="font-mono text-xs text-slate-700">{p.home_zone_name.split("-")[0]}</span>
      ),
    },
    {
      key: "qualifications",
      header: "Qualifications",
      render: (p) => (
        <div className="flex items-center gap-1 flex-wrap max-w-xs">
          {p.qualifications.slice(0, 2).map((q) => (
            <span
              key={q}
              className="text-[9px] font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded border border-slate-200"
            >
              {q}
            </span>
          ))}
          {p.qualifications.length > 2 && (
            <span className="text-[9px] text-slate-400 font-mono">
              +{p.qualifications.length - 2}
            </span>
          )}
        </div>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      align: "right",
      render: (p) => (
        <Button
          variant="outline"
          size="sm"
          onClick={() => handleOpenDetail(p.id)}
          className="text-[11px] py-1 px-2.5 h-auto"
        >
          Dossier
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
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">Personnel & Flight Crew</h2>
            <Badge variant="default">{personnel.length} Crew Members</Badge>
          </div>
          <p className="text-sm text-slate-500">
            Crew readiness rosters, accumulated duty tracking against 12-hour limits, and mission qualification validity.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchPersonnel} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Roster
          </Button>
        </div>
      </div>

      {/* DataTable */}
      <DataTable
        data={filteredPersonnel}
        columns={columns}
        keyField="id"
        loading={loading}
        error={error}
        onRetry={fetchPersonnel}
        searchPlaceholder="Search by operator name or callsign..."
        filters={
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="ALL">All Roles</option>
              <option value="pilot">Pilots</option>
              <option value="maintenance_tech">Technicians</option>
              <option value="wso">Weapons Systems Officers (WSO)</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="available">Available</option>
              <option value="on_duty">On Duty</option>
              <option value="rest_period">Rest Period (Mandatory)</option>
              <option value="leave">Leave</option>
            </select>

            <select
              value={zoneFilter}
              onChange={(e) => setZoneFilter(e.target.value)}
              className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="ALL">All Airbases</option>
              {zones.map((z) => (
                <option key={z.id} value={z.id}>
                  {z.code} - {z.name.split("-")[0]}
                </option>
              ))}
            </select>
          </div>
        }
      />

      {/* Dossier Drawer */}
      {selectedPersonnelId && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end animate-fade-in">
          <div className="w-full max-w-lg bg-white h-full shadow-2xl flex flex-col justify-between overflow-y-auto">
            {/* Drawer Header */}
            <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-blue-100 rounded-lg text-blue-700">
                  <Users className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="font-bold text-slate-900 text-base font-mono">
                    {personnelDetail?.name || "Personnel Dossier"}
                  </h3>
                  <p className="text-xs text-slate-500">
                    Role: {personnelDetail?.role_type.replace(/_/g, " ").toUpperCase()} · {personnelDetail?.home_zone_name}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedPersonnelId(null)}
                className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-200/60"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Drawer Body */}
            <div className="p-6 space-y-6 flex-1">
              {detailLoading ? (
                <div className="py-20 text-center text-slate-400 text-xs animate-pulse">
                  Loading comprehensive crew dossier...
                </div>
              ) : personnelDetail ? (
                <>
                  {/* Status & Readiness */}
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider">
                        Operational Status
                      </span>
                      <StatusBadge status={personnelDetail.status} />
                    </div>

                    <div className="flex items-center justify-between text-xs font-mono">
                      <span className="text-slate-600">Duty Hours Accrued</span>
                      <span className="font-bold text-slate-900">
                        {personnelDetail.duty_hours_accumulated.toFixed(1)} hrs / 12.0 hrs max
                      </span>
                    </div>
                  </div>

                  {/* Certified Qualifications & Expirations */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                        Mission Certifications & Validity
                      </h4>
                      <Badge variant="outline" className="text-[10px]">
                        {personnelDetail.qualification_details.length} Active Badges
                      </Badge>
                    </div>

                    <div className="space-y-2">
                      {personnelDetail.qualification_details.map((q) => (
                        <div
                          key={q.qualification_code}
                          className="p-3 rounded-lg border border-slate-200 bg-white text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold font-mono text-slate-900">
                              {q.qualification_code}
                            </span>
                            <Badge variant={q.is_expired ? "danger" : "success"}>
                              {q.is_expired ? "EXPIRED" : "CURRENT & VALID"}
                            </Badge>
                          </div>
                          <p className="text-[11px] text-slate-600">{q.qualification_name}</p>
                          <div className="flex justify-between text-[10px] text-slate-400 font-mono pt-1">
                            <span>Acquired: {new Date(q.acquired_at).toLocaleDateString()}</span>
                            <span>Expires: {new Date(q.expires_at).toLocaleDateString()}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Update Status / Duty Form (Audited) */}
                  <div className="border-t border-slate-200 pt-4 space-y-3">
                    {!isEditing ? (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setIsEditing(true)}
                        className="w-full text-xs"
                      >
                        <Edit3 className="w-3.5 h-3.5 mr-1.5" />
                        Update Readiness / Reset Duty (Audited)
                      </Button>
                    ) : (
                      <form onSubmit={handleSaveStatus} className="bg-blue-50/60 p-4 rounded-xl border border-blue-200 space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-blue-900">
                            Update Crew Member Readiness
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
                          <label className="text-[11px] font-semibold text-slate-700">Readiness Status</label>
                          <select
                            value={newStatus}
                            onChange={(e) => setNewStatus(e.target.value)}
                            className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white"
                          >
                            <option value="available">Available (Flight Ready)</option>
                            <option value="on_duty">On Duty (Sortie Active)</option>
                            <option value="rest_period">Rest Period (Mandatory 12h Rest)</option>
                            <option value="leave">Leave / Unavailable</option>
                          </select>
                        </div>

                        <div className="space-y-1">
                          <label className="text-[11px] font-semibold text-slate-700">Accumulated Duty Hours</label>
                          <input
                            type="number"
                            step="0.5"
                            min="0"
                            max="24"
                            value={newDutyHours}
                            onChange={(e) => setNewDutyHours(parseFloat(e.target.value))}
                            className="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white"
                          />
                        </div>

                        <div className="space-y-1">
                          <label className="text-[11px] font-semibold text-slate-700">
                            Reason / Justification (Mandatory Audit Requirement)
                          </label>
                          <textarea
                            value={auditReason}
                            onChange={(e) => setAuditReason(e.target.value)}
                            placeholder="State justification for crew state adjustment..."
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
              <Button variant="outline" size="sm" onClick={() => setSelectedPersonnelId(null)}>
                Close Dossier
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
