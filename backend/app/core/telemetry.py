"""OpenTelemetry Tracing and Observability Stub.

Provides a uniform interface for distributed tracing, span creation,
and APM telemetry across FastAPI and Celery worker operations.
"""
from collections.abc import Generator
from contextlib import contextmanager
import structlog

logger = structlog.get_logger()


class SpanStub:
    """Lightweight span representation when full OpenTelemetry exporter is inactive."""

    def __init__(self, name: str, attributes: dict[str, str | int | float | bool] | None = None) -> None:
        self.name = name
        self.attributes = attributes or {}

    def set_attribute(self, key: str, value: str | int | float | bool) -> None:
        self.attributes[key] = value

    def set_status(self, status: str, description: str | None = None) -> None:
        self.attributes["status"] = status
        if description:
            self.attributes["status_description"] = description


class TracerStub:
    """Tracer stub conforming to the OpenTelemetry trace protocol."""

    def __init__(self, service_name: str = "airops-nexus-api") -> None:
        self.service_name = service_name

    @contextmanager
    def start_as_current_span(
        self,
        name: str,
        attributes: dict[str, str | int | float | bool] | None = None,
    ) -> Generator[SpanStub, None, None]:
        span = SpanStub(name=name, attributes=attributes)
        try:
            yield span
        except Exception as exc:
            span.set_status("ERROR", str(exc))
            raise


tracer = TracerStub("airops-nexus")


def get_tracer(name: str = "airops-nexus") -> TracerStub:
    """Returns the platform tracer stub."""
    return TracerStub(service_name=name)
