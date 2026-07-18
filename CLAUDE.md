# Jensen AI Technical Support Assistant

RAG assistant for field technicians servicing Jensen industrial laundry equipment.
Answers troubleshooting questions from an internal manual library first, web only as fallback.

## Golden rules
- Internal library FIRST, web search ONLY as fallback — this ordering is enforced in code
  (`backend/app/rag/`), never left to the model. Do not "simplify" it away.
- Every answer must carry source citations (manual + page/section). No citation → it's a bug.
- Safety-first: for electrical/steam/high-temp/moving-part steps, surface the safety
  precaution BEFORE the repair step.
- Never invent part numbers, torque values, or error-code meanings. If unknown, say so and
  recommend escalation.
- Region is eu-central-1 (Frankfurt). Data stays in the EU. Never hardcode another region.

## Stack (do not swap without a decision record)
- Frontend: React + Vite SPA, hosted on S3 + CloudFront. Streaming chat UI (SSE).
- Auth: Amazon Cognito (User Pool only; NO Identity Pool). Roles via Cognito Groups.
- Backend: Python 3.12 + FastAPI, containerized, on Lambda (container image) via ECR.
- AI: Amazon Bedrock — Claude Sonnet (answers) + Claude Haiku (routing). Titan embeddings.
- Vector store + data: Amazon RDS PostgreSQL + pgvector (one DB: vectors, chunks, metadata,
  conversations, audit logs).
- Ingestion: EventBridge → Lambda workers → parse (PDF/Office) + Textract OCR → chunk →
  embed → pgvector. Source of documents is an S3 bucket (see architecture doc).
- IaC: Terraform. CI/CD: GitHub Actions with AWS OIDC (no long-lived keys).

## Repo layout
- `infra/`      Terraform modules + per-env composition. Cloud engineer's domain.
- `backend/`    FastAPI RAG orchestrator. Has its own Dockerfile → ECR → Lambda.
- `ingestion/`  Sync/parse/chunk/embed workers. Own Dockerfile → ECR → Lambda.
- `frontend/`   React SPA. NO Dockerfile — static build shipped to S3.
- `shared/`     Schemas shared across backend/ingestion (pydantic) → frontend (TS types).
- `docs/`       Architecture and decision records.
Backend and ingestion share chunking/embedding code — keep that in `shared/` or a common module.

## Commands
Local dev loop (postgres+pgvector, MinIO for S3, api) comes up with:
- `docker compose up`            # full local stack
- `make dev`                     # convenience wrapper
Backend:
- `pytest backend/tests`         # tests
- `ruff check backend && ruff format backend`   # lint + format
Ingestion:
- `pytest ingestion/tests`
Frontend:
- `cd frontend && npm ci && npm run dev`   # local (Vite, port 5173)
- `npm run build`                # production build → dist/
Infra (single environment — one app for Jensen):
- `cd infra && terraform plan`             # never `apply` locally; CI applies

## Conventions
- Python: FastAPI + SQLAlchemy, type hints required, ruff for lint/format, no bare excepts.
- Vector queries go through the `db/` layer — no raw SQL scattered in route handlers.
- TypeScript strict mode in frontend, functional components + hooks.
- Conventional commits (feat:, fix:, refactor:, chore:).
- Tests required for new RAG logic and any auth/role guard.

## Guardrails (STOP and ask a human before)
- Any `terraform apply` against the live environment (CI applies, not local).
- Editing Cognito auth flows, IAM policies, KMS, or security-group rules.
- Anything touching audit-log retention or how citations are produced.
- Adding a new external data source or egress endpoint.
- Never commit secrets. Config via env vars + AWS Secrets Manager. `.env` is gitignored.

## Current status
Greenfield. Build order: infra skeleton → Cognito + API auth → ingestion (S3→pgvector) →
RAG core (retrieve/rerank/synthesize/citations) → web fallback → chat UI → admin console.

**Local MVP works end-to-end.** `frontend/` + `backend/` + Postgres/pgvector run locally with:
- **Auth + roles** — local JWT login simulating Cognito: `admin` / `technician`, instant
  disable, access-expiry, **self-service password change + admin forced-reset**
  (`must_change_password`) (`app/auth/`). Real Cognito swaps in behind the same route guards.
