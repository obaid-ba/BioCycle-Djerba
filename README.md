# BioCycle Djerba

Intelligent platform connecting hotels with a biomethanization plant. Smart bins
stream sensor data over MQTT, the backend stores it, an external AI service
classifies waste and predicts energy output, and a realtime dashboard visualizes
everything.

> Scope of **this** repo: Backend, Database, Dashboard, Auth, Analytics, APIs,
> Realtime, and the **integration layer** with the AI service. We do **not**
> build the AI model — we only consume its REST API.

## Tech Stack

| Layer     | Stack |
|-----------|-------|
| Frontend  | React, Vite, TypeScript, TailwindCSS, shadcn/ui, TanStack Query, Recharts, Leaflet |
| Backend   | FastAPI, Python 3.12, SQLAlchemy 2.0 (async), Pydantic v2, Alembic, JWT, WebSockets, MQTT |
| Database  | PostgreSQL |
| Infra     | Docker Compose |
| Quality   | Ruff, Black, Pytest, ESLint, Prettier |

## Architecture

Backend follows **feature-based vertical slices**: each feature owns its router,
schemas, models, service, and repository in a single folder under
`app/features/`. Shared infra lives in `app/core/`, reusable primitives in
`app/shared/`.

## Quick start (backend)

```bash
cd backend
cp .env.example .env
docker compose up -d db          # from repo root: starts Postgres
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/api/docs

## Full stack via Docker

```bash
docker compose up --build
```

## Project status

Built feature-by-feature. See the roadmap in the project notes. Current phase:
**Phase 0 — Foundation** (runnable skeleton, health check, tooling).

## License

[MIT](LICENSE) © 2026 Obaid Allah Ben Ali
