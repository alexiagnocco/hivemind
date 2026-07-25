#!/usr/bin/env bash
# PreToolUse (Bash): block `git stash drop` when cwd is inside the vault
#
# Rationale: in-progress, untracked authoring (new skills, hooks, notes) often
# lives in the vault working tree. A `git stash -u` followed by a conflict on
# `git stash pop` and a later `git stash drop` silently destroys that authoring
# with no recovery path (unlike a tracked-file deletion the reflog can recover).

set -u

INPUT="$(cat)"
[ -z "$INPUT" ] && exit 0

TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
[ "$TOOL_NAME" != "Bash" ] && exit 0

CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null)
[ -z "$CMD" ] && exit 0

# Normalise whitespace so `git   stash   drop` still matches
NORMALISED=$(printf '%s' "$CMD" | tr -s '[:space:]' ' ')
if ! printf '%s' "$NORMALISED" | grep -qE '(^|[; &|])git stash drop($| |;|&|\|)'; then
  exit 0
fi

# Only block when cwd is under the vault root. Outside it, stash drop is fine.
VAULT_ROOT="${VAULT_PATH:-${CLAUDE_PROJECT_DIR:-$HOME/vault}}"
case "$CWD" in
  "$VAULT_ROOT"|"$VAULT_ROOT"/*) ;;
  *) exit 0 ;;
esac

cat <<'MSG' >&2
BLOCKED: `git stash drop` inside the vault can permanently destroy
untracked authoring (skills, hooks, notes). A stash created by
`git stash -u` takes live untracked work with it when dropped.

Before dropping, verify the stash holds nothing live:
  git stash show --include-untracked -p stash@{0}

Preferred pattern for vault rebases:
  git add .claude/skills/ .claude/hooks/ .
  git commit -m "WIP: protect untracked before rebase"
  git pull --rebase
  git reset --soft HEAD~1    # restore to working tree if you want

If you really need to drop, temporarily remove this hook from
.claude/settings.json, do the drop, and put it back.
MSG

# PreToolUse: non-zero exit denies the tool call; stderr is surfaced to Claude.
exit 2
