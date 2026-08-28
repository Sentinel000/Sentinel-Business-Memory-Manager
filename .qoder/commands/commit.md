---
description: Invoked after changes are made and ready to be saved to the feature branch.
---

## Steps:
### 1. Confirm You Are on the Feature Branch
```bash
git branch --show-current
```
- If on `main` → stop immediately. Do not commit. Notify the user.
- If on a feature branch → proceed.

### 2. Review What Changed
```bash
git status
git diff --stat
```
Understand what files changed before staging anything.

### 3. Stage Changes
```bash
git add .
```

### 4. Commit with a Conventional Commit Message
Format: `<type>: <short description>`

| Type | When to Use |
|---|---|
| `feat:` | New functionality added |
| `fix:` | Bug or error resolved |
| `refactor:` | Code restructured, no behavior change |
| `docs:` | Documentation only |
| `chore:` | Config, deps, tooling |

```bash
git commit -m "feat: short description of what changed"
```

### 5. Push to the Feature Branch
```bash
git push origin feature/<current-branch-name>
```
Never push to `main`.

### 6. (If GitHub MCP is connected)
Use GitHub MCP to confirm the push was received on the remote.
Use `get-commit` or `list-commits` on the feature branch to verify.

## Rules
- Always verify the current branch before committing — never commit on `main`.
- One commit per logical change — do not bundle unrelated changes into one commit.
- Commit message must be meaningful — no `fix`, `update`, `changes`, or similar vague messages.
- Always push immediately after committing — never leave commits only local.
- Notify the user with the commit message and branch name after every successful push.