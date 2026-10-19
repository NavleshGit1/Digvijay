import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from app.db.session import SessionLocal
from app.engines.data_fusion.adapters import CsvDataSourceAdapter, JsonDataSourceAdapter
from app.engines.data_fusion.quality import QualityValidator
from app.models.provenance import DataQualityIssue


def test_csv_adapter_parsing():
    csv_payload = """
    part_number, name, category, unit_cost
    PRT-001, Turbine Blade, propulsion, 1200.50
    PRT-002, Hydraulic Pump, hydraulics, 3400.00
    """
    adapter = CsvDataSourceAdapter(source_name="test_csv", csv_content=csv_payload)
    assert adapter.validate_connection() is True
    records = adapter.fetch_records()
    assert len(records) == 2
    assert records[0]["part_number"] == "PRT-001"
    assert records[1]["category"] == "hydraulics"


def test_json_adapter_parsing():
    json_payload = [
        {"identifier": "SB-001", "status": "available", "health_score": 0.92},
        {"identifier": "RB-002", "status": "maintenance", "health_score": 0.61},
    ]
    adapter = JsonDataSourceAdapter(source_name="test_json", json_content=json_payload)
    assert adapter.validate_connection() is True
    records = adapter.fetch_records()
    assert len(records) == 2
    assert records[0]["identifier"] == "SB-001"


def test_quality_validator_bounds_check():
    db = SessionLocal()
    try:
        validator = QualityValidator(db)

        # 1. Valid record passes
        valid_rec = {"identifier": "SB-001", "health_score": 0.88, "flight_hours": 120.0, "cycles": 50}
        ok, res = validator.validate_asset_record(valid_rec)
        assert ok is True

        # 2. Out-of-bounds health score (1.45) is flagged as review issue
        bad_rec = {"identifier": "SB-999", "health_score": 1.45, "flight_hours": 10.0, "cycles": 2}
        ok, res = validator.validate_asset_record(bad_rec)
        assert ok is False

        # Verify DataQualityIssue was created
        stmt = select(DataQualityIssue).where(DataQualityIssue.entity_id == "SB-999")
        issue = db.execute(stmt).scalars().first()
        assert issue is not None
        assert issue.issue_class == "integrity_error"
        assert issue.raw_value["health_score"] == 1.45
    finally:
        db.close()


def test_quality_validator_temporal_sanity():
    db = SessionLocal()
    try:
        validator = QualityValidator(db)
        # Inverted task window: end_time < start_time
        start_time = datetime(2026, 10, 20, 14, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)  # 2 hours before start!

        inverted_task = {
            "code": "TSK-INVERTED-001",
            "earliest_start": start_time,
            "latest_end": end_time,
        }
        ok, res = validator.validate_task_record(inverted_task)
        assert ok is False

        stmt = select(DataQualityIssue).where(DataQualityIssue.entity_id == "TSK-INVERTED-001")
        issue = db.execute(stmt).scalars().first()
        assert issue is not None
        assert "inverted time window" in issue.description
    finally:
        db.close()


def test_quality_validator_conflict_preservation():
    db = SessionLocal()
    try:
        validator = QualityValidator(db)
        current_state = {"status": "available", "location": "Bay-1"}
        incoming_state = {"status": "grounded", "location": "Bay-4"}

        issue = validator.detect_and_record_conflict(
            entity_type="asset",
            entity_id="SB-005",
            current_state=current_state,
            incoming_state=incoming_state,
        )
        assert issue.id is not None
        assert issue.issue_class == "conflict"
        assert issue.expected_value == current_state
        assert issue.raw_value == incoming_state
    finally:
        db.close()
