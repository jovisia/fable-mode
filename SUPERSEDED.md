# Superseded

Status as of 2026-10-10. The live skill set is **v6**:

| Skill | File |
|---|---|
| `fable-mode` | `SKILL.md` |
| `fable-opus` | `fable-opus/SKILL.md` |
| `fable-sonnet` | `fable-sonnet/SKILL.md` |
| `double-check` | `double-check/SKILL.md` |
| `execution-guardrails` | `execution-guardrails/SKILL.md` |

Each live file carries a `Family version:` line under its title, so a copy can be dated
with one grep.

## What v6 replaced, and why

| Item | Superseded by | Why |
|---|---|---|
| `agents/` (fable-orchestrator, fable-worker-sonnet, fable-worker-haiku, fable-verifier), `V3-CHANGES.md` | v4 tool-routed runners | Custom agent definitions do not load on skill-only surfaces (Cowork, claude.ai), so v3 routing fell through to its fallback there. See the v4 note in `fable-opus/SKILL.md`. |
| `fable-fable/` | v5 | Removed from the skill set: its own benchmark (`BENCHMARK-2026-09-02.md`) measured zero correctness delta on Fable 5.1. Ladder top is Opus; past Opus, gaps go to the user. |
| v5 runner text (commit "Snapshot installed v5 skill set") | v6 | Cloud review 2026-10-10: spawn authorization, main-thread fan-out for fable-opus, wait for every spawned result, default checker panel 1 Haiku + 1 Sonnet, one re-check round. |

## Still in the repo, not superseded yet

- `fable-haiku/` is still the v3 router: it routes to the `fable-worker-haiku` agent and
  falls back to inline mode without it. Keep or retire is the owner's call.
- `install.sh` still copies `agents/`, because `fable-haiku` uses `fable-worker-haiku`
  in Claude Code. It no longer installs `fable-fable`. An existing install keeps
  `~/.claude/skills/fable-fable/` until it is removed by hand.

Superseded files stay in the repo for history. Install only the live set above.
