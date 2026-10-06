"""Score a weekly run against the answer key, exactly as test/PREREGISTRATION.md says.

  python3 score.py --export ../data/export --outbox ../data/outbox --key ../test/answer-key/seed-20261012.csv

Also used by robustness.py for the 20 other seeds (rules + candidates + rules-only duplicates, no AI).
"""
import argparse
import csv
import json
from collections import defaultdict

import hygiene_checks as hc

RULE_CODES = ["STALE", "ZOMBIE", "PAST_CLOSE", "NO_AMOUNT", "NO_CLOSE_DATE", "NO_OWNER", "WON_FUTURE_DATE"]


def load_key(path):
    key = list(csv.DictReader(open(path, encoding="utf-8")))
    planted = defaultdict(set)
    dups, traps, true_amounts = set(), set(), {}
    for k in key:
        if k["code"] in ("DUP_EXACT", "DUP_FUZZY"):
            dups.add((k["record_id"], k["other_record_id"], k["code"]))
        elif k["code"] == "TRAP":
            traps.add((k["record_id"], k["other_record_id"]))
        else:
            planted[k["code"]].add(k["record_id"])
        if k["code"] == "NO_AMOUNT":
            true_amounts[k["record_id"]] = float(k["true_amount"])
    return planted, dups, traps, true_amounts


def score_rules(rule_flags, planted):
    out = {}
    flagged = defaultdict(set)
    for rid, code in rule_flags:
        flagged[code].add(rid)
    for code in RULE_CODES:
        out[code] = {"planted": len(planted[code]), "caught": len(flagged[code] & planted[code]),
                     "false_flags": len(flagged[code] - planted[code])}
    return out


def score_dups(flagged_pairs, unsure_pairs, dups, traps, candidate_pairs=None):
    """flagged_pairs: set of (copy_id, original_id) called duplicate."""
    true_pairs = {(c, o) for c, o, _ in dups}
    by_code = defaultdict(lambda: {"planted": 0, "caught": 0, "unsure": 0, "reached_ai": 0})
    for c, o, code in sorted(dups, key=lambda x: (x[2], x[0])):
        by_code[code]["planted"] += 1
        by_code[code]["caught"] += (c, o) in flagged_pairs
        by_code[code]["unsure"] += (c, o) in unsure_pairs
        if candidate_pairs is not None:
            by_code[code]["reached_ai"] += (c, o) in candidate_pairs
    false = flagged_pairs - true_pairs
    trap_pairs = {(c, o) for c, o in traps}
    return {"by_code": dict(by_code), "false_flags": len(false),
            "false_flags_on_traps": len(false & trap_pairs),
            "traps_marked_unsure": len(unsure_pairs & trap_pairs),
            "false_flag_pairs": sorted(false)}


def true_forecast(deals, dups, planted, true_amounts):
    copies = {c for c, _, _ in dups}
    total = 0.0
    for d in deals:
        if not hc.in_q4(d) or d["Record ID"] in copies or d["Record ID"] in planted["ZOMBIE"]:
            continue
        amt = true_amounts.get(d["Record ID"], d["_amount"])
        total += amt * hc.PROB[d["Deal Stage"]]
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", default="../data/export")
    ap.add_argument("--outbox", default="../data/outbox")
    ap.add_argument("--key", default="../test/answer-key/seed-20261012.csv")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    planted, dups, traps, true_amounts = load_key(a.key)
    deals, _ = hc.load(a.export)
    fix = list(csv.DictReader(open(f"{a.outbox}/1-fix-list.csv", encoding="utf-8")))
    rules = score_rules([(r["record_id"], r["check"]) for r in fix if r["check"] != "DUPLICATE"], planted)
    review = list(csv.DictReader(open(f"{a.outbox}/2-duplicate-review.csv", encoding="utf-8")))
    ai_flag = {(r["copy_id"], r["original_id"]) for r in review if r["verdict"] == "DUPLICATE"}
    ai_unsure = {(r["copy_id"], r["original_id"]) for r in review if r["verdict"] == "UNSURE"}
    ai = score_dups(ai_flag, ai_unsure, dups, traps)

    # the rules-only comparison, on the same candidate pairs
    exact, cands = hc.duplicate_pairs(deals)
    ro = {(p["copy"]["Record ID"], p["original"]["Record ID"]) for p in exact}
    ro |= {(p["copy"]["Record ID"], p["original"]["Record ID"]) for p in cands if hc.rules_only_duplicate(p)}
    rules_only = score_dups(ro, set(), dups, traps,
                            candidate_pairs={(p["copy"]["Record ID"], p["original"]["Record ID"]) for p in cands + exact})

    facts = json.load(open(f"{a.outbox}/facts.json", encoding="utf-8"))
    num = lambda s: float(s.replace("€", "").replace(",", ""))
    raw, cleaned = num(facts["q4_forecast_as_exported"]), num(facts["q4_forecast_cleaned"])
    truth = true_forecast(deals, dups, planted, true_amounts)
    res = {"rules": rules, "duplicates_ai": ai, "duplicates_rules_only": rules_only,
           "candidate_pairs": len(cands), "exact_pairs": len(exact),
           "forecast": {"raw": round(raw), "cleaned": round(cleaned), "true": round(truth),
                        "raw_minus_true": round(raw - truth), "raw_minus_true_pct": round(100 * (raw - truth) / truth, 1),
                        "cleaned_minus_true": round(cleaned - truth), "cleaned_minus_true_pct": round(100 * (cleaned - truth) / truth, 1)}}
    s = json.dumps(res, indent=2)
    if a.json:
        open(a.json, "w").write(s + "\n")
    print(s)


if __name__ == "__main__":
    main()
