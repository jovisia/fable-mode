# Checker-only bench

Tests **checkers**, not builders. Suggested on Reddit: give every checker version the same
mix of correct and deliberately broken outputs, and score **missed bugs** separately from
**invented flaws**.

```
python3 gen.py OUT            # fixtures + items.json (110 claims, 39 with one planted bug)
python3 audit_key.py OUT      # independent re-derivation of the answer key from the fixture files
# run each checker arm; each writes OUT_RUNS/<arm>-r<N>-<part>.txt, one verdict line per claim
python3 score.py OUT_RUNS     # caught / invented / unverifiable per arm and run; panels = union of FAILs
```

The key is never written next to the items. `score.py` rebuilds it in memory from `gen.py`.

Bug families: week-boundary off-by-one, superseded or region-scoped price errata, returns
ignored, cases read as units, the documented duplicate row counted, truncated rounding,
swapped rank order, a false "no returns", hedges escalated or confirmed facts demoted, and
an unreleased changelog version reported as installed. Controls include a real 480-unit
outlier, an item exactly at par, a release candidate, and revenue figures that are right only
with the errata applied.

See `RESULTS.md`.
