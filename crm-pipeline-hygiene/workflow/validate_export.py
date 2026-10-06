"""Check the generator did what PREREGISTRATION.md says: the base is clean, and each planted problem is exactly as described.
Reads the export and the answer key (this is a test helper, not part of the weekly check)."""
import csv, sys
from datetime import datetime, date
TODAY = date(2026, 10, 12)
exp, key = sys.argv[1], sys.argv[2]
deals = {r["Record ID"]: r for r in csv.DictReader(open(f"{exp}/deals.csv", encoding="utf-8"))}
comps = {r["Record ID"]: r for r in csv.DictReader(open(f"{exp}/companies.csv", encoding="utf-8"))}
ans = list(csv.DictReader(open(key, encoding="utf-8")))
planted = {a["record_id"]: a["code"] for a in ans}
d = lambda s: datetime.strptime(s, "%Y-%m-%d").date() if s else None
dt = lambda s: datetime.strptime(s, "%Y-%m-%d %H:%M") if s else None
probs = []
opn = lambda r: r["Deal Stage"] not in ("Closed Won", "Closed Lost")
for i, r in deals.items():
    code = planted.get(i)
    age = (TODAY - dt(r["Last Activity Date"]).date()).days
    if dt(r["Last Activity Date"]) < dt(r["Create Date"]): probs.append((i, "activity before create"))
    if dt(r["Last Activity Date"]) > datetime(2026, 10, 12, 7, 30): probs.append((i, "activity after now"))
    if r["Associated Company IDs (Primary)"] not in comps: probs.append((i, "unknown company"))
    if opn(r):
        if code not in ("NO_AMOUNT",) and not r["Amount"]: probs.append((i, "amount missing, not planted"))
        if code != "NO_CLOSE_DATE" and not r["Close Date"]: probs.append((i, "close missing, not planted"))
        if code != "NO_OWNER" and not r["Deal owner"]: probs.append((i, "owner missing, not planted"))
        if code != "PAST_CLOSE" and r["Close Date"] and d(r["Close Date"]) < TODAY: probs.append((i, "past close, not planted"))
        if code not in ("STALE", "ZOMBIE") and age > 25: probs.append((i, f"activity {age}d, not planted"))
        if code == "STALE" and not 31 <= age <= 60: probs.append((i, "STALE out of range"))
        if code == "ZOMBIE" and not 61 <= age <= 150: probs.append((i, "ZOMBIE out of range"))
    elif r["Deal Stage"] == "Closed Won" and d(r["Close Date"]) > TODAY and code != "WON_FUTURE_DATE":
        probs.append((i, "won future, not planted"))
for a in ans:
    if a["code"] in ("DUP_EXACT", "DUP_FUZZY", "TRAP"):
        c, o = deals[a["record_id"]], deals[a["other_record_id"]]
        ratio = abs(float(c["Amount"]) - float(o["Amount"])) / max(float(c["Amount"]), float(o["Amount"]))
        lim = {"DUP_EXACT": 0, "DUP_FUZZY": 0.1, "TRAP": 0.15}[a["code"]]
        if ratio > lim + 0.006: probs.append((a["record_id"], f"{a['code']} amount gap {ratio:.3f}"))
        if a["code"] == "DUP_EXACT" and (c["Deal Name"] != o["Deal Name"] or c["Associated Company IDs (Primary)"] != o["Associated Company IDs (Primary)"]):
            probs.append((a["record_id"], "exact dup differs"))
        if a["code"] == "DUP_FUZZY" and c["Associated Company IDs (Primary)"] == o["Associated Company IDs (Primary)"]:
            probs.append((a["record_id"], "fuzzy dup shares company record"))
# no two base deals at one company with the same name
seen = {}
for i, r in deals.items():
    k = (r["Associated Company IDs (Primary)"], " ".join(r["Deal Name"].lower().split()))
    if k in seen and planted.get(i) != "DUP_EXACT" and planted.get(seen[k]) != "DUP_EXACT":
        probs.append((i, f"same name as {seen[k]}"))
    seen.setdefault(k, i)
print(f"{len(deals)} deals, {len(ans)} answer-key rows, problems: {len(probs)}")
for p in probs[:30]: print("  ", p)
sys.exit(1 if probs else 0)
