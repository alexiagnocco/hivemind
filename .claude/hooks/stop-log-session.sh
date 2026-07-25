#!/usr/bin/env bash
# Stop (async): log session metadata via Python
VAULT_ROOT="${VAULT_PATH:-${CLAUDE_PROJECT_DIR:-$HOME/vault}}"
python3 "$VAULT_ROOT/_meta/scripts/log-session.py" "$(pwd)" 2>/dev/null
