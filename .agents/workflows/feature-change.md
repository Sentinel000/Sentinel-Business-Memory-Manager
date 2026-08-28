---
description: Runs when asked to change an existing feature's implementation.
---

## Steps

### 1. Locate the Feature
Search `docs/features/` for the feature directory by name slug.
If not found, stop and ask the user to confirm the feature name.

```
docs/features/{feature-name}/
├── plan.md
├── tasks.md
└── architecture.md
```

### 2. Update `plan.md`
Replace the entire content of `plan.md` with the new implementation plan.
Do not diff or append — full replacement only.

### 3. Update `tasks.md`
Derive a new task list from the updated plan. Replace the entire content of `tasks.md`.
Single-line checkboxes only. No descriptions, no sub-bullets, no implementation.

```md
- [ ] Task one
- [ ] Task two
- [ ] Task three
```

### 4. Update `architecture.md`
Replace the Mermaid diagram to reflect the new architecture.
Full replacement only — no partial edits.

```md
## Architecture: {Feature Name}

```mermaid
graph TD
    ...
```
```

## Rules
- Never partially update a file — always full replacement
- Never implement tasks during this workflow
- Confirm all three updated file paths to the user after writing