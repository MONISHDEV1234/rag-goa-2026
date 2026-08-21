# DEVELOPMENT RULES

Before editing:
1. Inspect the actual implementation.
2. Search for existing files/functions before creating duplicates.
3. Check relevant progress.
4. Check shared contracts/interfaces.
5. Make the smallest justified change.

Avoid unrelated refactors and unnecessary dependencies.

For external services use sensible timeouts and retry only transient failures.

After editing:
- run relevant tests;
- inspect the diff;
- remove debug artifacts;
- document meaningful changes.
