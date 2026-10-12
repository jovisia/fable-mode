"""Checker-only bench, round 2.

Builds fixtures + items for testing CHECKERS (not builders): every arm gets the same
finished outputs, a mix of correct claims and claims with one planted, subtle bug.
Scores misses (bad claim passed) separately from invented flaws (good claim failed).

    python3 gen.py OUT_DIR          # writes OUT_DIR/fixtures/*, OUT_DIR/items.json
    python3 gen.py OUT_DIR --key    # also prints the answer key (keep it away from checkers)

The key is never written next to the items; score.py rebuilds it in memory.
"""
import csv, json, os, random, sys
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

SEED = 20261012
REGIONS = ["North", "South", "East", "West"]
SKUS = [f"B{n}" for n in range(200, 212)]


def r1(x):  # round half up to 1 decimal, as a string
    return str(Decimal(str(x)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def money(x):
    return f"${Decimal(str(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,}"


def build(out=None):
    rnd = random.Random(SEED)
    start = date(2026, 7, 6)  # a Monday; 12 weeks, Mon-Sun
    # ---------- data ----------
    sales = []
    rid = 1000
    for _ in range(600):
        d = start + timedelta(days=rnd.randrange(84))
        sales.append({"row_id": rid, "date": d.isoformat(), "region": rnd.choice(REGIONS),
                      "sku": rnd.choice(SKUS), "units": rnd.randint(1, 24)})
        rid += 1
    # returns: negative-unit rows, documented in README
    for _ in range(14):
        d = start + timedelta(days=rnd.randrange(84))
        sales.append({"row_id": rid, "date": d.isoformat(), "region": rnd.choice(REGIONS),
                      "sku": rnd.choice(SKUS), "units": -rnd.randint(1, 6)})
        rid += 1
    # a real outlier (true, not an error)
    sales.append({"row_id": rid, "date": "2026-08-14", "region": "East", "sku": "B207", "units": 480}); rid += 1
    # a known duplicate row (documented as to-be-excluded)
    dup_src = sales[137]
    dup = dict(dup_src); dup["row_id"] = rid; rid += 1
    sales.append(dup)
    sales.sort(key=lambda r: (r["date"], r["row_id"]))
    dup_id = dup["row_id"]

    base_price = {s: round(rnd.uniform(4, 30), 2) for s in SKUS}
    # errata chain: E1 changes B203 from 2026-08-01; E2 (later memo) supersedes E1 from 2026-09-01
    e1_from, e1_price = "2026-08-01", round(base_price["B203"] - 1.25, 2)
    e2_from, e2_price = "2026-09-01", round(base_price["B203"] + 0.75, 2)
    # B209 errata applies only to the West region
    e3_from, e3_price = "2026-08-15", round(base_price["B209"] - 2.00, 2)

    pack = {s: rnd.choice([6, 12, 24]) for s in SKUS}
    inv = []
    for s in SKUS:
        par_units = rnd.choice([48, 72, 96, 120, 144])
        cases = rnd.randint(1, 14)
        inv.append({"sku": s, "on_hand_cases": cases, "par_units": par_units})
    inv[4]["on_hand_cases"] = inv[4]["par_units"] // pack[inv[4]["sku"]]  # exactly at par (if divisible)

    apps = {
        "billing": ("3.4.2", ["3.5.0 (Unreleased)", "3.4.2 (2026-09-30)", "3.4.1 (2026-08-02)"]),
        "ledger": ("1.9.0", ["1.9.0 (2026-10-01)", "1.8.7 (2026-07-12)"]),
        "intake": ("2.0.0-rc2", ["2.0.0 (Unreleased)", "2.0.0-rc2 (2026-09-21)", "1.12.3 (2026-06-30)"]),
        "notify": ("0.8.4", ["0.8.4 (2026-03-03)", "0.8.3 (2026-01-15)"]),
    }
    notes = [
        ("P-11", "Vibration trending up; likely early bearing wear. Not confirmed — teardown scheduled."),
        ("P-12", "Seal leak confirmed at teardown on 2026-09-18."),
        ("P-14", "Temperature spike on 2026-09-02; probably a sensor fault, sensor swap pending."),
        ("P-15", "Impeller damage confirmed by inspection on 2026-09-25; replacement ordered."),
        ("P-17", "Noise reported by operator; no cause found yet."),
    ]

    # ---------- write fixtures ----------
    if out:
        fx = os.path.join(out, "fixtures")
        os.makedirs(os.path.join(fx, "apps"), exist_ok=True)
        with open(os.path.join(fx, "sales.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["row_id", "date", "region", "sku", "units"])
            w.writeheader(); w.writerows(sales)
        with open(os.path.join(fx, "prices.csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(["sku", "unit_price_usd"])
            for s in SKUS: w.writerow([s, f"{base_price[s]:.2f}"])
        open(os.path.join(fx, "README.md"), "w").write(
            "# Sales data notes\n\n"
            "- Weeks run Monday to Sunday. Week 1 starts 2026-07-06.\n"
            "- Negative `units` are customer returns. Net units = sum of all rows.\n"
            f"- Row {dup_id} is a known duplicate of row {dup_src['row_id']} (double import). Exclude row {dup_id} from all figures.\n"
            "- Row with 480 units on 2026-08-14 (East, B207) is a verified bulk order, not an error.\n"
            "- Revenue = units x unit price in effect on the sale date (see prices.csv and errata/).\n")
        os.makedirs(os.path.join(fx, "errata"), exist_ok=True)
        open(os.path.join(fx, "errata", "2026-07-28-memo.md"), "w").write(
            f"# Price memo E1\n\nB203 unit price is {e1_price:.2f} USD for sales dated {e1_from} or later.\n")
        open(os.path.join(fx, "errata", "2026-08-27-memo.md"), "w").write(
            f"# Price memo E2 (supersedes E1 from its effective date)\n\nB203 unit price is {e2_price:.2f} USD for sales dated {e2_from} or later.\n")
        open(os.path.join(fx, "errata", "2026-08-10-memo.md"), "w").write(
            f"# Price memo E3\n\nB209 unit price is {e3_price:.2f} USD for West-region sales dated {e3_from} or later. Other regions unchanged.\n")
        with open(os.path.join(fx, "inventory.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["sku", "on_hand_cases", "par_units"]); w.writeheader(); w.writerows(inv)
        with open(os.path.join(fx, "pack_sizes.csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(["sku", "units_per_case"])
            for s in SKUS: w.writerow([s, pack[s]])
        for app, (ver, log) in apps.items():
            os.makedirs(os.path.join(fx, "apps", app), exist_ok=True)
            open(os.path.join(fx, "apps", app, "VERSION"), "w").write(ver + "\n")
            open(os.path.join(fx, "apps", app, "CHANGELOG.md"), "w").write(
                "# Changelog\n\n" + "".join(f"## {e}\n- changes\n\n" for e in log))
        open(os.path.join(fx, "pump-notes.md"), "w").write(
            "# Maintenance notes\n\n" + "".join(f"- {p}: {t}\n" for p, t in notes))

    # ---------- truth helpers ----------
    live = [r for r in sales if r["row_id"] != dup_id]

    def week_of(d):
        return (date.fromisoformat(d) - start).days // 7 + 1

    def units(rows, **kw):
        return sum(r["units"] for r in rows if all(r[k] == v for k, v in kw.items()))

    def price_on(sku, d, region):
        p = base_price[sku]
        if sku == "B203":
            if d >= e2_from: p = e2_price
            elif d >= e1_from: p = e1_price
        if sku == "B209" and region == "West" and d >= e3_from:
            p = e3_price
        return p

    def revenue(rows, sku, pricer=price_on):
        return round(sum(r["units"] * pricer(r["sku"], r["date"], r["region"]) for r in rows if r["sku"] == sku), 2)

    claims = []  # (text, type, ok, family)

    def add(text, typ, ok, fam):
        claims.append((text, typ, ok, fam))

    # F1 region-week units (long table); bug = week boundary shifted one day
    for i, (reg, wk) in enumerate([(r, w) for r in REGIONS for w in (3, 7, 10)]):
        true = sum(r["units"] for r in live if r["region"] == reg and week_of(r["date"]) == wk)
        shifted = sum(r["units"] for r in live if r["region"] == reg and
                      ((date.fromisoformat(r["date"]) - start).days + 1) // 7 + 1 == wk)
        bad = i % 2 == 1 and shifted != true
        add(f"{reg} sold {shifted if bad else true} net units in week {wk}.", "mech", not bad, "F1-week-boundary")
    # F2 B203 / B209 revenue with errata chain
    e1_only = lambda s, d, g: (e1_price if (s == "B203" and d >= e1_from) else price_on(s, d, g))
    no_region = lambda s, d, g: (e3_price if (s == "B209" and d >= e3_from) else price_on(s, d, g))
    gt_boundary = lambda s, d, g: (base_price[s] if (s == "B203" and d == e1_from) else price_on(s, d, g))
    add(f"B203 revenue (all rows, prices as in effect): {money(revenue(live, 'B203'))}.", "mech", True, "F2-errata")
    add(f"B203 revenue (all rows, prices as in effect): {money(revenue(live, 'B203', e1_only))}.", "mech", False, "F2-errata-superseded")
    add(f"B209 revenue (all rows, prices as in effect): {money(revenue(live, 'B209'))}.", "mech", True, "F2-errata")
    add(f"B209 revenue (all rows, prices as in effect): {money(revenue(live, 'B209', no_region))}.", "mech", False, "F2-errata-region")
    if revenue(live, "B203", gt_boundary) != revenue(live, "B203"):
        add(f"B203 revenue for August only: {money(round(sum(r['units']*gt_boundary(r['sku'],r['date'],r['region']) for r in live if r['sku']=='B203' and r['date'][:7]=='2026-08'),2))}.", "mech", False, "F2-boundary-day")
    add(f"B203 revenue for September only: {money(round(sum(r['units']*price_on(r['sku'],r['date'],r['region']) for r in live if r['sku']=='B203' and r['date'][:7]=='2026-09'),2))}.", "mech", True, "F2-errata")
    # F3 net vs gross (returns)
    for j, s in enumerate(SKUS):
        net = units(live, sku=s)
        gross = sum(r["units"] for r in live if r["sku"] == s and r["units"] > 0)
        if gross == net:
            add(f"{s} net units sold: {net}.", "mech", True, "F3-net-control")
        elif j % 2 == 0:
            add(f"{s} net units sold: {gross}.", "mech", False, "F3-returns-ignored")
        else:
            add(f"{s} net units sold, after returns: {net}.", "mech", True, "F3-net")
    # F4 inventory units vs cases
    for k, row in enumerate(inv):
        s = row["sku"]; u = row["on_hand_cases"] * pack[s]
        if k % 3 == 0 and row["on_hand_cases"] != u:
            add(f"{s} on hand: {row['on_hand_cases']} units.", "mech", False, "F4-cases-as-units")
        else:
            add(f"{s} on hand: {u} units ({row['on_hand_cases']} cases of {pack[s]}).", "mech", True, "F4-units")
    below = [r["sku"] for r in inv if r["on_hand_cases"] * pack[r["sku"]] < r["par_units"]]
    add(f"Exactly {len(below)} SKUs are below par (par is in units).", "mech", True, "F4-below-par")
    below_cases = [r["sku"] for r in inv if r["on_hand_cases"] < r["par_units"]]
    if len(below_cases) != len(below):
        add(f"Exactly {len(below_cases)} SKUs are below par (par is in units).", "mech", False, "F4-cases-vs-par")
    # F5 duplicate row
    tot = units(live); tot_dup = units(sales)
    add(f"Total net units, all rows after the documented exclusion: {tot}.", "mech", True, "F5-dedupe")
    dsku = dup["sku"]
    add(f"{dsku} net units sold in {dup['region']}: {units(sales, sku=dsku, region=dup['region'])}.", "mech", False, "F5-duplicate-counted")
    add(f"Row count after the documented exclusion: {len(live)}.", "mech", True, "F5-dedupe")
    # F6 hedges (logic)
    add("P-11 shows likely early bearing wear; not confirmed, teardown scheduled.", "logic", True, "F6-hedge-kept")
    add("P-11 has confirmed bearing wear.", "logic", False, "F6-hedge-escalated")
    add("P-12's seal leak was confirmed at teardown on 2026-09-18.", "logic", True, "F6-confirmed")
    add("P-12 may have a seal leak; it is not yet confirmed.", "logic", False, "F6-confirmed-demoted")
    add("P-14's temperature spike is probably a sensor fault; the sensor swap is still pending.", "logic", True, "F6-hedge-kept")
    add("P-14's temperature spike was caused by a sensor fault.", "logic", False, "F6-hedge-escalated")
    add("P-15 impeller damage is confirmed and a replacement is on order.", "logic", True, "F6-confirmed")
    add("P-17: operator-reported noise, cause not yet found.", "logic", True, "F6-hedge-kept")
    # F7 versions (logic: changelog Unreleased is not installed)
    add("billing is running 3.4.2.", "mech", True, "F7-version")
    add("billing is running 3.5.0, the newest version in its changelog.", "logic", False, "F7-unreleased")
    add("ledger is running 1.9.0.", "mech", True, "F7-version")
    add("intake is on 2.0.0-rc2, a release candidate; 2.0.0 is not released yet.", "logic", True, "F7-rc")
    add("intake is running 2.0.0.", "logic", False, "F7-unreleased")
    add("notify is running 0.8.4, its latest released version.", "mech", True, "F7-old-but-current")
    # F8 shares, one decimal, round-half-up
    for m, reg in enumerate(REGIONS):
        sh = 100 * units(live, region=reg) / tot
        good = r1(sh); trunc = str(Decimal(str(sh)).quantize(Decimal("0.1"), rounding="ROUND_DOWN"))
        if m % 2 == 1 and trunc != good:
            add(f"{reg} share of total net units: {trunc}%.", "mech", False, "F8-truncated")
        elif m % 2 == 1:
            wrong = r1(100 * units(live, region=reg) / tot_dup)
            add(f"{reg} share of total net units: {wrong}%.", "mech", wrong == good, "F8-dup-denominator")
        else:
            add(f"{reg} share of total net units: {good}%.", "mech", True, "F8-share")
    # F9 ordered top-3 by net units
    ranked = sorted(SKUS, key=lambda s: -units(live, sku=s))
    top3 = ranked[:3]
    add(f"Top 3 SKUs by net units, highest first: {', '.join(top3)}.", "mech", True, "F9-order")
    swapped = [ranked[3], ranked[4], ranked[5]]
    if units(live, sku=ranked[4]) != units(live, sku=ranked[3]):
        add(f"SKUs ranked 4th to 6th by net units, highest first: {swapped[1]}, {swapped[0]}, {swapped[2]}.", "mech", False, "F9-swapped")
    # F10 absence claims
    returns_by = {s: [r for r in live if r["sku"] == s and r["units"] < 0] for s in SKUS}
    has_ret = [s for s in SKUS if returns_by[s]]; no_ret = [s for s in SKUS if not returns_by[s]]
    if no_ret:
        add(f"{no_ret[0]} had no returns in the period.", "mech", True, "F10-absence-true")
    add(f"{has_ret[-1]} had no returns in the period.", "mech", False, "F10-absence-false")
    # F12 per-SKU below-par yes/no; bug = compares cases to a par stated in units
    for k, row in enumerate(inv):
        s = row["sku"]; is_below = row["on_hand_cases"] * pack[s] < row["par_units"]
        case_below = row["on_hand_cases"] < row["par_units"]
        if k % 3 == 1 and case_below != is_below:
            add(f"{s} is {'below' if case_below else 'at or above'} par.", "mech", False, "F12-par-in-cases")
        else:
            add(f"{s} is {'below' if is_below else 'at or above'} par.", "mech", True, "F12-par")
    # F13 per-SKU revenue; bugs = duplicate row kept / returns ignored
    for k, s in enumerate(SKUS):
        if s in ("B203", "B209"):
            continue
        good = revenue(live, s)
        if s == dsku:
            add(f"{s} revenue: {money(revenue(sales, s))}.", "mech", False, "F13-duplicate-counted")
        elif k % 4 == 2:
            gross_rev = round(sum(r["units"] * base_price[s] for r in live if r["sku"] == s and r["units"] > 0), 2)
            add(f"{s} revenue: {money(gross_rev)}.", "mech", gross_rev == good, "F13-returns-ignored")
        else:
            add(f"{s} revenue: {money(good)}.", "mech", True, "F13-revenue")
    # F14 more region-week cells (weeks 2, 5, 8, 11); bug = boundary shift
    for i, (reg, wk) in enumerate([(r, w) for r in REGIONS for w in (2, 5, 8, 11)]):
        true = sum(r["units"] for r in live if r["region"] == reg and week_of(r["date"]) == wk)
        shifted = sum(r["units"] for r in live if r["region"] == reg and
                      ((date.fromisoformat(r["date"]) - start).days - 1) // 7 + 1 == wk)
        bad = i % 3 == 0 and shifted != true
        add(f"{reg}, week {wk}: {shifted if bad else true} net units.", "mech", not bad, "F14-week-boundary")
    # F11 suspicious-but-true controls
    add("The 480-unit East sale of B207 on 2026-08-14 is a verified bulk order.", "logic", True, "F11-outlier-true")
    big = max(live, key=lambda r: r["units"])
    add(f"The largest single sale row is {big['units']} units (row {big['row_id']}).", "mech", True, "F11-outlier")
    exact = inv[4]
    eu = exact["on_hand_cases"] * pack[exact["sku"]]
    add(f"{exact['sku']} holds {eu} units against a par of {exact['par_units']} units.", "mech", True, "F11-at-par")
    add(f"{len([r for r in live if r['units'] < 0])} rows are returns (negative units).", "mech", True, "F11-returns-count")

    # ---------- pair claims into items (2 per item), shuffled deterministically ----------
    order = list(range(len(claims)))
    random.Random(SEED + 1).shuffle(order)
    items, key, types, fams = [], {}, {}, {}
    for n in range(0, len(order) - 1, 2):
        iid = f"J{n // 2 + 1:02d}"
        a, b = claims[order[n]], claims[order[n + 1]]
        items.append({"id": iid,
                      "spec": "Answer from the data in fixtures/ (read fixtures/README.md first). State figures exactly.",
                      "claims": {"a": a[0], "b": b[0]}})
        for letter, c in (("a", a), ("b", b)):
            key[iid + letter] = c[2]; types[iid + letter] = c[1]; fams[iid + letter] = c[3]
    if out:
        json.dump(items, open(os.path.join(out, "items.json"), "w"), indent=1)
    return items, key, types, fams


if __name__ == "__main__":
    out = sys.argv[1]
    items, key, types, fams = build(out)
    bad = [k for k, ok in key.items() if not ok]
    print(f"{len(items)} items, {len(key)} claims, {len(bad)} bad, {sum(t == 'logic' for t in types.values())} logic")
    if "--key" in sys.argv:
        for k in sorted(key): print(k, "OK " if key[k] else "BAD", fams[k])
