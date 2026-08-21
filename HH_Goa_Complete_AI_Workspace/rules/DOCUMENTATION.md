# DOCUMENTATION ROUTING RULES

The repository intentionally has both large and small documentation.

## Large documents

```text
README.md
ARCHITECTURE.md
rules/COMPLETE_GOVERNANCE_REFERENCE.md
roles/COMPLETE_ROLE_SPEC_REFERENCE.md
```

These preserve complete context and are read when the task requires it.

## Small documents

```text
RULES.md
ROLES.md
roles/ROLE*_README.md
rules/*.md
progress/*.md
```

Use these for ordinary work.

Do not duplicate project facts unnecessarily. If a detail belongs to the master README, reference it rather than creating a second conflicting copy.

When a project-wide decision changes, update the master source and relevant compact routing documentation.
