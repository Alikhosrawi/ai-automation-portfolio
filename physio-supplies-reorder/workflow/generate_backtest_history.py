# Makes the realistic, varied 50-week history for the fair re-test (backtest v2), exactly as written in
# backtest/PREREGISTRATION.md (and the clarifications in backtest/AMENDMENTS.md). Everything is invented (synthetic).
#   python3 generate_backtest_history.py [seed] [out_dir]      default seed 20261004 -> backtest/data/
# Only the Python standard library is used.
import csv, datetime as dt, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reorder_maths import rd
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 20261004
OUT = sys.argv[2] if len(sys.argv) > 2 else f"{HERE}/backtest/data"
os.makedirs(OUT, exist_ok=True)
R = lambda part: random.Random(f"{SEED}-{part}")       # one random stream per part (AMENDMENTS.md, clarification 1)
D = dt.date
def days(a, b): return {a + dt.timedelta(days=k) for k in range((b - a).days + 1)}

# ---- calendar (Hamburg) ----
WEEKS = [D(2025, 11, 3) + dt.timedelta(weeks=k) for k in range(50)]          # 3 Nov 2025 .. 12 Oct 2026
SCHOOL = days(D(2025, 12, 17), D(2026, 1, 2)) | {D(2026, 1, 30)} | days(D(2026, 3, 2), D(2026, 3, 13)) \
    | days(D(2026, 5, 11), D(2026, 5, 15)) | days(D(2026, 7, 9), D(2026, 8, 19))
PUBLIC = {D(2025, 12, 25), D(2025, 12, 26), D(2026, 1, 1), D(2026, 4, 3), D(2026, 4, 6), D(2026, 5, 1), D(2026, 5, 14), D(2026, 5, 25)}
CLOSED = PUBLIC | days(D(2025, 12, 24), D(2026, 1, 1))
def open_days(w): return [w + dt.timedelta(days=k) for k in range(5) if w + dt.timedelta(days=k) not in CLOSED]

# ---- practice ----
T = ["Physiotherapy", "Manual therapy", "Sports physio + taping", "Lymph drainage", "Massage", "Ultrasound", "Electrotherapy", "Shockwave"]
THER = {  # full weekly list, mix in % in the order of T
    "Jana": (32, [40, 15, 6, 6, 9, 9, 12, 3]), "Malte": (32, [38, 16, 9, 14, 6, 6, 7, 4]),
    "Selin": (30, [34, 22, 14, 9, 6, 8, 5, 2]), "Tom": (32, [42, 12, 4, 9, 15, 7, 9, 2]),
    "Lena": (28, [15, 15, 35, 25, 0, 0, 0, 10])}
LENA_START = D(2026, 6, 1); RAMP = [0.25, 0.5, 0.75, 1.0]
REBOUND = {D(2026, 1, 5), D(2026, 1, 12), D(2026, 1, 19)}
items = rd(f"{HERE}/data/items.csv"); rates = rd(f"{HERE}/data/usage-rates.csv")
RATES = {}
for r in rates: RATES.setdefault(r["item_id"], {})[r["treatment_type"]] = float(r["use_per_session"])
AVG = {"DISINF-WIPES": 0.034, "HAND-SAN": 0.021, "PAPER-TOWELS": 0.085}
WINTER = lambda w: w.month in (12, 1, 2)

def poisson(rng, lam):          # Knuth; lam is at most ~20 here
    if lam <= 0: return 0
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= L: return k
        k += 1

# ---- planned vacations and unannounced sickness ----
rv = R("vacation"); OLD = ["Jana", "Malte", "Selin", "Tom"]
summer_starts = [D(2026, 7, 13), D(2026, 7, 20), D(2026, 7, 27), D(2026, 8, 3)]
vacation = {t: (lambda s: {s, s + dt.timedelta(weeks=1)})(rv.choice(summer_starts)) for t in OLD}
rs = R("sick"); sick_starts = [w for w in WEEKS if D(2026, 1, 5) <= w <= D(2026, 10, 5)]
while True:
    eps = [(rs.choice(OLD), rs.choice(sick_starts), n) for n in (2, 1)]
    weeks_of = [{s + dt.timedelta(weeks=k) for k in range(n)} for _, s, n in eps]
    if weeks_of[0] & weeks_of[1]: continue
    if any(weeks_of[k] & vacation[eps[k][0]] for k in range(2)): continue
    break
sick_booked_not_held = {(t, s) for t, s, n in eps}                                   # first sick week: booked, nothing held
sick_not_booked = {(t, s + dt.timedelta(weeks=k)) for t, s, n in eps for k in range(1, n)}

