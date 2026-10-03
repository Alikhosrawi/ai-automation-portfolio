# Build story: document chasing for a small relocation agency

*One chore, gone. Everything here is made up: the agency, the clients, the employers, the documents. No real message was sent to anyone. The document checklist is illustrative, not legal advice.*

## The chore

A relocation agency helps people who are moving to Hamburg for a job, a study place or to join their family. Every new client needs a residence permit, and every permit needs a stack of documents. Which ones depends on the type of permit and sometimes on the person's nationality.

So for every new client, someone puts together a checklist by hand. Then the documents trickle in over weeks. Someone keeps track of what's missing, writes polite "could you send…?" emails, and tries not to nag the same person twice in a week. On Friday, the client wants to know where things stand, and so does their employer's HR team. HR should hear about progress, not about the client's marriage certificate.

## Why n8n

Same reason as in the [physio demo](../physio-appointment-reminders/): n8n is free to run yourself, and the whole process is visible as one picture on a canvas. Here that matters even more, because the important part is a **rules table**, a plain spreadsheet that says which permit needs which documents. The agency can change that table without touching the workflow.

## What I built, step by step

1. **Fake data.** Six made-up clients from India, the US, Brazil, Nigeria, Japan and Iran, with five permit types: EU Blue Card, ICT card (a transfer within a company), §18b skilled worker, family reunion and student. Emails like `client1@example.com`, phone numbers like `+49 000 0000 0101`, employers like "Example Employer A GmbH".
2. **A rules table** with 22 rows: six documents everyone needs (passport, photo, address registration and so on), some per permit type (degree, employer's declaration, admission letter…), and a few that depend on nationality (in this made-up rule set, US and Japanese nationals skip the entry visa copy). Each rule also says who provides the document (client or employer) and has one plain-English sentence on why it's needed.
3. **Check 1: intake (09:00).** A form submission without a case gets a case number, a checklist (every rule that matches the client's permit and nationality), and a welcome email listing each document and why it's needed.
4. **Check 2: chasing (09:30).** For every document that hasn't arrived, decide: may we remind about this one today? Then one email per person with everything that's due. Employer documents go to HR, the rest to the client.
5. **Check 3: weekly status (Fridays 16:00).** The client gets the full picture: what came in this week, what's still needed from them, what's waiting on the employer. HR gets a progress-only version: "8 of 11 documents in (73%)", what's needed from HR, and only a *count* of the employee's open items.
6. **The log.** As in the physio demo, nothing is sent. Every message goes into a "would send" file. The workflow has no sending step at all.

## The guard against repeat-chasing

The physio demo's bug was a check that answered every reply in the sheet on every run, so people would have been thanked over and over. Chasing documents is the same trap: "remind everyone about everything missing" sends the same email every morning.

So the chasing check works per document. It looks up the **last contact** for each missing document (the day the checklist went out, or the last reminder about it, whichever is later). It only reminds if that was at least 7 days ago. Every reminder is written to a chase log, which the next run reads. The weekly update has the same kind of memory: a status log with one line per case per week.

I tested it in three ways (all real runs in n8n):

- **Same day, run again:** 0 new cases, 0 reminders, 0 weekly updates.
- **Two more weeks, one run per day** (17 to 30 Oct, weekly status on Fridays): I then checked the whole chase log from 28 Sep to 30 Oct. 107 reminders for 43 documents, none closer than 7 days to the previous contact, and none for a document that had already arrived. No case got two weekly updates in the same week.
- **The demo day itself:** 37 documents are missing. 6 are due (last contact on 9 Oct) and 31 wait, because they were chased on 12 Oct or the checklist only went out this week.

Honestly, this part worked the first time, because I designed it around the physio demo's lesson. The bugs I did hit were elsewhere.

## What went wrong along the way (all of this actually happened)

- **The later checks read the sheets before the first check had saved them.** My first version added new rows to a sheet with a Merge step ("old rows + new rows"). In the first test run, with all six clients new, the welcome emails came out fine, but the chasing and weekly checks saw empty sheets. n8n had pushed the Merge steps to the very end of the run, after the other checks had already read the files. **Fix:** one step that builds "old rows + new rows" as a single list right after the new rows are made, then splits it back into rows. Now each check saves before the next one starts.
- **An invisible character made every document look… not missing.** n8n starts the CSV files it writes with an invisible marker (a byte-order mark, the same one that tripped my screenshot script in the physio demo). When the workflow read its own checklist sheet back, the first column wasn't called `case_id` any more but `\ufeffcase_id`, so every lookup by case found nothing. The chasing check reported **0 missing documents out of 65**, with no error message. **Fix:** switch on "Exclude Byte Order Mark" in every step that reads a sheet. This is the bug that scared me most, because a silent "nothing to do" looks exactly like success.
- **New clients would have got two emails on day one.** Reading the output, I saw that Yui and Arash got their welcome checklist at 09:00 and then a "weekly update: 0 of 10 documents in" at 16:00 with the same list. **Fix:** weekly updates only go to cases opened before today.
- **The Execute button ran only part of the workflow.** With several triggers, n8n's "Execute workflow" button picked "from Every morning 09:00", so a click ran only the intake check. **Fix:** pick "Run the demo day (test button)" in the small menu next to the button. The README says so.

## What the final version does

In one click (about 1.3 seconds in n8n), on the demo Friday it:

- opens **2 new cases** (Yui, family reunion; Arash, student) with checklists of 10 and 11 documents, and writes **2 welcome emails**,
- checks **37 missing documents**, chases the **6** that are due and writes **3 reminders** (Jake, Jake's HR contact, Larissa),
- writes **4 weekly client updates** and **4 HR updates** (progress only),
- and saves all 13 messages to the "would send" log. Nothing leaves the computer.

The "before" sheets for that Friday weren't typed by hand. I ran the workflow once per simulated day from 21 Sep to 15 Oct, starting with empty sheets, so the case history and chase log are what the workflow itself would have produced.

What it doesn't do: send or receive anything, check that a received document is actually usable, stop or escalate after many reminders, or know the real, current requirements. The rules table is made up and illustrative.

## AI: not in this version

I'd planned an optional AI step to write the friendly explanation for each document. The demo had to run without an API key, so the explanation comes from the rules table instead (one sentence per document, written by hand). That's the fallback, and it's what you see in the output. The canvas marks where an AI step could go, but none is included or tested. The bonus idea, drafting a German letter from English notes, needs AI too, so I skipped it.

## Time saved

Not measured yet. The honest next step is to time someone building a checklist and writing a week of reminders by hand before putting any number on it.

## Biggest lesson

The physio demo taught me to only look at what's new since the last run. This one added a second lesson: when a check says "nothing to do", make sure that's really true. The two worst bugs here produced no error at all. They just quietly did less.
