"""Make a fake HubSpot deals + companies export with known problems planted in it.

Follows test/PREREGISTRATION.md. Writes:
  <out>/deals.csv, <out>/companies.csv   (what the weekly check reads)
  <key>                                  (the answer key; the check never reads it)

Usage:
  python3 generate_export.py --seed 20261012 --out ../data/export --key ../test/answer-key/seed-20261012.csv

Everything here is made up. Python 3 standard library only.
"""
import argparse
import csv
import os
import random
from datetime import datetime, timedelta, date

NOW = datetime(2026, 10, 12, 7, 30)
TODAY = NOW.date()

STAGES_OPEN = [  # (stage, share of open deals)
    ("Appointment Scheduled", 0.25),
    ("Qualified To Buy", 0.25),
    ("Presentation Scheduled", 0.20),
    ("Decision Maker Bought-In", 0.15),
    ("Contract Sent", 0.15),
]
OWNERS = ["Jonas Example", "Leonie Example", "Murat Example", "Clara Example", "Finn Example", "Aylin Example"]
CITIES = ["Hamburg", "Bremen", "Kiel", "Lübeck", "Hannover", "Berlin", "Rostock", "Oldenburg", "Flensburg", "Lüneburg"]
PREFIXES = [
    "Nordlicht", "Alsterblick", "Elbufer", "Hafenkante", "Kranich", "Möwenweg", "Deichgraf", "Fleetwerk", "Speicherstadt",
    "Ostwind", "Westwall", "Leuchtturm", "Ankerplatz", "Seemeile", "Brückenbau", "Lotsenhaus", "Kompass", "Wattenmeer",
    "Heidekraut", "Birkenhain", "Lindenhof", "Eichenwald", "Rotklinker", "Grünspan", "Blauwal", "Silbermöwe", "Bernstein",
    "Strandgut", "Sturmflut", "Ebbe", "Tidenhub", "Kaiserkai", "Sandtor", "Wilhelmsburg", "Veddel", "Barmbek", "Altona",
    "Harburg", "Bergedorf", "Wandsbek", "Ottensen", "Eppendorf", "Winterhude", "Uhlenhorst", "Hammerbrook", "Rothenburg",
    "Billwerder", "Finkenwerder", "Steinwerder", "Moorburg", "Kirchdorf", "Ochsenwerder", "Reitbrook", "Curslack",
    "Neuland", "Gut Moor", "Allermöhe", "Spadenland", "Tatenberg", "Moorfleet", "Rönneburg", "Sinstorf", "Marmstorf",
    "Eißendorf", "Heimfeld", "Hausbruch", "Neugraben", "Fischbek", "Cranz", "Neuenfelde", "Francop", "Waltershof",
]
INDUSTRIES = [
    ("Logistik", "logistik"), ("Pflege", "pflege"), ("Kliniken", "kliniken"), ("Facility Services", "facility"),
    ("Sicherheitsdienst", "sicherheit"), ("Gastro", "gastro"), ("Reinigung", "reinigung"), ("Spedition", "spedition"),
    ("Handel", "handel"), ("Bau", "bau"), ("Event", "event"), ("Hotels", "hotels"),
]
LEGAL = ["GmbH", "GmbH", "GmbH", "AG", "SE", "GmbH & Co. KG", "gGmbH", "UG"]
PRODUCTS = ["Shift planning", "Time tracking", "Shift planning + time tracking", "Workforce analytics"]

DEAL_COLS = ["Record ID", "Deal Name", "Pipeline", "Deal Stage", "Amount", "Close Date", "Create Date",
             "Last Activity Date", "Deal owner", "Associated Company IDs (Primary)", "Associated Company (Primary)"]
COMPANY_COLS = ["Record ID", "Company name", "Company Domain Name", "City", "Country/Region", "Create Date"]
KEY_COLS = ["code", "record_id", "other_record_id", "true_amount", "note"]


def fmt_dt(d):
    return d.strftime("%Y-%m-%d %H:%M") if d else ""


def fmt_d(d):
    return d.strftime("%Y-%m-%d") if d else ""


def rand_time(rng, day):
    """A working-hours timestamp on a given date."""
    return datetime(day.year, day.month, day.day, rng.randint(8, 17), rng.choice([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]))


def amount(rng):
    v = rng.lognormvariate(10.1, 0.75)  # median about 24k EUR ARR
    return int(round(min(max(v, 4000), 180000) / 100.0) * 100)


def pick_stage(rng):
    r, acc = rng.random(), 0.0
    for s, p in STAGES_OPEN:
        acc += p
        if r < acc:
            return s
    return STAGES_OPEN[-1][0]


