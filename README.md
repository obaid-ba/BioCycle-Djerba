# BioCycle Djerba

Platform connecting Djerba's hotels with a biomethanization plant. Hotels declare
their organic waste, an external AI scores each load for quality and expected
energy yield, and operators work a ranked collection queue — tracking every
pickup from request to completion.

> Scope of **this** repo: Backend, Database, Dashboard, Auth, Analytics, APIs,
> Realtime, and the **integration layer** with the AI service. We do **not**
> build the AI model — we only consume its output.

## The core idea

A **Collection Request** is the central aggregate. A hotel declares a container
count; the backend derives the weight, snapshots the distance to the plant, and
enriches the request with AI scores (purity, contamination, estimated methane,
energy, CO₂). An operator then drives it through
`pending → accepted → on_the_way → collected → completed`.

The queue is deliberately **not** ordered by the AI's opaque priority score.
Operators dispatch real trucks, and "because the model said so" is not a reason
anyone can act on, so it sorts on rules a human can read and challenge: priority,
then quality, then distance, then load size, then FIFO. The AI informs the
decision; the operator makes it.

## Tech Stack

| Layer     | Stack |
|-----------|-------|
| Frontend  | React, Vite, TypeScript, TailwindCSS, shadcn/ui, TanStack Query, Recharts, Leaflet |
| Backend   | FastAPI, Python 3.12, SQLAlchemy 2.0 (async), Pydantic v2, Alembic, JWT, WebSockets |
| Database  | PostgreSQL |
| Infra     | Docker Compose |
| Quality   | Ruff, Black, Pytest, ESLint, Prettier |

## Architecture

Backend follows **feature-based vertical slices**: each feature owns its router,
schemas, models, service, and repository in a single folder under
`app/features/`. Shared infra lives in `app/core/`, reusable primitives in
`app/shared/`.

Analysis data reaches the app through a `RequestDataProvider` interface
(Adapter + DI). A deterministic stub backs it today; swapping in the live
Firebase reader is a one-line change at the DI wiring, with no business-code
change. The backend computes no scores of its own — it is a pure consumer.

Roles are **Administrator**, **Operator**, and **Hotel manager**, enforced
server-side: a hotel manager is hard-scoped to their own hotels' requests
regardless of the filters they send.

## Quick start (backend)

```bash
cd backend
cp .env.example .env
docker compose up -d db          # from repo root: starts Postgres
pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
python -m scripts.seed_admin     # initial admin from FIRST_SUPERUSER_*
python -m scripts.seed_demo      # optional: hotels + requests to click through
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/api/docs

Both seed scripts are idempotent — re-running them adds nothing.

## Full stack via Docker

```bash
docker compose up --build
```

## Project status

Built feature-by-feature. The Collection Request workflow is complete end to
end: hotel declaration, AI enrichment, the ranked operator queue, the full
lifecycle with guarded transitions, photo upload, notifications, role-scoped
dashboards and analytics, CSV reports, and a per-request map showing the hotel,
the plant, and the distance between them.

Covered by **110 backend tests**.

### A note on the IoT layer

An earlier iteration was built around Smart Bins streaming telemetry over MQTT.
The product then pivoted to manual declaration, so those routers are **no longer
mounted** and MQTT is disabled by default. The code (models, MQTT client,
WebSocket telemetry) is kept and still tested rather than demolished — hence the
skipped tests you'll see in the suite, which are explicitly marked with why.

## License

[MIT](LICENSE) © 2026 Obaid Allah Ben Ali
