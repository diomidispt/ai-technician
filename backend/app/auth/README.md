# `app/auth/` — Cognito token guard (placeholder)

**Phase: Cognito + API auth** (see CLAUDE.md §8).

Application-level RBAC. FastAPI dependencies validate the Cognito access token and read the
`cognito:groups` claim (`admins`, `developers`, `technicians`) to guard each route.
UI role-gating is cosmetic only — **this is the security boundary** (CLAUDE.md §2 Auth).
