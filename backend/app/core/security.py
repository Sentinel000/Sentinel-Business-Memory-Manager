"""Password hashing and JWT issue/verify.

The signing key is the tenancy boundary: company_id travels as a signed claim, so
anyone who can forge a token can read any tenant. It is never taken from a request.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.models.enums import UserRole

# bcrypt is pinned to 4.0.x in requirements.txt — passlib 1.7.4 reads bcrypt.__about__,
# which was removed in 4.1.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """False rather than raising on a malformed stored hash."""
    try:
        return pwd_context.verify(plain_password, password_hash)
    except ValueError:
        return False


def create_access_token(
    *,
    user_id: uuid.UUID,
    company_id: uuid.UUID,
    role: UserRole | str,
    expires_delta: timedelta | None = None,
) -> str:
    """Issue a token. company_id is what every downstream query is scoped by."""
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    role_str = role.value if hasattr(role, "value") else str(role)
    claims: dict[str, Any] = {
        "sub": str(user_id),
        "company_id": str(company_id),
        "role": role_str,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Verified claims, or None if the token is invalid, expired, or tampered with."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
