---
name: fable-opus
description: "Run fable-mode execution discipline on Claude Opus — the top of the escalation ladder. Trigger when the user explicitly asks for thorough/systematic/\"deep work\" handling on Opus (\"fable on opus\", \"stage this on opus\", \"deep work mode, opus\"). When a task exceeds Opus's ceiling, report that to the user rather than escalating further."
---

# Fable Mode — Opus (v5, tool-routed)

v4 removed the named-agent routing from v3. That design depended on custom agent
definitions (`fable-orchestrator`, `fable-worker-sonnet`, `fable-worker-haiku`,
`fable-verifier`) that do not exist on skill-only surfaces like Cowork — so every
invocation fell through to the fallback while the file still described the dead
path as primary, and the v3 structural guarantee never actually applied. The
fallback is now the only path, stated directly.

v5 change: this skill is now the top of the ladder. The Fable 5.1 runner was
removed from the skill set (its own benchmark measured zero correctness delta at
that tier), so escalation past Opus goes to the user, not to another runner.

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

## How to run it

1. Confirm the runtime exposes the **Agent tool** with `"opus"` among its
   `model` options. If the Agent tool is absent, say so and run the fable-mode
   Core Loop inline on this thread, sequentially — then go to step 5.

2. Spawn a worker with `subagent_type: "general-purpose"` and `model: "opus"`.
   Brief it with:
   - the user's task, verbatim
   - the output directory
   - relevant session context
   - any user-set limits (warning threshold, worker cap, deadline)
   - the Core Loop, domain patterns, and operational rules copied **verbatim**
     from the **fable-mode** skill, which is installed alongside this one
   - the three execution-guardrails rules, inlined verbatim (below) — a spawned
     subagent cannot load skills

3. Instruct the worker to delegate its own artifact production one level down:
   `model: "sonnet"` for ordinary stage reasoning, `model: "haiku"` for bulk
   mechanical work. Opus tokens buy judgment, not file-shuffling. Keep
   delegation one level deep — workers do not spawn workers.

4. When it returns, relay: the result, every stage it marked unverified, and any
   scope it surfaced but did not build. If it reports the task beyond Opus's
   capability, say so to the user plainly — this is the top of the ladder and
   there is no further tier to hand off to. That report must follow
   verify-before-flag: name what was attempted and where it failed, not a vague
   appeal to difficulty.

5. **Mandatory delivery gate:** before presenting anything to the user, invoke
   the **double-check** skill on the finished deliverable.

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

A spawned subagent cannot load the execution-guardrails skill. Copy these three
rules into every briefing verbatim.

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

Delegation is requested in prose, not enforced structurally. A general-purpose
worker has Write and Edit, so nothing stops it doing the work inline instead of
spawning its own workers — the exact failure v3 tried to fix by removing Write
from a named orchestrator agent. That fix required custom agent definitions this
surface cannot load, so it never took effect.

Available tightening if audits show workers running everything inline: require
the stage plan as a numbered list with one named artifact per stage in the
returned report, so an inline run is visible in the output rather than silent.
Prose-level "you may spawn workers" reliably does not survive contact.