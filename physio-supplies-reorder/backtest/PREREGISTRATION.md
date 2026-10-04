# Pre-registration: fair re-test of the reorder agent (backtest v2)

Written **before** any v2 backtest was run and before the v2 history generator existed. After its SHA-256 hash and time
are recorded in `PREREGISTRATION.lock.txt`, this file is not edited. Any change found necessary later (a real bug) is added
as a dated amendment in `AMENDMENTS.md` with the reason. The amendments never replace this text.

## Why a v2
The first backtest (v1) used the demo's 10-week history, which is steady from week to week and was tuned so every check fires.
v2 asks a fairer question: on a longer, realistically varied history, does the agent beat two simple baselines?

## What stays fixed (not tuned)
- **The agent's algorithm, exactly as it is now:** `workflow/reorder_maths.py` `plan()` (the Python copy of the n8n workflow; equal on every
  item in every repeat-run test), with its current settings: 8 weeks for the correction factor (clamped 0.8–1.5), 4 weeks for the average items,
  order = ceil(forecast) + safety stock − on hand, rounded up to whole packs. No parameter, rule or item setting is changed for or after v2.
- **The items:** `data/items.csv` (11 items, pack sizes, lead times, safety stock, forecast method) and the agent's standard usage table
  `data/usage-rates.csv`. Both are used unchanged.

## The v2 history generator (`workflow/generate_backtest_history.py`, to be written after this file)
**Random seed: 20261004** (the date this was written). There is one primary run with this seed, and no other seed is tried in order to pick one.

**Period:** 50 weeks, Mon 3 Nov 2025 to the week of Mon 12 Oct 2026 (weeks start on Monday).

**Calendar (Hamburg):**
- School holidays, from the official Hamburg Ferienordnung (hamburg.de): Christmas 17 Dec 2025 – 2 Jan 2026; Halbjahrespause Fri 30 Jan 2026;
  spring 2–13 Mar 2026; Ascension/Whitsun 11–15 May 2026; summer 9 Jul – 19 Aug 2026.
- Public holidays (practice closed): Thu 25 Dec, Fri 26 Dec 2025, Thu 1 Jan, Fri 3 Apr (Good Friday), Mon 6 Apr (Easter Monday), Fri 1 May,
  Thu 14 May (Ascension), Mon 25 May (Whit Monday) 2026. (3 Oct 2026 is a Saturday.)
- The practice is closed between the years: Wed 24 Dec 2025 – Thu 1 Jan 2026. It reopens Fri 2 Jan.
- "Open days" = Mon–Fri minus public holidays and closure days.

**Therapists and their weekly lists** (sessions per full week, and treatment mix in %, in the order Physiotherapy / Manual therapy /
Sports physio + taping / Lymph drainage / Massage / Ultrasound / Electrotherapy / Shockwave):
- Jana 32: 40 / 15 / 6 / 6 / 9 / 9 / 12 / 3
- Malte 32: 38 / 16 / 9 / 14 / 6 / 6 / 7 / 4
- Selin 30: 34 / 22 / 14 / 9 / 6 / 8 / 5 / 2
- Tom 32: 42 / 12 / 4 / 9 / 15 / 7 / 9 / 2
- **New therapist** Lena, starts Mon 1 Jun 2026, full list 28, at 25 % / 50 % / 75 % / 100 % in her first four weeks.
  A different mix: 15 / 15 / 35 / 25 / 0 / 0 / 0 / 10. She also uses 30 % more kinesiology tape per taping session than the table says.

