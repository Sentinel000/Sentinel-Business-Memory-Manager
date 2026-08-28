# Security Rules

- Never commit secrets, API keys, or credentials — use environment variables only.
- All environment variables must be documented in `.env.example` with placeholder values.
- All API routes must validate the authenticated user before accessing any data.
- Never log sensitive data (passwords, tokens, personal info) in any environment.