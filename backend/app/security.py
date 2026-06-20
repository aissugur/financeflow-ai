"""Password hashing and JWT helpers for authentication.

Pure functions — no FastAPI imports — so they stay unit-testable. bcrypt for
password storage (via passlib), PyJWT for short-lived HS256 access tokens.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from passlib.context import CryptContext

from . import config

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# A throwaway hash to verify against when a login email is unknown, so that the
# "no such user" path costs roughly the same time as "wrong password" (this
# blunts user-enumeration via timing).
_DUMMY_HASH = _pwd_context.hash("dummy-password-for-constant-time-compare")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: Optional[str]) -> bool:
    """Verify a password against a stored hash. When no hash is given (unknown
    user) we still run a compare against a dummy hash and return False, keeping
    timing roughly constant."""
    if password_hash is None:
        _pwd_context.verify(password, _DUMMY_HASH)
        return False
    return _pwd_context.verify(password, password_hash)


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    minutes = expires_minutes or config.ACCESS_TOKEN_EXPIRE_MINUTES
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": "access",  # so a future token kind can't be replayed as an access token
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, config.AUTH_SECRET_KEY, algorithm=config.AUTH_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises jwt.PyJWTError on any problem."""
    return jwt.decode(token, config.AUTH_SECRET_KEY, algorithms=[config.AUTH_ALGORITHM])
