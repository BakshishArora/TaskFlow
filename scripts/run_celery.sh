#!/usr/bin/env bash
set -euo pipefail

UV="${UV:-uv}"

"$UV" run celery -A taskflow.celery_app worker --loglevel=info &
WORKER_PID=$!
trap 'kill "$WORKER_PID" 2>/dev/null || true' EXIT

sleep 3
"$UV" run python -m taskflow.scripts.demo_notification
sleep 3