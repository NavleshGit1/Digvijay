import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Wrench, Package, RefreshCw, Plus } from "lucide-react";
import { api } from "../services/api";
import { Asset, MaintenanceRecord, SparesInventory, Zone } from "../types/api";
import { DataTable, Column } from "../components/data-display/DataTable";
import { Button } from "../components/ui/Button";
import { Badge } from "../components/ui/Badge";

export const MaintenancePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = searchParams.get("tab") || "active";
  const [activeTab, setActiveTab] = useState<string>(initialTab);

  const [records, setRecords] = useState<MaintenanceRecord[]>([]);
  const [spares, setSpares] = useState<SparesInventory[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Schedule modal state
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [scheduleAssetId, setScheduleAssetId] = useState("");
  const [scheduleCategory, setScheduleCategory] = useState("100_hour");
  const [scheduleStart, setScheduleStart] = useState("");
  const [scheduleEnd, setScheduleEnd] = useState("");
  const [scheduleReason, setScheduleReason] = useState("");
  const [scheduleError, setScheduleError] = useState<string | null>(null);
  const [scheduleSaving, setScheduleSaving] = useState(false);

  // Resupply modal state
  const [showResupplyModal, setShowResupplyModal] = useState(false);
  const [resupplyPartId, setResupplyPartId] = useState("");
  const [resupplyZoneId, setResupplyZoneId] = useState("");
  const [resupplyQuantity, setResupplyQuantity] = useState(5);
  const [resupplyReason, setResupplyReason] = useState("");
  const [resupplyError, setResupplyError] = useState<string | null>(null);
  const [resupplySaving, setResupplySaving] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [maintRecords, sparesList, assetList, zoneList] = await Promise.all([
        api.getMaintenanceRecords(),
        api.getSpares(),
        api.getAssets(),
        api.getZones(),
      ]);
      setRecords(maintRecords);
      setSpares(sparesList);
      setAssets(assetList);
      setZones(zoneList);

      if (assetList.length > 0 && !scheduleAssetId) setScheduleAssetId(assetList[0].id);
      if (sparesList.length > 0 && !resupplyPartId) {
        setResupplyPartId(sparesList[0].part_id);
        setResupplyZoneId(sparesList[0].zone_id);
      }
    } catch (err: any) {
      setError(err?.detail || "Failed to load maintenance data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  const handleScheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scheduleAssetId || !scheduleStart || !scheduleEnd || !scheduleReason.trim()) {
      setScheduleError("All fields including mandatory audit justification are required.");
      return;
    }

    try {
      setScheduleSaving(true);
      setScheduleError(null);
      await api.scheduleMaintenance({
        asset_id: scheduleAssetId,
        category: scheduleCategory,
        start_time: new Date(scheduleStart).toISOString(),
        end_time: new Date(scheduleEnd).toISOString(),
        reason: scheduleReason,
      });
      setShowScheduleModal(false);
      setScheduleReason("");
      fetchData();
    } catch (err: any) {
      setScheduleError(err?.detail || "Failed to schedule maintenance window.");
    } finally {
      setScheduleSaving(false);
    }
  };

  const handleResupplySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resupplyPartId || !resupplyZoneId || !resupplyReason.trim()) {
      setResupplyError("All fields including mandatory audit reason are required.");
      return;
    }

    try {
      setResupplySaving(true);
      setResupplyError(null);
      await api.orderSpares({
        part_id: resupplyPartId,
        zone_id: resupplyZoneId,
        quantity: Number(resupplyQuantity),
        reason: resupplyReason,
      });
      setShowResupplyModal(false);
      setResupplyReason("");
      fetchData();
    } catch (err: any) {
      setResupplyError(err?.detail || "Failed to place resupply order.");
    } finally {
      setResupplySaving(false);
    }
  };

  const workOrderColumns: Column<MaintenanceRecord>[] = [
    {
      key: "asset_identifier",
      header: "Airframe",
      sortable: true,
      render: (r) => (
        <span className="font-mono font-bold text-slate-900">{r.asset_identifier}</span>
      ),
    },
    {
      key: "category",
      header: "Service Category",
      sortable: true,
      render: (r) => (
        <span className="font-semibold text-slate-700">
          {r.category.replace(/_/g, " ").toUpperCase()}
        </span>
      ),
    },
    {
      key: "status",
      header: "Status",
      sortable: true,
      render: (r) => (
        <Badge
          variant={
            r.status === "completed"
              ? "success"
              : r.status === "in_progress"
              ? "warning"
              : r.is_overdue
              ? "danger"
              : "info"
          }
        >
          {r.is_overdue ? "OVERDUE" : r.status.toUpperCase()}
        </Badge>
      ),
    },
    {
      key: "start_time",
      header: "Maintenance Window",
      sortable: true,
      render: (r) => (
        <span className="font-mono text-xs text-slate-600">
          {new Date(r.start_time).toLocaleDateString()} {new Date(r.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} →{" "}
          {new Date(r.end_time).toLocaleDateString()} {new Date(r.end_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      ),
    },
    {
      key: "is_unplanned",
      header: "Type",
      render: (r) => (
        <Badge variant={r.is_unplanned ? "danger" : "default"}>
          {r.is_unplanned ? "UNPLANNED / AOG" : "SCHEDULED"}
        </Badge>
      ),
    },
  ];

  const sparesColumns: Column<SparesInventory>[] = [
    {
      key: "part_number",
      header: "Part Number & Name",
      sortable: true,
      render: (s) => (
        <div>
          <span className="font-mono font-bold text-slate-900">{s.part_number}</span>
          <span className="text-[11px] text-slate-500 block">{s.part_name}</span>
        </div>
      ),
    },
    {
      key: "category",
      header: "System Category",
      sortable: true,
      render: (s) => (
        <span className="font-mono text-xs text-slate-600 uppercase">{s.category}</span>
      ),
    },
    {
      key: "zone_name",
      header: "Base Depot",
      sortable: true,
      render: (s) => (
        <span className="font-mono text-xs text-blue-700">{s.zone_name.split("-")[0]}</span>
      ),
    },
    {
      key: "on_hand",
      header: "Stock vs Safety Level",
      sortable: true,
      render: (s) => {
        const isShortage = s.is_shortage;
        return (
          <div className="flex items-center gap-2">
            <span
              className={`font-mono font-bold text-xs ${
                isShortage ? "text-rose-600" : "text-emerald-700"
              }`}
            >
              {s.on_hand} on-hand
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              (Min Safe: {s.minimum_safety_level})
            </span>
            {isShortage && (
              <Badge variant="danger" className="text-[9px] py-0 px-1">
                SHORTAGE
              </Badge>
            )}
          </div>
        );
      },
    },
    {
      key: "reserved",
      header: "Reserved",
      align: "right",
      render: (s) => <span className="font-mono text-xs">{s.reserved}</span>,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-xl font-bold text-slate-900 tracking-tight">Maintenance & Logistics</h2>
            <Badge variant="default">{records.length} Work Orders</Badge>
          </div>
          <p className="text-sm text-slate-500">
            Work order scheduling with Hard Maintenance Window validation, spares inventory safety thresholds, and resupply pipeline.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowResupplyModal(true)}
          >
            <Package className="w-3.5 h-3.5 mr-1.5" />
            Order Spares
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowScheduleModal(true)}
          >
            <Plus className="w-3.5 h-3.5 mr-1.5" />
            Schedule Work Order
          </Button>
        </div>
      </div>

      {/* Tabs Row */}
      <div className="flex border-b border-slate-200 space-x-6 text-sm font-semibold">
        {[
          { id: "active", label: "All Work Orders", count: records.length },
          { id: "overdue", label: "Overdue Work Orders", count: records.filter((r) => r.is_overdue).length },
          { id: "spares", label: "Spares Inventory", count: spares.filter((s) => s.is_shortage).length, isAlert: true },
          { id: "rules", label: "Service Inspection Rules", count: 4 },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleTabChange(tab.id)}
            className={`pb-3 flex items-center gap-2 border-b-2 transition-colors ${
              activeTab === tab.id
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            <span>{tab.label}</span>
            <Badge variant={tab.isAlert && tab.count > 0 ? "danger" : "default"} className="text-[10px]">
              {tab.count}
            </Badge>
          </button>
        ))}
      </div>

      {/* Tab 1: All Work Orders */}
      {activeTab === "active" && (
        <DataTable
          data={records}
          columns={workOrderColumns}
          keyField="id"
          loading={loading}
          error={error}
          onRetry={fetchData}
          searchPlaceholder="Search work orders by airframe ID or service..."
        />
      )}

      {/* Tab 2: Overdue Work Orders */}
      {activeTab === "overdue" && (
        <DataTable
          data={records.filter((r) => r.is_overdue)}
          columns={workOrderColumns}
          keyField="id"
          loading={loading}
          error={error}
          onRetry={fetchData}
          emptyTitle="Zero Overdue Work Orders"
          emptyMessage="All scheduled maintenance work orders are currently within their compliance windows."
          searchPlaceholder="Search overdue work orders..."
        />
      )}

      {/* Tab 3: Spares Inventory */}
      {activeTab === "spares" && (
        <DataTable
          data={spares}
          columns={sparesColumns}
          keyField="id"
          loading={loading}
          error={error}
          onRetry={fetchData}
          searchPlaceholder="Search spares by part number or name..."
        />
      )}

      {/* Tab 4: Service Inspection Rules */}
      {activeTab === "rules" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { code: "RULE-100H", name: "100-Hour Periodic Inspection", threshold: "100.0 Flight Hours", duration: "8.0 Hours", parts: "Primary Actuator O-Rings, Oil Pump Filters" },
            { code: "RULE-500H", name: "500-Hour Depot Overhaul", threshold: "500.0 Flight Hours", duration: "48.0 Hours", parts: "Turbine Blade Set, Fuel Injector Ring" },
            { code: "RULE-250C", name: "250-Cycle Landing Gear Inspection", threshold: "250 Landings", duration: "12.0 Hours", parts: "Main Gear Bearing Set, Brake Disks" },
            { code: "RULE-AV-CAL", name: "Annual Avionics Sensor Recalibration", threshold: "365 Calendar Days", duration: "16.0 Hours", parts: "Radar T/R Module Set, IFF Transponder" },
          ].map((rule) => (
            <div key={rule.code} className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-blue-700">{rule.code}</span>
                <Badge variant="success">ACTIVE RULE</Badge>
              </div>
              <h4 className="font-bold text-slate-800 text-sm">{rule.name}</h4>
              <div className="text-xs text-slate-600 space-y-1 font-mono">
                <div><span className="text-slate-400">Trigger Threshold:</span> {rule.threshold}</div>
                <div><span className="text-slate-400">Estimated Ground Time:</span> {rule.duration}</div>
                <div><span className="text-slate-400">Required Components:</span> {rule.parts}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Schedule Work Order Modal */}
      {showScheduleModal && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full shadow-2xl border border-slate-200 p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Wrench className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-slate-900">Schedule Work Order</h3>
              </div>
              <button onClick={() => setShowScheduleModal(false)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>

            {scheduleError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs">
                {scheduleError}
              </div>
            )}

            <form onSubmit={handleScheduleSubmit} className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Target Airframe</label>
                <select
                  value={scheduleAssetId}
                  onChange={(e) => setScheduleAssetId(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2 bg-white"
                >
                  {assets.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.identifier} ({a.model_name}) - {a.status}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Service Category</label>
                <select
                  value={scheduleCategory}
                  onChange={(e) => setScheduleCategory(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2 bg-white"
                >
                  <option value="100_hour">100-Hour Periodic Inspection</option>
                  <option value="phase_inspection">Phase Inspection & Avionics Check</option>
                  <option value="overhaul">Turbine Engine Overhaul</option>
                  <option value="unscheduled_repair">Unscheduled Hydraulic Repair</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Start Time</label>
                  <input
                    type="datetime-local"
                    value={scheduleStart}
                    onChange={(e) => setScheduleStart(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg p-2 bg-white"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">End Time</label>
                  <input
                    type="datetime-local"
                    value={scheduleEnd}
                    onChange={(e) => setScheduleEnd(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg p-2 bg-white"
                  />
                </div>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Audit Justification (Mandatory)
                </label>
                <textarea
                  value={scheduleReason}
                  onChange={(e) => setScheduleReason(e.target.value)}
                  placeholder="State reason for scheduling maintenance window..."
                  rows={2}
                  className="w-full border border-slate-300 rounded-lg p-2 bg-white"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <Button variant="outline" size="sm" type="button" onClick={() => setShowScheduleModal(false)}>
                  Cancel
                </Button>
                <Button variant="primary" size="sm" type="submit" loading={scheduleSaving}>
                  Validate & Schedule
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Resupply Order Modal */}
      {showResupplyModal && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full shadow-2xl border border-slate-200 p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Package className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-slate-900">Order Spares Resupply</h3>
              </div>
              <button onClick={() => setShowResupplyModal(false)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>

            {resupplyError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs">
                {resupplyError}
              </div>
            )}

            <form onSubmit={handleResupplySubmit} className="space-y-3 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Component / Part</label>
                <select
                  value={resupplyPartId}
                  onChange={(e) => setResupplyPartId(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2 bg-white"
                >
                  {spares.map((s) => (
                    <option key={s.id} value={s.part_id}>
                      {s.part_number} - {s.part_name} ({s.on_hand} in stock)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Destination Base</label>
                <select
                  value={resupplyZoneId}
                  onChange={(e) => setResupplyZoneId(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg p-2 bg-white"
                >
                  {zones.map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.code} - {z.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Quantity</label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={resupplyQuantity}
                  onChange={(e) => setResupplyQuantity(parseInt(e.target.value))}
                  className="w-full border border-slate-300 rounded-lg p-2 bg-white"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">
                  Audit Justification (Mandatory)
                </label>
                <textarea
                  value={resupplyReason}
                  onChange={(e) => setResupplyReason(e.target.value)}
                  placeholder="State operational reason for parts order..."
                  rows={2}
                  className="w-full border border-slate-300 rounded-lg p-2 bg-white"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <Button variant="outline" size="sm" type="button" onClick={() => setShowResupplyModal(false)}>
                  Cancel
                </Button>
                <Button variant="primary" size="sm" type="submit" loading={resupplySaving}>
                  Dispatch Resupply Order
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
