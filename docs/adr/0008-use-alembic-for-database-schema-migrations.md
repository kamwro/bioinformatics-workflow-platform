# ADR-0008: Use Alembic for database schema migrations

## Status

Accepted

## Date

2026-05-25

## Context

The MVP originally used SQLAlchemy `create_all()` during FastAPI startup. That
was enough for creating an empty local database, but it did not evolve existing
tables when the ORM model changed. A local PostgreSQL database created before
the `run_name` column existed failed during seeding because `create_all()` does
not add missing columns to existing tables.

## Decision

We will use Alembic to manage database schema changes.

The API will no longer auto-create tables by default. Local setup should run:

```bash
uv run alembic upgrade head
```

The first migration bootstraps the current `qc_runs` schema. If a local MVP
database already has an older `qc_runs` table, the migration adds and backfills
the current columns rather than requiring the developer to drop the database.

## Alternatives considered

### Keep startup `create_all()`

Rejected. It creates missing tables but does not apply schema changes to
existing tables.

### Add ad hoc startup schema patching

Rejected. It would hide schema evolution inside application startup and become
harder to reason about as the project grows.

### Use Alembic migrations

Accepted. Alembic is the standard migration tool for SQLAlchemy applications
and makes schema changes explicit, reviewable, and repeatable.

## Consequences

- Database setup has one extra explicit migration step.
- Existing local MVP databases can be upgraded without dropping metadata.
- Future schema changes should be added as Alembic revisions.
- `AUTO_CREATE_TABLES` remains only as a local escape hatch and is disabled by
  default.
