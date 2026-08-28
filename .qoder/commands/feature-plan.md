---
description: Runs immediately after the user approves a feature implementation plan.
---

## Steps

### 1. Extract from Approved Plan
- The full approved plan (scope, decisions, approach)
- The task list (implementation steps only, no descriptions)
- The architecture (system/component relationships)

### 2. Derive Feature Name
Convert the feature title to a slug: lowercase, hyphens, no special characters.
Example: `Anti Gravity Engine` → `anti-gravity-engine`

### 3. Create Directory Structure
```
docs/
└── features/
    └── {feature-name}/
        ├── plan.md
        ├── tasks.md
        └── architecture.md
```

### 4. Write Files

#### `plan.md`
Complete implementation plan as approved by the user. Includes context, scope, approach, decisions, and any constraints. No summarizing — preserve the full plan.

#### `tasks.md`
Single-line tasks only. One task per line as a checkbox. No sub-bullets, no descriptions, no implementation.
```md
- [ ] Task one
- [ ] Task two
- [ ] Task three
```

#### `architecture.md`
A complete Mermaid diagram representing the feature's architecture — components, data flow, and relationships.
```md
## Architecture: {Feature Name}

```mermaid
graph TD
    ...
```
```

## Rules
- Never implement tasks during this workflow — only document them
- Do not modify existing files; create new ones only
- If the feature directory already exists, append `-v2` (or increment) to the slug
- Confirm file paths to the user after writing