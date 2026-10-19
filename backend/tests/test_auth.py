import pytest
from app.core.security import hash_password, verify_password, create_access_token, decode_access_token


def test_password_hashing():
    password = "SuperSecretMissionPass2026!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_roundtrip():
    username = "planner"
    roles = ["planner"]
    token = create_access_token(subject=username, roles=roles)

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == username
    assert payload["roles"] == roles
    assert payload["iss"] == "airops-nexus"


def test_jwt_invalid_token():
    payload = decode_access_token("not-a-valid-token-string")
    assert payload is None
