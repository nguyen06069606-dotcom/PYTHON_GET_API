# DummyJSON Product Sync

FastAPI service that imports products from `https://dummyjson.com/products` into PostgreSQL. DummyJSON's product `id` is the primary key; PostgreSQL `INSERT ... ON CONFLICT DO UPDATE` makes repeated and concurrent syncs idempotent. Raw upstream JSON is retained in `products.raw_data`.

## Deploy with Portainer (Ubuntu 24.04)

1. Copy this project to the server and create `.env` from `.env.example`. Generate distinct random values for `JWT_SECRET` and both database passwords; do not commit `.env`.
2. To use the bundled PostgreSQL container, set `DATABASE_URL` to `postgresql+psycopg://dummyjson_app:<same-password>@db:5432/dummyjson`. Deploy `compose.yaml` as a Portainer stack with the environment values supplied securely. The database has no published host port and keeps data in the `postgres_data` volume.
3. If using an existing PostgreSQL server/container, deploy `compose.external-db.yaml` instead and set `DATABASE_URL` to its reachable private hostname and credentials. For another container on the same Docker host, first attach that PostgreSQL container and this stack to the same user-defined Docker network and set `DATABASE_DOCKER_NETWORK` to that network's name. Allow network access only from the API container and use TLS for connections crossing an untrusted network (`?sslmode=require`).
4. Put a TLS reverse proxy (for example, the existing ingress) in front of the API. Port 8000 is bound to host loopback in the supplied compose file; change that binding only if the host firewall and proxy are configured.
5. For initial setup, set `BOOTSTRAP_ADMIN_USERNAME` and a unique `BOOTSTRAP_ADMIN_PASSWORD` (at least 12 characters). On first start the admin user is created; subsequent starts do not reset the password. Remove the bootstrap variables after creation. If the admin password is lost, perform a controlled password reset directly in the database/application maintenance process.

The first API container start applies versioned Alembic migrations, creates the built-in `reader`, `operator`, and `admin` roles, and optionally bootstraps an admin. Migrations are run before the web server starts.

## Authorization

All business endpoints require a short-lived signed JWT (`HS256`, issuer checked). Obtain one with `POST /auth/token` and JSON `{"username":"...","password":"..."}`, then send `Authorization: Bearer <access_token>`.

| Role | Permissions |
|---|---|
| reader | Read products and sync history |
| operator | Reader permissions and run product sync |
| admin | Operator permissions and create users/assign roles |

An admin creates users with `POST /admin/users`, e.g. `{"username":"etl_operator","password":"a-long-unique-password","roles":["operator"]}`. Role names are validated; passwords are Argon2-hashed. Inactive accounts and invalid/expired tokens are rejected. API docs are disabled by default. `GET /health/live` and `/health/ready` are unauthenticated for container health monitoring; readiness checks the DB.

## Use

- `POST /admin/sync`: pull every products page from DummyJSON and upsert by source id.
- `GET /products?skip=0&limit=50&category=beauty`: read stored products (maximum page size 200).
- `GET /admin/sync-runs`: inspect sync history.
- `POST /admin/users`: provision a user and roles.
- `GET /me`: inspect the current user's roles and permissions.

An unsuccessful upstream import is recorded in `sync_runs`; product rows are written only after all upstream pages are fetched. A CLI one-shot importer is also available inside the API container: `python -m sync`. To schedule it, use a Portainer cron container/task with the same image and environment, or call `POST /admin/sync` from a secured scheduler. No inbound database port is needed.

## Local run

Copy `.env.example` to `.env`, update all secrets, then run `docker compose up --build -d`. Check `docker compose logs -f api` and `GET http://127.0.0.1:8000/health/ready` from the host. For a standalone Python run, install `requirements.txt`, set environment variables, run `alembic upgrade head`, then `uvicorn app.main:app`.

## Operational notes

Back up PostgreSQL volumes with database-aware backups and test restores. Rotate JWT/database secrets deliberately. Use HTTPS at the reverse proxy, restrict that proxy and Docker networks, set resource limits in Portainer, and monitor container logs and free disk. The service does not configure TLS termination, automatic scheduled sync, or cloud firewall rules; those depend on the target server and Portainer setup.

