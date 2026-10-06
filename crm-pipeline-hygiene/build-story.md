# Build story: a Monday pipeline hygiene check for a HubSpot export

*One chore, gone. Everything here is made up: the company, its reps, its customers, every number. Nothing connects to HubSpot and nothing is sent.*

## The chore

Before the Monday forecast call, someone in RevOps exports the deals, sorts them a few ways and scans for trouble. Two rows for the same deal. A customer spelled two ways by two reps. A deal in "Presentation Scheduled" since August. Deals with no amount. Then they message each rep. It's not hard. It's just every week, and when it's skipped, the forecast the CEO sees is quietly wrong.

I've done the same kind of clean-up in Salesforce in my own job: list views for stale records, reports that only work once the data underneath is tidy. This demo is the HubSpot version of that habit, automated.

## The question I started from

My other demos remove a chore. This one also had to answer a question a Head of RevOps would actually ask: *how much is my forecast off, and in which direction?* So the opening of the README is a before/after of the Q4 number, not a list of tools.

That also meant the test had to know the right answer. On a real CRM you never know how many duplicates there "really" are. So I made the data myself, planted the problems, and kept an answer key the workflow never reads.

## Rules first, written down before anything else

The lesson from the supplies demo: if I tune the test after seeing results, the results mean nothing. So before writing a line of code I wrote [`test/PREREGISTRATION.md`](test/PREREGISTRATION.md): the seed, the 400 clean deals, exactly which problems get planted and how many, the check rules, the metrics, and the 20 extra seeds. I hashed it together with the two AI prompts and committed it first. It hasn't changed since. Everything I changed later is in [`test/AMENDMENTS.md`](test/AMENDMENTS.md).

The most useful line in it turned out to be the **look-alike traps**: 6 pairs of real, different deals at the same company with similar amounts. Without them, a duplicate finder that flags everything vaguely similar would look great.

## What I built, step by step

1. **A fake HubSpot export.** `generate_export.py` writes `deals.csv` and `companies.csv` with HubSpot's own column names ("Associated Company IDs (Primary)" and so on) and HubSpot's default stages and probabilities. 6 reps, about 230 customer companies with German-sounding made-up names ("Nordlicht Logistik GmbH"), `.example` domains.
2. **A validator for the generator.** Before trusting the data, `validate_export.py` checks the generator did what the rules say: every clean open deal really has an owner, an amount, a future close date and recent activity, and every planted problem is exactly as described. It caught two bugs (below).
3. **The rule checks.** Seven simple ones: missing amount, close date or owner; close date in the past; no activity for 31–60 days or over 60; closed won with a future close date.
4. **Duplicates in two steps.** Exact copies are easy: same company record, same deal name. The messy ones are the reason for AI. Someone types "Sandtor Spediiton GmbH" as a new company and words the deal differently. A rule that's loose enough to catch that also catches "Renewal 2027" vs "Expansion +40 seats" at the same company. So the rules only *find candidates* (similar company, amounts within 25 %, created within 90 days), and the AI decides.
5. **The forecast bridge.** Weighted Q4 forecast as exported, minus duplicate copies, minus deals with no activity for 60+ days. Every deal that moves the number is listed in `3-forecast-bridge.csv`, so nobody has to trust a single total.
6. **The Monday note, with a guard.** The AI writes the note from a facts file the code computes. Then the code checks every number in the note against the facts. If the AI rounds, adds up, or invents anything, its note is thrown away and a plain template goes out instead.
7. **One message per owner.** "Hi Jonas, 12 things in HubSpot need you before this week's forecast call", most urgent first.

## Keeping the AI honest: a blind judge

I wrote the generator, so I know which pairs are traps. If I judged the 36 look-alike pairs, the result would be worthless. So the 36 prompts went to a separate Claude agent that was told to read one file, the prompts, and nothing else. Its answers are recorded word for word in `data/ai/duplicate-verdicts.csv`, together with the exact prompts it saw. The note was written the same way, from the facts file only.