- **Admin console** — manage users (incl. reset password), upload/ingest PDFs, view the query
  audit log (`app/api/admin.py`).
- **Chat history** — persisted per-user conversations (`conversations` + `messages` tables) behind a
  sidebar; private per user, last-30 retention (`app/api/conversations.py`). The RDS `conversations`
  table, now local.
- **RAG** — internal-first **hybrid retrieval**: pgvector similarity + Postgres full-text keyword
  search fused with **RRF** (a $0 reranker; catches error codes / part numbers), with citations
  (manual · page · section); **history-aware** (follow-ups rewritten to standalone queries);
  **web-search fallback** (DuckDuckGo, `app/rag/websearch.py`) only when the library is
  insufficient; each query audited.
- **Ingestion** — pdfplumber: section-aware prose chunks + whole-table chunks + **Tesseract OCR
  fallback** for scanned pages/drawings (local stand-in for Textract; degrades gracefully).
- **Eval** — `make eval` scores retrieval + routing against `app/eval/` so RAG changes are
  measured, not eyeballed.
- **Model** — Ollama ($0, offline): `aya-expanse:8b` answers + `bge-m3` embeddings (multilingual),
  behind `app/rag/ollama_client.py` — swappable for Claude/Bedrock later. Models kept resident
  (`keep_alive`), answer length capped. Intent routing + query rewrite share **one** LLM call on
  the answer model (`_route_and_rewrite` in `pipeline.py`) instead of two calls on two different
  models — a smaller English-tuned model was found to misroute Greek technical questions as
  chitchat, and one shared model call means one round trip and no swapping between resident models.

Still to build for cloud: real Cognito, RDS (vs local Postgres), S3+Textract ingestion (vs
folder/pypdf), Terraform infra + deploy. The app logic doesn't change — only the backing services.

See the Architecture & Decisions reference below for the phase plan and per-component detail.

---

# Architecture & Decisions (reference)

Deeper detail behind the summary above: what each component does, why it was chosen, and how
the pieces connect. Keep it updated as decisions change.

## 1. Goal

A digital "technical assistant" for field technicians servicing Jensen industrial laundry
equipment. Technicians ask troubleshooting questions in a chat UI; the system answers from
the company's internal technical library (manuals, drawings, problem/solution history) and
falls back to the web only when the internal library is insufficient. Client requirements:
RAG on Claude, internal-first retrieval, controlled user access with instant revocation,
citations, EU data residency, and a future read-only Gmail source.

## 2. Component-by-component

### Frontend — the "looks like Claude" UI
- React + Vite SPA, hosted as static files on **S3 + CloudFront** (CDN, HTTPS, speed).
- Two surfaces: technician chat + admin console.
- The "feels like Claude" quality comes from (a) **streaming** responses token-by-token via
  SSE, and (b) an open-source chat UI library (e.g. assistant-ui or Vercel AI SDK UI) for
  bubbles, markdown, and citation rendering — then branded.
- The SPA never talks to AWS services directly; it only calls our API. This is why we do
  NOT use a Cognito Identity Pool.

### Auth — Amazon Cognito (User Pool only)
- **User Pool** = the user directory: technicians + admins, sign-in, password policy, JWTs.
- **Identity Pool** = deliberately NOT used (would hand raw AWS creds to the browser).
- **RBAC via Cognito Groups**: `admins`, `developers`, `technicians`. Membership rides in
  the token as the `cognito:groups` claim.
- Enforcement lives in the **backend** (application RBAC): FastAPI reads the group claim and
  guards each route. UI role-gating is cosmetic only — never a security boundary.
- Three tokens: ID token (who + groups, for the UI), access token (short-lived ~15-60 min,
  sent on every API call), refresh token (silently mints new access tokens).
- Plug-in: React uses AWS Amplify Auth (or Cognito Hosted UI). Interceptor attaches the
  access token; **API Gateway Cognito authorizer** validates signature + expiry before the
  Lambda runs.
- Login: email + password out of the box (password policy, forced first-login reset, MFA —
  required for admins). **SSO optional**: federate the User Pool to Google Workspace or
  Microsoft Entra ID via OIDC/SAML. Recommendation: launch pilot with email+password (no
  dependency on client IT), add SSO as a fast follow.
