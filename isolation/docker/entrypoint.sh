#!/usr/bin/env bash
# entrypoint.sh — run a single scenario inside the container and copy results out.
#
# Environment variables:
#   SCENARIO_ID      — scenario ID to run (e.g. A1_direct_01)
#   ISOLATION_MODE   — isolation mode string to tag results with (e.g. docker)
#
# Results are written to /results/ which should be a mounted host volume.

set -euo pipefail

: "${SCENARIO_ID:?SCENARIO_ID environment variable must be set}"
: "${ISOLATION_MODE:=docker}"

echo "[entrypoint] Starting scenario=${SCENARIO_ID} mode=${ISOLATION_MODE}"

python -m agentseceval.experiments.orchestrator \
    --config agentseceval/experiments/configs/baseline.yaml \
    --scenario "${SCENARIO_ID}" \
    --mode "${ISOLATION_MODE}"

# Copy any result files to the mounted volume (results are already written there
# by LogCollector, but this ensures visibility even if RESULTS_DIR differs).
if [ -d "/app/results" ] && [ "/app/results" != "/results" ]; then
    cp -r /app/results/. /results/ 2>/dev/null || true
fi

echo "[entrypoint] Done."
