# Results

## Round 2 (2026-10-11): 110 claims, 39 bad, 3 runs per arm

| Arm | Setup | Caught (each run) | Invented (each run) | Subagent tokens per run |
|---|---|---|---|---|
| A | plain "review these" prompt, Opus | 39/39 ×3 | 0/71 ×3 | ~91K |
| B | double-check self-check mode, Opus | 39/39 ×3 | 0/71 ×3 | ~96K |
| C | v6 panel: 1 Haiku (98 mechanical claims) + 1 Sonnet (12 logic claims) | 39/39 ×3 | 0/71 ×3 | ~205K |
| D | v5 panel: 2 Haiku (49 + 49) + 1 Sonnet | 39/39 ×3 | 0/71 ×3 | ~305K |

D reused C's Sonnet outputs: the logic checker is configured the same way in v5 and v6.

The answer-key audit found 0 mismatches, and no run disagreed with the key on any claim.

**Reading:** saturated on all 12 runs. Every checker, Haiku included, wrote a script and
recomputed the figures from the files. With code execution available, every bug that
recomputation exposes is caught, whatever the checker setup. On this kind of work, the
panel's structure changes cost, not accuracy: one Opus pass did the same job for about a
third of the v5 panel's tokens.

## Round 1 (2026-10-11): 48 claims, 12 bad, 1 run per arm

Every arm caught 12/12 with 0 invented flaws. The v6 panel matched the v5 panel at about
two-thirds of the tokens. Two answer-key defects were found by the checkers and excluded.

## What would discriminate next

Bugs that recomputation cannot expose:
- judgment calls over long prose
- a claim that is true but answers a different question
- a source that contradicts itself
- outputs too large to fit one checker's context
- runs with no code execution
