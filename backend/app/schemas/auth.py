import uuid
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    roles: list[str]


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    is_active: bool
    roles: list[str]

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username: str
    password: str
