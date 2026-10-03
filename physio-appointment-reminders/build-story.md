# Build story: appointment reminders for a small physio practice

*One chore, gone. Everything here is made up: the practice, the patients, the replies. No real message was sent to anyone.*

## The chore

A practice with three therapists and one shared appointment sheet. Every afternoon someone writes to tomorrow's patients one by one. Then the replies trickle in during treatments and each one needs an answer. A "can we move it?" means looking for a free slot. And when someone doesn't turn up, the kind thing is a same-day message offering a new time. That's usually the first thing to get skipped.

## Why n8n

n8n is a free tool you can run yourself. You build a process by connecting boxes on a canvas: read a file → filter → write a message → save. I picked it because the whole flow is visible as one picture, there's no code to maintain, and the free self-hosted version is enough. A spreadsheet plus a script would also work, but then the process only lives inside the script.

## What I built, step by step

1. **A fake sheet.** 18 made-up patients from Mon 5 to Thu 8 Oct, three therapists (Lena, Jonas, Mira), statuses `booked`, `attended` or `no-show`. Plus 9 empty `open` rows as free slots, and a column for what the patient replied.
2. **A fixed demo clock.** The workflow pretends it's Monday 5 Oct, so the same sheet always gives the same result. Each check starts with a "What time is it?" step. Going live means switching that step to the real clock.
3. **Check 1: afternoon reminders (15:00).** Keep the rows booked *for tomorrow* and write: "Hi Felix, a reminder of your physio appointment with Mira tomorrow at 08:00. Reply 1 = See you tomorrow, or 2 = I need to move it."
4. **Check 2: replies (every 15 minutes).** "1" or "see you tomorrow" gets a short thank-you. "2" or anything with "move" gets the next three open slots, same therapist first. Anything else ("can I come a bit later?") gets **no** automatic reply and is flagged for a person.
5. **Check 3: same-day no-shows (18:30).** Keep the rows marked no-show *today* and write a kind note offering to rebook.
6. **The log.** Instead of sending anything, every message goes into a "would send" file with who, when and what. The workflow doesn't contain a single sending step.

## The real bug: patients would have been thanked over and over

My first version of the reply check looked at **every** reply in the sheet.

I tested it by running the check twice, 15 minutes apart (17:00 and 17:15), and again the next day. Each run answered the same five people again. Felix would have got "Thanks, see you tomorrow!" every 15 minutes, four times an hour, and again on Tuesday.

**The fix:** save the time each reply arrived, and only answer replies that came in **since the last check**. Each check now asks "what's new since I last looked?" instead of "what's in the sheet?".

I re-tested with eight checks, 15 minutes apart. Every reply was answered exactly once.

## The same trap, caught while planning

"Follow up with everyone marked no-show" would have messaged Monday's no-shows again every single evening. Limiting it to **today's** no-shows fixes that. I tested a Tuesday run: Ben and David, Monday's no-shows, got nothing.

## Smaller snags

- **n8n wouldn't install at first.** The current n8n needs Node.js 24 and my setup had Node 20. My first install attempt also failed with an unhelpful error ("Tracker idealTree already exists"). The fix was to install Node 24 inside the project folder and give the folder its own small settings file (`npm init`) so the installer knew where to put things. After that it installed in about 2 minutes.
- **Two copies of n8n fighting over a port.** Running the workflow from the command line while the editor was open failed with "port 5679 is already in use". Giving the command-line run its own port fixed it.
- **An invisible character.** One log file starts with an invisible marker that Excel likes (a byte-order mark). It tripped up my screenshot script until I told the script to expect it.

## What the final version does

In one click (about 1.1 seconds in n8n), on the demo Monday it:

- writes **6 reminders** for Tuesday's patients,
- writes **2 thank-yous** (Felix, Ida) and **2 slot offers** (Greta, Hannes), and **flags 1 unclear reply** (Karla) for a person,
- writes **2 same-day no-show notes** (Ben, David),
- and saves all 13 to the "would send" log. Nothing leaves the computer.

What it doesn't do yet: actually send, receive replies, hold or book the chosen slot (a person still does that), or catch bookings for tomorrow made after the 15:00 check.

## Time saved

Not measured yet. The honest next step is to time the manual version with a stopwatch (write five reminders by hand from the sheet and divide by five) before putting any number on it.

## Biggest lesson

Writing the messages was the easy part. The hard part was making sure nobody hears the same thing twice. Any check that runs again and again should only look at what's new since the last run.
