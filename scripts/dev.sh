#!/usr/bin/env bash
set -euo pipefail

cmd="${1:-up}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNDIR="$ROOT/.apicred-dev"
LOGDIR="$RUNDIR/logs"

mkdir -p "$LOGDIR"

backend_pid_file="$RUNDIR/backend.pid"
frontend_pid_file="$RUNDIR/frontend.pid"

backend_log="$LOGDIR/backend.log"
frontend_log="$LOGDIR/frontend.log"

pid_from_port() {
  local port="$1"
  if ! command -v ss >/dev/null 2>&1; then
    return 0
  fi
  ss -ltnpH "sport = :$port" 2>/dev/null | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | head -n1 || true
}

wait_for_port_pid() {
  local port="$1"
  local timeout_seconds="${2:-10}"
  local deadline=$((SECONDS + timeout_seconds))
  while (( SECONDS < deadline )); do
    local pid
    pid="$(pid_from_port "$port")"
    if [[ -n "$pid" ]] && is_pid_running "$pid"; then
      echo "$pid"
      return 0
    fi
    sleep 0.2
  done
  return 1
}

is_pid_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

is_pid_listening_on_port() {
  local pid="$1"
  local port="$2"
  local port_pid
  port_pid="$(pid_from_port "$port")"
  [[ -n "$pid" ]] && [[ -n "$port_pid" ]] && [[ "$pid" == "$port_pid" ]]
}

read_pid() {
  local file="$1"
  [[ -f "$file" ]] && cat "$file" || true
}

stop_pidfile() {
  local name="$1"
  local file="$2"
  local pid
  pid="$(read_pid "$file")"
  if [[ -z "$pid" ]]; then
    return 0
  fi
  if is_pid_running "$pid"; then
    echo "Stopping $name (pid $pid)"
    kill "$pid" 2>/dev/null || true
    for _ in {1..25}; do
      if ! is_pid_running "$pid"; then
        break
      fi
      sleep 0.2
    done
    if is_pid_running "$pid"; then
      echo "Force killing $name (pid $pid)"
      kill -9 "$pid" 2>/dev/null || true
    fi
  fi
  rm -f "$file"
}

stop_port() {
  local name="$1"
  local port="$2"
  local pid_file="$3"
  local pid
  pid="$(read_pid "$pid_file")"
  if [[ -z "$pid" ]]; then
    pid="$(pid_from_port "$port")"
  fi
  if [[ -z "$pid" ]]; then
    return 0
  fi
  if is_pid_running "$pid"; then
    echo "Stopping $name on port $port (pid $pid)"
    kill "$pid" 2>/dev/null || true
    for _ in {1..25}; do
      if ! is_pid_running "$pid"; then
        break
      fi
      sleep 0.2
    done
    if is_pid_running "$pid"; then
      echo "Force killing $name (pid $pid)"
      kill -9 "$pid" 2>/dev/null || true
    fi
  fi
  rm -f "$pid_file"
}

start_backend() {
  local existing
  existing="$(read_pid "$backend_pid_file")"
  if [[ -n "$existing" ]] && is_pid_running "$existing"; then
    echo "Backend already running (pid $existing)"
    return 0
  fi
  local port_pid
  port_pid="$(pid_from_port 8001)"
  if [[ -n "$port_pid" ]] && is_pid_running "$port_pid"; then
    echo "Backend already running on :8001 (pid $port_pid)"
    echo "$port_pid" >"$backend_pid_file"
    return 0
  fi
  local backend_dir="$ROOT/backend"
  if [[ ! -d "$backend_dir" ]]; then
    echo "Backend directory not found: $backend_dir" >&2
    exit 1
  fi
  echo "Starting backend on :8001"
  (
    cd "$backend_dir"
    # Detect backend type: Python or Node.js (adjust as needed)
    if [[ -f "pyproject.toml" ]]; then
      nohup python3 -m app >"$backend_log" 2>&1 &
    elif [[ -f "package.json" ]]; then
      nohup npm run dev >"$backend_log" 2>&1 &
    else
      echo "Unknown backend type in $backend_dir" >&2
      exit 1
    fi
    if listener_pid="$(wait_for_port_pid 8001 60)"; then
      echo "$listener_pid" >"$backend_pid_file"
    else
      echo $! >"$backend_pid_file"
    fi
  )
}

