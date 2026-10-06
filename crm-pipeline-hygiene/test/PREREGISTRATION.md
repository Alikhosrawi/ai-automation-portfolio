# Pre-registration: planted-error test of the pipeline hygiene check

Written **before** the data generator, the checks, the AI prompts or any result existed. After its SHA-256 hash and time are
recorded in `PREREGISTRATION.lock.txt`, this file is not edited. Anything found necessary later (a real bug, a gap in these
rules) goes into `AMENDMENTS.md` with the date and the reason. Amendments never replace this text.

## The question
On a fake HubSpot deals export with known problems planted in it, how many problems does the weekly check find, how many
things does it flag that are not problems, and how far is its "cleaned" Q4 forecast from the true one?

## Fixed setting
- **"Now":** Monday 12 Oct 2026, 07:30 (Europe/Berlin). "Today" for every rule is 12 Oct 2026.
- **The company (fictional):** "Hafenlicht Example GmbH", a Hamburg B2B SaaS company. 6 account executives. All customer
  companies, people and domains are made up (domains end in `.example`).
- **The pipeline:** HubSpot's default sales pipeline and its default stage probabilities:
  Appointment Scheduled 20 %, Qualified To Buy 40 %, Presentation Scheduled 60 %, Decision Maker Bought-In 80 %,
  Contract Sent 90 %, Closed Won 100 %, Closed Lost 0 %.
- **Q4 forecast (weighted):** the sum of Amount × stage probability over open deals (not Closed Won / Closed Lost) whose
  Close Date is between 1 Oct and 31 Dec 2026. A missing amount counts as 0, which is what HubSpot's own weighted amount does.
- **Primary random seed: 20261012.** One primary run. No other seed is tried to pick a result.

## The data (generator written after this file)
Two CSV files in HubSpot's export layout: `deals.csv` and `companies.csv`. Amounts in EUR.

**The clean base: 400 deals** for about 230 companies.
- 110 Closed Won and 90 Closed Lost, with close dates between 5 Jan 2026 and 9 Oct 2026.
- 200 open deals. Every open base deal is clean by construction: an owner, an amount, a close date on or after 12 Oct 2026
  (about 60 % in Q4 2026, the rest Jan–Mar 2027), and a last activity 0–25 days before now.
- Some companies have more than one real deal (for example a new-business deal and a later expansion). These are real,
  different deals and count as "not a duplicate".

**Planted problems** (chosen at random from the open base deals, each base deal gets at most one planted problem):

| Code | Count | What is planted |
|---|---|---|
| `DUP_EXACT` | 8 | A second row for an open deal: same company record, same deal name, same amount, created 0–3 days after the original (a double import). |
| `DUP_FUZZY` | 10 | A second row for an open deal, entered by someone else under a **second company record** with a variant of the name (legal form changed or dropped, different capitalisation, a city added, a typo), a reworded deal name, an amount within ±10 %, created 5–45 days after the original. |
| `STALE` | 6 | Last activity 31–60 days ago. Still a real deal (counts in the true forecast). |
| `ZOMBIE` | 8 | Last activity 61–150 days ago. The buyer has gone (does **not** count in the true forecast). |
| `PAST_CLOSE` | 6 | Close date 1–30 days before now, still open, recent activity. A real deal whose date was never moved. |
| `NO_AMOUNT` | 8 | Amount empty, in a stage after Appointment Scheduled. The answer key keeps the real amount. |
| `NO_CLOSE_DATE` | 4 | Close date empty. |
| `NO_OWNER` | 3 | Deal owner empty. |
| `WON_FUTURE_DATE` | 3 | Changed to Closed Won with a close date 3–40 days **after** now. (Picked from Closed Won base deals, not open ones.) |

**Look-alike traps: 6 pairs that are not duplicates**, planted on purpose: two real deals at the same company (same record or
a variant record) with similar amounts (within ±15 %) and created within 60 days, but clearly different business in the
deal name (another site, another product, a renewal vs an upsell). They test whether the check flags things it shouldn't.