**Demand per therapist, treatment and week:** expected = list × mix × (open days ÷ 5) × season × ramp-up × availability, where season is the product of:
- school holidays: × (1 − 0.15 × share of the week's open days that are school-holiday days);
- January rebound: × 1.12 in the weeks of 5, 12 and 19 Jan 2026;
- sports season: Sports physio + taping × 1.20 from April to September (by week start).

Each therapist-week gets a busy-ness factor from a normal distribution, mean 1 and SD 0.08, clipped to 0.75–1.25.
The appointments that week are Poisson(expected × busy-ness) per treatment.

**Bookings vs sessions held** (the realistic gap between what is booked and what happens):
- Each appointment is already booked on the Friday before with probability 0.93. The other 7 % are booked during the week (late bookings, always held).
- Of the appointments booked on Friday, a share c is cancelled or no-show. c is drawn per week, uniform 5–10 %, plus 3 points in December–February (colds and flu).
- Sessions held = booked on Friday − cancelled/no-show + late bookings.
- **Sickness, unannounced:** one 2-week episode and one 1-week episode. Therapist (one of the four) and start week are drawn with the seed among the weeks
  of 5 Jan – 5 Oct 2026, with no overlap. In the first sick week, the therapist's appointments are in Friday's bookings but none are held.
  In a second sick week they are no longer booked.
- **Summer vacation, planned:** each of the four original therapists takes 2 consecutive weeks off. The start week is drawn with the seed among the
  weeks of 13 Jul – 3 Aug 2026. Vacations are known, so they are not in Friday's bookings.

**Consumption** (what really comes off the shelf):
- Booking-driven items: for each held session, the table rate × the item's true factor. Lena's taping sessions use × 1.3 for kinesiology tape.
- The true factor starts at a value drawn uniform 0.90–1.15 per item and drifts every week: × exp(Normal(0, 0.02)), clipped to 0.80–1.30.
- Average items: per held appointment, disinfectant wipes 0.034, hand sanitiser 0.021 (× 1.30 in December–February), paper towels 0.085, each × the item's drifting true factor.
- Weekly consumption = Poisson(expected).

**Losses and counting errors:**
- Loss (unrecorded: breakage, taken home, a box in the wrong room): per item-week with probability 0.03, an amount = max(1, round(U(0.3, 1.0) × the item's
  mean weekly consumption over the 50 weeks)). It leaves the shelf at the end of that week.
- Counting error: per item-week with probability 0.05, Friday's count is off by −2, −1, +1 or +2 units (uniform), without going below 0.
  It affects only what the count says, not the shelf.

**Generator outputs** (`backtest/data/`):
- `sessions-held-per-week.csv` (the agent's history);
- `usage-recorded-per-week.csv`: used = consumption + loss + last week's count error − this week's count error, not below 0. This is what a practice
  computes from its counts, so it is the agent's usage history and the naive forecast;
- `bookings-on-friday.csv`: one row per appointment, with date, therapist and treatment;
- `removal-per-week.csv`: consumption and loss, i.e. the truth, used only for scoring and for the simulated shelf;
- `count-errors.csv`;
- `events.csv` (sickness, vacations, the new therapist, closures).

## The backtest (`workflow/backtest.py`, updated for v2)
- **Walk-forward:** each Friday before a scored week, each policy uses only what was known that Friday: held sessions and recorded usage of earlier weeks,
  that Friday's count (with its counting error, if any), and the Friday bookings for next week. Usage history of the week that is ending is not
  available to the agent (as now). It is available to the naive forecast, through the count.
- **Information advantage, stated plainly:** the agent sees next week's bookings. The baselines don't use them.
  The agent also inherits the realistic flaws of bookings: they include cancellations and no-shows and miss late bookings.
- **Scored weeks: 41**, the weeks of Mon 5 Jan – Mon 12 Oct 2026 (decisions on Fri 2 Jan – Fri 9 Oct). These are all the weeks that have a full 8-week
  history before them. 11 items × 41 weeks = 451 item-weeks.
- **Shelf simulation:**
  - All policies start Fri 2 Jan 2026 with exactly the safety stock.
  - A delivery arrives at the start of the day given by the agent's own lead-time rule (working days from Friday, no holidays). If the practice is
    closed that day, it arrives on the next open day.
  - The week's consumption is spread evenly over its open days (whole units, the remainder on the first days). The loss comes off at the end of the week.
  - What the shelf can't cover is lost (not carried over).
  - The manager approves every proposed line.
  - The count and order are treated as happening every Friday. If the practice is closed that Friday, they happen on the last open day before it,
    which gives the same numbers because nothing is used in between.
- **Policies:**
  1. **agent:** `plan()` as is, with that Friday's observed count and next week's Friday bookings;
  2. **same order as last week:** a standing order that never changes. **Seed changed from v1:** ceil(average recorded use of the 8 history weeks before
     2 Jan ÷ pack size), because the week right before 2 Jan is the Christmas closure and would give a meaningless seed;
  3. **naive forecast + shelf check:** the agent's order rule with forecast = the recorded use of the week that is ending (from the count).
- **Metrics (the same three as v1):**
  1. **stock-out weeks:** weeks in which on at least one open day the shelf could not cover the use (per item; overall = the sum over items, out of 451);
  2. **weeks of stock above safety:** the average over scored weeks of max(0, Friday stock − safety stock), divided by the item's average weekly
     removal (per item; overall = the mean over the 11 items);
  3. **forecast error %:** Σ|forecast − actual removal| ÷ Σ actual removal × 100 per item, with the agent's unrounded forecast and the naive forecast
     (overall = the mean over the 11 items). The standing order has no forecast, so it has none.
- **Wins and losses:** per item and metric, lower is better. The comparison uses the reported rounding (whole weeks, 2 decimals for weeks of stock,
  1 decimal for %); equal after rounding is a tie. Every item-level result is reported, wins and losses alike.
- **Secondary (robustness), decided now:** the same backtest on 20 more histories with seeds 20261005–20261024, reported as median and range of the
  overall numbers. This is reported, never used to choose a seed or to replace the primary result.
- **n8n cross-check (primary seed):** run the real n8n reorder workflow for the decisions of Fri 2 Jan 2026 and Fri 10 Jul 2026, and compare forecast
  and packs with the backtest on all 11 items (22 item-weeks). Any difference is reported.

## What will not be done
- No change to the agent after seeing results. Ideas for improvement go in the report as proposals and are not applied.
- No dropping of items, weeks or metrics, and no re-running with other seeds to get a nicer primary result.
- v1's results stay documented (build story), and they are labelled as v1.
