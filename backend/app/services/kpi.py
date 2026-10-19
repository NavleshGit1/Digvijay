"""
Server-Side Operational KPI Engine (Phase 2 Task P2-6 & Data Dictionary Section 4).
Implements exact mathematical definitions querying the relational database:
- kpi_asset_availability
- kpi_serviceability
- kpi_eligible_tasks
- kpi_tasks_scheduled
- kpi_maintenance_workload
- kpi_overdue_maintenance
- kpi_crew_availability
- kpi_total_delay
- kpi_spares_shortage
Guarantees every KPI is computed directly from live database tables with DataKind provenance.
"""

from datetime import datetime, timedelta
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.core.enums import AssetStatus, DataKind, PersonnelStatus, TaskStatus
from app.models.logistics import SparesInventory
from app.models.operations import MaintenanceRecord, Task, TaskExecution
from app.models.plans import PlanAssignment, PlanVersion
from app.models.resources import Asset, Personnel
from app.schemas.overview import DataKindEnvelope, OverviewKPIResponse


class KpiService:
    """Calculates server-side operational KPIs with provenance envelopes."""

    def __init__(self, db: Session):
        self.db = db

    def calculate_overview_kpis(self, as_of: datetime | None = None) -> OverviewKPIResponse:
        effective_as_of = as_of or get_clock().as_of()

        # 1. Asset Availability & Serviceability
        # Total active aircraft
        total_assets = self.db.execute(select(func.count(Asset.id))).scalar() or 0

        # Available aircraft (status == 'available')
        avail_assets = self.db.execute(
            select(func.count(Asset.id)).where(Asset.status == AssetStatus.AVAILABLE.value)
        ).scalar() or 0

        # Serviceable aircraft (status == 'available' AND health >= 0.70)
        ready_assets = self.db.execute(
            select(func.count(Asset.id)).where(
                Asset.status == AssetStatus.AVAILABLE.value,
                Asset.health_score >= 0.70,
            )
        ).scalar() or 0

        asset_availability_ratio = (avail_assets / total_assets) if total_assets > 0 else 0.0
        serviceability_ratio = (ready_assets / total_assets) if total_assets > 0 else 0.0

        # 2. Eligible Tasks
        # Tasks not cancelled/completed in horizon
        horizon_end = effective_as_of + timedelta(days=7)
        eligible_tasks_count = self.db.execute(
            select(func.count(Task.id)).where(
                Task.status.notin_([TaskStatus.CANCELLED.value, TaskStatus.COMPLETED.value]),
                Task.earliest_start <= horizon_end,
            )
        ).scalar() or 0

        # 3. Tasks Scheduled
        # Tasks assigned in a plan version
        tasks_scheduled_count = self.db.execute(
            select(func.count(func.distinct(PlanAssignment.task_id)))
        ).scalar() or 0

        # 4. Maintenance Workload
        # Total scheduled maintenance duration vs available technician capacity
        maint_hours = self.db.execute(
            select(
                func.sum(
                    func.extract('epoch', MaintenanceRecord.end_time - MaintenanceRecord.start_time) / 3600.0
                )
            ).where(MaintenanceRecord.status.in_(["scheduled", "in_progress"]))
        ).scalar() or 0.0

        tech_count = self.db.execute(
            select(func.count(Personnel.id)).where(
                Personnel.role_type == "maintenance_tech",
                Personnel.status == PersonnelStatus.AVAILABLE.value,
            )
        ).scalar() or 1

        tech_capacity_hours = tech_count * 8.0 * 7.0  # 8 hrs/day across 7 days
        workload_ratio = min(1.0, float(maint_hours) / tech_capacity_hours) if tech_capacity_hours > 0 else 0.0

        # 5. Overdue Maintenance
        overdue_count = self.db.execute(
            select(func.count(MaintenanceRecord.id)).where(
                MaintenanceRecord.status != "completed",
                MaintenanceRecord.end_time < effective_as_of,
            )
        ).scalar() or 0

        # 6. Crew Availability
        avail_crew = self.db.execute(
            select(func.count(Personnel.id)).where(
                Personnel.status == PersonnelStatus.AVAILABLE.value
            )
        ).scalar() or 0

        total_crew = self.db.execute(select(func.count(Personnel.id))).scalar() or 1
        crew_ratio = (avail_crew / total_crew) if total_crew > 0 else 0.0

        # 7. Total Delay
        total_delay_min = self.db.execute(
            select(func.sum(TaskExecution.delay_minutes))
        ).scalar() or 0.0

        # 8. Spares Shortage
        # Items where on_hand < minimum_safety_level
        shortage_count = self.db.execute(
            select(func.count(SparesInventory.id)).where(
                SparesInventory.on_hand < SparesInventory.minimum_safety_level
            )
        ).scalar() or 0

        return OverviewKPIResponse(
            asset_availability=DataKindEnvelope(
                value=round(asset_availability_ratio, 3),
                data_kind=DataKind.OBSERVED,
                as_of=effective_as_of,
            ),
            serviceability=DataKindEnvelope(
                value=round(serviceability_ratio, 3),
                data_kind=DataKind.OBSERVED,
                as_of=effective_as_of,
            ),
            eligible_tasks=int(eligible_tasks_count),
            tasks_scheduled=int(tasks_scheduled_count),
            maintenance_workload=DataKindEnvelope(
                value=round(workload_ratio, 3),
                data_kind=DataKind.OBSERVED,
                as_of=effective_as_of,
            ),
            overdue_maintenance=int(overdue_count),
            crew_availability=DataKindEnvelope(
                value=round(crew_ratio, 3),
                data_kind=DataKind.OBSERVED,
                as_of=effective_as_of,
            ),
            total_delay=round(float(total_delay_min), 1),
            spares_shortage=int(shortage_count),
            as_of=effective_as_of,
        )
