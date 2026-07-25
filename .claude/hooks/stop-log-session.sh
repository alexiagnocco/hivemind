#!/usr/bin/env bash
# Stop (async): log session metadata via Python.
# Always exit 0 — a missing script or logging failure must never block
# session shutdown (a non-zero Stop hook re-invokes the agent in a loop).
HIVE_ROOT="${HIVE_PATH:-$HOME/hive}"
LOGGER="$HIVE_ROOT/_meta/scripts/log-session.py"
[ -f "$LOGGER" ] && python3 "$LOGGER" "$(pwd)" 2>/dev/null
exit 0
