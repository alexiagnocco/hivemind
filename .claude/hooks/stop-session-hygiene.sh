#!/usr/bin/env bash
# Stop: per-session turn counter + cache-ratio nudges
# - increments ~/.claude/hook-state/<session_id>.state
# - at turn>=12: suggest /compact (once)
# - at turn>=20: strongly suggest /clear (once)
# - at cache-read ratio>=85%: warn context saturation (once)
# - output { "systemMessage": "..." } → invisible to user, visible to Claude

set -u

STATE_DIR="$HOME/.claude/hook-state"
mkdir -p "$STATE_DIR" 2>/dev/null

# Best-effort cleanup of state files older than 7 days
find "$STATE_DIR" -name '*.state' -type f -mtime +7 -delete 2>/dev/null || true

INPUT="$(cat)"
[ -z "$INPUT" ] && exit 0

SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // empty' 2>/dev/null)
STOP_HOOK_ACTIVE=$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)
STOP_REASON=$(printf '%s' "$INPUT" | jq -r '.stop_reason // empty' 2>/dev/null)
TRANSCRIPT=$(printf '%s' "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)

[ -z "$SESSION_ID" ] && exit 0
[ "$STOP_HOOK_ACTIVE" = "true" ] && exit 0

case "$STOP_REASON" in
  error|cancelled|interrupted|canceled) exit 0 ;;
esac

STATE_FILE="$STATE_DIR/$SESSION_ID.state"

if [ -f "$STATE_FILE" ]; then
  OLD=$(cat "$STATE_FILE" 2>/dev/null)
  TURN_COUNT=$(printf '%s' "$OLD" | awk -F'|' '{print $1+0}')
  FLAGS=$(printf '%s' "$OLD" | awk -F'|' '{print $2}')
else
  TURN_COUNT=0
  FLAGS=""
fi

TURN_COUNT=$((TURN_COUNT + 1))

# Compute cache-read ratio from the session transcript
RATIO=0
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  RATIO=$(jq -s '
    [.[] | select(.type == "assistant") | .message.usage // empty]
    | if length == 0 then 0
      else
        (map(.cache_read_input_tokens // 0) | add) as $cr
        | (map(.input_tokens // 0) | add) as $in
        | (map(.cache_creation_input_tokens // 0) | add) as $cc
        | ($cr + $in + $cc) as $total
        | if $total == 0 then 0 else (($cr * 100) / $total) | floor end
      end
  ' "$TRANSCRIPT" 2>/dev/null || echo 0)
fi
case "$RATIO" in
  ''|*[!0-9]*) RATIO=0 ;;
esac

has_flag() { printf '%s' "$FLAGS" | grep -q "$1"; }

NUDGE=""

if [ "$TURN_COUNT" -ge 20 ] && ! has_flag 'N20'; then
  FLAGS="${FLAGS}N20,"
  NUDGE="[session-hygiene] Turn ${TURN_COUNT} of this session. Strongly recommend /clear at the next natural stopping point — weave a brief suggestion into your next response. Context is growing; a fresh session will be faster and cheaper."
elif [ "$TURN_COUNT" -ge 12 ] && ! has_flag 'N12'; then
  FLAGS="${FLAGS}N12,"
  NUDGE="[session-hygiene] Turn ${TURN_COUNT} of this session. Suggest /compact at the next natural break if work so far can be summarized cleanly."
fi

if [ "$RATIO" -ge 85 ] && ! has_flag 'CACHE'; then
  FLAGS="${FLAGS}CACHE,"
  CACHE_MSG="[session-hygiene] Cache-read ratio is ${RATIO}% of total input tokens — context is saturated. Prefer /clear over /compact at the next natural break."
  if [ -n "$NUDGE" ]; then
    NUDGE="${NUDGE} ${CACHE_MSG}"
  else
    NUDGE="$CACHE_MSG"
  fi
fi

printf '%d|%s' "$TURN_COUNT" "$FLAGS" > "$STATE_FILE"

if [ -n "$NUDGE" ]; then
  jq -n --arg msg "$NUDGE" '{systemMessage: $msg}'
fi

exit 0
