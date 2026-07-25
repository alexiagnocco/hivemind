#!/usr/bin/env bash
# PreToolUse (Bash): block deletion of active hive notes — archive them instead
#
# Hive notes carry backlinks, outlinks, and citation history; an outright `rm`
# breaks the link graph and loses context that may still be retrieved through
# MemRL / hive_retrieve. The archive-move discipline keeps the link target
# resolvable (40-archive/ stays in the manifest) while marking the note inactive.
#
# Reads JSON on stdin (current Claude Code hook shape).

set -u

INPUT="$(cat)"
[ -z "$INPUT" ] && exit 0

TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[ "$TOOL_NAME" != "Bash" ] && exit 0

CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
[ -z "$CMD" ] && exit 0

# Match `rm ... <PARA-dir>/... .md` where the target is an active note (not
# already under 40-archive/). Deleting something already archived is fine.
if printf '%s' "$CMD" | grep -qE '(^|[^a-zA-Z_])rm([[:space:]]|$).*/(00-inbox|10-projects|20-areas|30-resources|50-maps)/.*\.md' \
   && ! printf '%s' "$CMD" | grep -q '40-archive'; then
  cat <<'MSG' >&2
BLOCKED: Never `rm` active hive notes — move them to 40-archive/ instead.

Hive notes carry backlinks, outlinks, and citation history. A bare `rm`
breaks the link graph and loses context that may still be retrieved via
hive_retrieve or MemRL scoring. Archiving preserves the link target.

Preferred:
  mv <note>.md 40-archive/<YYYY-MM-DD>-<note>.md

If the note really must go, set frontmatter `status: archived` and
`updated: <today>`, then leave it in place — a future /prune sweep will
handle final disposition.

Override (only if intentionally purging a known-safe file): temporarily
remove this hook entry from .claude/settings.json.
MSG
  exit 2
fi

exit 0
