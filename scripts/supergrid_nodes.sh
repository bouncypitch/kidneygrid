#!/usr/bin/env bash
# Connect one SuperNode per hospital to SuperGrid (federation @kdotmahesh/kidneygrid).
# Each node authenticates with its own key and reads only its own records file.
# Usage: scripts/supergrid_nodes.sh [start|stop]
set -euo pipefail
cd "$(dirname "$0")/.."
LOGS=.stack
HOSPITALS=(bay-general mission-medical valley-health peninsula-medical capitol-hospital golden-gate-courier)

# SuperGrid keeps a stopped node "active" for about a minute, so wait before reconnecting.
stop() { if pkill -f "flower-supernode --superlink=fleet-supergrid" 2>/dev/null; then echo "waiting 65s for SuperGrid to release the nodes..."; sleep 65; fi; }
if [[ "${1:-start}" == "stop" ]]; then stop; echo "stopped"; exit 0; fi

stop
mkdir -p "$LOGS"
# Model access for agents on the nodes; the key lives in a private, git-ignored file.
if [[ -f keys/flower_api_key ]]; then
  FLWR_MODEL_API_KEY="$(cat keys/flower_api_key)"
  export FLWR_MODEL_API_KEY
fi
port=9120
for h in "${HOSPITALS[@]}"; do
  # Separate FLWR_HOME per node: nodes sharing one machine must not share runtime folders.
  mkdir -p "$LOGS/home-$h"
  FLWR_HOME="$PWD/$LOGS/home-$h" uv run flower-supernode --superlink=fleet-supergrid.flower.ai:443 \
    --auth-supernode-private-key="keys/$h" \
    --port "$port" \
    --node-config "records=\"$PWD/data/nodes/$h.json\"" > "$LOGS/grid-$h.log" 2>&1 &
  port=$((port + 1))
done
sleep 6
echo "${#HOSPITALS[@]} hospital SuperNodes connecting to SuperGrid. Logs: $LOGS/grid-*.log"
