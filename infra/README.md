# `infra/` — AWS resources (Terraform, placeholder)

**One folder for all cloud resources. Single environment** — this is one application for
Jensen, so there's no dev/prod split, no per-env composition. Just the resources this app
needs. Not yet written (see build order in CLAUDE.md §8).

Region is **eu-central-1** (Frankfurt) — EU data residency. Never hardcode another region.
State goes in an S3 backend + DynamoDB lock; applied by CI via AWS OIDC (no long-lived keys).

```
infra/
├── network/         VPC, private subnets, NAT, VPC endpoints
├── cognito/         User Pool (no Identity Pool), groups, app client
├── data/            RDS PostgreSQL + pgvector, KMS, Secrets Manager
├── api/             backend compute (Lambda/Fargate) + public URL
├── ingestion/       EventBridge, workers, Textract wiring, S3 document bucket
├── frontend/        S3 + CloudFront (static SPA hosting)
└── observability/   CloudWatch, alarms
```

Each folder is one Terraform module for that concern; a single root composition wires them
together. Nothing here is billable until it's actually applied — the Phase 1 demo uses none
of it.
