"""Score checker runs.  python3 score.py RUNS_DIR

Run files: RUNS_DIR/<arm>-r<N>-<part>.txt, one line per claim, e.g.
  J01a PASS|FAIL|UNVERIFIABLE (also accepts CONFIRMED/REFUTED) <evidence>
A panel's verdict on a claim is FAIL if any of its checkers failed it.
"""
import os, re, sys, glob, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import build

_, key, types, fams = build(None)
bad = {c for c, ok in key.items() if not ok}
good = set(key) - bad
runs = collections.defaultdict(lambda: collections.defaultdict(dict))  # arm -> run -> claim -> verdicts
for path in sorted(glob.glob(os.path.join(sys.argv[1], "*.txt"))):
    m = re.match(r"(.+)-r(\d+)-(.+)\.txt$", os.path.basename(path))
    if not m: continue
    arm, run = m.group(1), int(m.group(2))
    for line in open(path):
        v = re.match(r"\s*(J\d\d[ab])\s*[:\-—]?\s*(PASS|FAIL|UNVERIFIABLE|CONFIRMED|REFUTED)\b", line, re.I)
        if v:
            verdict = {"CONFIRMED": "PASS", "REFUTED": "FAIL"}.get(v.group(2).upper(), v.group(2).upper())
            prev = runs[arm][run].get(v.group(1))
            runs[arm][run][v.group(1)] = "FAIL" if "FAIL" in (prev, verdict) else (prev or verdict)

print(f"{len(key)} claims: {len(bad)} bad, {len(good)} good\n")
print(f"{'arm':14} {'run':>3} {'caught':>9} {'invented':>9} {'unverif':>8} {'unanswered':>10}")
miss_fam = collections.defaultdict(collections.Counter)
inv_claims = collections.defaultdict(collections.Counter)
disagree = collections.Counter(); nruns = 0
for arm in sorted(runs):
    for run in sorted(runs[arm]):
        v = runs[arm][run]; nruns += 1
        fails = {c for c, x in v.items() if x == "FAIL"}
        unv = {c for c, x in v.items() if x == "UNVERIFIABLE"}
        caught = len(bad & fails); invented = len(good & fails)
        print(f"{arm:14} {run:>3} {caught:>5}/{len(bad)} {invented:>5}/{len(good)} {len(unv):>8} {len(set(key) - set(v)):>10}")
        for c in bad - fails: miss_fam[arm][fams[c]] += 1
        for c in good & fails: inv_claims[arm][c] += 1
        for c in key:
            if (c in fails) != (c in bad): disagree[c] += 1
print("\nMissed bugs by family (summed over runs):")
for arm in sorted(miss_fam): print(f"  {arm}: {dict(miss_fam[arm])}")
print("Invented flaws (claim: runs):")
for arm in sorted(inv_claims): print(f"  {arm}: {dict(inv_claims[arm])}")
sus = [c for c, n in disagree.items() if nruns and n / nruns >= 0.75]
print("\nClaims most runs disagree with the key on (review as possible key errors):", sus or "none")