start_frontend() {
  local existing
  existing="$(read_pid "$frontend_pid_file")"
  if [[ -n "$existing" ]] && is_pid_running "$existing"; then
    if is_pid_listening_on_port "$existing" 3000; then
      echo "Frontend already running (pid $existing)"
      return 0
    fi
    echo "Removing stale PID for frontend (pid $existing, expected :3000)"
    rm -f "$frontend_pid_file"
  fi
  local port_pid
  port_pid="$(pid_from_port 3000)"
  if [[ -n "$port_pid" ]] && is_pid_running "$port_pid"; then
    echo "Frontend already running on :3000 (pid $port_pid)"
    echo "$port_pid" >"$frontend_pid_file"
    return 0
  fi
  echo "Starting frontend"
  (
    cd "$ROOT/frontend"
    nohup npm run dev >"$frontend_log" 2>&1 &
    if listener_pid="$(wait_for_port_pid 3000 30)"; then
      echo "$listener_pid" >"$frontend_pid_file"
    else
      echo $! >"$frontend_pid_file"
    fi
  )
}

status() {
  local bp fp
  bp="$(read_pid "$backend_pid_file")"
  fp="$(read_pid "$frontend_pid_file")"
  if [[ -z "${bp:-}" ]] || ! is_pid_running "${bp:-0}"; then bp="$(pid_from_port 8001)"; fi
  if [[ -z "${fp:-}" ]] || ! is_pid_running "${fp:-0}"; then fp="$(pid_from_port 3000)"; fi
  echo "Repo: $ROOT"
  echo "Run dir: $RUNDIR"
  echo
  printf "%-10s %s\n" "backend" "${bp:-<none>}"; echo "  - $( [[ -n "${bp:-}" ]] && is_pid_running "${bp:-}" && is_pid_listening_on_port "${bp:-}" 8001 && echo running || echo stopped )"
  printf "%-10s %s\n" "frontend" "${fp:-<none>}"; echo "  - $( [[ -n "${fp:-}" ]] && is_pid_running "${fp:-}" && is_pid_listening_on_port "${fp:-}" 3000 && echo running || echo stopped )"
  echo
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp | grep -E ':(3000|8001)\\b' || true
  fi
}

logs() {
  echo "Tail logs (Ctrl+C to stop):"
  echo "- $backend_log"
  echo "- $frontend_log"
  echo
  tail -n 80 -f "$backend_log" "$frontend_log"
}

healthcheck() {
  local ok=0
  local backend_tries=100
  local frontend_tries=20
  for i in $(seq 1 "$backend_tries"); do
    curl -fsS http://127.0.0.1:8001/health >/dev/null && break
    sleep 0.2
  done
  curl -fsS http://127.0.0.1:8001/health >/dev/null && echo "8001 OK" || { echo "8001 FAIL"; ok=1; }
  for i in $(seq 1 "$frontend_tries"); do
    curl -fsS "http://127.0.0.1:3000/" >/dev/null && break
    sleep 0.2
  done
  curl -fsS "http://127.0.0.1:3000/" >/dev/null && echo "3000 OK" || { echo "3000 FAIL"; ok=1; }
  return "$ok"
}

case "$cmd" in
  up)
    start_backend
    start_frontend
    echo
    status
    echo
    echo "URLs:"
    echo "- Backend:  http://localhost:8001/health"
    echo "- Frontend: http://localhost:3000/"
    echo
    echo "Logs: $LOGDIR (or run: scripts/dev.sh logs)"
    if command -v curl >/dev/null 2>&1; then
      echo
      echo "Health check:"
      healthcheck || true
    fi
    ;;
  down|stop)
    stop_port "frontend" 3000 "$frontend_pid_file"
    stop_port "backend" 8001 "$backend_pid_file"
    pkill -f "npm run dev" 2>/dev/null || true
    pkill -f "python3 -m app" 2>/dev/null || true
    echo "Stopped."
    ;;
  status)
    status
    ;;
  logs)
    logs
    ;;
  health)
    healthcheck
    ;;
  *)
    echo "Usage: scripts/dev.sh {up|down|status|logs|health}" >&2
    exit 2
    ;;
esac
