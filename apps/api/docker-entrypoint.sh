#!/usr/bin/env sh
set -e

# Apply database migrations before starting the app. Idempotent; safe to run
# on every boot. If the DB isn't reachable yet, Alembic will error and the
# container restarts (Coolify/Compose retry) until the db healthcheck passes.
echo "Running database migrations (alembic upgrade head)..."
alembic upgrade head

echo "Starting API: $*"
exec "$@"
