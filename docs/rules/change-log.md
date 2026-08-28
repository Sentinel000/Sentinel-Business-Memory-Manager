---
description: After each change , addtion , fix or debug add a log in CHANGE-LOG.md
---

## Purpose
The changelog is the project's shared memory. It transfers context between agents — every entry must give the next agent enough information to understand what changed, why, and what to watch out for.

## Format
```
## [version] - YYYY-MM-DD
### Added / Fixed / Changed
- What changed, why it changed, and anything the next agent should know.
```

## Example
```md
## [1.1.0] - 2026-02-18
### Added
- Dark mode toggle in settings — theme preference is stored in localStorage.
- Task drag-and-drop reordering — order is persisted on drop, not on save.
### Fixed
- Save button was unresponsive on mobile due to a z-index conflict with the nav overlay.
```

## Rules
- DONT create new file , only update in existing CHANGE-LOG.md 
- Keep entries to **1–2** [Strict] lines. Be concise but never sacrifice clarity for brevity.
- Plain language — no jargon, no raw implementation details.
- Always include **why** something changed or **what to watch out for** if it affects future work. [At most 2 lines]
- Every entry should leave the next agent with zero ambiguity about the current state of the project.