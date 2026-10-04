# Backtest v2: the fair re-test, exactly as written in backtest/PREREGISTRATION.md (v1 is kept in build-history/backtest-v1-steady-history/).
#
# Walk-forward over 41 weeks (5 Jan - 12 Oct 2026) of a realistic, varied, SYNTHETIC history (workflow/generate_backtest_history.py):
# every Friday each policy decides next week's order using only what was known that Friday; then the week is played on a simulated shelf.
#   agent       reorder_maths.plan() unchanged (the same maths as the n8n workflow) with that Friday's count and next week's Friday bookings
#   same order  a standing order that never changes: ceil(average recorded use of the 8 weeks 3 Nov - 22 Dec / pack size)
#   naive rule  the agent's order rule, but forecast = recorded use of the week that is ending (from the count)
# Information advantage, plainly: the agent sees next week's bookings; the baselines don't use them. Bookings include cancellations and
# no-shows and miss late bookings, so they are not the truth either.
#   python3 backtest.py [history_dir] [out_dir] [--quiet]     defaults: backtest/data -> backtest/results
import csv, math, datetime as dt, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reorder_maths import plan, rd, add_working_days
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = [a for a in sys.argv[1:] if not a.startswith("--")]; QUIET = "--quiet" in sys.argv
H = args[0] if len(args) > 0 else f"{HERE}/backtest/data"
OUT = args[1] if len(args) > 1 else f"{HERE}/backtest/results"; os.makedirs(OUT, exist_ok=True)
items, rates = rd(f"{HERE}/data/items.csv"), rd(f"{HERE}/data/usage-rates.csv")
sessions, usage = rd(f"{H}/sessions-held-per-week.csv"), rd(f"{H}/usage-recorded-per-week.csv")
bookings_all, removal, errs = rd(f"{H}/bookings-on-friday.csv"), rd(f"{H}/removal-per-week.csv"), rd(f"{H}/count-errors.csv")
D = dt.date
def days(a, b): return {a + dt.timedelta(days=k) for k in range((b - a).days + 1)}
PUBLIC = {D(2025, 12, 25), D(2025, 12, 26), D(2026, 1, 1), D(2026, 4, 3), D(2026, 4, 6), D(2026, 5, 1), D(2026, 5, 14), D(2026, 5, 25)}
CLOSED = PUBLIC | days(D(2025, 12, 24), D(2026, 1, 1))
def is_open(d): return d.weekday() < 5 and d not in CLOSED
def open_days(w): return [w + dt.timedelta(days=k) for k in range(5) if is_open(w + dt.timedelta(days=k))]
def spread(n, k): return [n // k + (1 if j < n % k else 0) for j in range(k)]   # whole units per open day, remainder on the first days

weeks = sorted({s["week_start"] for s in sessions})
scored = [w for w in weeks if "2026-01-05" <= w <= "2026-10-12"]
assert len(scored) == 41, len(scored)
rem = {(r["week_start"], r["item_id"]): (int(r["consumption"]), int(r["loss"])) for r in removal}
rec = {(u["week_start"], u["item_id"]): int(u["used"]) for u in usage}
err = {(e["count_date"], e["item_id"]): int(e["count_error"]) for e in errs}
POL = ["agent", "same_order", "naive_rule"]
seed_weeks = [w for w in weeks if w < "2025-12-29"][-8:]           # 3 Nov .. 22 Dec 2025
assert seed_weeks[0] == "2025-11-03" and seed_weeks[-1] == "2025-12-22"
standing = {it["item_id"]: math.ceil(sum(rec[(w, it["item_id"])] for w in seed_weeks) / 8 / float(it["pack_size"])) for it in items}
shelf = {(p, it["item_id"]): float(it["safety_stock"]) for p in POL for it in items}     # true shelf, Fri 2 Jan 2026
pending = {(p, it["item_id"]): [] for p in POL for it in items}                            # (arrival date, units)
weekly = []
for W in scored:
    wd = D.fromisoformat(W); friday = wd - dt.timedelta(days=3); cw = (wd - dt.timedelta(days=7)).isoformat()
    observed = {(p, i): max(0.0, shelf[(p, i)] + err.get((friday.isoformat(), i), 0)) for (p, i) in shelf}
    bk = [dict(date=b["date"], treatment_type=b["treatment_type"]) for b in bookings_all if b["week_start"] == W]
    known_sessions = [s for s in sessions if s["week_start"] <= cw]
    known_usage = [u for u in usage if u["week_start"] < cw]       # the week that is ending isn't in the usage history yet
    counts = [dict(count_date=friday.isoformat(), item_id=i, on_hand=observed[("agent", i)], earliest_best_before="") for i in (it["item_id"] for it in items)]
    p_agent = {r["item_id"]: r for r in plan(friday, items, rates, bk, known_sessions, known_usage, counts, [])}
    od = open_days(wd)
    for it in items:
        i, pack, safety = it["item_id"], float(it["pack_size"]), float(it["safety_stock"])
        naive = rec[(cw, i)]
        packs = {"agent": p_agent[i]["packs"], "same_order": standing[i],
                 "naive_rule": math.ceil(max(0, naive + safety - observed[("naive_rule", i)]) / pack)}
        arrive = add_working_days(friday, int(it["lead_time_working_days"]))
        while not is_open(arrive): arrive += dt.timedelta(days=1)
        cons, loss = rem[(W, i)]
        row = dict(week_start=W, item_id=i, item=it["item"], unit=it["count_unit_plural"], pack=it["pack_label"],
                   friday_bookings=len(bk), consumption=cons, loss=loss, actual_removal=cons + loss, recorded_use=rec[(W, i)],
                   agent_forecast=p_agent[i]["forecast_exact"], agent_forecast_rounded_up=p_agent[i]["forecast"], agent_factor=p_agent[i]["factor"],
                   naive_forecast=naive, safety_stock=int(safety), delivery_day=arrive.isoformat(), open_days=len(od))
        for p in POL:
            pending[(p, i)].append((arrive, packs[p] * pack))
            s = shelf[(p, i)]; short = 0
            row[f"{p}_true_shelf_friday_before"] = int(s); row[f"{p}_counted_friday_before"] = int(observed[(p, i)])
            for d, need in zip(od, spread(cons, len(od))):
                s += sum(u for a, u in pending[(p, i)] if a <= d); pending[(p, i)] = [(a, u) for a, u in pending[(p, i)] if a > d]
                take = min(s, need); short += need - take; s -= take
            s -= min(s, loss)
            shelf[(p, i)] = s
            row.update({f"{p}_packs": packs[p], f"{p}_units_ordered": int(packs[p] * pack), f"{p}_short": int(short),
                        f"{p}_left_friday": int(s), f"{p}_above_safety": int(max(0, s - safety))})
        weekly.append(row)
with open(f"{OUT}/backtest-weekly.csv", "w", newline="") as f:
    w = csv.DictWriter(f, list(weekly[0].keys())); w.writeheader(); w.writerows(weekly)

summ = []
for it in items:
    rs = [r for r in weekly if r["item_id"] == it["item_id"]]; n = len(rs); act = sum(r["actual_removal"] for r in rs)
    s = dict(item_id=it["item_id"], item=it["item"], unit=it["count_unit_plural"], weeks=n, avg_removal_per_week=round(act / n, 2))
    for f, key in [("agent", "agent_forecast"), ("naive", "naive_forecast")]:
        e = [float(r[key]) - r["actual_removal"] for r in rs]
        s[f"{f}_forecast_pct_error"] = round(100 * sum(map(abs, e)) / act, 1)
        s[f"{f}_forecast_bias_per_week"] = round(sum(e) / n, 2)
    for p in POL:
        s[f"{p}_stockout_weeks"] = sum(r[f"{p}_short"] > 0 for r in rs)
        s[f"{p}_units_short"] = sum(r[f"{p}_short"] for r in rs)
        s[f"{p}_weeks_above_safety"] = round(sum(r[f"{p}_above_safety"] for r in rs) / n / (act / n), 2)
        s[f"{p}_units_ordered"] = sum(r[f"{p}_units_ordered"] for r in rs)
    summ.append(s)
def cmp(a, b): return "win" if a < b else "loss" if a > b else "tie"     # for the agent; values already at the reported rounding
for s in summ:
    s["vs_same_order_stockouts"] = cmp(s["agent_stockout_weeks"], s["same_order_stockout_weeks"])
    s["vs_naive_rule_stockouts"] = cmp(s["agent_stockout_weeks"], s["naive_rule_stockout_weeks"])
    s["vs_same_order_above_safety"] = cmp(s["agent_weeks_above_safety"], s["same_order_weeks_above_safety"])
    s["vs_naive_rule_above_safety"] = cmp(s["agent_weeks_above_safety"], s["naive_rule_weeks_above_safety"])
    s["vs_naive_forecast_error"] = cmp(s["agent_forecast_pct_error"], s["naive_forecast_pct_error"])
tot = dict(item_id="ALL", item=f"all {len(items)} items", unit="(mixed)", weeks=len(scored), avg_removal_per_week="")
for f in ["agent", "naive"]:
    tot[f"{f}_forecast_pct_error"] = round(sum(s[f"{f}_forecast_pct_error"] for s in summ) / len(summ), 1)
    tot[f"{f}_forecast_bias_per_week"] = ""
for p in POL:
    tot[f"{p}_stockout_weeks"] = sum(s[f"{p}_stockout_weeks"] for s in summ)
    tot[f"{p}_units_short"] = sum(s[f"{p}_units_short"] for s in summ)
    tot[f"{p}_weeks_above_safety"] = round(sum(s[f"{p}_weeks_above_safety"] for s in summ) / len(summ), 2)
    tot[f"{p}_units_ordered"] = ""
for k in [k for k in summ[0] if k.startswith("vs_")]:
    tot[k] = "/".join(f"{sum(s[k] == r for s in summ)} {r}{'s' if r != 'loss' else 'es'}" for r in ("win", "loss", "tie"))
summ.append(tot)
with open(f"{OUT}/backtest-summary.csv", "w", newline="") as f:
    w = csv.DictWriter(f, list(summ[0].keys())); w.writeheader(); w.writerows(summ)
if not QUIET:
    print(f"{len(scored)} scored weeks ({scored[0]} .. {scored[-1]}), {len(items)} items = {len(weekly)} item-weeks; history {H}")
    print(f"{'item':13} {'%err ag/nv':>12} {'stock-out wks ag/same/naive':>28} {'units short':>14} {'wks above safety ag/same/naive':>32}")
    for s in summ:
        print(f"{s['item_id']:13} {str(s['agent_forecast_pct_error']) + '/' + str(s['naive_forecast_pct_error']):>12} "
              f"{'/'.join(str(s[p + '_stockout_weeks']) for p in POL):>28} {'/'.join(str(s[p + '_units_short']) for p in POL):>14} "
              f"{'/'.join(str(s[p + '_weeks_above_safety']) for p in POL):>32}")
    for k in [k for k in tot if k.startswith("vs_")]: print(f"agent {k}: {tot[k]}")
