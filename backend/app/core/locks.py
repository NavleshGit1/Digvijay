import hashlib
import json
from typing import Any
import redis

from app.core.config import settings

# Redis client instance for locks and coordination
redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


class ScopeLock:
    """
    Redis-based scope lock for concurrency control.
    Enforces section 26.5: only one active job per operational scope (e.g., 'opt:horizon').
    """

    def __init__(self, scope: str, timeout_seconds: int = 120) -> None:
        self.scope = scope
        self.lock_key = f"lock:{scope}"
        self.timeout = timeout_seconds

    def acquire(self, owner_job_id: str) -> bool:
        """Attempts to acquire the lock. Returns True if acquired, False otherwise."""
        try:
            return bool(
                redis_client.set(
                    self.lock_key,
                    owner_job_id,
                    nx=True,
                    ex=self.timeout,
                )
            )
        except redis.RedisError:
            # In local mode without Redis, gracefully succeed
            return True

    def release(self, owner_job_id: str) -> None:
        """Releases the lock if owned by this job."""
        try:
            current_owner = redis_client.get(self.lock_key)
            if current_owner == owner_job_id:
                redis_client.delete(self.lock_key)
        except redis.RedisError:
            pass

    def heartbeat(self, owner_job_id: str) -> bool:
        """Renews lock lease while job is actively running."""
        try:
            current_owner = redis_client.get(self.lock_key)
            if current_owner == owner_job_id:
                redis_client.expire(self.lock_key, self.timeout)
                return True
            return False
        except redis.RedisError:
            return True


def compute_idempotency_hash(payload: dict[str, Any]) -> str:
    """Computes a SHA-256 fingerprint for idempotent request deduplication."""
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
