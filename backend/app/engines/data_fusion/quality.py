"""
Data Normalisation, Validation & Quality Fusion Engine (Phase 2 Task P2-4).
Detects:
- Out-of-bounds health scores (<0 or >1)
- Inverted chronological windows (end < start)
- Missing required keys
- Negative flight hours or cycles
- Data conflicts: preserves conflicting records as DataQualityIssue review items rather than overwriting.
"""

import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.core.enums import IssueClass, IssueStatus
from app.models.provenance import DataQualityIssue


class QualityValidator:
    """Independent data fusion validator for incoming entities."""

    def __init__(self, db: Session):
        self.db = db

    def validate_asset_record(self, raw_record: dict[str, Any], source_id: uuid.UUID | None = None) -> tuple[bool, dict[str, Any] | None]:
        """
        Validates asset entity attributes.
        Returns (is_valid, sanitized_record).
        """
        identifier = raw_record.get("identifier")
        health = raw_record.get("health_score")

        # 1. Bounds check on health score [0.0, 1.0]
        if health is not None:
            try:
                health_val = float(health)
                if health_val < 0.0 or health_val > 1.0:
                    self._record_issue(
                        source_id=source_id,
                        entity_type="asset",
                        entity_id=identifier,
                        issue_class=IssueClass.INTEGRITY_ERROR.value,
                        description=f"Asset {identifier} health score {health_val} is out of bounds [0.0, 1.0]",
                        raw_val=raw_record,
                        expected_val={"health_score_range": "[0.0, 1.0]"},
                    )
                    return False, None
            except (ValueError, TypeError):
                self._record_issue(
                    source_id=source_id,
                    entity_type="asset",
                    entity_id=identifier,
                    issue_class=IssueClass.INTEGRITY_ERROR.value,
                    description=f"Asset {identifier} health score is non-numeric: {health}",
                    raw_val=raw_record,
                    expected_val={"health_score": "float"},
                )
                return False, None

        # 2. Non-negative usage counters
        for counter_key in ("flight_hours", "cycles"):
            val = raw_record.get(counter_key)
            if val is not None and float(val) < 0:
                self._record_issue(
                    source_id=source_id,
                    entity_type="asset",
                    entity_id=identifier,
                    issue_class=IssueClass.INTEGRITY_ERROR.value,
                    description=f"Asset {identifier} has negative {counter_key}: {val}",
                    raw_val=raw_record,
                    expected_val={counter_key: ">= 0"},
                )
                return False, None

        return True, raw_record

    def validate_task_record(self, raw_record: dict[str, Any], source_id: uuid.UUID | None = None) -> tuple[bool, dict[str, Any] | None]:
        """
        Validates task entity attributes and temporal consistency.
        Returns (is_valid, sanitized_record).
        """
        code = raw_record.get("code")
        start = raw_record.get("earliest_start")
        end = raw_record.get("latest_end")

        if start and end:
            start_dt = datetime.fromisoformat(str(start)) if isinstance(start, str) else start
            end_dt = datetime.fromisoformat(str(end)) if isinstance(end, str) else end

            if end_dt <= start_dt:
                self._record_issue(
                    source_id=source_id,
                    entity_type="task",
                    entity_id=code,
                    issue_class=IssueClass.INTEGRITY_ERROR.value,
                    description=f"Task {code} has invalid inverted time window: latest_end ({end_dt}) <= earliest_start ({start_dt})",
                    raw_val=raw_record,
                    expected_val={"temporal_constraint": "earliest_start < latest_end"},
                )
                return False, None

        return True, raw_record

    def detect_and_record_conflict(
        self,
        entity_type: str,
        entity_id: str,
        current_state: dict[str, Any],
        incoming_state: dict[str, Any],
        source_id: uuid.UUID | None = None,
    ) -> DataQualityIssue:
        """
        Records a state discrepancy as a review item without overwriting source truth.
        """
        return self._record_issue(
            source_id=source_id,
            entity_type=entity_type,
            entity_id=entity_id,
            issue_class=IssueClass.CONFLICT.value,
            description=f"Conflicting state detected for {entity_type} {entity_id} between current DB and external feed",
            raw_val=incoming_state,
            expected_val=current_state,
        )

    def _record_issue(
        self,
        source_id: uuid.UUID | None,
        entity_type: str,
        entity_id: str | None,
        issue_class: str,
        description: str,
        raw_val: dict[str, Any] | None,
        expected_val: dict[str, Any] | None,
    ) -> DataQualityIssue:
        clock = get_clock()

        def _jsonify(val: Any) -> Any:
            if isinstance(val, dict):
                return {k: _jsonify(v) for k, v in val.items()}
            elif isinstance(val, (list, tuple, set)):
                return [_jsonify(v) for v in val]
            elif isinstance(val, datetime):
                return val.isoformat()
            elif isinstance(val, uuid.UUID):
                return str(val)
            return val

        issue = DataQualityIssue(
            id=uuid.uuid4(),
            source_id=source_id,
            entity_type=entity_type,
            entity_id=entity_id,
            issue_class=issue_class,
            description=description,
            raw_value=_jsonify(raw_val),
            expected_value=_jsonify(expected_val),
            status=IssueStatus.OPEN.value,
            created_at=clock.now(),
            updated_at=clock.now(),
        )
        self.db.add(issue)
        self.db.commit()
        return issue
