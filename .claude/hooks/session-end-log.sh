#!/usr/bin/env bash
# SessionEnd: append session end record
VAULT_ROOT="${VAULT_PATH:-${CLAUDE_PROJECT_DIR:-$HOME/vault}}"
echo "SESSION_END $(date -Iseconds) | $(pwd) | reason=$CLAUDE_SESSION_END_REASON" >> "$VAULT_ROOT/_meta/session-end.log"
