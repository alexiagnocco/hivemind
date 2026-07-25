---
created: 2026-06-18
updated: 2026-06-18
tags:
  - mcp
  - scripting
status: active
type: note
domain: work
parent: "[[50-maps/MOC-MCP-Gateway]]"
seed: demo
---

# Launch Wrapper Env Resolution

Client config files do not expand environment variables. Put `${TOKEN}` in an MCP config's env block and the server receives the literal string `${TOKEN}` — not the variable's value. The server then starts *successfully* with a garbage credential or path, and the failure surfaces later, somewhere else, wearing a different error's clothes.

## Why this bites so reliably

Every config format that *looks* like shell teaches the intuition that `${VAR}` interpolates. JSON config files are not shell. There is no substitution pass, no error for the unresolved reference, and no warning — the string is passed through faithfully, which is the worst outcome because everything appears to work. The same trap generalizes: absolute paths and home-directory assumptions baked into config break the moment the config runs on a different machine, a CI runner, or a sandbox.

## The pattern: a wrapper owns all resolution

Point the client config at a small launch script and give the script sole authority over env and path resolution:

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -z "${API_TOKEN:-}" ]; then
    API_TOKEN="$(secret-lookup my-service 2>/dev/null || true)"
fi
[ -n "${API_TOKEN:-}" ] && export API_TOKEN

cd "$PROJECT_DIR"
exec run-the-server
```

The config invokes the wrapper and nothing else. The wrapper derives the project root *from its own location* — not from `$HOME`, not from the client's working directory — reads real environment, falls back to a secrets store ([[credential-handling-in-mcp-servers]] for the precedence rules), and `exec`s the server so signals pass through cleanly.

## Verification, not faith

Two checks make the pattern trustworthy: the server logs (or exposes via a status tool) the *resolved* configuration at startup — which paths, which backend, credential present or absent — and the smoke test asserts on that surface rather than on "process started" ([[mcp-server-testing-strategies]]). A server that can report its own resolved config turns this whole class of bug from an archaeology project into a one-line diff.

stdio transport makes the wrapper doubly important: the server inherits its entire environment from whoever spawned it, and the wrapper is your only interception point ([[mcp-transport-tradeoffs]]).
