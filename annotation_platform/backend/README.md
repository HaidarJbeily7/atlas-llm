# ATLAS Backend

FastAPI service for **investigating** and **annotating** findings produced by ATLAS
red-team experiments. Pairs with the React frontend in `../website/`.

## What it does

- **Seeds directly from raw experiment directories** (the scan files ATLAS
  produces), no preprocessing step needed. Stores structured scans + findings
  in PostgreSQL via SQLAlchemy.
- **Computes the summary on-the-fly** from DB tables (scans, findings) with
  in-memory caching — no static `summary.json` blob.
- **Accounts** are created via CLI only (`atlas-backend-adduser`).
  Authentication uses scrypt-hashed passwords with bearer-token sessions.
- **Two-annotator settlement**: each reviewer casts a single vote per finding
  (status: confirmed / false positive / investigating / won't fix / pending);
  a finding becomes **settled** only when ≥2 *distinct* users vote the same
  status. Mixed votes are **disputed**, one vote is **partial**, zero is
  **open**. Annotation writes are tied to the logged-in user.
- Optionally serves the built Vite frontend from `../website/dist/` for single-port
  production deployments.

## Prerequisites

- Python ≥ 3.10
- [uv](https://docs.astral.sh/uv/) (package manager)
- PostgreSQL (or a hosted Neon DB)

## Install & run

```bash
cd annotation_platform/backend

# Install dependencies
uv sync

# Run the server
uv run atlas-backend                      # listens on 127.0.0.1:8000

# Or with reload for development
ATLAS_RELOAD=1 uv run atlas-backend
```

## Configuration

Create a `.env` file in this directory (see `.env.example`):

```env
DATABASE_URL=postgresql://user:password@localhost:5432/atlas
```

All environment variables:

| Variable            | Default                  | Purpose                               |
| ------------------- | ------------------------ | ------------------------------------- |
| `DATABASE_URL`      | *(required, from .env)*  | PostgreSQL connection string          |
| `ATLAS_DATA_DIR`    | `../website/public/data` | Where summary.json + findings/ live   |
| `ATLAS_WEB_DIST`    | `../website/dist`        | Built frontend to serve (optional)    |
| `ATLAS_HOST`        | `127.0.0.1`              |                                       |
| `ATLAS_PORT`        | `8000`                   |                                       |
| `ATLAS_RELOAD`      | unset                    | If set, enables uvicorn auto-reload   |

## Database migrations

Migrations are managed with [Alembic](https://alembic.sqlalchemy.org/):

```bash
# Apply all migrations (run this after first setup or pulling new changes)
uv run alembic upgrade head

# Create a new migration after changing models.py
uv run alembic revision --autogenerate -m "describe the change"
```

## User management

User accounts are created via the CLI — there is no self-registration endpoint.

```bash
# Interactive (prompts for password with confirmation)
uv run atlas-backend-adduser alice

# Non-interactive
uv run atlas-backend-adduser alice --password secret123
```

## Seed experiments

The DB starts empty. Load experiments with `atlas-backend-seed`, which reads
raw experiment directories (containing `experiment_meta.json` + model/probe
scan files) directly — no preprocessing needed:

```bash
# Single experiment directory
uv run atlas-backend-seed ../../docs/experiment/20260410_121121

# All experiments under a parent folder
uv run atlas-backend-seed --recursive ../../docs/experiment

# Also works with the results/ directory
uv run atlas-backend-seed --recursive ../../results

# JSON output (for scripting)
uv run atlas-backend-seed --json ../../docs/experiment/20260410_121121
```

List what's in the DB:

```bash
uv run atlas-backend-experiments
```

You can also seed via HTTP: `POST /api/experiments/seed` with
`{"path": "...", "recursive": false}`.

## Dev workflow with the Vite frontend

Two terminals:

```bash
# Terminal 1 — backend
cd annotation_platform/backend && ATLAS_RELOAD=1 uv run atlas-backend

# Terminal 2 — frontend (proxies /api/* → backend)
cd annotation_platform/website && yarn dev
```

Vite's dev server proxies `/api/*` to `http://127.0.0.1:8000` (see
`website/vite.config.ts`). Override with `VITE_BACKEND_URL=...` if the backend
runs elsewhere.

## Auth & voting model

- `POST /api/auth/login` returns `{token, expires_at, user}`. Send it as
  `Authorization: Bearer <token>` on every mutating request.
- All write endpoints (`POST/PATCH/DELETE /api/annotations*`,
  `PUT/DELETE /api/findings/{id}/review`) require auth.
- Each user has **one vote per finding**; re-PUTting overwrites their own vote,
  `DELETE` withdraws it.
- Settlement returned in the review payload:
  - `open` – no votes
  - `partial` – 1 voter
  - `settled` – ≥2 distinct users agree on a status (that status is the settled result)
  - `disputed` – ≥2 distinct users but none with ≥2 matching votes

## API overview

```text
GET    /api/health
GET    /api/summary                          # latest experiment summary
GET    /api/findings/{id}                    # finding detail + annotations + review

# Experiments (DB-backed)
GET    /api/experiments                      # list persisted experiments
GET    /api/experiments/{id}                 # full computed summary
GET    /api/experiments/{id}/findings        # list with ?model=&probe=&passed=
GET    /api/experiments/{id}/findings/{fid}  # detail scoped to this experiment
DELETE /api/experiments/{id}                 # cascade-deletes its findings
POST   /api/experiments/seed                 # {path, recursive}

# Auth
POST   /api/auth/login                       # {username, password} -> LoginOut
POST   /api/auth/logout                      # invalidates bearer token
GET    /api/auth/me                          # current user (requires auth)

# Annotations (writes require auth; author = logged-in user)
GET    /api/findings/{id}/annotations
POST   /api/findings/{id}/annotations        # {label, note}
PATCH  /api/annotations/{ann_id}             # {label?, note?} (only your own)
DELETE /api/annotations/{ann_id}             # only your own
GET    /api/annotations/counts               # {finding_id: count}

# Reviews / voting (writes require auth; one vote per user per finding)
GET    /api/findings/{id}/review             # summary {settlement, status, votes, my_vote}
PUT    /api/findings/{id}/review             # {status, rationale?} — cast or update your vote
DELETE /api/findings/{id}/review             # withdraw your vote
GET    /api/reviews                          # aggregate per finding, settlement + counts
GET    /api/stats                            # user_count, votes_by_status, annotations, etc.
```

Interactive docs live at <http://127.0.0.1:8000/docs>.

## CLI commands

| Command                        | Description                          |
| ------------------------------ | ------------------------------------ |
| `uv run atlas-backend`        | Start the API server                 |
| `uv run atlas-backend-adduser` | Create a user account               |
| `uv run atlas-backend-seed`   | Seed experiments from raw data       |
| `uv run atlas-backend-experiments` | List persisted experiments       |
| `uv run alembic upgrade head` | Apply database migrations            |

## Valid review statuses

`pending`, `confirmed_vulnerability`, `false_positive`, `needs_investigation`, `wont_fix`
