# PROGRESS RULES

Progress logs are audit trails.

## Current state
May be updated to reflect the latest verified state.

## Change history
Historical entries are append-only and immutable.

When changing an existing feature, NEVER edit the old entry. Append a new entry containing:

```text
Entry ID
Date
Type
Previous behavior
Change
Reason
Affected files
Tests
Benchmark
Integration impact
Next step / blocker
```

`DONE` means implemented and verified. If not verified, use an accurate status such as `IMPLEMENTED — NOT TESTED`.
