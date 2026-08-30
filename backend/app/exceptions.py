"""Domain exceptions and the handlers that render them.

Handlers are registered once in main.py so the structured error shape
``{"error": ..., "code": ...}`` is structural rather than repeated in every route.
See docs/rules/error-handling.md.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = logging.getLogger(__name__)


class SentinelError(Exception):
    """Base for anything we raise deliberately."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "INTERNAL_ERROR"
    message: str = "Something went wrong."

    def __init__(self, message: str | None = None) -> None:
        if message:
            self.message = message
        super().__init__(self.message)


class InvalidCredentialsError(SentinelError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "INVALID_CREDENTIALS"
    # Deliberately does not distinguish unknown email from wrong password — the
    # response must not reveal whether an account exists.
    message = "Incorrect email or password."


class NotAuthenticatedError(SentinelError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "NOT_AUTHENTICATED"
    message = "Authentication required."


class InactiveUserError(SentinelError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "INACTIVE_USER"
    message = "This account is disabled."


class ForbiddenError(SentinelError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"
    message = "You do not have permission to perform this action."


class NotFoundError(SentinelError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"
    message = "Resource not found."


class ValidationError(SentinelError):
    status_code = status.HTTP_400_BAD_REQUEST
    code = "VALIDATION_ERROR"
    message = "The request was invalid."


class ConflictError(SentinelError):
    """The request is valid but conflicts with the current state.

    Deleting an employee who still owns open tasks, or deciding an approval that has
    already been decided. Distinct from a validation error: nothing about the request
    is malformed, it just cannot be applied right now.
    """

    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"
    message = "That action conflicts with the current state."

    def __init__(self, message: str | None = None, *, details: dict | None = None) -> None:
        #: Extra context the client needs to resolve it — e.g. which tasks block a
        #: delete. Rendered alongside the error rather than buried in the message.
        self.details = details
        super().__init__(message)


def _body(code: str, message: str) -> dict[str, object]:
    return {"error": message, "code": code}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(SentinelError)
    async def handle_sentinel_error(_: Request, exc: SentinelError) -> JSONResponse:
        content = _body(exc.code, exc.message)
        details = getattr(exc, "details", None)
        if details:
            content["details"] = details
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(p) for p in first.get("loc", ())[1:]) or "request"
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_body("VALIDATION_ERROR", f"Invalid value for {field}."),
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
        # Logged in full, returned vague: the driver message can carry column values.
        logger.warning("Integrity error: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_body("CONFLICT", "That record already exists."),
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_db_error(_: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Database error", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_body("DATABASE_ERROR", "A database error occurred."),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_body("INTERNAL_ERROR", "Something went wrong."),
        )
