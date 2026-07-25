#!/usr/bin/env python3
"""Generate a compact hive brief for Claude Code session start hook."""

import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

HIVE_PATH = os.environ.get("HIVE_PATH", str(Path(__file__).resolve().parents[2]))
MANIFEST_PATH = os.path.join(HIVE_PATH, "_meta", "hive-manifest.json")
BUILD_SCRIPT = os.path.join(HIVE_PATH, "_meta", "scripts", "build-manifest.py")


def rebuild_manifest():
    """Rebuild manifest to ensure freshness."""
    try:
        subprocess.run(
            [sys.executable, BUILD_SCRIPT],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "HIVE_PATH": HIVE_PATH},
        )
    except Exception:
        pass


def generate_brief():
    """Generate a compact hive brief."""
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("Hivemind: manifest not found. Run: python _meta/scripts/build-manifest.py")
        return

    notes = manifest.get("notes", [])
    total = len(notes)

    # Domain counts
    domains = Counter(n.get("domain", "unset") for n in notes)

    # Inbox count
    inbox = sum(1 for n in notes if n["path"].startswith("00-inbox/") and n["title"] != "_README")

    # Active projects
    active_projects = [
        n["title"] for n in notes
        if n.get("type") == "project" and n.get("status") == "active"
    ]

    # Recent changes (7 days)
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    recent = [n for n in notes if n.get("updated", "") >= cutoff]
    recent_domains = Counter(n.get("domain", "unset") for n in recent)

    # Build brief
    lines = [f"Hivemind: {total} notes indexed."]

    if inbox:
        lines.append(f"Inbox: {inbox} items pending.")

    if active_projects:
        lines.append(f"Active projects: {', '.join(active_projects[:8])}")

    if recent:
        parts = [f"{d}:{c}" for d, c in sorted(recent_domains.items()) if d]
        lines.append(f"Last 7 days: {len(recent)} notes modified ({', '.join(parts)})")

    print(" | ".join(lines))


if __name__ == "__main__":
    rebuild_manifest()
    generate_brief()
