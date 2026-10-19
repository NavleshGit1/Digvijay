from enum import Enum


class UserRole(str, Enum):
    PLANNER = "planner"
    REVIEWER = "reviewer"
    ANALYST = "analyst"
    ADMIN = "admin"


class AssetStatus(str, Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    GROUNDED = "grounded"
    TRANSIT = "transit"


class TaskStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class PlanKind(str, Enum):
    BASELINE = "baseline"
    OPTIMISED = "optimised"
    REPLAN = "replan"
    FALLBACK = "fallback"
    ROLLBACK = "rollback"
    ALTERNATIVE = "alternative"


class PlanStatus(str, Enum):
    PROPOSED = "proposed"
    STALE = "stale"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    INVALID = "invalid"
    WITHDRAWN = "withdrawn"


class PlanSource(str, Enum):
    CPSAT = "cpsat"
    HEURISTIC_FALLBACK = "heuristic_fallback"
    ROLLBACK = "rollback"
    MANUAL = "manual"


class SolverStatus(str, Enum):
    OPTIMAL = "optimal"
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"
    ERROR = "error"


class ValidationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    UNVALIDATED = "unvalidated"


class DataKind(str, Enum):
    OBSERVED = "observed"
    PREDICTED = "predicted"
    SIMULATED = "simulated"
    GENERATED = "generated"
    SYNTHETIC = "synthetic"
    DEMO = "demo"


class SeverityLevel(str, Enum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class JobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ClockMode(str, Enum):
    SYSTEM = "system"
    FIXED = "fixed"
    SIMULATED = "simulated"


class PersonnelStatus(str, Enum):
    AVAILABLE = "available"
    ON_DUTY = "on_duty"
    REST_PERIOD = "rest_period"
    LEAVE = "leave"
    TRAINING = "training"


class TaskPriority(str, Enum):
    LOW = "low"
    ROUTINE = "routine"
    HIGH = "high"
    CRITICAL = "critical"
    FLASH = "flash"


class EventType(str, Enum):
    ASSET_UNAVAILABILITY = "asset_unavailability"
    MAINTENANCE_DELAY = "maintenance_delay"
    CAPACITY_REDUCTION = "capacity_reduction"
    STALE_DATA = "stale_data"
    ENVIRONMENTAL_RESTRICTION = "environmental_restriction"
    TASK_PROGRESS = "task_progress"
    RESUPPLY_DELAY = "resupply_delay"


class AssetType(str, Enum):
    FIGHTER_MULTIROLE = "FIGHTER_MULTIROLE"
    TRANSPORT_CARGO = "TRANSPORT_CARGO"
    RECON_SURVEILLANCE = "RECON_SURVEILLANCE"
    REFUELER_TANKER = "REFUELER_TANKER"


class IssueClass(str, Enum):
    INTEGRITY_ERROR = "integrity_error"
    CONFLICT = "conflict"
    STALE = "stale"


class IssueStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    IGNORED = "ignored"

