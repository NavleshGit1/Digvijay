"""
Deterministic Synthetic Data Generator (Phase 2 Task P2-2 & generator-spec.md).
Uses reproducible random streams to generate:
- 3 Airbases / Operating Zones
- 40 Operational Aircraft (Su-30MKI, Rafale, Tejas LCA, C-130J, Il-78)
- 120 Flight & Ground Crew with 8 Qualification Types
- 25 Critical Spare Parts & Base-Level Inventory
- 6 Maintenance Trigger Rules & Schedules
- 300 Operational Tasks with Precedence DAG across 7-day Horizon
- Historical Realized Executions ($y_downtime, $y_delay, $y_disruption)
- Disruption Events & Freshness Heartbeats
Guarantees byte-for-byte dataset_hash determinism for identical (seed, as_of).
"""

import hashlib
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.core.enums import (
    AssetStatus,
    AssetType,
    EventType,
    PersonnelStatus,
    SeverityLevel,
    TaskPriority,
    TaskStatus,
)
from app.models.logistics import (
    MaintenancePartRequirement,
    MaintenanceRule,
    Part,
    ResupplyOrder,
    SparesInventory,
)
from app.models.operations import (
    MaintenanceRecord,
    Task,
    TaskDependency,
    TaskExecution,
    TaskRequirement,
)
from app.models.provenance import (
    DataSource,
    DataSourceFreshness,
    DatasetVersion,
    Event,
)
from app.models.plans import (
    ApprovalRecord,
    Plan,
    PlanAssignment,
    PlanValidation,
    PlanVersion,
)
from app.models.resources import (
    Asset,
    Personnel,
    PersonnelQualification,
    Qualification,
    Zone,
)
from app.services.audit import write_audit_entry

GENERATOR_VERSION = "1.1"


