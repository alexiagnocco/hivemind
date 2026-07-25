#!/usr/bin/env bash
# UserPromptSubmit: mark session activity boundary
VAULT_ROOT="${VAULT_PATH:-${CLAUDE_PROJECT_DIR:-$HOME/vault}}"
echo "--- SESSION $(date -Iseconds) | $(pwd) ---" >> "$VAULT_ROOT/_meta/session-activity.log"
