"""Independent answer-key audit. Re-derives every claim's truth from the fixture FILES
(not from gen.py internals) and reports any disagreement with gen.py's key.

    python3 audit_key.py BENCH_DIR
"""
import csv, json, os, re, sys
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import build  # only for the key being audited

B = sys.argv[1]; F = os.path.join(B, "fixtures")
readme = open(os.path.join(F, "README.md")).read()
dup = int(re.search(r"Row (\d+) is a known duplicate", readme).group(1))
rows = [dict(r, row_id=int(r["row_id"]), units=int(r["units"])) for r in csv.DictReader(open(os.path.join(F, "sales.csv")))]
live = [r for r in rows if r["row_id"] != dup]
price = {r["sku"]: float(r["unit_price_usd"]) for r in csv.DictReader(open(os.path.join(F, "prices.csv")))}
memo = {f: open(os.path.join(F, "errata", f)).read() for f in os.listdir(os.path.join(F, "errata"))}
m1 = re.search(r"B203 unit price is ([\d.]+) USD for sales dated (\S+) or later", memo["2026-07-28-memo.md"])
m2 = re.search(r"B203 unit price is ([\d.]+) USD for sales dated (\S+) or later", memo["2026-08-27-memo.md"])
m3 = re.search(r"B209 unit price is ([\d.]+) USD for West-region sales dated (\S+) or later", memo["2026-08-10-memo.md"])
inv = {r["sku"]: r for r in csv.DictReader(open(os.path.join(F, "inventory.csv")))}
pack = {r["sku"]: int(r["units_per_case"]) for r in csv.DictReader(open(os.path.join(F, "pack_sizes.csv")))}
week1 = date(2026, 7, 6)


def p(r):
    s, d = r["sku"], r["date"]
    if s == "B203":
        if d >= m2.group(2): return float(m2.group(1))
        if d >= m1.group(2): return float(m1.group(1))
    if s == "B209" and r["region"] == "West" and d >= m3.group(2): return float(m3.group(1))
    return price[s]


def money(x): return f"${Decimal(str(round(x, 2))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,}"
def wk(d): return (date.fromisoformat(d) - week1).days // 7 + 1
def onh(s): return int(inv[s]["on_hand_cases"]) * pack[s]
tot = sum(r["units"] for r in live)
rank = sorted(price, key=lambda s: -sum(r["units"] for r in live if r["sku"] == s))

LOGIC = {  # truths read by hand from pump-notes.md, VERSION and CHANGELOG files
    "P-11 shows likely early bearing wear; not confirmed, teardown scheduled.": True,
    "P-11 has confirmed bearing wear.": False,
    "P-12's seal leak was confirmed at teardown on 2026-09-18.": True,
    "P-12 may have a seal leak; it is not yet confirmed.": False,
    "P-14's temperature spike is probably a sensor fault; the sensor swap is still pending.": True,
    "P-14's temperature spike was caused by a sensor fault.": False,
    "P-15 impeller damage is confirmed and a replacement is on order.": True,
    "P-17: operator-reported noise, cause not yet found.": True,
    "billing is running 3.5.0, the newest version in its changelog.": False,
    "intake is on 2.0.0-rc2, a release candidate; 2.0.0 is not released yet.": True,
    "intake is running 2.0.0.": False,
    "The 480-unit East sale of B207 on 2026-08-14 is a verified bulk order.": True,
}


