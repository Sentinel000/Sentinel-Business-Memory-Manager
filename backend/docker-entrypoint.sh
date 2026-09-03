#!/bin/sh
# Sentinel API container entrypoint.
#
#   serve            (default) run the API
#   migrate          run `alembic upgrade head`, then exit
#   <anything else>  exec'd verbatim — e.g. `python scripts/seed.py`
#
set -eu

: "${PORT:=8000}"
: "${WEB_CONCURRENCY:=1}"
: "${ENABLE_SCHEDULER:=false}"
: "${RUN_MIGRATIONS:=false}"
: "${LOG_LEVEL:=info}"
# The container is always behind a load balancer in these deployments, so
# X-Forwarded-* has to be trusted for request URLs and client IPs to be right.
# Narrow it to the proxy's subnet on a VPS where the port is directly reachable.
: "${FORWARDED_ALLOW_IPS:=*}"

is_true() {
    case "$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')" in
        1|true|yes|on) return 0 ;;
        *) return 1 ;;
    esac
}

# cwd is /app, which is what alembic.ini's relative `script_location` and
# `prepend_sys_path` both depend on.
run_migrations() {
    echo "sentinel: alembic upgrade head"
    alembic upgrade head
}

case "${1:-serve}" in
    migrate)
        run_migrations
        ;;

    serve)
        # Alembic takes no advisory lock, so two replicas starting together can
        # both attempt the same revision. Off by default: migrate as a separate
        # one-shot step (`docker run --rm <image> migrate`) before rolling the
        # new version out. RUN_MIGRATIONS=true is for single-instance deploys
        # where that extra step is not worth the ceremony.
        if is_true "$RUN_MIGRATIONS"; then
            run_migrations
        fi

        case "$WEB_CONCURRENCY" in
            ''|*[!0-9]*)
                echo "sentinel: WEB_CONCURRENCY must be a positive integer, got '$WEB_CONCURRENCY'" >&2
                exit 1
                ;;
        esac

        # APScheduler's BackgroundScheduler lives inside the process, so every
        # worker AND every replica fires its own chase cycle — each one
        # incrementing chase_count and minting reminders for the same tasks.
        # Exactly one process may own the schedule. Refuse the combination
        # rather than let it double-chase a real team.
        if is_true "$ENABLE_SCHEDULER" && [ "$WEB_CONCURRENCY" -ne 1 ]; then
            echo "sentinel: ENABLE_SCHEDULER=true requires WEB_CONCURRENCY=1." >&2
            echo "sentinel: to scale out, leave the scheduler off and drive" >&2
            echo "sentinel: POST /api/v1/admin/run-chase from a platform cron." >&2
            exit 1
        fi

        echo "sentinel: listening on :${PORT} (workers=${WEB_CONCURRENCY}, scheduler=${ENABLE_SCHEDULER})"

        # exec so uvicorn becomes PID 1 and receives SIGTERM directly. Without
        # it the shell swallows the signal and the platform hard-kills the
        # container on its grace timer instead of draining in-flight requests.
        exec uvicorn app.main:app \
            --host 0.0.0.0 \
            --port "$PORT" \
            --workers "$WEB_CONCURRENCY" \
            --log-level "$LOG_LEVEL" \
            --proxy-headers \
            --forwarded-allow-ips "$FORWARDED_ALLOW_IPS" \
            --timeout-graceful-shutdown 30
        ;;

    *)
        exec "$@"
        ;;
esac
