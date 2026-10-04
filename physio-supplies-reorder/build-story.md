# Build story: a supplies reorder agent for a small physio practice

*One chore, gone. Everything here is made up: the practice, the suppliers, the therapists, the numbers. Nothing was ordered and no supplier was contacted.*

## The chore

Every Friday, the practice manager walks to the supply cupboard and counts: kinesiology tape, rigid tape, ultrasound gel, couch roll, disinfectant wipes, gloves, electrode pads, massage lotion. Then comes the guess: how much will we need next week? Then the order goes to two or three suppliers.

The guess is the hard part. If more sports-taping sessions are booked than usual, the tape runs out on Wednesday. If the order is "the same as last week" while half the ultrasound sessions are gone, the shelf overflows and gel expires. And when something disappears faster than it should, nobody notices until it's gone.

## Why n8n

Same reason as in the first two demos ([physio reminders](../physio-appointment-reminders/) and [expat onboarding](../expat-onboarding-autopilot/)): n8n is free to run yourself, and the whole process is one picture on a canvas. Here every step of the maths is its own box: "Booked next week", "Look back: last 8 weeks", "Forecast next week", "Check the shelf", "Order quantity". You can click any box and see the numbers for every item.

## What I built, step by step

1. **Fake data.** A practice with 4 therapists and 8 treatment types, 11 supply items from 3 made-up suppliers ("Alster Example Praxisbedarf", "Elbe Example Hygiene", "Hafen Example Electro", with `.example` email addresses), 139 appointments for next week, the stock counts of last Friday and this Friday, 10 weeks of usage history and last week's order. The bookings have no patient names at all: only date, time, therapist and treatment type. A small script makes the data with a fixed random seed, so it's the same every time. I tuned the numbers so each check fires at least once. With my first numbers, the electrode pads never looked like running short, because the safety stock always covered Monday and Tuesday.
2. **Usage per treatment.** A small table: one sports-taping session uses about half a roll of kinesiology tape, an ultrasound session a quarter of a bottle of gel, and so on. Made up, but plausible.
3. **The forecast.** For most items: next week's bookings × usage per treatment × a correction learned from the last 8 weeks. The correction is simply "what we really used ÷ what the table predicted". For kinesiology tape it's 1.07: the therapists use a bit more than the table says. It's kept between 0.8 and 1.5, so one strange week can't run away with it. For general items like paper towels and hand sanitiser, bookings per treatment don't mean much, so it's the 4-week average, scaled by how busy next week is (139 appointments vs about 126). Rounded up to whole units.
4. **The order.** Forecast + safety stock − what's on the shelf − what's already in this week's cart, rounded up to whole packs. If the shelf already covers it, the item is skipped.
5. **Flags for a person.** Three checks, each one simple: did more disappear this week than the bookings explain (last count + delivery − today's count, compared with what this week's appointments should have used)? Is something on the shelf close to its best-before date (60 days)? Will an item run out before the delivery arrives? That last one uses the supplier's lead time and next week's bookings day by day.
6. **The output.** One proposed cart per supplier as a CSV file (called "would order" carts in the first version), a decisions file with every item and its numbers, a flags file, and a plain-language change report for the practice manager to read before checkout, compared with last week's order.

## The guard against ordering twice

The lesson from the first two demos was: if it runs twice, it must not do the work twice. Here that means: if someone clicks "run" again on Friday, the supplier must not get a second order.

So every cart line goes into an order log, together with the week it's for. Before deciding, the agent subtracts what's already in this week's cart. A second run finds everything already covered and adds nothing. If someone recounts and there's less on the shelf than first counted, it adds only the difference.

I tested the first version with real runs in n8n, on the same Friday (the tests now include the review step, see below):

