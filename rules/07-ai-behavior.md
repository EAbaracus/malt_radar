# AI Behavior Rules

- **Read-Only First:** Always prioritize analysis and diagnostic investigation before modifications.
- **Prefer Analysis:** Make informed decisions backed by data and schema checks.
- **Prefer Minimal Changes:** Make targeted changes, keeping diffs compact and readable.
- **Do Not Assume Success:** Always run verification checks, and inspect SQLite status post-execution.
- **Validate Before Completion:** Ensure git status, DB integrity, and counts match expectations.
- **Explain Uncertainty:** Clearly flag assumptions, and present risk levels when confidence is low.
- **Escalate:** Stop execution and request human review when database anomalies or security risks occur.
