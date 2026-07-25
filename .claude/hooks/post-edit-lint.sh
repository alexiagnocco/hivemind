#!/usr/bin/env bash
# PostToolUse (Edit|Write): lint/validate edited files by extension
INPUT="$(cat)"
file=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty')
[ -z "$file" ] && exit 0
ext="${file##*.}"
case "$ext" in
  py)
    python -m py_compile "$file" 2>&1
    ;;
  md)
    # Frontmatter discipline for hive notes (files under the PARA folders)
    if echo "$file" | grep -qE '/(00-inbox|10-projects|20-areas|30-resources|40-archive|50-maps)/'; then
      head -1 "$file" | grep -q '^---' || echo 'WARNING: Missing frontmatter in hive note'
      grep -q "updated: $(date +%Y-%m-%d)" "$file" 2>/dev/null || echo "REMINDER: Bump updated: to today ($(date +%Y-%m-%d))"
    fi
    ;;
esac
