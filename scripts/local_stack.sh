#!/usr/bin/env bash
# Start a local SuperLink plus one SuperNode per hospital (development only: no TLS).
# Usage: scripts/local_stack.sh [start|stop]
set -euo pipefail
cd "$(dirname "$0")/.."
LOGS=.stack
HOSPITALS=(bay-general mission-medical valley-health peninsula-medical capitol-hospital)

stop() {
  pkill -f "flower-superlink --insecure" 2>/dev/null || true
  pkill -f "flower-supernode --insecure" 2>/dev/null || true
}

if [[ "${1:-start}" == "stop" ]]; then stop; echo "stopped"; exit 0; fi

stop
mkdir -p "$LOGS"
uv run flower-superlink --insecure > "$LOGS/superlink.log" 2>&1 &
sleep 4
port=9110
for h in "${HOSPITALS[@]}"; do
  uv run flower-supernode --insecure --superlink 127.0.0.1:9092 --port "$port" \
    --node-config "records=\"$PWD/data/nodes/$h.json\"" > "$LOGS/$h.log" 2>&1 &
  port=$((port + 1))
done
sleep 4
echo "SuperLink + ${#HOSPITALS[@]} hospital SuperNodes running. Logs in $LOGS/"
