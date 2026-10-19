from collections.abc import Callable
from fastapi import Depends, Header, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.clock import Clock, get_clock as _get_clock
from app.core.enums import UserRole
from app.core.exceptions import AppException, ForbiddenException
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.identity import User
from app.services.auth import get_user_by_username

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_clock() -> Clock:
    """Dependency returning the active Clock implementation."""
    return _get_clock()


def get_current_user(
    db: Session = Depends(get_db),
    token: str | None = Depends(oauth2_scheme),
    authorization: str | None = Header(default=None),
) -> User:
    """Validates JWT access token and returns authenticated User entity."""
    raw_token = token
    if not raw_token and authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split(" ")[1]

    if not raw_token:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Missing or invalid authentication token.",
            code="unauthorized",
        )

    payload = decode_access_token(raw_token)
    if not payload or "sub" not in payload:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="Expired or malformed authentication token.",
            code="invalid_token",
        )

    username: str = payload["sub"]
    user = get_user_by_username(db, username)
    if not user or not user.is_active:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Unauthorized",
            detail="User account inactive or not found.",
            code="user_inactive",
        )

    return user


def require_permission(allowed_roles: list[UserRole] | UserRole) -> Callable[[User], User]:
    """Dependency factory enforcing server-side role-based authorization."""
    if isinstance(allowed_roles, UserRole):
        roles_set = {allowed_roles.value}
    else:
        roles_set = {r.value for r in allowed_roles}

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        user_roles = {r.name for r in current_user.roles}
        # Admin has superuser access across all capabilities
        if UserRole.ADMIN.value in user_roles:
            return current_user

        if not user_roles.intersection(roles_set):
            raise ForbiddenException(
                detail=f"Operation requires one of the following roles: {list(roles_set)}. Your active roles: {list(user_roles)}."
            )
        return current_user

    return role_checker
