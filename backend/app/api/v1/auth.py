from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.security import create_access_token
from app.models.identity import User
from app.schemas.auth import LoginRequest, Token, UserResponse
from app.services.auth import authenticate_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Token:
    """Authenticates demo users using either OAuth2 form data or JSON body."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            payload = await request.json()
            username = payload.get("username", "")
            password = payload.get("password", "")
        except Exception:
            username, password = "", ""
    else:
        try:
            form = await request.form()
            username = form.get("username", "")
            password = form.get("password", "")
        except Exception:
            username, password = "", ""

    user = authenticate_user(db, username, password)
    if not user:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            title="Authentication Failed",
            detail="Invalid username or password.",
            code="invalid_credentials",
        )

    roles = [r.name for r in user.roles]
    access_token = create_access_token(subject=user.username, roles=roles)

    # Set rotating refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=f"refresh-{user.username}",
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        roles=roles,
    )


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    """Clears refresh token cookie and logs out user."""
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Returns current authenticated user details."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        roles=[r.name for r in current_user.roles],
    )
