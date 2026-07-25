---
created: 2026-06-24
updated: 2026-06-28
tags:
  - mcp
  - devops
status: active
type: note
domain: work
parent: "[[50-maps/MOC-MCP-Gateway]]"
seed: demo
---

# Credential Handling in MCP Servers

Precedence: environment variable, then OS keychain, then nothing — fail loudly. Secrets never live in client config files, and "nothing" is a state the server must report honestly rather than paper over.

## The precedence, and why that order

```text
1. explicit env var        (operator intent, CI-friendly, always wins)
2. OS keychain / secrets   (developer machines, survives reboots, per-user)
3. absent                  (declared, visible, fails on first authenticated call)
```

Env-first matters because it is the only layer an operator can override without touching stored state — CI, containers, and one-off debugging all need that escape hatch. The keychain is the durable local default: per-user, encrypted at rest, and invisible to `git diff`. The resolution itself belongs in a launch wrapper, not in client config — config files don't expand `${VAR}`, so a config-file "secret" is either plaintext or a literal dollar-sign string ([[launch-wrapper-env-resolution]]).

## Why config files are disqualified

A secret in client config is plaintext in a file that gets committed, synced, pasted into bug reports, and copied between machines. The convenience is real and the blast radius is unbounded. The rule has no exceptions worth honoring: rotating one leaked token costs more than every minute the keychain lookup ever saved.

## Absence is a state, not an error — until it isn't

Some servers can do useful unauthenticated work (local reads, cached queries). Booting without a credential is therefore legitimate — but only if the absence is *visible*: log it at startup, expose it in the status surface, and let the first call that actually needs auth fail with a clean 401-class error that surfaces to the caller per [[auth-failure-semantics]]. The anti-pattern is the server that boots "fine," silently downgrades every authenticated capability, and lets the user discover the missing token by noticing the answers got worse.

## Operational hygiene

- Never log the credential — log its *presence*, its source layer, and (for rotation debugging) a short fingerprint.
- Treat scopes as part of the credential: a token with the wrong scope is a 403 waiting to happen; surface scope errors verbatim.
- Contract-test the resolution order itself — set both layers, assert env wins; set neither, assert the declared-absent path ([[mcp-server-testing-strategies]]).
