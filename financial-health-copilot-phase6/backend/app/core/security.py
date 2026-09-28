from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import config
from app.core.database import get_db
from app.core.errors import APIError
from app.db.user import User

bearer = HTTPBearer(auto_error=False)
# Used when the account does not exist to avoid a cheap, distinguishable failure path.
DUMMY_HASH = bcrypt.hashpw(b"dummy-password-not-an-account", bcrypt.gensalt(config.BCRYPT_ROUNDS))


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(config.BCRYPT_ROUNDS)).decode()


def verify_password(password: str, hashed: str | None) -> bool:
    raw = password.encode()
    if len(raw) > config.PASSWORD_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(raw, hashed.encode() if hashed else DUMMY_HASH)
    except ValueError:
        return False


def create_token(user_id: UUID) -> str:
    settings = config.get_settings()
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=settings.access_token_minutes),
            "iss": config.JWT_ISSUER,
            "aud": config.JWT_AUDIENCE,
            "jti": str(uuid4()),
        },
        settings.jwt_secret.get_secret_value(),
        algorithm=config.JWT_ALGORITHM,
    )


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    error = APIError(401, "unauthorized", "Please log in again.", headers={"WWW-Authenticate": "Bearer"})
    if not credentials:
        raise error
    try:
        payload = jwt.decode(
            credentials.credentials,
            config.get_settings().jwt_secret.get_secret_value(),
            algorithms=[config.JWT_ALGORITHM],
            issuer=config.JWT_ISSUER,
            audience=config.JWT_AUDIENCE,
            options={"require": ["sub", "exp", "iat", "nbf", "iss", "aud", "jti"]},
        )
        user_id = UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError, KeyError):
        raise error from None
    user = db.get(User, user_id)
    if user is None:
        raise error
    return user
