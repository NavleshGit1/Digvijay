import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import get_clock
from app.core.enums import EventType, IssueClass, IssueStatus, SeverityLevel
from app.models.base import BaseModel


class DataSource(BaseModel):
    """Registered ingestion sources, telemetry connectors, and adapter definitions (Architecture Section 3.2)."""

    __tablename__ = "data_sources"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    adapter_type: Mapped[str] = mapped_column(String(50), nullable=False)  # csv, json, telemetry_mock, erp_spares
    expected_interval_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    runs: Mapped[list["IngestionRun"]] = relationship("IngestionRun", back_populates="source")
    freshness: Mapped["DataSourceFreshness | None"] = relationship("DataSourceFreshness", back_populates="source", uselist=False)


class IngestionRun(BaseModel):
    """Batch ingestion job tracking with content hashing for idempotency."""

    __tablename__ = "ingestion_runs"

    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False)
    records_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: get_clock().now(), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    source: Mapped["DataSource"] = relationship("DataSource", back_populates="runs")


class SourceRecord(BaseModel):
    """Immutable raw landing records preserved for audit and lineage."""

    __tablename__ = "source_records"

    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: get_clock().now(), nullable=False)


class DatasetVersion(BaseModel):
    """Fingerprinted deterministic synthetic dataset snapshots (Task P2-2)."""

    __tablename__ = "dataset_versions"

    version_tag: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    generator_version: Mapped[str] = mapped_column(String(50), default="1.1", nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_counts: Mapped[dict] = mapped_column(JSONB, nullable=False)


class DataSourceFreshness(BaseModel):
    """Heartbeat and freshness tracking per data source for SLA compliance."""

    __tablename__ = "data_source_freshness"

    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("data_sources.id"), unique=True, nullable=False)
    last_successful_sync: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: get_clock().now(), nullable=False)
    staleness_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    source: Mapped["DataSource"] = relationship("DataSource", back_populates="freshness")


class DataQualityIssue(BaseModel):
    """Data quality and reconciliation conflicts preserved for human review (Task P2-4)."""

    __tablename__ = "data_quality_issues"

    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("data_sources.id"), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issue_class: Mapped[str] = mapped_column(String(50), default=IssueClass.INTEGRITY_ERROR.value, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    raw_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    expected_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default=IssueStatus.OPEN.value, nullable=False)


class Event(BaseModel):
    """Operational events and disruption injects (Architecture Section 3.7)."""

    __tablename__ = "events"

    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), default=EventType.ASSET_UNAVAILABILITY.value, index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(100), default="synthetic_generator", nullable=False)
    affected_entity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    affected_entity_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), default=SeverityLevel.MEDIUM.value, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: get_clock().now(), nullable=False)
