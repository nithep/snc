---
name: snc-agent-patterns
description: "Class-level: Grok Bot Agent/Loop/Graph → SNC PBX (5-Core, proxy 2323, quarantine refs). Load when SNC + agent/autonomy/loop/graph/quarantine."
version: 1.0.0
author: Hermes Agent
tags: [snc, agent-architecture, loop, graph, grok-bot, pbx, self-healing, quarantine]
---

# SNC Agent Patterns — Grok Bot → SNC Adaptation

When: SNC + agent autonomy / self-check loops / parallel graphs / 24/7 / Grok Bot / quarantine/re-scan.

## Source signals (this session)
- `.txt`: `Grok Bot. What It Is...` — agent = autonomous role (not chatbot); loop = self-check; graph = parallel workers; 24/7 cloud.
- Images: `HO5t8UXWsAAJrRf.jpg` (Agents→Loops→Graphs), `HQcF1B-XkAAEf7P.jpg` (multi-worker bot UI), `HQc2jRNWAAEXexT.jpg` (one job, many bots).
- Actions: `hermes skills trust` clear → `hermes update` v0.20.4→v0.21.0 → profile reset → repo `snc` SKILL.md quarantined (security scan).

## Pattern mapping
| Grok concept | SNC mapping |
| Agent (autonomous, holds role) | `pbx/snc_pbx_listener.py`: 24/7 session, `_heartbeat_loop` 30s `..VERS=`, auto-reconnect |
| Loop (self-check until bar clears) | Enhance `api/server.py`: loop over `ack_time_seconds` / `resolution_time_seconds` / `sla_breached`; retry/escalate if ACK>30s or RES>180s |
| Graph (many workers, one answer) | Parser (pbx) / DB (sqlite) / WebSocket / proxy `:2323` / dashboard (app); never parallel-connect `:23` |
| 24/7 cloud | Pi 4 (`ecs-agent`) + systemd (`snc-backend`, `snc-pbx-listener`) |
| Browser automation (no-API tools) | `:2323` handshake emulation (`..tcmd=`, `..VERS=`, `..PASS=`, `..EVNT=`) for Room Manager |

## Quarantine signal (durable)
Profile reset does NOT clear repo-bound `snc`; security scan flagged `.opencode/skills/snc/SKILL.md` → quarantined (`skill_view` refused). Fix: content change passes re-scan, or user `hermes curator adopt snc`. Do NOT treat as transient retry.

## Pitfalls (embedded)
1. PBX `:23` = ONE session only; parallel clients must use `:2323` proxy (SNC already handles).
2. `hermes update` blocked by running `hermes.exe` PID; close desktop/gateway first (`hermes gateway stop`).
3. User prefers Thai (operator docs), English (code/IDs), concise, UTF-8 strict; SSH key auth (`ecs-agent` `192.168.1.94`).
4. `hermes skills trust` clear = profile reset (skills preserved at `~/AppData/Local/hermes/skills/`); repo skills (`.opencode/skills/`) are separate and can be quarantined independently.

## References (session detail — see `references/`)
- `references/grok_bot_text.md` — condensed `.txt` (agent/loop/graph, 5 prompts, "name matters").
- `references/agent_diagram.md` — description of `HO5t8UXWsAAJrRf.jpg` (Agents→Loops→Graphs).
- `references/proxy_handshake.md` — `:2323` handshake order (`..tcmd=1` → `..VERS=` → `..PASS=` → `..EVNT=ALL`).
- `references/quarantine_note.md` — this session's `skills trust` + `update` v0.21.0 + quarantine event.

## Overlap / consolidation
`snc` (repo-bound, quarantined) overlaps architecture. Once un-quarantined, consolidate Agent/Loop/Graph subsection from this umbrella into `snc` SKILL.md; keep `references/quarantine_note.md` and `references/proxy_handshake.md` here.
