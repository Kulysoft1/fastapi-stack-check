# FastAPI Stack Check

A minimal FastAPI application with PostgreSQL and Redis that demonstrates a complete stack deployable to both Render and Railway free tiers. Provides a single HTML page to read/write to both data stores with real-time health monitoring.

---

## Local Run (no Docker)

Install PostgreSQL 16 and Valkey (Redis-compatible) locally, then run the app with `uv`.

### 1. Install and configure PostgreSQL
```bash
# AlmaLinux 10 / RHEL
sudo dnf install -y postgresql-server postgresql
sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql

# Set password and create the demo database
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
sudo -u postgres psql -c "CREATE DATABASE fastapi_demo;"

# Verify TCP auth works
PGPASSWORD=postgres psql -h 127.0.0.1 -U postgres -d fastapi_demo -c "SELECT 1;"
```
On Debian/Ubuntu use `sudo apt install postgresql` and `sudo pg_ctlcluster 16 main start`. On macOS, `brew install postgresql@16 && brew services start postgresql@16`.

### 2. Install and start Valkey (Redis-compatible)
```bash
# AlmaLinux 10 / RHEL
sudo dnf install -y valkey
sudo systemctl enable --now valkey
valkey-cli ping   # -> PONG

# Debian/Ubuntu
# sudo apt install redis-server
# sudo systemctl enable --now redis-server

# macOS
# brew install valkey
# brew services start valkey
```

### 3. Configure and start the app
```bash
cp .env.example .env
# .env defaults already point at localhost; edit only if your ports differ

uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Open http://localhost:8000 in your browser. Postgres (5432), Valkey (6379) and the app (8000) must all be listening:
```bash
pg_isready -h 127.0.0.1        # "accepting connections"
valkey-cli ping                # "PONG"
curl -s http://localhost:8000/health/ready   # postgres+redis both "ok"
```

If you prefer Docker instead of native installs, `docker compose up -d` plus the same `uv sync` / `alembic` / `uvicorn` sequence also works.

---

## Deploy to Render (free tier)

Render's free plan includes one free web service, a free 1 GB Postgres, and a free 25 MB Redis Key Value store. Web services on the free plan spin down after 15 minutes idle (cold start ~30 s) and the Redis store is capped at 25 MB. The free plan does **not** offer **Blueprint** (Infrastructure-as-Code) deployments, so create the three resources manually as below (the `render.yaml` in this repo is kept only as a reference/spec).

### Manual deploy steps
1. **Fork** this repository to your GitHub account.
2. **Create the PostgreSQL database**: Dashboard → **New +** → **PostgreSQL** → name `fastapi-demo-db`, database `fastapi_demo`. Wait until status is **Available**, then copy the **Internal Database URL** (or External if you deploy cross-region).
3. **Create the Redis store**: Dashboard → **New +** → **Key Value** → name `fastapi-demo-redis`, maxmemoryPolicy `noeviction`. Copy its **Internal Redis URL**.
4. **Create the web service**: Dashboard → **New +** → **Web Service** → Public Git Repository -> `Paste your repo URL` -> Connect -> Use `Docker`
5. Under the web service's **Environment Variables** tab, add:
   ```
   DATABASE_URL = <paste Postgres Internal URL>
   REDIS_URL    = <paste Redis Internal URL>
   ENVIRONMENT  = prod
   ```
   Render auto-converts the Postgres URL's `postgres://` scheme; the app also normalizes it as a safety net.
6. **Deploy** (Render builds the Dockerfile). `alembic upgrade head` runs automatically at container start, so the `notes` table is created for you — do **not** run migrations manually.
7. Open the service URL. `/health/ready` should report both stores `ok`.

### Notes
- Use **Internal URLs** for `DATABASE_URL` / `REDIS_URL` so traffic stays on Render's private network (faster, free egress).
- Render free web services **spin down after ~15 min idle**. The cold start costs the `/health/ready` check ~30 s; clicking a button right after wake-up may hit a still-warming container.
- **Blueprint** (`New > Blueprint`) requires a paid plan on Render, hence the manual flow above.

### Render free-tier limits & breakage notes
- Web service **spins down after ~15 min idle**. First request after spin-down waits ~30 s while the container wakes; the browser will show a slow page load (status pills stay red until it responds). Database + Redis stay warm.
- **Render Redis is 25 MB with `noeviction`**: writes fail (HTTP 503 from `/api/kv/*`) once memory is full. The index page surfaces the error as a red toast. Keep key/value and TTLs small.
- **PostgreSQL free tier is 1 GB** and expires after 90 days; export data before the deadline.
- outbound network egress and build minutes are also capped on the free plan; keep Docker layers cached (the Dockerfile already orders them for this).

---

## Deploy to Railway (free tier)

Railway's "free" plan is a one-time **$5 credit** (trial), not a permanent free tier. After the credit is exhausted, every service (web, Postgres, Redis) stops until you upgrade or add a paid plan. Plan accordingly.

1. In the Railway dashboard: **New Project** → Database → Postgresql → Wait to deploy
2. In the Railway dashboard newly created: Right click → Database → Redis
3. In the Railway dashboard newly created: Right click → **GitHub repo**, Input your fork -> Deploy
4. Click on `fast-api-stack` -> **Variables** -> Add variable -> Select URLS -> Add
5. Open the web service's **Variables** tab and set:
   ```
   DATABASE_URL = ${{Postgres.DATABASE_URL}}
   REDIS_URL    = ${{Redis.REDIS_URL}}
   ENVIRONMENT  = prod
   ```
   Railway resolves the `${{...}}` references at deploy time, so they always point at the provisioned plugins.