def truth(t):
    if t in LOGIC: return LOGIC[t]
    if m := re.fullmatch(r"(\w+) sold (-?\d+) net units in week (\d+)\.", t) or re.fullmatch(r"(\w+), week (\d+): (-?\d+) net units\.", t):
        g = m.groups()
        reg, n, w = (g[0], g[1], g[2]) if "sold" in t else (g[0], g[2], g[1])
        return int(n) == sum(r["units"] for r in live if r["region"] == reg and wk(r["date"]) == int(w))
    if m := re.fullmatch(r"(B\d+) revenue \(all rows, prices as in effect\): (\S+)\.", t):
        return m.group(2) == money(sum(r["units"] * p(r) for r in live if r["sku"] == m.group(1)))
    if m := re.fullmatch(r"B203 revenue for (August|September) only: (\S+)\.", t):
        mo = "2026-08" if m.group(1) == "August" else "2026-09"
        return m.group(2) == money(sum(r["units"] * p(r) for r in live if r["sku"] == "B203" and r["date"].startswith(mo)))
    if m := re.fullmatch(r"(B\d+) revenue: (\S+)\.", t):
        return m.group(2) == money(sum(r["units"] * p(r) for r in live if r["sku"] == m.group(1)))
    if m := re.fullmatch(r"(B\d+) net units sold(?:, after returns)?: (-?\d+)\.", t):
        return int(m.group(2)) == sum(r["units"] for r in live if r["sku"] == m.group(1))
    if m := re.fullmatch(r"(B\d+) on hand: (\d+) units(?: \((\d+) cases of (\d+)\))?\.", t):
        s = m.group(1); ok = int(m.group(2)) == onh(s)
        if m.group(3): ok = ok and int(m.group(3)) == int(inv[s]["on_hand_cases"]) and int(m.group(4)) == pack[s]
        return ok
    if m := re.fullmatch(r"Exactly (\d+) SKUs are below par \(par is in units\)\.", t):
        return int(m.group(1)) == sum(onh(s) < int(inv[s]["par_units"]) for s in inv)
    if m := re.fullmatch(r"(B\d+) is (below|at or above) par\.", t):
        return (m.group(2) == "below") == (onh(m.group(1)) < int(inv[m.group(1)]["par_units"]))
    if m := re.fullmatch(r"(B\d+) holds (\d+) units against a par of (\d+) units\.", t):
        return int(m.group(2)) == onh(m.group(1)) and int(m.group(3)) == int(inv[m.group(1)]["par_units"])
    if m := re.fullmatch(r"Total net units, all rows after the documented exclusion: (-?\d+)\.", t):
        return int(m.group(1)) == tot
    if m := re.fullmatch(r"Row count after the documented exclusion: (\d+)\.", t):
        return int(m.group(1)) == len(live)
    if m := re.fullmatch(r"(B\d+) net units sold in (\w+): (-?\d+)\.", t):
        return int(m.group(3)) == sum(r["units"] for r in live if r["sku"] == m.group(1) and r["region"] == m.group(2))
    if m := re.fullmatch(r"(\w+) share of total net units: ([\d.]+)%\.", t):
        sh = Decimal(str(100 * sum(r["units"] for r in live if r["region"] == m.group(1)) / tot)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return m.group(2) == str(sh)
    if m := re.fullmatch(r"Top 3 SKUs by net units, highest first: (.+)\.", t):
        return m.group(1).split(", ") == rank[:3]
    if m := re.fullmatch(r"SKUs ranked 4th to 6th by net units, highest first: (.+)\.", t):
        return m.group(1).split(", ") == rank[3:6]
    if m := re.fullmatch(r"(B\d+) had no returns in the period\.", t):
        return not any(r["units"] < 0 for r in live if r["sku"] == m.group(1))
    if m := re.fullmatch(r"The largest single sale row is (\d+) units \(row (\d+)\)\.", t):
        big = max(live, key=lambda r: r["units"]); return int(m.group(1)) == big["units"] and int(m.group(2)) == big["row_id"]
    if m := re.fullmatch(r"(\d+) rows are returns \(negative units\)\.", t):
        return int(m.group(1)) == sum(r["units"] < 0 for r in live)
    if m := re.fullmatch(r"(\w+) is running ([\w.\-]+)(?:, its latest released version)?\.", t):
        app = m.group(1); ver = open(os.path.join(F, "apps", app, "VERSION")).read().strip()
        return m.group(2) == ver
    raise ValueError("no audit rule for: " + t)


items = json.load(open(os.path.join(B, "items.json")))
_, key, _, fams = build(None)
bad = 0
for it in items:
    for c, t in it["claims"].items():
        cid = it["id"] + c
        try:
            a = truth(t)
        except ValueError as e:
            print("UNCHECKED", cid, e); bad += 1; continue
        if a != key[cid]:
            print("MISMATCH", cid, fams[cid], "key=", key[cid], "audit=", a, "|", t); bad += 1
print("audit mismatches/unchecked:", bad, "of", sum(len(i["claims"]) for i in items))
