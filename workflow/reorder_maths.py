# Plain-Python copy of the order maths in the n8n workflow. Used for two things only:
#  1. generate_data.py uses it to make LAST week's order lines (so the "last order" follows the same rules),
#  2. check_against_python.py re-calculates THIS week's order and compares it with what n8n produced,
#  3. backtest.py replays the past weeks with it (walk-forward).
# You don't need it to use the demo. Rounding is written to match JavaScript (Math.round / Math.ceil).
import csv, datetime as dt, math

def rd(p): return list(csv.DictReader(open(p, encoding="utf-8-sig")))
def jsround(x, d=0): f = 10 ** d; return math.floor(x * f + 0.5) / f
def D(s): return dt.date.fromisoformat(s[:10])
def monday(d): return d - dt.timedelta(days=d.weekday())
def add_working_days(d, n):   # same formula as the workflow (works for Mon-Fri start days)
    wd = d.isoweekday()
    return d + dt.timedelta(days=n + 2 * ((wd - 1 + n) // 5))

def plan(today, items, rates, bookings, sessions, usage, counts, order_log,
         history_weeks=8, avg_weeks=4, expiry_warn_days=60, first_week=None, approval_log=None):
    """bookings: list of {date, treatment_type} for next week. Returns one dict per item."""
    cw = monday(today)                      # this week (Monday)
    order_week = cw + dt.timedelta(days=7)  # the week we order for
    hist = [(cw - dt.timedelta(weeks=k)).isoformat() for k in range(history_weeks, 0, -1)]
    if first_week: hist = [w for w in hist if w >= first_week]   # backtest only: at the start there are fewer than 8 weeks
    avg4 = hist[-avg_weeks:]
    next_days = [(order_week + dt.timedelta(days=k)).isoformat() for k in range(5)]
    def sess(w, t=None): return sum(float(s["sessions"]) for s in sessions if s["week_start"] == w and (t is None or s["treatment_type"] == t))
    def used(w, i): return sum(float(u["used"]) for u in usage if u["week_start"] == w and u["item_id"] == i)
    def logged(w, i, f): return sum(float(o[f]) for o in order_log if o["order_week"] == w and o["item_id"] == i)
    # "delivered this week" and "last week's order" = what the manager APPROVED (approval log), if given
    def approved(w, i, f): return sum(float(o[f]) for o in approval_log if o["order_week"] == w and o["item_id"] == i)
    out = []
    for it in items:
        iid = it["item_id"]; pack = float(it["pack_size"]); bookings_based = it["forecast_method"] == "bookings"
        rr = [r for r in rates if r["item_id"] == iid]
        per_t = [{"treatment": r["treatment_type"], "rate": float(r["use_per_session"]),
                  "next_week": sum(1 for b in bookings if b["treatment_type"] == r["treatment_type"]),
                  "this_week": sess(cw.isoformat(), r["treatment_type"])} for r in rr]
        n_next, n_this = len(bookings), sess(cw.isoformat())
        booked_use = jsround(sum(p["rate"] * p["next_week"] for p in per_t), 2)
        pred8 = sum(p["rate"] * sess(w, p["treatment"]) for w in hist for p in per_t)
        used8 = sum(used(w, iid) for w in hist)
        factor = min(1.5, max(0.8, jsround(used8 / pred8, 2))) if bookings_based and pred8 > 0 else None
        avg_used4 = jsround(sum(used(w, iid) for w in avg4) / len(avg4), 2)
        avg_sess4 = jsround(sum(sess(w) for w in avg4) / len(avg4), 1)
        busy = jsround(n_next / avg_sess4, 2)
        forecast_exact = jsround(booked_use * factor if bookings_based else avg_used4 * busy, 2)
        forecast = math.ceil(forecast_exact)
        c_now = next((c for c in counts if c["count_date"] == today.isoformat() and c["item_id"] == iid), None)
        c_last = next((c for c in counts if c["count_date"] == (today - dt.timedelta(days=7)).isoformat() and c["item_id"] == iid), None)
        on_hand = float(c_now["on_hand"]) if c_now else 0.0
        delivered = approved(cw.isoformat(), iid, "final_units") if approval_log is not None else logged(cw.isoformat(), iid, "units")
        used_this = (float(c_last["on_hand"]) + delivered - on_hand) if c_last else None
        expected_this = jsround(sum(p["rate"] * p["this_week"] for p in per_t) * factor if bookings_based else avg_used4 * n_this / avg_sess4, 1)
        arrives = add_working_days(today, int(it["lead_time_working_days"]))
        days_before = [d for d in next_days if d < arrives.isoformat()]
        before = jsround(sum(p["rate"] * sum(1 for b in bookings if b["treatment_type"] == p["treatment"] and b["date"] in days_before) for p in per_t) * factor
                         if bookings_based else forecast_exact / 5 * len(days_before), 1)
        flags = []
        if c_now is None: flags.append("no count")
        if used_this is not None and used_this - expected_this > max(2, 0.4 * expected_this): flags.append("stock dropped more than usage explains")
        if c_now and c_now.get("earliest_best_before") and D(c_now["earliest_best_before"]) <= today + dt.timedelta(days=expiry_warn_days): flags.append("near expiry")
        if on_hand < before: flags.append("may run short before delivery")
        already_units, already_packs = logged(order_week.isoformat(), iid, "units"), logged(order_week.isoformat(), iid, "packs")
        target = forecast + float(it["safety_stock"])
        short = target - on_hand - already_units
        packs = math.ceil(short / pack) if short > 0 else 0
        out.append(dict(item_id=iid, supplier_id=it["supplier_id"], factor=factor, avg_used_4w=avg_used4, busy=busy,
                        booked_use=booked_use, forecast_exact=forecast_exact, forecast=forecast, on_hand=on_hand,
                        used_this_week=used_this, expected_this_week=expected_this, arrives_on=arrives.isoformat(),
                        usage_before_arrival=before, target=target, already_packs=already_packs, packs=int(packs),
                        units=int(packs * pack), last_packs=approved(cw.isoformat(), iid, "final_packs") if approval_log is not None else logged(cw.isoformat(), iid, "packs"),
                        delivered_this_week=delivered, flags=flags))
    return out