- **Run again:** 0 new cart lines, the order log stays at 15 lines, all three cart files are byte-for-byte the same, and the report says "nothing new added".
- **Recount kinesiology tape (1 roll instead of 4), run again:** exactly one new line, a top-up of 1 box. Only Supplier A's cart changes, from 2 to 3 boxes.
- **Run once more:** 0 new lines.
- **After every run**, a separate plain-Python copy of the maths recalculated all 11 items, and it matched n8n every time (0 differences). And no item's cart ever held more than one pack beyond what the latest count needs.

## What went wrong along the way (all of this actually happened)

- **The report gave reasons that pointed the wrong way.** The numbers were right, but one line read: "Rigid sports tape: none this week … 18 sports physio + taping sessions are booked next week vs 9 this week." So: we order nothing, because twice as many taping sessions are booked? (The real reason: last week's box of 12 rolls is still mostly on the shelf.) Hand sanitiser had the same problem with "next week is 10% busier". And ultrasound gel got no reason at all. My rule picked the treatment that uses the most gel next week (shockwave, 4 vs 4 sessions), not the one that changed (ultrasound, 11 down to 5). **Fix:** the reason is now the treatment whose usage changed most, and it's only given when it points the same way as the change. Otherwise the report talks about the shelf. This is the kind of bug a manager would spot in a second and then stop trusting the report.
- **The flags file had odd column names.** Splitting the list of flags into rows named the columns `flags.flag` and `flags.detail`. **Fix:** one small step that names them `flag` and `detail`.
- **The canvas was unreadable.** My first layout put every step in one long row, about 8,000 pixels wide. In the screenshot, the boxes were dots. **Fix:** two rows. Reading the sheets goes on top, and the per-item maths and outputs go underneath.
- **My test counted wrong, not the workflow.** The repeat-run test said the order log had 14 lines when it had 15. n8n's CSV files don't end with a line break, so counting line breaks misses one. **Fix:** the test counts rows with a CSV reader.
- **Small one:** the report said "Alster Example Praxisbedarf (fictional) (arrives Mon 19 Oct)". Two brackets in a row read badly, so now it's ", arrives Mon 19 Oct".

What worked the first time: the whole workflow ran without an error on its first execution. That's mostly because I reused the patterns from demo #2, including the "Exclude Byte Order Mark" switch on every sheet the workflow reads back. That invisible character cost me a silent bug last time.

## Round 2: units, a backtest, and the manager's review

After the first version, three upgrades: make the units consistent, replay the history to see whether the forecast is any good, and let the practice manager approve the cart before it's final.

**Units.** The report said "2 boxes of 5 bags" in the cart and "about 5.2 bags of 4" in a flag. Both were "right", but they read like two different products. The cause: the item list had one label per item, and it was used both as the thing you count ("bag of 4") and as the pack ("box of 5"). Now every item says what it's counted in and what a pack is, in singular and plural: electrode pads are counted in bags (1 bag = 4 pads) and ordered in boxes of 5 bags. I wrote a checker that reads every output file and complains when a number is followed by the wrong word. Run on the old outputs, it found 7 problems, not just the electrode pads:

- "6 boxes of 100 went this week" (gloves, in the report and the flags): same mix-up as the bags;
- "14 packs on the shelf" for instant cold packs, where "pack" also means a box of 24;
- a decisions column that said "box of 24" without saying 24 of what, and a cart column that said "bag of 4" where the unit belonged.

The new checker also caught a line I'd never looked at closely: after a recount, the report said "1 pack(s) added". Now it says "+1 box of 6 rolls".

**The manager's review.** The agent now writes a review sheet: one row per proposed line, with empty columns for the decision (approve, change or remove), the name, the time and a reason. A second small workflow turns the decisions into an approval log and builds the final cart only from approved lines. A script plays the manager in the demo: tape changed from 2 to 3 boxes, lotion removed, the rest approved. Running anything again doesn't ask again: decided lines stay decided.

Adding the review broke something quietly. Until then, the order log meant "what we ordered". The agent used it to work out what was delivered this week, and that number goes into "how much did we really use?". After the review step, the order log only means "what the agent proposed". I replayed the next Friday in Python: with the manager's extra box of tape and the removed lotion, the old rule would have said 7 rolls of tape were used instead of 13, and 3 bottles of lotion instead of 2. That didn't cause a wrong flag with this data, but under-counting the tape by 6 rolls is exactly how a real loss gets hidden. **Fix:** "delivered" and "last week's order" now come from the approval log. A new test (I) plays out the next Friday in n8n and checks it on every item.

Smaller things that broke:
- The sticky note "Guard: never order twice" covered the new "Review sheet" box in the screenshot. I moved it.
- My tests, not the workflows: the first comparison called the review sheet "changed" when it wasn't. n8n writes the file with an invisible byte-order mark and no final line break, and Python doesn't, so the bytes differed while the rows were the same. Now the test compares rows. And the next-Friday test first appended rows with the wrong line ending, which left an empty line in the CSV. n8n refused the file ("Invalid Record Length"), which is fair.

**The backtest (v1, replaced in round 3).** I replayed the 9 weeks that have history before them (17 Aug – 12 Oct), walk-forward: each Friday sees only what was known then. I compared it with two simple rules: a standing order ("same as last week") and the agent's own order rule with a naive forecast ("next week = last week"). The result is mixed, and I'm reporting it as it is:

- Against the standing order, the agent wins clearly: 0 stock-out weeks vs 5, and far less on the shelf.
- Against the naive forecast, it doesn't win. Both have 0 stock-outs. The naive version keeps slightly less stock, and its forecast was more accurate on 8 of 11 items (9.3% vs 11.7% error on average). The fake history is steady from week to week, so "same as last week" is a strong guess. The busy week the agent is built for (19 Oct, twice the taping sessions) has no actual use yet, so it can't be scored.
- The data is synthetic and even favours the agent, because the usage was generated from the same structure it assumes. So the backtest shows the logic works as intended, not that it would work in a real practice. A next step it suggests: also use this week's usage (from the count), which the naive rule has and the agent ignores.

To make sure the backtest's Python maths is the agent's maths, I ran the real n8n workflow for two of the replayed Fridays: 22 item-weeks, 0 differences.

## Round 3: a fair re-test, with the rules written down first

The round-2 backtest had a weak spot I'd named myself: 9 steady weeks of data I'd tuned for the demo, generated from the same structure the agent assumes. So I re-tested it on a longer, messier history, and this time I wrote the rules down **before** running anything. `backtest/PREREGISTRATION.md` fixes the history generator and its parameters, the seed, the three metrics, the two baselines, the 41 scored weeks, a check on 20 other seeds, and which two Fridays get re-run in real n8n. I recorded its hash and the time (4 Oct 2026, 09:39), then the hashes of the code before the first run. The agent's maths stayed exactly as it was.

The history covers 50 weeks: Hamburg school holidays and the Christmas closure, a busy January, a summer sports season, a therapist off sick without warning, summer vacations, a new therapist from June with a different treatment mix, cancellations and no-shows, late bookings, usage drifting away from the table, losses and miscounts. The agent sees next week's bookings, and the baselines don't. That's its information advantage, and I'm saying so up front.

The result is better than round 2 for the forecast, and mixed for the shelf:
- **Forecast:** the agent beat the naive forecast on all 11 items (43% vs 62% average error), and on at least 10 of 11 in each of the 20 other histories. With real variation, the bookings carry information that "same as this week" doesn't.
- **Against the naive rule:** fewer stock-out weeks on 8 items, the same on 3, worse on none (19 vs 42 in total), with about the same stock (1.30 vs 1.31 weeks of use).
- **Against the standing order:** far less stock on every item (1.3 vs 32.7 weeks of use above safety), but more stock-out weeks on 5 items. The total happened to favour the agent with the main seed (19 vs 24), but on 17 of the 20 other seeds the standing order ran out less often. That's the honest trade: the standing order avoids gaps by burying the shelf.
- **Where the agent still fails:** 19 stock-out weeks out of 451, 7 of them electrode pads (Wednesday delivery). Mostly a week ran over the forecast plus the whole safety stock, and the next week started short.

I'm not changing the maths after seeing this, because that would be tuning to the test. Two proposals for a next, separately pre-registered round: order up to the next delivery rather than the end of next week, and let the safety stock grow with the forecast error or the volume (rigid tape went from about 7 rolls a week in winter to 35–37 in two late-summer weeks, with a fixed safety stock of 4).

What broke or needed care:
- **The pre-registration left a few gaps:** whether a sick week may fall in the same therapist's vacation, how appointments spread over the days, what happens when a loss is bigger than the shelf. I wrote them down as clarifications in `backtest/AMENDMENTS.md` before the first run. None of them changes a rule.
- **A result that looked like a bug:** rigid tape once used 37 rolls when about 22 were expected. I checked the generator: over all 550 item-weeks the random use has the spread it should (variance 1.01 after scaling, 1.00 expected), so it was chance, not a bug. No amendment needed.
- **The seed's draw was awkward but kept:** both sick spells landed on the same therapist, back to back (a 1-week and a 2-week spell, 30 Mar to 17 Apr). Drawing again would have been seed-shopping, so it stays.
- **The old chart only had per-item bars,** so you couldn't see what the agent was up against. The new one starts with appointments per week (held vs booked by Friday), with the holidays, the sick spell, the new therapist and the vacations marked.

The real n8n workflow matched the backtest's maths on both pre-registered Fridays (2 Jan and 10 Jul 2026): 22 item-weeks, 0 differences. The data is still synthetic, and my generator still builds usage as "sessions × usage per treatment", so a real practice remains the real test.

## What the final version does

On the demo Friday (16 Oct 2026, 17:00), one click (about 1.8 seconds in n8n):

- checks **11 items** against **139 booked appointments**,
- proposes **5 lines in 3 carts**: kinesiology tape 2 boxes of 6 rolls, massage lotion 1 bottle, couch roll 1 pack of 9 rolls, disinfectant wipes 1 case of 6 tubs, electrode pads 2 boxes of 5 bags,
- skips **6 items** that have enough on the shelf,
- raises **3 flags**: 6 boxes of gloves went but the bookings explain about 2; 4 bottles of gel are best before 20 Nov; electrode pads arrive Wednesday, but Monday and Tuesday need about 5.2 bags and only 3 bags are on the shelf,
- writes the change report, e.g. *"Kinesiology tape 5 cm x 5 m: 2 boxes of 6 rolls instead of 1, because 18 sports physio + taping sessions are booked next week vs 9 this week."*,
- and puts the 5 lines on the review sheet. After the (scripted) review, the second workflow builds **approved carts with 4 lines** (tape 3 boxes, couch roll, wipes, electrode pads) and logs all 5 decisions with who, when and why.

What it doesn't do: order anything, know what anything costs, notify the manager, handle public holidays or supplier cut-off times, take cancellations off the bookings, or add this week's usage to the history by itself.

The backtest (round 3, pre-registered, synthetic history): over 41 weeks, the agent's forecast beat the naive one on every item, it ran out less often than the naive rule, and it kept far less stock than a standing order, which in turn ran out less often on most of the other histories.

## AI: not in this version

The report is template text built straight from the numbers. That's the fallback, and it's what you see in the output, so no API key is needed. The canvas marks where an optional AI step could go: between "Compare with last order" and "Write change report", to make the wording more natural. The numbers must still come from the maths. It isn't included or tested.

## Time saved

Not measured yet. The honest next step is to time a real Friday count-and-order by hand before putting any number on it.

## Biggest lesson

Demo #1 taught me to only handle what's new since the last run. Demo #2 taught me to distrust a quiet "nothing to do". This one added a third lesson: when the agent explains itself, the explanation needs testing as carefully as the numbers. A right number with a wrong "because" still loses the reader's trust. And from the second round: when a human step is added, check what every old file now means. The order log didn't change at all; its meaning did.
