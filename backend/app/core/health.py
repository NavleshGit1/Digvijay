from typing import Any
from pydantic import BaseModel


class EngineHealth(BaseModel):
    name: str
    is_healthy: bool
    is_enabled: bool
    status_message: str
    metrics: dict[str, Any] = {}


class HealthRegistry:
    """Registry managing engine health, circuit breakers, and feature flags."""

    def __init__(self) -> None:
        self._engines: dict[str, EngineHealth] = {
            "data_fusion": EngineHealth(name="data_fusion", is_healthy=True, is_enabled=True, status_message="Nominal"),
            "optimisation": EngineHealth(name="optimisation", is_healthy=True, is_enabled=True, status_message="Nominal"),
            "replanning": EngineHealth(name="replanning", is_healthy=True, is_enabled=True, status_message="Nominal"),
            "prediction": EngineHealth(name="prediction", is_healthy=True, is_enabled=True, status_message="Nominal"),
            "digital_twin": EngineHealth(name="digital_twin", is_healthy=True, is_enabled=True, status_message="Nominal"),
            "assistant": EngineHealth(name="assistant", is_healthy=True, is_enabled=True, status_message="Nominal"),
            "autoencoder": EngineHealth(name="autoencoder", is_healthy=True, is_enabled=False, status_message="Disabled (Optional)"),
            "demand_forecast": EngineHealth(name="demand_forecast", is_healthy=True, is_enabled=False, status_message="Disabled (Optional)"),
        }

    def get_status(self, engine_name: str) -> EngineHealth | None:
        return self._engines.get(engine_name)

    def set_status(self, engine_name: str, is_healthy: bool, message: str) -> None:
        if engine_name in self._engines:
            self._engines[engine_name].is_healthy = is_healthy
            self._engines[engine_name].status_message = message

    def set_enabled(self, engine_name: str, enabled: bool) -> None:
        if engine_name in self._engines:
            self._engines[engine_name].is_enabled = enabled

    def all_statuses(self) -> dict[str, EngineHealth]:
        return self._engines


health_registry = HealthRegistry()
