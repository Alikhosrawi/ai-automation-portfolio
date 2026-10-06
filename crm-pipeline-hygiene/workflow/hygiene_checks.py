"""The weekly pipeline hygiene check: rules, duplicate candidates and the Q4 forecast maths.

Reads a HubSpot deals + companies export. Never reads the answer key. Rules follow test/PREREGISTRATION.md.
Python 3 standard library only.
"""
import csv
import re
import unicodedata
from datetime import datetime, date
from difflib import SequenceMatcher

PROB = {"Appointment Scheduled": 0.2, "Qualified To Buy": 0.4, "Presentation Scheduled": 0.6,
        "Decision Maker Bought-In": 0.8, "Contract Sent": 0.9, "Closed Won": 1.0, "Closed Lost": 0.0}
CLOSED = ("Closed Won", "Closed Lost")
Q4 = (date(2026, 10, 1), date(2026, 12, 31))
LEGAL_TOKENS = {"gmbh", "ggmbh", "mbh", "ag", "se", "kg", "co", "ug", "ohg", "kgaa", "und"}

# what each check means for the owner, in plain words
ACTION = {
    "NO_AMOUNT": "Add the amount (it counts as €0 in the forecast until then)",
    "NO_CLOSE_DATE": "Add a close date (it is in no quarter's forecast until then)",
    "NO_OWNER": "Give it an owner",
    "PAST_CLOSE": "The close date has passed: move it or close the deal",
    "STALE": "No activity for 31-60 days: book a next step or downgrade it",
    "ZOMBIE": "No activity for over 60 days: close it as lost, or prove it's alive",
    "WON_FUTURE_DATE": "Closed won, but the close date is in the future: fix the date",
    "DUPLICATE": "Looks like a second copy of another deal: merge it into the original",
}


def parse_dt(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M") if s else None


def parse_d(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


def load(export_dir):
    deals = list(csv.DictReader(open(f"{export_dir}/deals.csv", encoding="utf-8-sig")))
    comps = {r["Record ID"]: r for r in csv.DictReader(open(f"{export_dir}/companies.csv", encoding="utf-8-sig"))}
    for d in deals:
        d["_open"] = d["Deal Stage"] not in CLOSED
        d["_amount"] = float(d["Amount"]) if d["Amount"].strip() else 0.0
        d["_close"] = parse_d(d["Close Date"])
        d["_create"] = parse_dt(d["Create Date"])
        d["_last"] = parse_dt(d["Last Activity Date"]) or d["_create"]
        d["_company"] = comps.get(d["Associated Company IDs (Primary)"], {})
    return deals, comps


def norm_company(name):
    s = name.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(t for t in s.split() if t not in LEGAL_TOKENS)


def norm_deal_name(name):
    return " ".join(name.lower().split())


def company_match(a, b):
    """(match?, how, similarity). Same record, same domain, or similar name."""
    if a["Associated Company IDs (Primary)"] == b["Associated Company IDs (Primary)"]:
        return True, "same company record", 1.0
    da, db = a["_company"].get("Company Domain Name", ""), b["_company"].get("Company Domain Name", "")
    sim = SequenceMatcher(None, norm_company(a["Associated Company (Primary)"]),
                          norm_company(b["Associated Company (Primary)"])).ratio()
    if da and db and da == db:
        return True, "same domain", sim
    return sim >= 0.80, f"name similarity {sim:.2f}", sim


def amount_gap(a, b):
    hi = max(a["_amount"], b["_amount"])
    return 0.0 if hi == 0 else abs(a["_amount"] - b["_amount"]) / hi


def copy_of(a, b):
    """Which row is the copy: created later; same day -> higher Record ID. Returns (copy, original)."""
    if a["_create"].date() != b["_create"].date():
        return (a, b) if a["_create"] > b["_create"] else (b, a)
    return (a, b) if int(a["Record ID"]) > int(b["Record ID"]) else (b, a)


def rule_flags(deals, today):
    flags = []
    for d in deals:
        if d["Deal Stage"] == "Closed Won" and d["_close"] and d["_close"] > today:
            flags.append((d, "WON_FUTURE_DATE", f"closed won, close date {d['Close Date']}"))
        if not d["_open"]:
            continue
        if d["_amount"] == 0 and d["Deal Stage"] != "Appointment Scheduled":
            flags.append((d, "NO_AMOUNT", f"stage {d['Deal Stage']}, no amount"))
        if not d["_close"]:
            flags.append((d, "NO_CLOSE_DATE", "no close date"))
        if not d["Deal owner"].strip():
            flags.append((d, "NO_OWNER", "no owner"))
        if d["_close"] and d["_close"] < today:
            flags.append((d, "PAST_CLOSE", f"close date {d['Close Date']}, {(today - d['_close']).days} days ago"))
        idle = (today - d["_last"].date()).days
        if 31 <= idle <= 60:
            flags.append((d, "STALE", f"last activity {idle} days ago"))
        elif idle > 60:
            flags.append((d, "ZOMBIE", f"last activity {idle} days ago"))
    return flags


def duplicate_pairs(deals):
    """Exact duplicates (rules only) and the candidate pairs that go to the AI judge."""
    opn = [d for d in deals if d["_open"]]
    exact, candidates = [], []
    for i in range(len(opn)):
        for j in range(i + 1, len(opn)):
            a, b = opn[i], opn[j]
            if (a["Associated Company IDs (Primary)"] == b["Associated Company IDs (Primary)"]
                    and norm_deal_name(a["Deal Name"]) == norm_deal_name(b["Deal Name"])):
                c, o = copy_of(a, b)
                exact.append({"copy": c, "original": o, "how": "same company record and same deal name"})
                continue
            match, how, sim = company_match(a, b)
            if not match:
                continue
            gap = amount_gap(a, b)
            days = abs((a["_create"] - b["_create"]).days)
            if gap <= 0.25 and days <= 90:
                c, o = copy_of(a, b)
                candidates.append({"copy": c, "original": o, "how": how, "sim": sim, "gap": gap, "days": days})
    return exact, candidates


def rules_only_duplicate(p):
    """The comparison without AI (fixed in the pre-registration)."""
    strong_company = p["how"] in ("same company record", "same domain") or p["sim"] >= 0.85
    return strong_company and p["gap"] <= 0.10


def in_q4(d):
    return d["_open"] and d["_close"] is not None and Q4[0] <= d["_close"] <= Q4[1]


def weighted(d):
    return d["_amount"] * PROB[d["Deal Stage"]]


def forecast(deals, dup_copies, zombies):
    """Raw Q4 weighted forecast and the cleaned one, with the deals behind each step."""
    q4 = [d for d in deals if in_q4(d)]
    raw = sum(weighted(d) for d in q4)
    dup_rows = [d for d in q4 if d["Record ID"] in dup_copies]
    zombie_rows = [d for d in q4 if d["Record ID"] in zombies and d["Record ID"] not in dup_copies]
    cleaned = raw - sum(weighted(d) for d in dup_rows) - sum(weighted(d) for d in zombie_rows)
    no_amount = [d for d in q4 if d["_amount"] == 0]
    return {"q4_deals": q4, "raw": raw, "dup_rows": dup_rows, "zombie_rows": zombie_rows,
            "cleaned": cleaned, "no_amount_rows": no_amount}
