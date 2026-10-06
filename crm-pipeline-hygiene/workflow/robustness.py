"""The 20 other histories fixed in the pre-registration (seeds 20261013-20261032).

For each seed: make the export, run the weekly check with the AI off, score the rule checks, and score the duplicate
step two ways: how many planted duplicates reached the AI step as a candidate (the ceiling for the AI), and the
rules-only decision. The AI judge itself is run on the primary seed only. Writes test/results/robustness-20-seeds.csv.
"""
import csv
import json
import os
import statistics
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SEEDS = range(20261013, 20261033)


def main():
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for s in SEEDS:
            exp, out, key = f"{tmp}/exp-{s}", f"{tmp}/out-{s}", f"{tmp}/key-{s}.csv"
            run = lambda *args: subprocess.run([sys.executable, *args], cwd=HERE, check=True, capture_output=True, text=True)
            run("generate_export.py", "--seed", str(s), "--out", exp, "--key", key)
            run("validate_export.py", exp, key)
            run("run_weekly.py", "--export", exp, "--out", out, "--ai", "off")
            res = json.loads(run("score.py", "--export", exp, "--outbox", out, "--key", key).stdout)
            r = {"seed": s}
            r["rule_planted"] = sum(v["planted"] for v in res["rules"].values())
            r["rule_caught"] = sum(v["caught"] for v in res["rules"].values())
            r["rule_false_flags"] = sum(v["false_flags"] for v in res["rules"].values())
            ro = res["duplicates_rules_only"]
            for code in ("DUP_EXACT", "DUP_FUZZY"):
                c = ro["by_code"][code]
                r[f"{code.lower()}_reached_ai_step"] = c["reached_ai"]
                r[f"{code.lower()}_caught_rules_only"] = c["caught"]
            r["rules_only_false_flags"] = ro["false_flags"]
            r["rules_only_false_flags_on_traps"] = ro["false_flags_on_traps"]
            r["candidate_pairs_for_ai"] = res["candidate_pairs"]
            r["raw_minus_true_pct"] = res["forecast"]["raw_minus_true_pct"]
            rows.append(r)
            print(s, r)
    path = os.path.join(HERE, "..", "test", "results", "robustness-20-seeds.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print("\nmedian (range) over 20 seeds:")
    for k in rows[0]:
        if k == "seed":
            continue
        v = [r[k] for r in rows]
        print(f"  {k}: {statistics.median(v)} ({min(v)}-{max(v)})")


if __name__ == "__main__":
    main()