def close_date_open(rng):
    if rng.random() < 0.6:  # Q4 2026, from today
        return TODAY + timedelta(days=rng.randint(0, (date(2026, 12, 31) - TODAY).days))
    return date(2027, 1, 1) + timedelta(days=rng.randint(0, 89))


def make_companies(rng, n):
    used, comps = set(), []
    prefixes = PREFIXES[:]
    rng.shuffle(prefixes)
    i = 0
    while len(comps) < n:
        pre = prefixes[i % len(prefixes)]
        ind, slug = rng.choice(INDUSTRIES)
        i += 1
        if (pre, ind) in used:
            continue
        used.add((pre, ind))
        legal = rng.choice(LEGAL)
        name = f"{pre} {ind} {legal}"
        domain = f"{pre.lower().replace(' ', '-').replace('ö', 'oe').replace('ü', 'ue').replace('ä', 'ae').replace('ß', 'ss')}-{slug}.example"
        comps.append({"key": f"C{len(comps)}", "name": name, "short": f"{pre} {ind}", "pre": pre, "ind": ind,
                      "legal": legal, "domain": domain, "city": rng.choice(CITIES)})
    return comps


def variant_name(rng, comp, kind):
    """A messy way someone else might type the same company."""
    pre, ind, legal = comp["pre"], comp["ind"], comp["legal"]
    if kind == 0:
        return f"{pre} {ind}"
    if kind == 1:
        other = "GMBH & CO. KG" if legal != "GmbH & Co. KG" else "GMBH"
        return f"{pre} {ind} {other}".upper()
    if kind == 2:
        return f"{pre} {ind} {comp['city']}"
    if kind == 3:  # typo: swap two letters in the industry word
        w = list(ind)
        j = rng.randint(1, max(1, len(w) - 3))
        w[j], w[j + 1] = w[j + 1], w[j]
        return f"{pre} {''.join(w)} {legal}"
    return f"{pre} {ind[:3]}. {legal}"  # abbreviation (the hardest one)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20261012)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "data", "export"))
    ap.add_argument("--key", default=None)
    a = ap.parse_args()
    rng = random.Random(a.seed)

    comps = make_companies(rng, 230)
    deals = []  # internal dicts; ids assigned at the end

    def new_deal(comp, kind, stage, amt, close, create, last, owner, product, seats):
        d = {"comp": comp, "kind": kind, "stage": stage, "amount": amt, "close": close, "create": create,
             "last": last, "owner": owner, "product": product, "seats": seats, "plant": None}
        d["name"] = deal_name(d)
        deals.append(d)
        return d

    def deal_name(d):
        c = d["comp"]["short"]
        k = d["kind"]
        if k == "new":
            return f"{c} – {d['product']}, {d['seats']} seats"
        if k == "expansion":
            return f"{c} – Expansion +{d['seats']} seats"
        if k == "renewal":
            return f"{c} – Renewal 2027"
        if k == "addon":
            return f"{c} – Workforce analytics add-on"
        if k == "site":
            return f"{c} – Rollout {d['site']} site"
        return f"{c} – {d['product']}"

    # --- the clean base: 110 won, 90 lost, 200 open ---------------------------------------------------
    company_cycle = comps[:]
    rng.shuffle(company_cycle)
    kinds_used = {}  # company key -> set of kinds, so no company has two deals with the same name

    def take_company():
        # about 60 companies get a second or third real deal
        if rng.random() < 0.28 and kinds_used:
            k = rng.choice(list(kinds_used))
            if len(kinds_used[k]) < 3:
                return next(c for c in comps if c["key"] == k)
        c = company_cycle.pop() if company_cycle else rng.choice(comps)
        return c

    def next_kind(comp):
        used = kinds_used.setdefault(comp["key"], set())
        for k in ["new", "expansion", "renewal", "addon"]:
            if k not in used:
                used.add(k)
                return k
        used.add("new")
        return "new"

    for status, n in [("Closed Won", 110), ("Closed Lost", 90)]:
        for _ in range(n):
            comp = take_company()
            kind = next_kind(comp)
            close = date(2026, 1, 5) + timedelta(days=rng.randint(0, (date(2026, 10, 9) - date(2026, 1, 5)).days))
            create = rand_time(rng, close - timedelta(days=rng.randint(20, 160)))
            last = rand_time(rng, close - timedelta(days=rng.randint(0, 10)))
            if last < create:
                last = create + timedelta(hours=2)
            new_deal(comp, kind, status, amount(rng), close, create, last, rng.choice(OWNERS),
                     rng.choice(PRODUCTS), rng.choice([25, 40, 60, 80, 120, 150, 200, 300]))

    open_base = []
    for _ in range(200):
        comp = take_company()
        kind = next_kind(comp)
        last_day = TODAY - timedelta(days=rng.randint(0, 25))
        create_day = last_day - timedelta(days=rng.randint(5, 170))
        create = rand_time(rng, create_day)
        last = rand_time(rng, last_day)
        if last_day == TODAY:
            last = datetime(TODAY.year, TODAY.month, TODAY.day, 7, rng.randint(0, 29))
        if last < create:
            last = create + timedelta(hours=1)
        d = new_deal(comp, kind, pick_stage(rng), amount(rng), close_date_open(rng), create, last,
                     rng.choice(OWNERS), rng.choice(PRODUCTS), rng.choice([25, 40, 60, 80, 120, 150, 200, 300]))
        open_base.append(d)

    # --- plant problems (each base deal gets at most one) ---------------------------------------------
    key_rows = []
    pool = open_base[:]
    rng.shuffle(pool)

    def take(pred=lambda d: True):
        for i, d in enumerate(pool):
            if pred(d):
                return pool.pop(i)
        raise RuntimeError("no base deal left for this plant")

    extra_companies = []

    # DUP_EXACT: double import
    for _ in range(8):
        o = take(lambda d: d["create"] < NOW - timedelta(days=4))
        o["plant"] = "DUP_ORIGINAL"
        create = o["create"] + timedelta(days=rng.randint(0, 3), minutes=rng.randint(1, 50))
        last = max(create, o["last"] - timedelta(days=rng.randint(0, 5)))
        if (TODAY - last.date()).days > 25:  # keep the copy as fresh as a clean row
            last = max(create, o["last"])
        c = dict(o, plant="DUP_EXACT", create=create, last=last, other=o)
        deals.append(c)

    # DUP_FUZZY: someone else enters the same deal under a second company record
    for i in range(10):
        o = take(lambda d: d["create"] < NOW - timedelta(days=10))
        o["plant"] = "DUP_ORIGINAL"
        comp = o["comp"]
        vname = variant_name(rng, comp, i % 5)
        dom_choice = rng.random()
        vdomain = comp["domain"] if dom_choice < 0.4 else ("" if dom_choice < 0.8 else comp["domain"].replace(".example", "-hh.example"))
        vcomp = {"key": f"V{i}", "name": vname, "short": vname, "domain": vdomain, "city": comp["city"],
                 "variant_of": comp["key"]}
        extra_companies.append(vcomp)
        max_off = min(45, (NOW - o["create"]).days - 1)
        create = o["create"] + timedelta(days=rng.randint(5, max(5, max_off)), minutes=rng.randint(1, 50))
        create = min(create, NOW - timedelta(hours=20))
        last = create + (NOW - create) * rng.random()
        if (TODAY - last.date()).days > 25:
            last = rand_time(rng, TODAY - timedelta(days=rng.randint(1, 20)))
        last = rand_time(rng, last.date()) if last.date() < TODAY else rand_time(rng, TODAY - timedelta(days=1))
        if last < create:
            last = create + timedelta(hours=1)
        amt = int(round(o["amount"] * rng.uniform(0.9, 1.1) / 100.0) * 100)
        close = max(TODAY, o["close"] + timedelta(days=rng.randint(-14, 14)))
        wording = rng.choice([
            f"{vname}: {o['name'].split('– ')[1].lower()}",
            f"{vname} - {o['name'].split('– ')[1]}",
            f"{o['name'].split('– ')[1]} for {vname}",
        ])
        others = [x for x in OWNERS if x != o["owner"]]
        c = dict(o, plant="DUP_FUZZY", comp=vcomp, name=wording, amount=amt, close=close, create=create, last=last,
                 owner=rng.choice(others) if rng.random() < 0.7 else o["owner"], other=o)
        deals.append(c)

    # TRAP: real second deal at the same company that looks similar but is different business
    trap_kinds = ["site", "renewal", "addon", "site", "expansion", "renewal"]
    for i in range(6):
        o = take(lambda d: d["create"] < NOW - timedelta(days=10) and d["kind"] in ("new",))
        o["plant"] = "TRAP_ANCHOR"
        comp = o["comp"]
        if i in (1, 4):  # entered under a variant record
            vcomp = {"key": f"T{i}", "name": variant_name(rng, comp, 0), "short": comp["short"], "domain": "",
                     "city": comp["city"], "variant_of": comp["key"]}
            extra_companies.append(vcomp)
        else:
            vcomp = comp
        kind = trap_kinds[i]
        if kind in kinds_used.get(comp["key"], set()) and kind != "site":
            kind = "site"
        kinds_used.setdefault(comp["key"], set()).add(kind)
        create = o["create"] + timedelta(days=rng.randint(3, 55), minutes=rng.randint(1, 50))
        create = min(create, NOW - timedelta(days=1))
        last = rand_time(rng, TODAY - timedelta(days=rng.randint(1, 15)))
        if last < create:
            last = create + timedelta(hours=3)
        amt = int(round(o["amount"] * rng.uniform(0.85, 1.15) / 100.0) * 100)
        t = {"comp": vcomp, "kind": kind, "stage": pick_stage(rng), "amount": amt, "close": close_date_open(rng),
             "create": create, "last": last, "owner": o["owner"], "product": o["product"], "seats": o["seats"],
             "site": rng.choice([c for c in CITIES if c != comp["city"]]), "plant": "TRAP", "other": o}
        t["name"] = deal_name(dict(t, comp=comp))
        deals.append(t)

    def plant(code, n, pred, fn):
        for _ in range(n):
            d = take(pred)
            d["plant"] = code
            fn(d)

    def stale(lo, hi):
        def f(d):
            d["last"] = rand_time(rng, TODAY - timedelta(days=rng.randint(lo, hi)))
            if d["create"] > d["last"]:
                d["create"] = d["last"] - timedelta(days=rng.randint(5, 60))
        return f

    plant("STALE", 6, lambda d: True, stale(31, 60))
    plant("ZOMBIE", 8, lambda d: True, stale(61, 150))
    plant("PAST_CLOSE", 6, lambda d: True,
          lambda d: d.update(close=TODAY - timedelta(days=rng.randint(1, 30))))
    plant("NO_AMOUNT", 8, lambda d: d["stage"] != "Appointment Scheduled",
          lambda d: d.update(true_amount=d["amount"], amount=None))
    plant("NO_CLOSE_DATE", 4, lambda d: True, lambda d: d.update(close=None))
    plant("NO_OWNER", 3, lambda d: True, lambda d: d.update(owner=""))
    won = [d for d in deals if d["stage"] == "Closed Won"]
    rng.shuffle(won)
    for d in won[:3]:
        d["plant"] = "WON_FUTURE_DATE"
        d["close"] = TODAY + timedelta(days=rng.randint(3, 40))

    # --- ids: HubSpot ids grow with creation time ---------------------------------------------------
    all_comps = comps + extra_companies
    first_seen = {}
    for d in deals:
        k = d["comp"]["key"]
        first_seen[k] = min(first_seen.get(k, d["create"]), d["create"])
    for c in all_comps:
        c["created"] = first_seen.get(c["key"], NOW - timedelta(days=300)) - timedelta(days=rng.randint(0, 90), hours=rng.randint(0, 8))
    nid = 18_402_000_000
    for c in sorted(all_comps, key=lambda c: c["created"]):
        nid += rng.randint(3_000, 900_000)
        c["id"] = str(nid)
    nid = 31_870_000_000
    for d in sorted(deals, key=lambda d: d["create"]):
        nid += rng.randint(5_000, 2_000_000)
        d["id"] = str(nid)

    # --- write ----------------------------------------------------------------------------------------
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "deals.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(DEAL_COLS)
        for d in sorted(deals, key=lambda d: int(d["id"])):
            w.writerow([d["id"], d["name"], "Sales Pipeline", d["stage"],
                        "" if d["amount"] is None else d["amount"], fmt_d(d["close"]), fmt_dt(d["create"]),
                        fmt_dt(d["last"]), d["owner"], d["comp"]["id"], d["comp"]["name"]])
    with open(os.path.join(a.out, "companies.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COMPANY_COLS)
        for c in sorted(all_comps, key=lambda c: int(c["id"])):
            if c["key"] not in first_seen:
                continue  # a company with no deals isn't exported here
            w.writerow([c["id"], c["name"], c["domain"], c["city"], "Germany", fmt_dt(c["created"])])

    for d in deals:
        p = d["plant"]
        if p in ("DUP_EXACT", "DUP_FUZZY"):
            key_rows.append([p, d["id"], d["other"]["id"], "", "copy is record_id; original is other_record_id"])
        elif p == "TRAP":
            key_rows.append([p, d["id"], d["other"]["id"], "", "NOT a duplicate: different business at the same company"])
        elif p == "NO_AMOUNT":
            key_rows.append([p, d["id"], "", d["true_amount"], ""])
        elif p in ("STALE", "ZOMBIE", "PAST_CLOSE", "NO_CLOSE_DATE", "NO_OWNER", "WON_FUTURE_DATE"):
            key_rows.append([p, d["id"], "", "", ""])
    key_path = a.key or os.path.join(os.path.dirname(__file__), "..", "test", "answer-key", f"seed-{a.seed}.csv")
    os.makedirs(os.path.dirname(key_path), exist_ok=True)
    with open(key_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(KEY_COLS)
        for r in sorted(key_rows, key=lambda r: (r[0], int(r[1]))):
            w.writerow(r)
    print(f"seed {a.seed}: {len(deals)} deals, {len(first_seen)} companies, {len(key_rows)} answer-key rows")


if __name__ == "__main__":
    main()
