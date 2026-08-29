# Feature Workflow Rule

## Big new feature (not small changes)

Before writing code for a big new feature, stop and remind the user:

> "This looks like a big feature. Let's plan it first, then run `feature-plan` so it's saved in the codebase."

Do not start building until the plan is made and `feature-plan` is run.

## Changing an existing feature

Before changing any existing feature, remind the user:

> "You're changing an existing feature. Run `feature-change [feature-name]` first so it's tracked."

Ask for the feature name if it's not given.

## Why this rule exists

Users forget these commands exist. This rule is here so the team always uses them, every time, without needing to remember on their own.

## When this does NOT apply

- Small changes (bug fixes, tiny tweaks, copy edits, config changes)
- Anything the user says is small or minor