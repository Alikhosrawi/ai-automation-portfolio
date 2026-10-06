"""Monday pipeline hygiene run: read the HubSpot export, flag problems, clean the Q4 forecast, write the note.

Usage (from this folder):
  python3 run_weekly.py --export ../data/export --out ../data/outbox --ai replay

Sends nothing. Everything goes into the outbox folder as files, and the note that would be posted is logged
in 5-would-send-log.csv.
"""
import argparse
import csv
import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime

import ai_steps
import hygiene_checks as hc

HERE = os.path.dirname(os.path.abspath(__file__))
NOW = datetime(2026, 10, 12, 7, 30)  # the demo's fixed "now"


def half_up(x, digits=0):
    """Round halves up, the same way the n8n (JavaScript) copy does. Python's round() and format() round halves to
    even, so 11.25 became 11.2 here and 11.3 in n8n."""
    f = 10 ** digits
    return math.floor(x * f + 0.5) / f


def eur(x):
    return f"€{int(half_up(x)):,}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", default=os.path.join(HERE, "..", "data", "export"))
    ap.add_argument("--out", default=os.path.join(HERE, "..", "data", "outbox"))
    ap.add_argument("--ai", choices=["replay", "live", "off"], default="replay")
    ap.add_argument("--recorded", default=os.path.join(HERE, "..", "data", "ai"))
    ap.add_argument("--now", default=NOW.strftime("%Y-%m-%d %H:%M"))
    a = ap.parse_args()
    now = datetime.strptime(a.now, "%Y-%m-%d %H:%M")
    today = now.date()
    os.makedirs(a.out, exist_ok=True)

    deals, _ = hc.load(a.export)

    # 1. rules
    flags = hc.rule_flags(deals, today)

    # 2. duplicates: exact by rule, the rest judged by the AI
    exact, candidates = hc.duplicate_pairs(deals)
    verdicts = ai_steps.judge_pairs(candidates, a.ai, os.path.join(a.recorded, "duplicate-verdicts.csv"))
    dup_rows = []
    for p in exact:
        dup_rows.append((p, "DUPLICATE", "same company record and same deal name", "rule"))
    for p in candidates:
        v, why, src = verdicts[ai_steps.pair_id(p)]
        dup_rows.append((p, v, why, src))
    dup_copies = {p["copy"]["Record ID"] for p, v, _, _ in dup_rows if v == "DUPLICATE"}
    for p, v, why, src in dup_rows:
        if v == "DUPLICATE":
            flags.append((p["copy"], "DUPLICATE",
                          f"copy of {p['original']['Record ID']} ({p['original']['Deal Name']}); {why}"))

    # 3. forecast
    zombies = {d["Record ID"] for d, code, _ in flags if code == "ZOMBIE"}
    fc = hc.forecast(deals, dup_copies, zombies)

    # 4. outbox files
    owner_of = lambda d: d["Deal owner"].strip() or "(no owner)"
    order = list(hc.ACTION)
    flags.sort(key=lambda f: (owner_of(f[0]), order.index(f[1]), -f[0]["_amount"]))
    with open(os.path.join(a.out, "1-fix-list.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["owner", "record_id", "deal", "stage", "amount", "check", "detail", "what_to_do"])
        for d, code, detail in flags:
            w.writerow([owner_of(d), d["Record ID"], d["Deal Name"], d["Deal Stage"], d["Amount"], code, detail, hc.ACTION[code]])

    with open(os.path.join(a.out, "2-duplicate-review.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair_id", "original_id", "original_deal", "original_company", "copy_id", "copy_deal", "copy_company",
                    "why_compared", "amount_gap_pct", "verdict", "reason", "decided_by"])
        for p, v, why, src in dup_rows:
            o, c = p["original"], p["copy"]
            w.writerow([ai_steps.pair_id(p), o["Record ID"], o["Deal Name"], o["Associated Company (Primary)"],
                        c["Record ID"], c["Deal Name"], c["Associated Company (Primary)"], p["how"],
                        f"{half_up(100 * hc.amount_gap(o, c), 1):.1f}", v, why, src])

    with open(os.path.join(a.out, "3-forecast-bridge.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["step", "record_id", "deal", "owner", "stage", "amount", "weighted", "running_total"])
        run = fc["raw"]
        w.writerow(["Q4 weighted forecast as exported", "", f"{len(fc['q4_deals'])} open deals closing in Q4", "", "", "", "", int(half_up(run))])
        for label, rows in [("minus duplicate copy", fc["dup_rows"]), ("minus no activity for over 60 days", fc["zombie_rows"])]:
            for d in sorted(rows, key=lambda d: -hc.weighted(d)):
                run -= hc.weighted(d)
                w.writerow([label, d["Record ID"], d["Deal Name"], owner_of(d), d["Deal Stage"], d["Amount"], int(half_up(hc.weighted(d))), int(half_up(run))])
        w.writerow(["Q4 weighted forecast, cleaned", "", "", "", "", "", "", int(half_up(fc["cleaned"]))])
        for d in fc["no_amount_rows"]:
            w.writerow(["not counted: no amount", d["Record ID"], d["Deal Name"], owner_of(d), d["Deal Stage"], "", "", ""])

    # 5. facts for the note (every number the note may use)
    per_owner = Counter(owner_of(d) for d, _, _ in flags)
    dup_amt = sum(hc.weighted(d) for d in fc["dup_rows"])
    zom_amt = sum(hc.weighted(d) for d in fc["zombie_rows"])
    unsure = [p for p, v, _, _ in dup_rows if v == "UNSURE"]
    top = lambda rows: [{"deal": d["Deal Name"], "owner": owner_of(d), "weighted": eur(hc.weighted(d))}
                        for d in sorted(rows, key=lambda d: -hc.weighted(d))[:3]]
    facts = {
        "date": now.strftime("%a %d %b %Y").replace(" 0", " "),
        "q4_forecast_as_exported": eur(fc["raw"]),
        "q4_forecast_cleaned": eur(fc["cleaned"]),
        "difference": eur(fc["raw"] - fc["cleaned"]),
        "difference_pct_of_exported": f"{half_up(100 * (fc['raw'] - fc['cleaned']) / fc['raw'], 1):.1f}%",
        "q4_open_deals": len(fc["q4_deals"]),
        "removed_duplicate_copies": {"deals": len(fc["dup_rows"]), "weighted": eur(dup_amt), "largest": top(fc["dup_rows"])},
        "removed_no_activity_over_60_days": {"deals": len(fc["zombie_rows"]), "weighted": eur(zom_amt), "largest": top(fc["zombie_rows"])},
        "not_counted_no_amount": {"deals": len(fc["no_amount_rows"]), "names": [d["Deal Name"] for d in fc["no_amount_rows"]],
                                  "meaning": "These count as zero in both figures, so once their amounts are filled in, the cleaned figure can only go up."},
        "fix_this_week": [{"owner": o, "items": n} for o, n in sorted(per_owner.items(), key=lambda x: (-x[1], x[0]))],
        "items_total": len(flags),
        "duplicate_pairs_for_a_person": len(unsure),
    }
    with open(os.path.join(a.out, "facts.json"), "w", encoding="utf-8") as f:
        json.dump(facts, f, indent=2, ensure_ascii=False)

    # 6. the note: AI draft -> number guard -> else the plain template
    note, source, guard_problems = None, "template", []
    if a.ai != "off":
        draft = None
        if a.ai == "live":
            draft = ai_steps.call_claude(ai_steps.note_prompt(facts))
        else:
            p = os.path.join(a.recorded, "weekly-note.md")
            draft = open(p, encoding="utf-8").read().strip() if os.path.exists(p) else None
        if draft:
            guard_problems = ai_steps.number_guard(draft, facts)
            if guard_problems:
                source = "template (AI draft failed the number guard)"
            else:
                note, source = draft, ("AI (recorded)" if a.ai == "replay" else f"AI ({ai_steps.DEFAULT_MODEL})")
    if note is None:
        note = template_note(facts)
    with open(os.path.join(a.out, "4-monday-note.md"), "w", encoding="utf-8") as f:
        f.write(note + "\n")
    with open(os.path.join(a.out, "4b-number-guard.txt"), "w", encoding="utf-8") as f:
        f.write(f"note used: {source}\n")
        f.write("numbers in the AI draft not found in facts.json: " + (", ".join(guard_problems) if guard_problems else "none") + "\n")

    # 7. one to-do message per owner (would be sent as a direct message; nothing is sent)
    by_owner = defaultdict(list)
    for d, code, detail in flags:
        by_owner[owner_of(d)].append((d, code))
    with open(os.path.join(a.out, "6-owner-messages.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["to", "items", "message"])
        for o in [x["owner"] for x in facts["fix_this_week"]]:
            w.writerow([owner_message_to(o), len(by_owner[o]), owner_message(o, by_owner[o])])

    with open(os.path.join(a.out, "5-would-send.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["logged_at", "channel", "what", "file", "note_source"])
        w.writerow([now.strftime("%Y-%m-%d %H:%M"), "#sales-leadership (would post, nothing sent)", "Monday pipeline hygiene note", "4-monday-note.md", source])
        w.writerow([now.strftime("%Y-%m-%d %H:%M"), "direct messages (would send, nothing sent)", f"{len(by_owner)} owner to-do messages", "6-owner-messages.csv", "template"])

    print(json.dumps({"q4_raw": int(half_up(fc["raw"])), "q4_cleaned": int(half_up(fc["cleaned"])), "flags": len(flags),
                      "exact_dups": len(exact), "candidates": len(candidates),
                      "verdicts": dict(Counter(v for _, v, _, _ in dup_rows)), "note": source}))


def owner_message_to(owner):
    return "Head of RevOps (deals with no owner)" if owner == "(no owner)" else owner


def owner_message(owner, items):
    """The Monday direct message: what this person should fix, most urgent first."""
    hi = "These deals have no owner. Please assign them:" if owner == "(no owner)" else \
        f"Hi {owner.split()[0]}, {len(items)} things in HubSpot need you before this week's forecast call:"
    lines = [hi] + [f"- {d['Deal Name']}: {hc.ACTION[code]}" for d, code in items]
    return "\n".join(lines)


def template_note(f):
    """The plain note, used when the AI is off or its draft fails the number guard."""
    lines = [f"Pipeline hygiene, {f['date']}",
             f"Q4 weighted forecast: {f['q4_forecast_as_exported']} as exported, {f['q4_forecast_cleaned']} after cleaning "
             f"({f['difference']} less, {f['difference_pct_of_exported']}).",
             f"- Duplicate copies removed: {f['removed_duplicate_copies']['deals']} deals, {f['removed_duplicate_copies']['weighted']}.",
             f"- No activity for over 60 days, removed: {f['removed_no_activity_over_60_days']['deals']} deals, "
             f"{f['removed_no_activity_over_60_days']['weighted']}.",
             f"- Not counted because the amount is empty: {f['not_counted_no_amount']['deals']} deals.",
             "Fix this week: " + ", ".join(f"{o['owner']} {o['items']}" for o in f["fix_this_week"]) + ".",
             f"Duplicate pairs a person needs to decide: {f['duplicate_pairs_for_a_person']}."]
    return "\n".join(lines)


if __name__ == "__main__":
    main()
