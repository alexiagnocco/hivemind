#!/usr/bin/env bash
# UserPromptSubmit: one-time reminder to run /boot at session start
SENTINEL=/tmp/hive-boot-reminded
if [ ! -f "$SENTINEL" ]; then
  echo "SESSION START: Run /boot to load full hive context (health + recall + project memory). End with /wrap."
  touch "$SENTINEL"
fi
