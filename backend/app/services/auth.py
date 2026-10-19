import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import UserRole
from app.core.security import hash_password, verify_password
from app.models.identity import Role, User


def get_user_by_username(db: Session, username: str) -> User | None:
    stmt = select(User).where(User.username == username)
    return db.execute(stmt).scalars().first()


def authenticate_user(db: Session, username_or_email: str, password: str) -> User | None:
    stmt = select(User).where((User.username == username_or_email) | (User.email == username_or_email))
    user = db.execute(stmt).scalars().first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def seed_demo_users(db: Session) -> None:
    """Seeds the 4 standard demonstration accounts with environment credentials."""
    # Ensure all 4 roles exist in database
    for role_enum in UserRole:
        role_record = db.execute(select(Role).where(Role.name == role_enum.value)).scalars().first()
        if not role_record:
            role_record = Role(
                id=uuid.uuid4(),
                name=role_enum.value,
                description=f"Standard operational {role_enum.value} role",
            )
            db.add(role_record)
    db.flush()

    # Role lookups
    roles_map = {r.name: r for r in db.execute(select(Role)).scalars().all()}

    demo_accounts = [
        (settings.DEMO_PLANNER_USER, "planner", settings.DEMO_PLANNER_PASSWORD, UserRole.PLANNER),
        (settings.DEMO_REVIEWER_USER, "reviewer", settings.DEMO_REVIEWER_PASSWORD, UserRole.REVIEWER),
        (settings.DEMO_ANALYST_USER, "analyst", settings.DEMO_ANALYST_PASSWORD, UserRole.ANALYST),
        (settings.DEMO_ADMIN_USER, "admin", settings.DEMO_ADMIN_PASSWORD, UserRole.ADMIN),
    ]

    for email, username, pwd, role in demo_accounts:
        existing_user = get_user_by_username(db, username)
        if not existing_user:
            user = User(
                id=uuid.uuid4(),
                username=username,
                email=email,
                hashed_password=hash_password(pwd),
                is_active=True,
                roles=[roles_map[role.value]],
            )
            db.add(user)
    db.commit()
