# CI/CD workflows (placeholders)

**Phase: alongside infra + each service** — see CLAUDE.md §6. Path-filtered GitHub Actions,
AWS auth via **OIDC** (no long-lived keys). PRs run tests + `terraform plan`; merge to `main`
deploys.

Planned workflows:
- `ci-backend.yml`   — test → docker build → push ECR → `aws lambda update-function-code`
- `ci-ingestion.yml` — same shape as backend
- `ci-frontend.yml`  — `npm ci && vite build` → `aws s3 sync dist/` → CloudFront invalidation
- `infra-plan.yml`   — `terraform plan` on PR
- `infra-apply.yml`  — `terraform apply` on merge (prod is CI-only; guardrail)

The stub files below define triggers + path filters only; build steps are filled in per phase.
