from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config
from app.db.user import User


def test_signup_login_and_current_user(client, db_engine, signup_payload):
    response = client.post("/api/v1/auth/signup", json=signup_payload)
    assert response.status_code == 201
    data = response.json()
    with Session(db_engine) as db:
        stored = db.scalar(select(User))
        assert stored.password_hash != signup_payload["password"]
        assert stored.password_hash.startswith("$2b$")
    headers = {"Authorization": f"Bearer {data['token']}"}
    profile = client.get("/api/v1/users/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["id"] == data["user_id"]
    assert profile.json()["preferred_buffer_days"] == config.PREFERRED_BUFFER_DAYS
    assert "password_hash" not in profile.text
    login = client.post("/api/v1/auth/login", json={k: v for k, v in signup_payload.items() if k != "name"})
    assert login.status_code == 200
    assert login.json()["user"]["id"] == data["user_id"]


def test_case_insensitive_duplicate_email(client, signup_payload):
    assert client.post("/api/v1/auth/signup", json=signup_payload).status_code == 201
    signup_payload["email"] = signup_payload["email"].upper()
    response = client.post("/api/v1/auth/signup", json=signup_payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_exists"


@pytest.mark.parametrize(
    "change",
    [
        {"email": "invalid"},
        {"password": "short"},
        {"name": "  "},
        {"password": "🧭" * 20},
        {"user_id": str(uuid4())},
    ],
)
def test_signup_validation_does_not_echo_password(client, signup_payload, change):
    signup_payload.update(change)
    response = client.post("/api/v1/auth/signup", json=signup_payload)
    assert response.status_code == 422
    assert signup_payload["password"] not in response.text
    assert "input" not in response.json()["error"]["details"]


def test_wrong_and_unknown_login_use_same_error(client, signup_payload):
    client.post("/api/v1/auth/signup", json=signup_payload)
    errors = []
    for email in [signup_payload["email"], "unknown@example.com"]:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": "wrong password"})
        assert response.status_code == 401
        errors.append(response.json())
    assert errors[0] == errors[1]


def test_missing_and_forged_tokens(client):
    assert client.get("/api/v1/users/me").status_code == 401
    assert client.get("/api/v1/users/me", headers={"Authorization": "Bearer forged"}).status_code == 401


def test_expired_token(client, signup_payload):
    signed = client.post("/api/v1/auth/signup", json=signup_payload).json()["token"]
    secret = config.get_settings().jwt_secret.get_secret_value()
    claims = jwt.decode(signed, secret, algorithms=[config.JWT_ALGORITHM], audience=config.JWT_AUDIENCE)
    claims["exp"] = datetime.now(UTC) - timedelta(seconds=1)
    expired = jwt.encode(claims, secret, algorithm=config.JWT_ALGORITHM)
    assert client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_identity_comes_from_token_not_query(client, signup_payload):
    first = client.post("/api/v1/auth/signup", json=signup_payload).json()
    second = client.post("/api/v1/auth/signup", json={**signup_payload, "email": "second@example.com"}).json()
    response = client.get(
        f"/api/v1/users/me?user_id={second['user_id']}", headers={"Authorization": f"Bearer {first['token']}"}
    )
    assert response.json()["id"] == first["user_id"]


def test_auth_throttling(client):
    for _ in range(config.get_settings().auth_rate_limit):
        client.post("/api/v1/auth/login", json={"email": "bad"})
    response = client.post("/api/v1/auth/login", json={"email": "bad"})
    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_health_and_cors(client):
    assert client.get("/health").json() == {"status": "ok", "phase": 3}
    ok = client.options(
        "/api/v1/auth/login",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    assert ok.headers["access-control-allow-origin"] == "http://localhost:3000"
    bad = client.options(
        "/api/v1/auth/login",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in bad.headers
