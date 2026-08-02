#!/usr/bin/env python3
"""End-to-end stdio smoke test for the hivemind MCP server.

Boots the server through ``scripts/launch.sh`` (the same path ``.mcp.json``
uses, so the wrapper's env resolution is exercised too) and drives a real
JSON-RPC session over stdio: initialize → tools/list → hive_status →
hive_retrieve → hive_health.

The client keeps stdin OPEN until every expected response has been read.
stdio MCP servers begin shutdown on stdin EOF and cancel in-flight tool
calls — a one-shot ``printf ... | server`` pipe makes slow calls (first-call
embedding, warmup) silently vanish and the failure looks like a broken tool.
Never convert this back to a shell pipe.

Usage:
    python3 scripts/stdio-smoke.py [--timeout SECONDS] [--handshake-only]

Exit 0 on pass. On failure: one actionable line on stderr, exit 1.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import shlex
import subprocess
import sys
import threading
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
LAUNCH = SCRIPT_DIR / "launch.sh"


def _server_cmd() -> list[str]:
    """Command that boots the server under test.

    Defaults to ``bash launch.sh`` so the wrapper's env resolution is exercised,
    which is what .mcp.json actually runs. HIVEMIND_SMOKE_CMD overrides it for
    environments that have no launcher — notably inside the container image,
    where there is no uv and the venv is already on PATH:

        HIVEMIND_SMOKE_CMD='python -m hivemind' python scripts/stdio-smoke.py
    """
    override = os.environ.get("HIVEMIND_SMOKE_CMD", "").strip()
    if override:
        return shlex.split(override)
    return ["bash", str(LAUNCH)]


def _fail(step: str, reason: str, hint: str, stderr_tail: list[str]) -> None:
    for line in stderr_tail[-8:]:
        print(f"  server stderr: {line.rstrip()}", file=sys.stderr)
    print(f"stdio smoke FAIL at {step}: {reason} — {hint}", file=sys.stderr)
    raise SystemExit(1)


def _reader(stream, out: queue.Queue) -> None:
    for line in stream:
        out.put(line)
    out.put(None)  # EOF marker


def main() -> int:
    parser = argparse.ArgumentParser(description="hivemind stdio smoke test")
    parser.add_argument(
        "--timeout",
        type=float,
        default=90.0,
        help="per-response timeout in seconds (default 90; first uv run may cold-sync)",
    )
    parser.add_argument(
        "--handshake-only",
        action="store_true",
        help="stop after initialize (cheapest boot check)",
    )
    args = parser.parse_args()

    proc = subprocess.Popen(
        _server_cmd(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout_q: queue.Queue = queue.Queue()
    stderr_tail: list[str] = []
    threading.Thread(target=_reader, args=(proc.stdout, stdout_q), daemon=True).start()
    threading.Thread(
        target=lambda: stderr_tail.extend(proc.stderr), daemon=True
    ).start()

    def send(msg: dict) -> None:
        try:
            proc.stdin.write(json.dumps(msg) + "\n")
            proc.stdin.flush()
        except BrokenPipeError:
            _fail(
                "send",
                "server closed stdin (crashed on boot?)",
                "run: cd _meta/mcp-server-py && uv sync --extra dev, then retry",
                stderr_tail,
            )

    def read_response(expect_id: int, step: str) -> dict:
        """Block until the response with expect_id arrives; skip notifications."""
        while True:
            try:
                line = stdout_q.get(timeout=args.timeout)
            except queue.Empty:
                _fail(
                    step,
                    f"no response for id={expect_id} within {args.timeout:.0f}s",
                    "cold uv sync or embedding warmup can be slow — retry with --timeout 300",
                    stderr_tail,
                )
            if line is None:
                _fail(
                    step,
                    "server exited before responding (stdout EOF)",
                    "check server stderr above; "
                    "try: cd _meta/mcp-server-py && uv run python -m hivemind",
                    stderr_tail,
                )
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue  # non-protocol noise on stdout
            if msg.get("id") == expect_id:
                if "error" in msg:
                    _fail(
                        step,
                        f"JSON-RPC error: {msg['error'].get('message', msg['error'])}",
                        "the server booted but rejected the call — check tool name/params",
                        stderr_tail,
                    )
                return msg["result"]
            # else: notification or unrelated message — keep reading

    def call_tool(call_id: int, name: str, arguments: dict, step: str) -> dict:
        send(
            {
                "jsonrpc": "2.0",
                "id": call_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        result = read_response(call_id, step)
        if result.get("isError"):
            text = (result.get("content") or [{}])[0].get("text", "")
            _fail(
                step,
                f"tool returned isError: {text[:200]}",
                "inspect the tool output above",
                stderr_tail,
            )
        text = (result.get("content") or [{}])[0].get("text", "{}")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"_raw": text}

    checks = 0

    # 1. initialize — stdin stays open for the whole session
    send(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "hivemind-stdio-smoke", "version": "1.0"},
            },
        }
    )
    init = read_response(1, "initialize")
    info = init.get("serverInfo", {})
    print(f"smoke: initialize OK — {info.get('name', '?')} {info.get('version', '?')}")
    checks += 1
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    if args.handshake_only:
        proc.stdin.close()
        proc.wait(timeout=10)
        print(f"stdio smoke PASS ({checks}/1 checks, handshake only)")
        return 0

    # 2. tools/list
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = read_response(2, "tools/list").get("tools", [])
    names = {t["name"] for t in tools}
    for required in ("hive_status", "hive_retrieve", "hive_health"):
        if required not in names:
            _fail(
                "tools/list",
                f"tool {required} missing",
                "server registered an unexpected tool set",
                stderr_tail,
            )
    print(f"smoke: tools/list OK — {len(tools)} tools")
    checks += 1

    # 3. hive_status — reports the active embedding backend
    status = call_tool(3, "hive_status", {}, "hive_status")
    backend = (status.get("embedding_backend") or {}).get("name", "none")
    print(f"smoke: hive_status OK — state={status.get('state', '?')} backend={backend}")
    checks += 1

    # 4. hive_retrieve — ranked results over the corpus (may embed on first call)
    retrieve = call_tool(
        4,
        "hive_retrieve",
        {"query": "how should tool calls handle retries safely", "max_results": 3},
        "hive_retrieve",
    )
    results = retrieve.get("results", [])
    if not results:
        _fail(
            "hive_retrieve",
            "0 results over the seeded corpus",
            "manifest missing or empty — run the manifest build step, then retry",
            stderr_tail,
        )
    top = results[0]
    print(f"smoke: hive_retrieve OK — {len(results)} results, top={top.get('path', '?')}")
    checks += 1

    # 5. hive_health — metrics compute
    health = call_tool(5, "hive_health", {"window_days": 7}, "hive_health")
    k = health.get("K", health.get("k"))
    if k is None:
        _fail(
            "hive_health",
            "no K metric in response",
            "health computation failed — inspect output",
            stderr_tail,
        )
    print(f"smoke: hive_health OK — K={k} status={health.get('status', '?')}")
    checks += 1

    # Only now is EOF safe: every expected response has been read.
    proc.stdin.close()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
    print(f"stdio smoke PASS ({checks}/5 checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
