# Flavor Source Conflict Matrix

This matrix defines the expected behavior when a whisky has flavor profiles available from multiple sources.

| Production Profile | WhiskeyMapper Profile | ScotchGit Preview Profile | Effective Source (Prod Mode) | Effective Source (QA Mode) | UI Badges (QA Mode) |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **YES** | YES | YES | **Production** | **Production** | "Preview Available (Lower Priority)" |
| **YES** | YES | NO | **Production** | **Production** | None |
| **YES** | NO | YES | **Production** | **Production** | "Preview Available (Lower Priority)" |
| **YES** | NO | NO | **Production** | **Production** | None |
| NO | **YES** | YES | **WhiskeyMapper** | **WhiskeyMapper**| "Preview Available (Lower Priority)" |
| NO | **YES** | NO | **WhiskeyMapper** | **WhiskeyMapper**| None |
| NO | NO | **YES** | **None** | **ScotchGit** | "QA Preview: ScotchGit" |
| NO | NO | NO | **None** | **None** | None |

## Summary of ScotchGit States
- **Conflict (49 whiskies)**: Falls into rows 1, 3, or 5. Production or WhiskeyMapper takes precedence. ScotchGit remains hidden unless explicitly compared in QA mode.
- **No Conflict (74 whiskies)**: Falls into row 7. Appears empty in Production. Shows up fully populated in QA mode with a warning badge.
