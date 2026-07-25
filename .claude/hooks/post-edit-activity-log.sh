#!/usr/bin/env bash
# PostToolUse (Edit|Write): append each edit to the session activity log
#
# Log format: `<iso-timestamp> | <absolute-file-path>`
# Powers the Stop-hook nudges and the wrap/handoff file-count read-outs.
# Reads JSON on stdin (current Claude Code hook shape).

set -u

HIVE_ROOT="${HIVE_PATH:-${CLAUDE_PROJECT_DIR:-$HOME/hive}}"
LOG="$HIVE_ROOT/_meta/session-activity.log"

INPUT="$(cat)"
[ -z "$INPUT" ] && exit 0

FP=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
[ -z "$FP" ] && exit 0

mkdir -p "$(dirname "$LOG")" 2>/dev/null
printf '%s | %s\n' "$(date -Iseconds)" "$FP" >> "$LOG"
exit 0