The answer key (`answer-key.csv`, one row per planted problem and trap, plus the true amount for every `NO_AMOUNT` deal) is
written by the generator to a separate file. The checks and the AI steps never read it.

## The checks (rules fixed here)
On open deals unless said otherwise; "days since activity" uses Last Activity Date, or Create Date when it is empty.
- `NO_AMOUNT`: amount empty or 0 and stage is not Appointment Scheduled.
- `NO_CLOSE_DATE`: close date empty.
- `NO_OWNER`: owner empty.
- `PAST_CLOSE`: close date before 12 Oct 2026.
- `STALE`: 31–60 days since activity. `ZOMBIE`: more than 60 days.
- `WON_FUTURE_DATE`: Closed Won with a close date after 12 Oct 2026 (all deals, not only open ones).
- **Duplicates, in two steps:**
  1. **Exact (rules only):** two open deals with the same company record ID and the same deal name after lower-casing and
     collapsing spaces → duplicate.
  2. **Candidates → AI:** every other pair of open deals where the companies match (same record ID, or same domain when both
     have one, or name similarity ≥ 0.80 after removing legal forms and punctuation; similarity = Python `difflib`
     `SequenceMatcher` ratio), the amounts are within 25 % of the larger one, and the create dates are within 90 days.
     Each candidate pair goes to the AI judge, which answers `DUPLICATE`, `DIFFERENT` or `UNSURE`. `UNSURE` goes on a list
     for a person and counts as **not flagged**.
- **Which row is the copy:** the row created later. If created the same day, the higher Record ID.

## The AI steps
- **Duplicate judge:** one prompt per candidate pair, with both deal rows and both company rows, nothing else. The prompt is
  written before the data is generated and is not changed after seeing any answer. For the recorded run, the judge is a separate blind AI run
  that has never seen the generator, the answer key or this file's planted lists.
- **Weekly note:** the AI writes the Monday summary from a facts file the Python code computes. A **number guard** then
  checks that every number in the note appears in the facts file. A note that fails the guard is not used; the plain
  template note is sent instead.
- **Rules-only comparison for duplicates** (to show what the AI adds): a candidate pair is a duplicate when the companies
  match with similarity ≥ 0.85 (or same record ID or domain) and the amounts are within 10 %.

## Metrics (reported for every check, nothing dropped)
1. **Caught / planted** per problem code.
2. **False flags** per code: flags that are not in the answer key. For duplicates this includes flagging a trap pair or a
   real multi-deal company.
3. **Duplicates, AI vs rules-only:** caught, false flags and UNSURE for the AI; caught and false flags for the rules-only version.
4. **Forecast:** raw Q4 weighted forecast (as exported), the tool's cleaned forecast, and the **true** forecast from the
   answer key. Tool's cleaned = raw minus the rows it flags as duplicate copies, minus deals it flags `ZOMBIE`. Deals without
   an amount are reported separately as "not counted" (with their number), not guessed. True = raw minus planted duplicate
   copies, minus planted zombies, plus the true weighted amount of the `NO_AMOUNT` deals that are in Q4.
   Reported: raw − true, cleaned − true, both in EUR and as % of true.

## Robustness (decided now)
Seeds 20261013–20261032 (20 seeds). For each, the rule checks, the duplicate candidates and the rules-only duplicate decision
are re-run and scored; reported as median and range, never used to pick a result. The AI judge is run on the primary seed
only (cost and time), and this is said in the results. For the other seeds the report shows how many planted duplicates
reached the AI step as a candidate at all (the ceiling for what the AI could catch).

## What this test cannot show
I write both the generator and the checks, and I know the planted problem types while writing the rules. So high catch
rates for the rule checks are expected and say little. The interesting numbers are the false flags, the duplicate step
(where the variants are messy and the AI is blind) and the forecast gap. It's synthetic data; it doesn't prove the check
works on a real CRM.
