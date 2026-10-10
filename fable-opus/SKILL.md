---
name: fable-opus
description: "Run fable-mode execution discipline on Claude Opus — the top of the escalation ladder. Trigger when the user explicitly asks for thorough/systematic/\"deep work\" handling on Opus (\"fable on opus\", \"stage this on opus\", \"deep work mode, opus\"). When a task exceeds Opus's ceiling, report that to the user rather than escalating further."
---

# Fable Mode — Opus (v6, main-thread orchestration)

Family version: v6 (2026-10-10).

v4 removed the named-agent routing from v3. That design depended on custom agent
definitions (`fable-orchestrator`, `fable-worker-sonnet`, `fable-worker-haiku`,
`fable-verifier`) that do not exist on skill-only surfaces like Cowork — so every
invocation fell through to the fallback while the file still described the dead
path as primary, and the v3 structural guarantee never actually applied. The
fallback is now the only path, stated directly.

v5 change: this skill is now the top of the ladder. The Fable 5.1 runner was
removed from the skill set (its own benchmark measured zero correctness delta at
that tier), so escalation past Opus goes to the user, not to another runner.

v6 change (2026-10-10, cloud review): v5 told a spawned Opus worker to spawn its
own Sonnet/Haiku workers, but in the cloud runtime general-purpose subagents had
no Agent tool (Haiku and Sonnet checked; Opus unchecked). The worker's brief also
pasted fable-mode's rule that a spawned subagent spawns no subagents of its own,
plus fable-mode's double-check gate, so the gate could run twice. Fan-out now
starts from the main thread, the worker brief omits fable-mode steps 2 and 5, and
the gate runs once, on the main thread.

## Invocation gate

When the user names this skill — a slash command, or "fable on opus" in words —
RUN IT. Do not weigh whether the task looks big enough. The user's explicit
invocation IS the trigger; the cost call is theirs, not yours.

The "skip for single-pass tasks" judgment below governs only autonomous
triggering — this skill deciding on its own to fire. It never overrides an
explicit request. If you think the loop is overkill for what was asked, run it
anyway and say so afterward.

**Autonomous trigger only:** if a task has one obvious correct approach, fits in
a single pass, and the user did not ask for this skill, do it directly.

**Spawn authorization** (same rule as fable-mode): a slash command or the skill
named ("fable-opus", "fable on opus") authorizes spawning. A wording-only trigger
("stage this on opus", "deep work mode, opus") or an autonomous trigger does not:
run the fable-mode Core Loop inline on this thread, run double-check in its
self-check mode, and say so. If this thread is not on Opus, also say the Opus pin
was skipped and that a slash command gets the pinned run. Usage limit: same as
fable-mode — at the user's reported threshold, check in first.

## How to run it

1. **The main thread orchestrates.** Subagents may have no Agent tool of their
   own, so every spawn starts here.
   - **Main thread on Opus** (per its own model line) → run fable-mode Core Loop
     steps 1–4 on this thread at frontier-tier calibration. Spawn stage workers
     directly from here: `model: "sonnet"` for ordinary stage reasoning,
     `model: "haiku"` for bulk mechanical work. Opus tokens buy judgment and
     synthesis, not file-shuffling. Respect any user-set worker cap. Then go to
     step 3.
   - **Main thread below Opus, Agent tool offers `"opus"`** → spawn ONE worker
     with `subagent_type: "general-purpose"` and `model: "opus"`, briefed per
     step 2.
   - **No Agent tool** → say so and run the fable-mode Core Loop inline on this
     thread, sequentially — then go to step 5.

2. Brief the Opus worker with:
   - the user's task, verbatim
   - the output directory
   - relevant session context
   - any user-set limits (warning threshold, deadline)
   - from the **fable-mode** skill, copied **verbatim**: Core Loop steps 1, 3 and
     4, the domain patterns, and the operational rules. Do NOT paste step 2
     (delegation) or step 5 (the double-check gate).
   - the three execution-guardrails rules, inlined verbatim (below)
   - this instruction: "Run every stage yourself and spawn nothing — the main
     thread handles verifiers and the delivery gate. Return a report that lists
     the stages you ran, numbered, each with its artifact and the exact check
     that verified it, plus every stage you marked unverified and any scope you
     found but did not build."

3. **Wait for every result.** Spawns may run in the background even when
   foreground is requested. Do not merge, relay, or start the gate until every
   spawned worker has returned.

4. Relay: the result, every stage marked unverified, and any scope surfaced but
   not built. If the task is beyond Opus's capability, say so to the user
   plainly — this is the top of the ladder and there is no further tier to hand
   off to. That report must follow verify-before-flag: name what was attempted
   and where it failed, not a vague appeal to difficulty.

5. **Mandatory delivery gate — once, on the main thread.** Before presenting
   anything to the user, invoke the **double-check** skill on the finished
   deliverable. Never run it inside a worker.

   Close your own report to double-check with a literal line:

   ```
   FINAL-COLD-CHECK: yes | intermediates-only | no
   ```

   - `yes` — a fresh verifier checked the FINISHED deliverable cold. Then
     double-check runs the seam check only.
   - `intermediates-only` — verification happened at stage level but nothing
     checked the final write-up. Full panel runs.
   - `no` — no cold verification happened. Full panel runs.

   Emit the line honestly. A missing or wrong line makes the gate either
   redundant or absent. Do not skip the gate; the user relies on it instead of
   re-checking the work themselves.

## Execution guardrails (inline these into every worker briefing)

Copy these three rules into every worker briefing verbatim. Whether a spawned
subagent can load skills itself varies by surface (cloud subagents could,
2026-10-10); the inline copy is shorter than a skill load and works everywhere.

1. **Verify before flag.** Never report a problem that has not been confirmed
   present by a direct check — grep it, run it, read the source. Absence of
   evidence is not the finding. Web silence is never grounds for a warning
   about the user's own firsthand facts.
2. **Warning threshold.** Batch minor concerns. At three (or the user's set
   number), stop and surface all at once. A concern that independently meets
   the verify-before-flag bar and is material on its own does not wait.
3. **Find-and-replace safety.** Anchor sed/substring replaces on word
   boundaries (`\bword\b`), never bare. Grep for corrupted compound words after
   every pass.

## Known limitation

Delegation is still requested in prose, not enforced structurally. The
orchestrating thread has Write and Edit, so nothing stops it doing stage work
inline on Opus instead of spawning Sonnet/Haiku workers. Make that visible rather
than silent: the stage map names, per stage, which tier produced its artifact.
v3 tried to enforce delegation by removing Write from a named orchestrator agent;
that needs custom agent definitions, which skill-only surfaces cannot load.