"""Signed links an employee can act on from an email, without logging in.

A link is bound to one task and one employee, and carries the tenant inside the
signature, so it can only ever move that one task, as that one person, in that one
company. The status is chosen on the landing page, which is why one token serves
all three buttons in the email.

The key is *derived* from the session key rather than reused. An action link must
never be accepted as a session token, and a session token must never be accepted as
an action link - the ``typ`` claim enforces that too, but with separate keys neither
check has to be remembered by whoever touches this next.
"""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from app.config import settings

TOKEN_TYPE = "task_action"
_ALGORITHM = "HS256"


def _signing_key() -> str:
    return hashlib.sha256(f"{settings.jwt_secret_key}:{TOKEN_TYPE}".encode()).hexdigest()


@dataclass(frozen=True)
class ActionClaims:
    task_id: uuid.UUID
    employee_id: uuid.UUID
    company_id: uuid.UUID


def issue_action_token(
    *,
    task_id: uuid.UUID,
    employee_id: uuid.UUID,
    company_id: uuid.UUID,
    ttl: timedelta | None = None,
) -> str:
    now = datetime.now(UTC)
    claims = {
        "typ": TOKEN_TYPE,
        "tid": str(task_id),
        "eid": str(employee_id),
        "cid": str(company_id),
        "iat": now,
        "exp": now + (ttl or timedelta(hours=settings.action_link_ttl_hours)),
    }
    return jwt.encode(claims, _signing_key(), algorithm=_ALGORITHM)


class ActionTokenExpired(Exception):
    """Genuine but past its expiry - worth a different message than a forged one."""


def verify_action_token(token: str) -> ActionClaims | None:
    """Claims for a valid link, None for a forged or malformed one.

    Raises ActionTokenExpired for a real link that has simply run out, so the page
    can tell the employee to open the app instead of implying the link is fake.
    """
    try:
        claims = jwt.decode(token, _signing_key(), algorithms=[_ALGORITHM])
    except ExpiredSignatureError:
        raise ActionTokenExpired() from None
    except JWTError:
        return None

    if claims.get("typ") != TOKEN_TYPE:
        return None
    try:
        return ActionClaims(
            task_id=uuid.UUID(claims["tid"]),
            employee_id=uuid.UUID(claims["eid"]),
            company_id=uuid.UUID(claims["cid"]),
        )
    except (KeyError, ValueError):
        return None