class DeterministicGenerator:
    """
    State-of-the-art deterministic synthetic data generator.
    Initializes independent pseudo-random streams per entity to prevent cross-stream leakage.
    Uses RFC 4122 UUID v5 for stable, collision-free, deterministic primary keys.
    """

    def __init__(self, seed: int = 42, as_of: datetime | None = None):
        self.master_seed = seed
        self.as_of = as_of or get_clock().as_of()

        # Seeded child RNG streams
        self.rng_zones = random.Random(seed ^ 0x1A2B3C4D)
        self.rng_assets = random.Random(seed ^ 0x5E6F7A8B)
        self.rng_personnel = random.Random(seed ^ 0x9C0D1E2F)
        self.rng_parts = random.Random(seed ^ 0x3A4B5C6D)
        self.rng_tasks = random.Random(seed ^ 0x7E8F9A0B)
        self.rng_events = random.Random(seed ^ 0x2C3D4E5F)

    def generate_all(self) -> dict[str, list[dict[str, Any]]]:
        """Generates the full relational synthetic dataset."""
        zones = self._generate_zones()
        qualifications = self._generate_qualifications()
        assets = self._generate_assets(zones)
        personnel, personnel_quals = self._generate_personnel(zones, qualifications)
        parts, spares_inv = self._generate_spares(zones)
        rules, rule_parts = self._generate_maintenance_rules(parts)
        tasks, requirements, dependencies = self._generate_tasks(zones, qualifications)
        executions = self._generate_task_executions(tasks)
        maint_records = self._generate_maintenance_records(assets)
        resupply_orders = self._generate_resupply_orders(parts, zones)
        data_sources = self._generate_data_sources()
        events = self._generate_events(assets, zones)

        return {
            "zones": zones,
            "qualifications": qualifications,
            "assets": assets,
            "personnel": personnel,
            "personnel_qualifications": personnel_quals,
            "parts_catalog": parts,
            "spares_inventory": spares_inv,
            "maintenance_rules": rules,
            "maintenance_part_requirements": rule_parts,
            "tasks": tasks,
            "task_requirements": requirements,
            "task_dependencies": dependencies,
            "task_executions": executions,
            "maintenance_records": maint_records,
            "resupply_orders": resupply_orders,
            "data_sources": data_sources,
            "events": events,
        }

    def compute_dataset_hash(self, dataset: dict[str, list[dict[str, Any]]]) -> str:
        """Computes deterministic SHA-256 hash over canonically serialized entities."""
        hasher = hashlib.sha256()
        hasher.update(f"{GENERATOR_VERSION}:{self.master_seed}:{self.as_of.isoformat()}:".encode("utf-8"))

        for table_name in sorted(dataset.keys()):
            rows = dataset[table_name]
            # Canonical sort by id or code
            sorted_rows = sorted(rows, key=lambda r: str(r.get("id") or r.get("code") or r.get("part_number") or ""))
            for row in sorted_rows:
                # Stringify UUIDs and datetimes
                clean_row = {
                    k: (v.isoformat() if isinstance(v, datetime) else str(v) if isinstance(v, uuid.UUID) else v)
                    for k, v in sorted(row.items())
                }
                hasher.update(json.dumps(clean_row, sort_keys=True).encode("utf-8"))

        return hasher.hexdigest()

    # --- Entity Generators ---

    def _generate_zones(self) -> list[dict[str, Any]]:
        zone_specs = [
            ("Airbase Alpha - Northern Sector", "BASE_ALPHA", 20, [76.81, 30.73]),
            ("Airbase Bravo - Western Sector", "BASE_BRAVO", 15, [72.58, 23.02]),
            ("Airbase Charlie - Central Sector", "BASE_CHARLIE", 15, [78.47, 17.38]),
        ]
        return [
            {
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.zone.{code}"),
                "name": name,
                "code": code,
                "capacity_limit": cap,
                "coordinates_geojson": {"type": "Point", "coordinates": coords},
            }
            for name, code, cap, coords in zone_specs
        ]

    def _generate_qualifications(self) -> list[dict[str, Any]]:
        qual_defs = [
            ("QUAL_NIGHT_OPS", "Night Sortie & FLIR Operations", 365),
            ("QUAL_INSTRUMENT", "Adverse Weather Instrument Rating", 365),
            ("QUAL_AVIONICS_LV3", "AESA Radar & EW Diagnostics Specialist", 730),
            ("QUAL_ENGINE_OVERHAUL", "Turbofan Hot-Section Engine Overhaul", 730),
            ("QUAL_WEAPONS_TECH", "Precision Ordnance & Pylon Armament Tech", 365),
            ("QUAL_AIR_REFUEL", "Air-to-Air Refueling Boom & Probe Qualified", 365),
            ("QUAL_EW_SUITE", "Electronic Warfare Countermeasures Specialist", 730),
            ("QUAL_FAST_TURNAROUND", "Combat Quick Turnaround Inspection Certified", 365),
        ]
        return [
            {
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.qual.{code}"),
                "code": code,
                "name": name,
                "validity_days": val_days,
            }
            for code, name, val_days in qual_defs
        ]

    def _generate_assets(self, zones: list[dict[str, Any]]) -> list[dict[str, Any]]:
        fleet_configs = [
            ("Su-30MKI Flanker-H", AssetType.FIGHTER_MULTIROLE.value, "SB", 18),
            ("Rafale EH/DH", AssetType.FIGHTER_MULTIROLE.value, "RB", 12),
            ("Tejas LCA Mk1", AssetType.FIGHTER_MULTIROLE.value, "LA", 6),
            ("C-130J Super Hercules", AssetType.TRANSPORT_CARGO.value, "KC", 2),
            ("Il-78 Midas Tanker", AssetType.REFUELER_TANKER.value, "RK", 2),
        ]

        assets = []
        asset_idx = 1
        zone_ids = [z["id"] for z in zones]

        for model_name, asset_type, prefix, count in fleet_configs:
            for c in range(1, count + 1):
                identifier = f"{prefix}-{c:03d}"
                raw_health = self.rng_assets.betavariate(8, 2)
                health = round(0.55 + raw_health * 0.44, 3)

                if health < 0.65:
                    status = AssetStatus.MAINTENANCE.value
                elif self.rng_assets.random() < 0.10:
                    status = AssetStatus.IN_USE.value
                else:
                    status = AssetStatus.AVAILABLE.value

                flight_hours = round(self.rng_assets.lognormvariate(6.1, 0.3), 1)
                cycles = int(self.rng_assets.gauss(320, 45))
                home_zone = zone_ids[(asset_idx - 1) % len(zone_ids)]

                assets.append({
                    "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.asset.{identifier}"),
                    "identifier": identifier,
                    "asset_type": asset_type,
                    "model_name": model_name,
                    "status": status,
                    "health_score": health,
                    "zone_id": home_zone,
                    "current_location": f"Bay-{(asset_idx % 8) + 1}",
                    "flight_hours": flight_hours,
                    "cycles": max(50, cycles),
                })
                asset_idx += 1

        return assets

    def _generate_personnel(
        self, zones: list[dict[str, Any]], qualifications: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        personnel = []
        personnel_quals = []
        zone_ids = [z["id"] for z in zones]
        qual_ids = [q["id"] for q in qualifications]

        roles_plan = [("pilot", 42), ("maintenance_tech", 54), ("wso", 24)]
        p_idx = 1

        callsign_seeds = [
            "Viper", "Hawk", "Eagle", "Falcon", "Thunder", "Shadow", "Ghost", "Titan", "Phantom",
            "Blaze", "Cobra", "Comet", "Raptor", "Stryker", "Corsair", "Reaper", "Cyclone", "Tempest",
        ]

        for role_type, count in roles_plan:
            for _ in range(count):
                p_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.personnel.{p_idx}")
                name = f"Operator-{p_idx:03d} ({role_type[:3].upper()})"
                callsign = f"{self.rng_personnel.choice(callsign_seeds)}-{p_idx % 20 + 1}" if role_type != "maintenance_tech" else None

                status_roll = self.rng_personnel.random()
                if status_roll < 0.85:
                    status = PersonnelStatus.AVAILABLE.value
                elif status_roll < 0.95:
                    status = PersonnelStatus.REST_PERIOD.value
                else:
                    status = PersonnelStatus.ON_DUTY.value

                duty_hours = round(self.rng_personnel.uniform(10.0, 48.0), 1)
                home_zone = zone_ids[(p_idx - 1) % len(zone_ids)]

                personnel.append({
                    "id": p_id,
                    "name": name,
                    "callsign": callsign,
                    "role_type": role_type,
                    "status": status,
                    "duty_hours_accumulated": duty_hours,
                    "home_zone_id": home_zone,
                })

                # Assign 2-3 qualifications
                assigned_quals = self.rng_personnel.sample(qual_ids, k=min(3, len(qual_ids)))
                for q_id in assigned_quals:
                    pq_uid = uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.personnel_qual.{p_idx}.{q_id}")
                    personnel_quals.append({
                        "id": pq_uid,
                        "personnel_id": p_id,
                        "qualification_id": q_id,
                        "acquired_at": self.as_of - timedelta(days=180),
                        "expires_at": self.as_of + timedelta(days=self.rng_personnel.randint(90, 365)),
                    })

                p_idx += 1

        return personnel, personnel_quals

    def _generate_spares(self, zones: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        parts_data = [
            ("PRT-AV-001", "AESA Radar T/R Module Set", "avionics", 12500.0),
            ("PRT-AV-002", "Integrated Mission Computer LRU", "avionics", 24000.0),
            ("PRT-AV-003", "IFF Mode 5 Transponder Unit", "avionics", 8500.0),
            ("PRT-AV-004", "HUD Electro-Optical Assembly", "avionics", 14500.0),
            ("PRT-AV-005", "EW RWR Antenna Pod Assembly", "avionics", 9200.0),
            ("PRT-AV-006", "Tactical Data-link Terminal Unit", "avionics", 11000.0),
            ("PRT-PR-001", "High-Pressure Turbine Blade Set", "propulsion", 32000.0),
            ("PRT-PR-002", "Afterburner Fuel Injector Ring", "propulsion", 18500.0),
            ("PRT-PR-003", "Full Authority Digital Engine Control (FADEC)", "propulsion", 29000.0),
            ("PRT-PR-004", "Compressor Stator Vane Assembly", "propulsion", 15400.0),
            ("PRT-PR-005", "Turbofan Oil Lubrication Scavenge Pump", "propulsion", 6200.0),
            ("PRT-PR-006", "Engine Ignition Exciter & Spark Plug", "propulsion", 2800.0),
            ("PRT-HY-001", "Primary Flight Control Actuator", "hydraulics", 16800.0),
            ("PRT-HY-002", "Dual-Channel Hydraulic Reservoir Pump", "hydraulics", 9500.0),
            ("PRT-HY-003", "Nosewheel Steering Servo Cylinder", "hydraulics", 7200.0),
            ("PRT-HY-004", "Titanium High-Pressure Return Valve", "hydraulics", 3400.0),
            ("PRT-HY-005", "Brake Pressure Accumulator Unit", "hydraulics", 5100.0),
            ("PRT-HY-006", "Hydraulic Fluorocarbon O-Ring Kit", "hydraulics", 450.0),
            ("PRT-AF-001", "Carbon-Composite Main Landing Gear Brake Disk", "airframe", 8400.0),
            ("PRT-AF-002", "High-Load Main Gear Bearing Set", "airframe", 4100.0),
            ("PRT-AF-003", "Canard Actuation Torque Tube", "airframe", 11200.0),
            ("PRT-AF-004", "Wing Pylon Heavy Ejector Rack", "airframe", 13600.0),
            ("PRT-AF-005", "Pitot-Static Heated Probe Mast", "airframe", 2900.0),
            ("PRT-AF-006", "Pressurized Cockpit Canopy Inflatable Seal", "airframe", 3800.0),
            ("PRT-AF-007", "Airframe Structural Fastener Assortment", "airframe", 650.0),
        ]

        parts = []
        spares_inv = []

        for pnum, name, cat, cost in parts_data:
            p_uid = uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.part.{pnum}")
            parts.append({
                "id": p_uid,
                "part_number": pnum,
                "name": name,
                "category": cat,
                "unit_cost": cost,
            })

            for z_idx, z in enumerate(zones):
                min_safety = self.rng_parts.randint(3, 6)
                # Controlled shortage on 3 parts in zone 1 to validate shortage KPI
                if z_idx == 0 and pnum in ("PRT-AV-001", "PRT-PR-001", "PRT-HY-001"):
                    on_hand = self.rng_parts.randint(0, min_safety - 1)
                else:
                    on_hand = self.rng_parts.randint(min_safety, min_safety + 8)

                spares_inv.append({
                    "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.spares.{pnum}.{z['id']}"),
                    "part_id": p_uid,
                    "zone_id": z["id"],
                    "on_hand": on_hand,
                    "reserved": self.rng_parts.randint(0, 2),
                    "minimum_safety_level": min_safety,
                })

        return parts, spares_inv

    def _generate_maintenance_rules(
        self, parts: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        rules_def = [
            ("RULE-50H", "periodic_inspection", "flight_hours", 50.0, 0.05, 4.0),
            ("RULE-100H", "hourly_service", "flight_hours", 100.0, 0.05, 8.0),
            ("RULE-300H", "phase_inspection", "flight_hours", 300.0, 0.05, 24.0),
            ("RULE-ENG-HOT", "hot_section", "cycles", 200.0, 0.05, 16.0),
            ("RULE-HYD-SEAL", "seal_replacement", "calendar_days", 180.0, 0.10, 6.0),
            ("RULE-AV-CAL", "avionics_calibration", "calendar_days", 365.0, 0.05, 12.0),
        ]

        rules = []
        rule_parts = []
        part_ids = [p["id"] for p in parts]

        for i, (code, cat, trigger, thresh, tol, dur) in enumerate(rules_def):
            r_uid = uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.rule.{code}")
            rules.append({
                "id": r_uid,
                "code": code,
                "category": cat,
                "trigger_type": trigger,
                "threshold": thresh,
                "tolerance": tol,
                "estimated_duration_hours": dur,
            })

            part_id = part_ids[i % len(part_ids)]
            rule_parts.append({
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.rule_part.{code}.{part_id}"),
                "rule_id": r_uid,
                "part_id": part_id,
                "quantity_required": self.rng_parts.randint(1, 2),
            })

        return rules, rule_parts

    def _generate_tasks(
        self, zones: list[dict[str, Any]], qualifications: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        tasks = []
        requirements = []
        dependencies = []

        categories = [
            ("patrol_sortie", AssetType.FIGHTER_MULTIROLE.value, 90, 0.35),
            ("recon_surveillance", AssetType.RECON_SURVEILLANCE.value, 180, 0.20),
            ("air_defense_escort", AssetType.FIGHTER_MULTIROLE.value, 120, 0.20),
            ("tactical_airlift", AssetType.TRANSPORT_CARGO.value, 240, 0.15),
            ("refueling_anchor", AssetType.REFUELER_TANKER.value, 210, 0.10),
        ]

        zone_ids = [z["id"] for z in zones]
        horizon_hours = 7 * 24

        for t_idx in range(1, 301):
            code = f"TSK-2026-{t_idx:04d}"
            t_uid = uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.task.{code}")
            roll = self.rng_tasks.random()
            cum = 0.0
            cat_name, asset_req, nominal_dur, _ = categories[0]
            for c_name, a_req, dur, weight in categories:
                cum += weight
                if roll <= cum:
                    cat_name, asset_req, nominal_dur, _ = c_name, a_req, dur, weight
                    break

            start_offset_hours = self.rng_tasks.uniform(2.0, horizon_hours - 8.0)
            earliest_start = self.as_of + timedelta(hours=start_offset_hours)
            dur_minutes = int(self.rng_tasks.gauss(nominal_dur, 15))
            dur_minutes = max(30, min(360, dur_minutes))
            latest_end = earliest_start + timedelta(minutes=dur_minutes + self.rng_tasks.randint(60, 240))

            priority = self.rng_tasks.choice([TaskPriority.ROUTINE.value, TaskPriority.HIGH.value, TaskPriority.CRITICAL.value])
            zone_id = zone_ids[(t_idx - 1) % len(zone_ids)]

            tasks.append({
                "id": t_uid,
                "code": code,
                "category": cat_name,
                "zone_id": zone_id,
                "earliest_start": earliest_start,
                "latest_end": latest_end,
                "duration_minutes": dur_minutes,
                "priority": priority,
                "weight": 1.5 if priority == TaskPriority.CRITICAL.value else 1.0,
                "status": TaskStatus.PENDING.value,
            })

            requirements.append({
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.task_req.{code}"),
                "task_id": t_uid,
                "asset_type_required": asset_req,
                "crew_headcount": 2 if asset_req == AssetType.FIGHTER_MULTIROLE.value else 3,
                "required_qualification_code": "QUAL_NIGHT_OPS" if earliest_start.hour >= 20 or earliest_start.hour <= 5 else None,
            })

            # Acyclic DAG dependency
            if t_idx > 5 and self.rng_tasks.random() < 0.15:
                pred_idx = self.rng_tasks.randint(max(1, t_idx - 10), t_idx - 1)
                pred_code = f"TSK-2026-{pred_idx:04d}"
                pred_uid = uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.task.{pred_code}")
                dependencies.append({
                    "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.task_dep.{pred_idx}.{t_idx}"),
                    "predecessor_id": pred_uid,
                    "successor_id": t_uid,
                    "min_lag_minutes": self.rng_tasks.randint(15, 60),
                })

        return tasks, requirements, dependencies

    def _generate_task_executions(self, tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        executions = []
        for i, t in enumerate(tasks[:50]):
            t_id = t["id"]
            is_delayed = self.rng_tasks.random() < 0.30
            delay = round(self.rng_tasks.expovariate(1.0 / 25.0), 1) if is_delayed else 0.0

            act_start = t["earliest_start"] - timedelta(days=2)
            act_end = act_start + timedelta(minutes=t["duration_minutes"] + int(delay))

            executions.append({
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.task_exec.{i}"),
                "task_id": t_id,
                "plan_version_id": None,
                "assignment_id": None,
                "actual_start": act_start,
                "actual_end": act_end,
                "delay_minutes": delay,
                "is_locked": True,
                "is_disrupted": is_delayed,
            })
        return executions

    def _generate_maintenance_records(self, assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        records = []
        rec_idx = 1
        for a in assets:
            records.append({
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.maint_rec.{a['id']}.comp.{rec_idx}"),
                "asset_id": a["id"],
                "category": "100_hour",
                "start_time": self.as_of - timedelta(days=15),
                "end_time": self.as_of - timedelta(days=14),
                "predicted_completion": self.as_of - timedelta(days=14),
                "is_unplanned": False,
                "status": "completed",
            })
            rec_idx += 1

            if a["status"] == AssetStatus.MAINTENANCE.value:
                records.append({
                    "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.maint_rec.{a['id']}.act.{rec_idx}"),
                    "asset_id": a["id"],
                    "category": "phase_inspection",
                    "start_time": self.as_of - timedelta(hours=6),
                    "end_time": self.as_of + timedelta(hours=18),
                    "predicted_completion": self.as_of + timedelta(hours=16),
                    "is_unplanned": False,
                    "status": "in_progress",
                })
                rec_idx += 1

        return records

    def _generate_resupply_orders(
        self, parts: list[dict[str, Any]], zones: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        orders = []
        for i in range(1, 6):
            part = parts[(i - 1) % len(parts)]
            zone = zones[(i - 1) % len(zones)]
            orders.append({
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.resupply.{i}"),
                "part_id": part["id"],
                "zone_id": zone["id"],
                "quantity": 5 * i,
                "ordered_at": self.as_of - timedelta(days=2),
                "estimated_arrival": self.as_of + timedelta(hours=24 * i),
                "status": "in_transit",
            })
        return orders

    def _generate_data_sources(self) -> list[dict[str, Any]]:
        sources = [
            ("telemetry_flight_tracker", "json", 60),
            ("erp_spares_inventory", "csv", 3600),
            ("weather_radar_feed", "json", 300),
        ]
        return [
            {
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.datasource.{name}"),
                "name": name,
                "adapter_type": ad_type,
                "expected_interval_seconds": interval,
                "is_active": True,
            }
            for name, ad_type, interval in sources
        ]

    def _generate_events(
        self, assets: list[dict[str, Any]], zones: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        evt1_key = f"EVT-WEATHER-ALPHA-{self.as_of.strftime('%Y%m%d')}"
        evt2_key = f"EVT-LEAK-{assets[0]['identifier']}"
        return [
            {
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.event.{evt1_key}"),
                "idempotency_key": evt1_key,
                "event_type": EventType.ENVIRONMENTAL_RESTRICTION.value,
                "source": "synthetic_generator",
                "affected_entity_type": "zone",
                "affected_entity_id": str(zones[0]["id"]),
                "severity": SeverityLevel.HIGH.value,
                "payload_json": {"phenomenon": "crosswind_limit", "gust_knots": 38, "runway": "09/27"},
                "timestamp": self.as_of - timedelta(minutes=45),
            },
            {
                "id": uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.event.{evt2_key}"),
                "idempotency_key": evt2_key,
                "event_type": EventType.ASSET_UNAVAILABILITY.value,
                "source": "synthetic_generator",
                "affected_entity_type": "asset",
                "affected_entity_id": str(assets[0]["id"]),
                "severity": SeverityLevel.MEDIUM.value,
                "payload_json": {"issue": "hydraulic_seal_drip", "subsystem": "canard_actuator"},
                "timestamp": self.as_of - timedelta(hours=2),
            },
        ]


def seed_database(db: Session, seed: int = 42, as_of: datetime | None = None, reset: bool = True) -> tuple[str, dict[str, int]]:
    """
    Idempotently seeds the database using the deterministic generator.
    Guarantees that re-running with the same seed produces identical entity counts and rows.
    """
    clock = get_clock()
    effective_as_of = as_of or clock.as_of()
    gen = DeterministicGenerator(seed=seed, as_of=effective_as_of)
    dataset = gen.generate_all()
    dataset_hash = gen.compute_dataset_hash(dataset)

    if reset:
        db.execute(delete(ApprovalRecord))
        db.execute(delete(PlanAssignment))
        db.execute(delete(PlanValidation))
        db.execute(delete(PlanVersion))
        db.execute(delete(Plan))
        db.execute(delete(Event))
        db.execute(delete(ResupplyOrder))
        db.execute(delete(MaintenanceRecord))
        db.execute(delete(TaskExecution))
        db.execute(delete(TaskDependency))
        db.execute(delete(TaskRequirement))
        db.execute(delete(Task))
        db.execute(delete(MaintenancePartRequirement))
        db.execute(delete(MaintenanceRule))
        db.execute(delete(SparesInventory))
        db.execute(delete(Part))
        db.execute(delete(PersonnelQualification))
        db.execute(delete(Qualification))
        db.execute(delete(Personnel))
        db.execute(delete(Asset))
        db.execute(delete(Zone))
        db.execute(delete(DataSourceFreshness))
        db.execute(delete(DataSource))
        db.flush()

    # 1. Insert Zones
    for r in dataset["zones"]:
        db.add(Zone(**r))
    db.flush()

    # 2. Insert Qualifications
    for r in dataset["qualifications"]:
        db.add(Qualification(**r))
    db.flush()

    # 3. Insert Assets
    for r in dataset["assets"]:
        db.add(Asset(**r))
    db.flush()

    # 4. Insert Personnel & Qualifications
    for r in dataset["personnel"]:
        db.add(Personnel(**r))
    db.flush()

    for r in dataset["personnel_qualifications"]:
        db.add(PersonnelQualification(**r))
    db.flush()

    # 5. Insert Parts & Spares
    for r in dataset["parts_catalog"]:
        db.add(Part(**r))
    db.flush()

    for r in dataset["spares_inventory"]:
        db.add(SparesInventory(**r))
    db.flush()

    # 6. Insert Maintenance Rules & Part Requirements
    for r in dataset["maintenance_rules"]:
        db.add(MaintenanceRule(**r))
    db.flush()

    for r in dataset["maintenance_part_requirements"]:
        db.add(MaintenancePartRequirement(**r))
    db.flush()

    # 7. Insert Tasks, Requirements & Dependencies
    for r in dataset["tasks"]:
        db.add(Task(**r))
    db.flush()

    for r in dataset["task_requirements"]:
        db.add(TaskRequirement(**r))
    db.flush()

    for r in dataset["task_dependencies"]:
        db.add(TaskDependency(**r))
    db.flush()

    # 8. Insert Executions, Maintenance & Resupply
    for r in dataset["task_executions"]:
        db.add(TaskExecution(**r))
    for r in dataset["maintenance_records"]:
        db.add(MaintenanceRecord(**r))
    for r in dataset["resupply_orders"]:
        db.add(ResupplyOrder(**r))
    db.flush()

    # 9. Insert Data Sources & Freshness
    for r in dataset["data_sources"]:
        ds = DataSource(**r)
        db.add(ds)
        db.flush()
        fresh = DataSourceFreshness(
            id=uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.freshness.{ds.id}"),
            source_id=ds.id,
            last_successful_sync=as_of,
            staleness_seconds=0.0,
            is_stale=False,
        )
        db.add(fresh)
    db.flush()

    # 10. Insert Events
    for r in dataset["events"]:
        db.add(Event(**r))
    db.flush()

    # Entity counts summary
    counts = {k: len(v) for k, v in dataset.items()}

    # Record or update DatasetVersion
    ver_tag = f"synthetic-seed-{seed}-v{GENERATOR_VERSION}"
    existing_ver = db.execute(select(DatasetVersion).where(DatasetVersion.version_tag == ver_tag)).scalars().first()
    if existing_ver:
        existing_ver.content_hash = dataset_hash
        existing_ver.as_of = as_of
        existing_ver.entity_counts = counts
    else:
        db.add(
            DatasetVersion(
                id=uuid.uuid5(uuid.NAMESPACE_DNS, f"airops.ds_version.{ver_tag}"),
                version_tag=ver_tag,
                generator_version=GENERATOR_VERSION,
                seed=seed,
                as_of=as_of,
                content_hash=dataset_hash,
                entity_counts=counts,
            )
        )

    # Record Audit Event
    write_audit_entry(
        db=db,
        actor_id=None,
        role="admin",
        action="SEED_DATABASE",
        entity_type="dataset_versions",
        entity_id=ver_tag,
        reason=f"Seeded deterministic dataset with seed {seed} (hash: {dataset_hash[:16]}...)",
        after_state={"seed": seed, "hash": dataset_hash, "counts": counts},
    )

    db.commit()
    return dataset_hash, counts
