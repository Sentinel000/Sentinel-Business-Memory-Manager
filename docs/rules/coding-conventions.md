# Coding Conventions

## General
- Use TypeScript on the frontend — no plain JS files.
- Use Python type hints on all FastAPI routes and functions.
- Prefer functional components with hooks — no class components.
- Use ES module imports (`import/export`) — never CommonJS (`require`).

## Naming
- Files and folders: `kebab-case`
- React components: `PascalCase`
- Functions and variables: `camelCase`
- Python functions and variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

## Frontend
- State management via Zustand — no prop drilling beyond 2 levels.
- All animations via Motion — no raw CSS transitions for interactive elements.
- Tailwind utility classes only — no inline styles.

## Backend
- All request/response models defined with Pydantic.
- All DB schema changes via Alembic migrations — never mutate schema directly.
- FastAPI routes grouped by domain in separate routers.
