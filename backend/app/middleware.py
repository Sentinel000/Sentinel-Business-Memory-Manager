"""Request-scoped middleware: correlation id and timing."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Tags each request with an id and logs its duration.

    The id is echoed as X-Request-ID so a user-reported error can be traced to a
    log line. Never logs headers or bodies - they carry tokens and passwords.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Answered here, inside the CORS middleware, rather than by Starlette's
            # outermost error handler - whose 500 carries no CORS headers. The
            # browser then hides the response entirely and the app can only say
            # "Cannot reach the server", which is wrong and sends people looking
            # for an outage that is not there.
            logger.exception("Unhandled error [%s]", request_id)
            response = JSONResponse(
                status_code=500,
                content={"error": "Something went wrong.", "code": "INTERNAL_ERROR"},
            )
        duration_ms = (time.perf_counter() - started) * 1000

        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s -> %s (%.1fms) [%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response
