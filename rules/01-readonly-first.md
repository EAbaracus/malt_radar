# Rule 01: Read-Only First Protocol

All agents must default to Read-Only mode at the start of any task.

## Rules of Engagement:
1. Do not modify databases or files on initialization.
2. Read schemas, run count queries, and inspect logs first.
3. Validate environment state and DB hashes before drafting changes.
4. If a task is investigatory or analysis-only, never write files or execute git operations.
