from typing import Any
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel


class ProblemDetails(BaseModel):
    """RFC 7807 compliant problem details model."""

    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None
    code: str | None = None
    invalid_params: list[dict[str, Any]] | None = None


class AppException(HTTPException):
    """Base application exception mapping to RFC 7807 problem details."""

    def __init__(
        self,
        status_code: int,
        title: str,
        detail: str,
        code: str | None = None,
        type_uri: str | None = None,
        invalid_params: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail)
        self.title = title
        self.code = code
        self.type_uri = type_uri or f"https://airops.local/errors/{code or 'internal-error'}"
        self.invalid_params = invalid_params


class ConflictVersionException(AppException):
    def __init__(self, detail: str = "Plan proposal is stale or version conflict detected.") -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            title="Conflict Version",
            detail=detail,
            code="conflict_version",
        )


class RevalidationFailedException(AppException):
    def __init__(self, detail: str, violations: list[dict[str, Any]]) -> None:
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            title="Approval Revalidation Failed",
            detail=detail,
            code="revalidation_failed",
            invalid_params=violations,
        )


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Insufficient role permissions for this operation.") -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            title="Forbidden",
            detail=detail,
            code="forbidden",
        )


class EngineUnavailableException(AppException):
    def __init__(self, engine_name: str) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            title="Engine Unavailable",
            detail=f"The {engine_name} engine is currently unavailable or disabled by circuit breaker.",
            code="engine_unavailable",
        )


async def problem_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """FastAPI handler formatting AppExceptions into RFC 7807 Problem Details."""
    problem = ProblemDetails(
        type=exc.type_uri,
        title=exc.title,
        status=exc.status_code,
        detail=exc.detail,
        instance=request.url.path,
        code=exc.code,
        invalid_params=exc.invalid_params,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(exclude_none=True),
        headers={"Content-Type": "application/problem+json"},
    )
