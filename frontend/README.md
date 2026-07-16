# `frontend/` — React SPA (technician chat)

Vite + React + TypeScript (strict). Hosted as static files on S3 + CloudFront in prod (no
Dockerfile). The SPA never talks to AWS directly — it only calls our API (CLAUDE.md §2).

## Run

```bash
npm install
npm run dev      # http://localhost:5173 (proxies /api → backend :8000)
npm run build    # typecheck + production build → dist/
```

## Phase 1 (now)
Minimal custom chat: streaming bubbles, markdown, Jensen branding. Talks to the backend's
`/api/chat` SSE endpoint. No auth yet (Cognito/Amplify lands in the auth phase). The
citation slot in `MessageBubble.tsx` is wired but empty until RAG returns citations.

## Structure
- `src/api/chat.ts` — SSE client (parses `token`/`done` events; matches the backend contract)
- `src/components/` — `Chat` (state) · `MessageList` · `MessageBubble` · `Composer`
- `src/styles/` — branded, Claude-like layout (light + dark)