- **Revocation** (all single API calls, wired into admin-console buttons):
  - `AdminDisableUser` — can't sign in; immediate.
  - `AdminUserGlobalSignOut` — kills all refresh tokens; active access token dies within its
    short TTL. This is why access-token lifetime is kept short.
  - delete user — permanent; remove-from-group — demote a role without killing the account.
- **Temp/expiring access**:
  - Temp password on creation is native (`AdminCreateUser`, one-time password, configurable
    validity, forced reset).
  - Date-based expiry for contractors: custom attribute `custom:access_expires` + either a
    pre-token-generation Lambda trigger (refuse tokens past the date) or a nightly
    EventBridge→Lambda sweep calling `AdminDisableUser`.
- Note: App admin (Cognito `admins` group) is distinct from AWS/cloud access (that's IAM
  accounts for the engineers, not Cognito). Don't conflate them.

### Backend — the brain (RAG + fallback)
Python/FastAPI on Lambda (container image) behind API Gateway. Per-query flow:
1. Validate Cognito token.
2. Embed the (optionally rewritten) query.
3. Vector search in pgvector → top-k chunks.
4. Rerank + sufficiency check ("do these cover the question?").
5. If sufficient → synthesize with Claude using ONLY those chunks, with manual/page citations.
6. If not → **web search fallback**, clearly flagged as external.
7. Write to conversation history + audit log.
Internal-first ordering is code (step 6 runs only if step 5 fails), not a prompt instruction
— this is the core advantage over the Claude Team alternative.

### Vector store + data — managed AWS, not custom
- **Amazon RDS for PostgreSQL** (or Aurora Serverless v2) + **pgvector** extension.
- One database holds: embeddings + chunk text + metadata (manual, page), plus tables for
  conversations and audit logs. AWS handles backups, patching, encryption, HA.
- Chosen over OpenSearch/Pinecone: keeps everything in one familiar Postgres, in-VPC, in-EU,
  cheaper at this scale.

### Indexing / chunking — what and why
A manual is 200-300 pages; neither the LLM nor vector search works well over whole documents.
- **Chunking**: split each doc into small pieces (~500-1000 tokens, on logical section
  boundaries).
