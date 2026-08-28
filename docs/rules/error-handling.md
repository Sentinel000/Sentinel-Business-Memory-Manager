# Error Handling Rules

## Backend
- All FastAPI route handlers must use try/except — never let unhandled exceptions reach the client.
- Return structured error responses: `{ "error": "message", "code": "ERROR_CODE" }`.
- Use HTTP status codes correctly — `400` for bad input, `401` for auth, `403` for forbidden, `404` for not found, `500` for server errors.
- All errors must be reported to Sentry in production.

## AI Agents
- Agent node failures must be caught and logged to LangSmith with full trace context.
- Transient failures (network, rate limits) use retry with exponential backoff — max 3 attempts.
- If an agent cannot recover, surface a structured failure state to the PM dashboard — never silently fail.

## Frontend
- All API calls wrapped in try/catch — no unhandled promise rejections.
- User-facing error messages must be plain English — never expose raw error strings or stack traces.
- Failed actions must show a clear inline error and retain the user's input so they can retry.
