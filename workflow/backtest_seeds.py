# Secondary robustness check from backtest/PREREGISTRATION.md: the same backtest on 20 more synthetic histories
# (seeds 20261005-20261024), reported as median and range. Never used to choose or replace the primary result (seed 20261004).
#   python3 backtest_seeds.py      -> backtest/results/robustness-20-seeds.csv
import csv, os, statistics, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); W = os.path.dirname(os.path.abspath(__file__))
KEYS = [f"{p}_stockout_weeks" for p in ("agent", "same_order", "naive_rule")] + [f"{p}_weeks_above_safety" for p in ("agent", "same_order", "naive_rule")] \
    + ["agent_forecast_pct_error", "naive_forecast_pct_error"]
rows = []
with tempfile.TemporaryDirectory() as tmp:
    for seed in range(20261005, 20261025):
        h, o = f"{tmp}/{seed}/history", f"{tmp}/{seed}/results"
        subprocess.run([sys.executable, f"{W}/generate_backtest_history.py", str(seed), h], check=True, capture_output=True)
        subprocess.run([sys.executable, f"{W}/backtest.py", h, o, "--quiet"], check=True, capture_output=True)
        summ = list(csv.DictReader(open(f"{o}/backtest-summary.csv")))
        tot = next(r for r in summ if r["item_id"] == "ALL")
        per = [r for r in summ if r["item_id"] != "ALL"]
        row = dict(seed=seed, **{k: tot[k] for k in KEYS})
        row["items_agent_better_forecast"] = sum(r["vs_naive_forecast_error"] == "win" for r in per)
        rows.append(row)
cols = list(rows[0].keys())
out = rows + [dict(seed=lab, **{k: (round(fn([float(r[k]) for r in rows]), 2)) for k in cols[1:]}) for lab, fn in
              [("median", statistics.median), ("min", min), ("max", max)]]
with open(f"{HERE}/backtest/results/robustness-20-seeds.csv", "w", newline="") as f:
    w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(out)
for r in out[-3:]: print(r)
