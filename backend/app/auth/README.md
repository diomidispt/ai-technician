# `app/auth/` — authentication + RBAC (local simulation of Cognito)

Real login for the local MVP; swaps to Amazon Cognito later without changing route logic.

- `security.py` — bcrypt password hashing + JWT sign/verify (HS256, local secret).
- `dependencies.py` — `get_current_user` (loads the user from the DB **every request** and
  re-checks `is_active` + `access_expires`, so disable/expiry take effect immediately) and
  `require_admin`. These are the security boundary (UI role-gating is cosmetic).

Users live in the `users` table (`app/db/models.py`). `role` mirrors a Cognito group
(`admin` | `technician`); `is_active` mirrors `AdminDisableUser`; `access_expires` mirrors the
`custom:access_expires` contractor attribute. A default admin + technician are seeded on
startup (`seed_users`). Login/admin routes: `app/api/auth.py`, `app/api/admin.py`.

**Cloud swap:** replace JWT issuance with Cognito + an API Gateway authorizer; keep
`require_admin`-style guards reading the role claim.