6. Open the generated domain (Settings → Domains → Generate).

### Railway free-tier (credit) limitations & breakage notes
- **$5 one-time credit**, not forever free. CPU, memory, egress and DB/Redis all burn credit. A small always-on service with a free Postgres + Redis plugin will typically last ~1–3 months on $5.
- **No spin-down savings**: unlike Render, Railway keeps services running while credit lasts, so there are no cold starts until funds run out.
- Once credit is exhausted: all services stop, requests time out, and `/health/ready` becomes unreachable. Data in the managed Postgres/Redis may be deleted after ~7 days if not migrated to a paid plan.
- **Port binding**: Railway injects `$PORT`; if you override `startCommand`, keep `--port $PORT`, otherwise health checks fail.

---

## Environment Variables

| Name           | Required | Example                                                    | Notes                                                    |
|----------------|----------|------------------------------------------------------------|----------------------------------------------------------|
| `DATABASE_URL` | Yes      | `postgresql+asyncpg://user:pass@host:5432/db`              | Auto-normalizes `postgres://` → `postgresql+asyncpg://` |
| `REDIS_URL`    | Yes      | `redis://localhost:6379/0`                                 | Passed through as-is                                     |
| `ENVIRONMENT`  | No       | `dev` / `prod`                                             | Defaults to `dev`                                        |

---

## Index Page Usage

The index page (`/`) has two side-by-side panels:

### PostgreSQL Panel (Left)
- **Form**: Enter a title and body, click **Add Note** → POSTs to `/api/notes`
- **List**: Shows all notes newest-first with title, body preview, timestamp, and **×** delete button
- **Verify**: Add a note → appears instantly. Delete → disappears. Refresh page → data persists.

### Redis Panel (Right)
- **Form**: Enter key, value, optional TTL (seconds), click **Set Key** → PUTs to `/api/kv/{key}`
- **List**: Shows all keys with value, remaining TTL, and **×** delete button
- **Verify**: Set a key → appears instantly. Wait for TTL → auto-expires. Delete → disappears.

### Top Bar
- Two status pills: **Postgres: ok/down** and **Redis: ok/down**
- Polled from `/health/ready` every 5 seconds
- Green = healthy, Red = down

All interactions use `fetch()` with direct DOM updates — no page reloads, no frameworks.

---

## Free-Tier Caveats

- **Render web service**: Spins down after ~15 min idle. Cold start ~30s. Database and Redis stay running.
- **Render Redis**: 25 MB maxmemory. `noeviction` policy means writes fail when full. Monitor usage.
- **Render Postgres**: 1 GB cap, expires after 90 days.
- **Railway**: One-time $5 credit. No perpetual free tier. Services stop when credit runs out; data deleted after ~7 days.
- **Railway has no spin-down**: services keep running while credit lasts (faster, but burns credit constantly).

---

## Troubleshooting

### "postgres:// scheme" error
**Symptom**: `sqlalchemy.exc.ArgumentError: Could not parse rfc1738 URL from string`  
**Cause**: Render/Heroku-style `postgres://` URLs.  
**Fix**: The app normalizes this automatically in `config.py`. Ensure `DATABASE_URL` is set correctly.

### Redis eviction after idle / out of memory
**Symptom**: Keys disappear unexpectedly; `/api/kv/*` returns 503.  
**Cause**: Free tier 25 MB limit with `noeviction` — writes fail when full.  
**Fix**: Monitor Redis memory in Render dashboard. Reduce data or upgrade plan.

### Port mismatch on Railway
**Symptom**: App fails to start, health checks fail.  
**Cause**: Railway assigns dynamic `$PORT`.  
**Fix**: `railway.toml` uses `startCommand` with `$PORT`. Ensure `uvicorn` binds to `0.0.0.0:$PORT`.

### Database password authentication failed on local
**Symptom**: `asyncpg.exceptions.InvalidPasswordError: password authentication failed`.  
**Fix**: Run `sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"` and verify `pg_hba.conf` allows `scram-sha-256` for `127.0.0.1/32`.

### Connection refused on localhost (WSL + PostgreSQL)
**Symptom**: `[Errno 111] Connection refused` from the app.  
**Cause**: PostgreSQL not listening on TCP.  
**Fix**: Verify `sudo -u postgres pg_ctl -D /var/lib/pgsql/data -l /tmp/pg.log start`, and check `port = 5432` in `/var/lib/pgsql/data/postgresql.conf`.

---

## Project Structure

```
app/
  main.py              # FastAPI app, lifespan, middleware, routes
  config.py            # Pydantic-settings config with URL normalization
  db.py                # SQLAlchemy async engine, session dependency
  redis_client.py      # Redis async client with lifespan management
  models.py            # SQLAlchemy Note model
  schemas.py           # Pydantic request/response models
  routers/
    health.py          # /health, /health/ready
    notes.py           # /api/notes CRUD
    kv.py              # /api/kv CRUD with SCAN
  templates/
    index.html         # Single HTML page
  static/
    app.js             # Vanilla JS for all interactions
    style.css          # Dark theme, <250 lines total
alembic/
  versions/0001_initial.py  # Notes table migration
  env.py               # Async Alembic config
Dockerfile             # Multi-stage, non-root, uv
docker-compose.yml     # Local dev with healthchecks
render.yaml            # Render Blueprint
railway.toml           # Railway deploy config
.env.example           # Local env template
```