- **Embedding + indexing**: compute an embedding per chunk, store in pgvector.
- Why: at query time, embed the question, find the nearest-meaning chunks, pass only those to
  Claude — targeted retrieval, low cost, precise citations (page/section, not "somewhere in
  the manual"). Without chunking, content wouldn't fit context and retrieval couldn't target.

### Ingestion pipeline — S3-sourced (no OneDrive access)
Decision: the AI never connects to OneDrive/Google. Instead, documents are pushed into a
private **S3 bucket**, and ingestion reads ONLY from S3. Nothing in the stack holds
credentials to the client's Microsoft/Google tenant.
- Getting files into S3 (client's choice): `aws s3 sync` or rclone on a schedule; Power
  Automate / Azure Data Factory / Logic Apps from the Microsoft side; AWS DataSync for
  continuous sync; or an upload button in the admin console.
- Pipeline: EventBridge (schedule) → Lambda workers detect new/changed objects → parse
  (PDF/Office) + **Textract** OCR for scans + vision for drawings → chunk → embed → upsert
  into pgvector.
- Trade-off vs a live connector: you lose "automatic live sync" but gain a sync path you
  control 100% and zero third-party access.
- Access control = what you put in the bucket. Documents never uploaded are never seen.
- Honest limitation: text-first retrieval reads scanned drawings poorly; the pilot will
  reveal where OCR/vision needs investment.

## 3. AWS services used
Frontend: S3, CloudFront. Auth: Cognito. API/compute: API Gateway, Lambda. AI: Bedrock
(Claude + Titan) — or the Anthropic API directly. Data: RDS PostgreSQL (pgvector), S3.
Ingestion: EventBridge, Lambda, Textract, optional Step Functions. Network/security: VPC
(private subnets), KMS, Secrets Manager, IAM. Observability: CloudWatch (+ optional X-Ray).
IaC/CI-CD: Terraform, GitHub Actions. Web fallback: Anthropic web search or Tavily/Brave.

## 4. Repo strategy

Monorepo (two-person team, tightly coupled system) — atomic cross-cutting PRs, one CI config.
Split only if ownership/release cadence diverges; the natural cut then is three repos:
`infra`, `app` (backend + ingestion + shared), `frontend`.

```
ai-technician/
├── infra/            Terraform, single env: {network,cognito,data,api,ingestion,frontend,observability}
├── backend/          FastAPI RAG orchestrator + Dockerfile (→ ECR → Lambda)
├── ingestion/        sync/parse/chunk/embed + Dockerfile (→ ECR → Lambda)
├── frontend/         React SPA (no Dockerfile; static → S3)
├── shared/           schemas/types shared across services
├── .github/workflows/  ci-backend, ci-ingestion, ci-frontend, infra-plan, infra-apply
├── docker-compose.yml  local: postgres+pgvector, api, minio(S3)
└── docs/
```

## 5. Containers, registry, deploy targets

Three deployables; two are containerized:
- **backend** → Dockerfile → ECR `jensen/backend` → **Lambda (container image)**. RAG deps
  exceed the 250 MB zip limit, so container-image Lambda (up to 10 GB) is correct.
- **ingestion** → own Dockerfile → ECR `jensen/ingestion` → Lambda, EventBridge-triggered.
- **frontend** → NO Dockerfile; `vite build` → `dist/` → S3 + CloudFront.

Backend Dockerfile uses `public.ecr.aws/lambda/python:3.12`, FastAPI wrapped with Mangum.
For token streaming, use a **Lambda Function URL with RESPONSE_STREAM** invoke mode (classic
API Gateway REST buffers). Alternative if Lambda streaming is fiddly: **ECS Fargate behind an
ALB** (native SSE/WebSocket, same image) — Lambda is cheaper at this volume, Fargate simpler
for long-lived streams.

Registry: one private ECR repo per image; scan-on-push; lifecycle policy to expire untagged
images; tag with git SHA (+ moving `latest`).

Note: ECR is the AWS registry (the Azure equivalent, ACR, does not apply here).

## 6. CI/CD

GitHub Actions, **path-filtered** (a frontend change doesn't rebuild the backend). Auth to
AWS via **OIDC** — no long-lived keys; a role per pipeline assumed at runtime. PRs run tests
+ `terraform plan`; merge to `main` deploys.
- `ci-backend`: test → docker build → push ECR → `aws lambda update-function-code`.
- `ci-ingestion`: same shape.
- `ci-frontend`: `npm ci && vite build` → `aws s3 sync dist/` → CloudFront invalidation.
- `infra-plan` (on PR) / `infra-apply` (on merge). Terraform state in S3 backend + DynamoDB
  lock.
- Optional given team's background: front the Terraform with **Spacelift** (policy-as-code,
  drift detection) instead of `infra-apply`. **Argo CD does not fit** (no Kubernetes) unless
  the backend later moves to EKS — over-engineering at this scale.

## 7. Monthly cost (indicative)

~10 technicians × ~15 queries/workday (~3,300 queries/mo), eu-central-1. Confirm in the AWS
Pricing Calculator for a final quote.

| Service | Pilot (single-AZ) | Production (HA) |
|---|---|---|
| RDS PostgreSQL + pgvector | ~$35 | ~$90 |
| NAT Gateway | ~$35 | ~$35 |
| Claude Sonnet (answers) | ~$85 | ~$180 |
| Claude Haiku (routing) | ~$3 | ~$5 |
| Embeddings (Titan) | ~$2 | ~$5 |
| Textract (OCR) | ~$2 | ~$5 |
| Web Search API | ~$5 | ~$10 |
| Lambda + API Gateway | ~$3 | ~$8 |
| S3 + CloudFront | ~$3 | ~$5 |
| Cognito | ~$0 | ~$1 |
| CloudWatch + KMS + Secrets | ~$8 | ~$15 |
| **Total** | **~$180/mo** | **~$360/mo** |

Biggest levers: RDS size + Multi-AZ, Claude token volume (context × queries, softened by
prompt caching), and NAT Gateway. Always-on baseline (RDS + NAT + endpoints) is ~$70-90/mo
even at zero usage; the rest scales with traffic.

## 8. Build order

infra skeleton → Cognito + API auth → ingestion (S3 → pgvector) → RAG core
(retrieve / rerank / synthesize / citations) → web fallback → chat UI → admin console
(user management: create / disable / global-sign-out / expire) → analytics + hardening.
