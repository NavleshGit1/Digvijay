"""
Data Source Adapters & Ingestion Protocols (Phase 2 Task P2-3 & Architecture Section 3.2).
Provides normalized extraction from CSV, JSON, and simulated telemetry feeds.
"""

import csv
import io
import json
from typing import Any, Protocol


class DataSourceAdapter(Protocol):
    """Protocol contract for all ingest adapters."""

    @property
    def source_name(self) -> str:
        ...

    def fetch_records(self) -> list[dict[str, Any]]:
        ...

    def validate_connection(self) -> bool:
        ...


class CsvDataSourceAdapter:
    """Ingests and normalizes tabular records from CSV payloads or files."""

    def __init__(self, source_name: str, csv_content: str):
        self.name = source_name
        self.csv_content = csv_content

    @property
    def source_name(self) -> str:
        return self.name

    def fetch_records(self) -> list[dict[str, Any]]:
        reader = csv.DictReader(io.StringIO(self.csv_content.strip()))
        records = []
        for row in reader:
            # Strip whitespace and normalize keys
            clean_row = {k.strip(): v.strip() for k, v in row.items() if k}
            records.append(clean_row)
        return records

    def validate_connection(self) -> bool:
        return len(self.csv_content.strip()) > 0


class JsonDataSourceAdapter:
    """Ingests and normalizes JSON payloads or API responses."""

    def __init__(self, source_name: str, json_content: str | list[dict[str, Any]] | dict[str, Any]):
        self.name = source_name
        self.content = json_content

    @property
    def source_name(self) -> str:
        return self.name

    def fetch_records(self) -> list[dict[str, Any]]:
        if isinstance(self.content, str):
            data = json.loads(self.content)
        else:
            data = self.content

        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Check for standard container keys (e.g. "items", "records", "data")
            for k in ("items", "records", "data"):
                if k in data and isinstance(data[k], list):
                    return data[k]
            return [data]
        return []

    def validate_connection(self) -> bool:
        return self.content is not None