That's also what `replay` mode is: the demo runs without an API key by replaying those recorded answers. `live` mode sends the same prompts to the API with your own key.

## Why the checks run inside n8n

The plan was "Python does the maths, n8n runs it every Monday". That changed when I tried it: **n8n 2.x switches off its "Execute Command" step by default**, for good security reasons, and the official n8n Docker image has no Python. A setup guide that starts with "first, turn off a safety setting" is not what you want someone to read before they trust a tool with their CRM.

So the checks run as normal n8n Code steps, one box per job, and the Python version became the reference copy and the test harness. That only works if both give the same answers, so `compare_outboxes.py` compares every output file, cell by cell. They're identical in all three AI modes, on 5 more seeds, when the guard rejects a note, and when the workflow runs twice ([`test/n8n-checks.txt`](test/n8n-checks.txt)).

## What went wrong along the way (all of this actually happened)

- **A day-boundary bug in the generator.** The validator found "clean" deals whose last activity was 26 days ago, where I'd promised at most 25. The code compared "now, Monday 07:30" with whole dates: a deal at 25 days and some hours counted as 25 for one line of code and 26 for another. **Fix:** compare whole dates everywhere. Separately, copies from a double import could inherit an old activity date. Neither would have triggered a check (stale starts at 31), but the data has to match what I wrote down.
- **Copying Python's similarity score into JavaScript.** Which pairs reach the AI depends on a name-similarity score from Python's `difflib`. If n8n's version differed even slightly, n8n and Python would send different pairs to the AI. So I copied the algorithm line by line, including a rule that only matters for strings over 200 characters, and compared both on 3,500 pairs: 0 differences.
- **n8n stopped with "amountGap is not defined".** Each Code step is its own little program, and step 3 used a helper that only existed in step 2. **Fix:** step 3 gets the helpers it uses.
- **11.2 or 11.3?** One amount gap was exactly 11.25 %. Python wrote 11.2, n8n wrote 11.3. Python rounds a half to the even digit; JavaScript rounds it up. Tiny, but it made the two versions disagree. **Fix:** one explicit "half up" rule in both.
- **The number guard had a hole.** I tested it with deliberately wrong notes. A rounded total, a percentage the AI worked out itself, a changed count: all rejected. But "One deal is worth €300" passed, because a deal is called "300 seats" and 300 is in the facts. **Fix:** euro amounts must match a euro amount, percentages a percentage. One known limit stays, and is one of the 9 tests: the guard checks that a number exists, not that it sits next to the right name.
- **The cleaned forecast was too low.** I expected cleaning to land close to the truth. It landed 7 % *below* it. The 8 deals without an amount count as €0 in HubSpot's weighted forecast, and the check (rightly) doesn't guess them. So the note now says the cleaned figure is a floor, and "add the amount" is the first line in every owner message.
- **My own write-up was wrong first.** I wrote "rules only would wrongly flag 13 real deals". Checking it against the data: 13 wrong *pairs*, involving 11 distinct deals. Fixed in the README.
- **The canvas.** The first layout hung the eight output lanes far below everything else, so in a full screenshot every box was a dot. Now the outputs sit to the right of the main row.

## What the test showed

On the primary seed: the rule checks caught 38 of 38 with no false flags (expected, since I wrote both sides). The AI judge caught all 10 messy duplicates and called all 6 traps "different". A rules-only version of the same step caught 17 of 18 duplicates but flagged 13 wrong pairs, including all 6 traps. The full numbers are in the [README](README.md#the-test-planted-problems-rules-written-down-before-it-ran).

The most useful finding came from the 20 other seeds: **17 of 200 messy duplicates never reached the AI at all**. Every one was a city added to the name ("Deichgraf Hotels Lüneburg") or an abbreviation ("Sandtor Rei. AG"), with a similarity just under the 0.80 cut-off. Lowering the cut-off would catch them but roughly triple the AI calls, so the next version should get a narrow rule for exactly that pattern instead. That's in the README under "What I'd change next".

## Time saved

Not measured. I haven't timed a real Monday clean-up, so I'm not putting a number on it.
