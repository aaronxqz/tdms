# TDMS — Product Roadmap

**Document Version:** 1.0  
**Last Updated:** 2026-04-12  
**Current Release:** v1.0.0  
**Next Planned Release:** v2.0.0

---

## Overview

This document outlines the planned enhancements and open engineering questions identified at the close of the v1.0.0 release. Items are grouped by theme and prioritised within each section.

---

## v2.0.0 — Planned Enhancements

### 1. Deployment Infrastructure — Frontend Serving and Port Management

#### 1.1 Local Development Port Release on Process Exit

**Current behaviour:** When the Vite development server is terminated with `Ctrl + C`, the operating system does not immediately release the bound port (default `5173`). Subsequent attempts to restart the server may fail with an `EADDRINUSE` error until the port is freed.

**Root cause:** This is a known behaviour of Node.js servers on Linux/WSL environments. The TCP socket enters a `TIME_WAIT` state and is held by the kernel for a short grace period after the process exits.

**Planned resolution:**
- Introduce a `Makefile` target (`make dev`) that wraps the `npm run dev` command with a pre-flight check and automatic port teardown using `fuser -k <port>/tcp` on SIGINT/SIGTERM.
- Alternatively, configure Vite with `server.strictPort: true` and document the manual cleanup command (`npx kill-port 5173`) in the developer setup guide.

#### 1.2 Production Deployment — Static Frontend Serving on AWS

In a production environment, the Vite development server is **never used**. The frontend is compiled into a set of static assets (`npm run build` → `dist/`) and served by a dedicated web server or CDN. The recommended AWS deployment model is as follows:

| Layer | Service | Notes |
|---|---|---|
| Frontend | AWS CloudFront + S3 | Static assets distributed globally via CDN. Zero port concerns; CloudFront terminates HTTPS. |
| Backend API | AWS Elastic Beanstalk or ECS (Fargate) | Containerised FastAPI served by Uvicorn behind an Application Load Balancer. |
| Database | AWS RDS (PostgreSQL) | Managed, multi-AZ PostgreSQL instance. |
| Environment config | AWS Secrets Manager | Replaces local `.env` files. |

Because the frontend is served as static files (HTML, CSS, JS), there is no persistent Node.js process in production and therefore no port management concern. CloudFront handles all inbound connections and scales horizontally without any manual port configuration.

---

### 2. Task Chunk Lifecycle — Hard Delete Capability

**Current behaviour:** Task chunks in `COMPLETED` or `FAILED` state are retained in the database and are searchable via `GET /tasks/search`. However, there is no mechanism to permanently remove a task chunk from the system, regardless of its lifecycle state.

**Planned additions:**

#### 2.1 Delete Endpoint

Introduce a `DELETE /tasks/{chunk_id}` endpoint that permanently removes a task chunk and all associated status history records (enforced by the existing `CASCADE` constraint on `status_history.chunk_id`).

**Behaviour matrix:**

| Current Status | Delete Behaviour |
|---|---|
| `OK` / `BREACH` / `BREACH_ACTION` (unassigned) | Deleted immediately. |
| `IN_PROGRESS` (assigned) | Deletes the record and, if a `calendar_event_id` is present, issues a `DELETE` to the Google Calendar API to remove the corresponding event. |
| `COMPLETED` / `FAILED` | Deleted permanently from the audit log. This action is irreversible. |

#### 2.2 Soft Delete vs. Hard Delete

The v1.0.0 schema includes an `is_archived` boolean column on `TaskChunk`. In v2.0.0, the following distinction will be formalised:

- **Soft delete (archive):** Sets `is_archived = true`. The chunk is hidden from all list views and the dashboard but remains queryable by passing `include_archived=true` to the search endpoint. Suitable for preserving audit history.
- **Hard delete:** Permanently removes the row and all cascaded history. Intended for data hygiene or user-requested erasure.

A frontend confirmation dialog will be required before executing either operation to prevent accidental data loss.

---

### 3. Administrative Access — Database and Application Management

#### 3.1 Connecting to the PostgreSQL Database Directly

As the system operator, you have full access to the PostgreSQL instance via the `psql` CLI or a GUI tool such as `pgAdmin`. Use the credentials defined in your `.env` file (which correspond to the `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` values in `docker-compose.yml`).

**Connecting via psql (local Docker instance):**

```bash
# From within the running Docker container
docker exec -it tdms_db psql -U <POSTGRES_USER> -d <POSTGRES_DB>

# Or directly if PostgreSQL client tools are installed on the host
psql -h localhost -p 5432 -U <POSTGRES_USER> -d <POSTGRES_DB>
```

**Useful psql commands:**

| Command | Purpose |
|---|---|
| `\dt` | List all tables |
| `\d task_chunks` | Show the schema of the `task_chunks` table |
| `SELECT * FROM task_chunks;` | View all task chunk records |
| `SELECT * FROM status_history WHERE chunk_id = 'REF-0001';` | View audit trail for a specific chunk |
| `\q` | Quit psql |

#### 3.2 Restarting the Application

**Backend (FastAPI + Uvicorn):**
```bash
# If running via Docker Compose
docker compose restart backend

# If running directly in the terminal (with venv activated)
# Stop with Ctrl+C, then re-run:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Database only:**
```bash
docker compose restart db
```

**Full stack restart:**
```bash
docker compose down && docker compose up -d
```

**Important:** Because `main.py` calls `Base.metadata.create_all()` on startup, restarting the backend does not destroy any data. Existing tables are preserved; only missing tables are created.

#### 3.3 Planned: Administrative API and Role-Based Access Control (RBAC)

In v1.0.0, the API has no authentication layer — all endpoints are accessible to anyone who can reach the server. This is acceptable for single-user local deployment but is not suitable for multi-user or internet-facing deployment.

**Planned for v2.0.0:**
- Introduce JWT-based authentication (`python-jose`, `passlib`) for all API endpoints.
- Define two roles:
  - **User:** Can only read and modify their own task chunks and goals.
  - **Admin:** Can read all records across all users, delete any task chunk, and manage user accounts.
- Protect admin-only endpoints with a role dependency (`Depends(require_admin)`).
- Add a `GET /admin/users` and `GET /admin/tasks` endpoint for administrative oversight.

---

## Summary Table

| # | Theme | Priority | Target Release |
|---|---|---|---|
| 1.1 | Local dev port release on Ctrl+C | Low | v2.0.0 |
| 1.2 | AWS production deployment architecture | Medium | v2.0.0 |
| 2.1 | `DELETE /tasks/{chunk_id}` endpoint | High | v2.0.0 |
| 2.2 | Soft delete (archive) vs. hard delete | Medium | v2.0.0 |
| 3.3 | JWT authentication and RBAC | High | v2.0.0 |

---

## Open Questions

- Should completed and failed task chunks be retained indefinitely by default, or should a configurable retention policy (e.g., auto-archive after 90 days) be introduced?
- For multi-user deployment, should each user have an isolated goal registry, or should goals be shared across the organisation with per-user task chunk assignment?
- Should the `DELETE /tasks/{chunk_id}` endpoint be exposed in the standard REST API or restricted to an admin-only sub-router?