# ---- appointments ----
rb, ra, rd_, rc = R("busy"), R("appointments"), R("days"), R("cancel")
sessions, bookings, events = [], [], []
held_by = {}       # (week, therapist, treatment) -> held sessions
for w in WEEKS:
    od = open_days(w)
    share_school = (sum(d in SCHOOL for d in od) / len(od)) if od else 0
    canc = rc.uniform(0.05, 0.10) + (0.03 if WINTER(w) else 0)
    held_t = {t: 0 for t in T}; bid = 0
    for th, (lst, mix) in THER.items():
        busy = min(1.25, max(0.75, rb.gauss(1, 0.08)))
        if th == "Lena":
            if w < LENA_START: continue
            ramp = RAMP[min(3, (w - LENA_START).days // 7)]
        else: ramp = 1.0
        avail = 0 if (th in vacation and w in vacation[th]) or (th, w) in sick_not_booked else 1
        apps = []
        for t, m in zip(T, mix):
            season = (1 - 0.15 * share_school) * (1.12 if w in REBOUND else 1) * (1.2 if t == "Sports physio + taping" and 4 <= w.month <= 9 else 1)
            lam = lst * m / 100 * len(od) / 5 * season * ramp * avail * busy
            apps += [t] * poisson(ra, lam)
        sick = (th, w) in sick_booked_not_held
        by_day = {}
        for t in apps:
            day = rd_.choice(od); by_day.setdefault(day, []).append(t)
        for day in sorted(by_day):
            for slot, t in enumerate(by_day[day]):
                on_friday = ra.random() < 0.93
                if on_friday:
                    cancelled = rc.random() < canc
                    outcome = "therapist off sick (not held)" if sick else "cancelled or no-show" if cancelled else "held"
                    bid += 1
                    bookings.append(dict(week_start=w.isoformat(), booking_id=f"{w:%y%m%d}-{bid:03d}", date=day.isoformat(),
                                         start=f"{8 + slot // 2:02d}:{(slot % 2) * 30:02d}", therapist=th, treatment_type=t, outcome=outcome))
                    held = outcome == "held"
                else:
                    held = not sick                                      # a late booking (made during the week)
                if held:
                    held_t[t] += 1; held_by[(w, th, t)] = held_by.get((w, th, t), 0) + 1
    for t in T: sessions.append(dict(week_start=w.isoformat(), treatment_type=t, sessions=held_t[t]))
    events.append(dict(week_start=w.isoformat(), what="week", detail=f"{len(od)} open days, {round(100 * share_school)}% of them school holidays, "
                       f"cancel/no-show rate {canc:.3f}" + (", January rebound" if w in REBOUND else "")))
for t, s, n in eps: events.append(dict(week_start=s.isoformat(), what="sickness", detail=f"{t} off sick {n} week(s), unannounced (week 1 booked, not held)"))
for t in OLD: events.append(dict(week_start=min(vacation[t]).isoformat(), what="vacation", detail=f"{t} 2 weeks summer vacation (known, not booked)"))
events.append(dict(week_start=LENA_START.isoformat(), what="new therapist", detail="Lena starts (25/50/75/100% of a 28-session list over 4 weeks), more taping and lymph drainage"))

# ---- consumption, losses, counting errors ----
rf, ru, rl, re_ = R("factor"), R("use"), R("loss"), R("count")
factor = {it["item_id"]: rf.uniform(0.90, 1.15) for it in items}
cons = {}
for w in WEEKS:
    total_held = sum(held_by.get((w, th, t), 0) for th in THER for t in T)
    for it in items:
        i = it["item_id"]
        if i in RATES:
            lam = sum(r * held_by.get((w, th, t), 0) * (1.3 if th == "Lena" and i == "KT-TAPE" and t == "Sports physio + taping" else 1)
                      for t, r in RATES[i].items() for th in THER) * factor[i]
        else:
            lam = AVG[i] * (1.3 if i == "HAND-SAN" and WINTER(w) else 1) * total_held * factor[i]
        cons[(w, i)] = poisson(ru, lam)
        events_factor = factor[i]
        factor[i] = min(1.30, max(0.80, factor[i] * math.exp(ru.gauss(0, 0.02))))
removal, errs, usage = [], [], []
for it in items:
    i = it["item_id"]; mean_use = sum(cons[(w, i)] for w in WEEKS) / len(WEEKS); prev_e = 0
    for w in WEEKS:
        loss = max(1, round(rl.uniform(0.3, 1.0) * mean_use)) if rl.random() < 0.03 else 0
        e = re_.choice([-2, -1, 1, 2]) if re_.random() < 0.05 else 0
        removal.append(dict(week_start=w.isoformat(), item_id=i, consumption=cons[(w, i)], loss=loss, actual_removal=cons[(w, i)] + loss))
        if e: errs.append(dict(count_date=(w + dt.timedelta(days=4)).isoformat(), week_start=w.isoformat(), item_id=i, count_error=e))
        usage.append(dict(week_start=w.isoformat(), item_id=i, used=max(0, cons[(w, i)] + loss + prev_e - e)))
        prev_e = e

def wr(name, rows, cols):
    with open(f"{OUT}/{name}", "w", newline="", encoding="utf-8") as f:
        c = csv.DictWriter(f, cols); c.writeheader(); c.writerows(rows)
wr("sessions-held-per-week.csv", sessions, ["week_start", "treatment_type", "sessions"])
wr("usage-recorded-per-week.csv", usage, ["week_start", "item_id", "used"])
wr("bookings-on-friday.csv", bookings, ["week_start", "booking_id", "date", "start", "therapist", "treatment_type", "outcome"])
wr("removal-per-week.csv", removal, ["week_start", "item_id", "consumption", "loss", "actual_removal"])
wr("count-errors.csv", errs, ["count_date", "week_start", "item_id", "count_error"])
wr("events.csv", events, ["week_start", "what", "detail"])
print(f"seed {SEED}: {len(WEEKS)} weeks, {len(bookings)} Friday bookings, {sum(s['sessions'] for s in sessions)} sessions held, "
      f"{sum(r['loss'] > 0 for r in removal)} losses, {len(errs)} counting errors -> {OUT}")
