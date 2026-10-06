# Amendments to the pre-registration

`PREREGISTRATION.md` is unchanged since it was locked (6 Oct 2026, 18:18). Everything that changed afterwards is listed
here with the date and the reason. None of these changes the rules, the planted problems, the metrics or the scored result:
`results/primary-seed-score.json` was re-run after each change and stayed identical.

**A1, 6 Oct 2026: two generator bugs fixed before any check code ran.** The validator (`workflow/validate_export.py`)
found clean rows with a last activity 26–28 days old, where the pre-registration promises 0–25. Causes: copies from a
double import could inherit an older activity date, and one calculation compared "now at 07:30" with whole dates, so a row
the code counted as 25 days old was 26 calendar days old. Both fixed; all 21 seeds pass the validator. No problem code was
affected (stale starts at 31 days), so no check would have changed.

**A2, 6 Oct 2026: the facts for the note gained one sentence.** `not_counted_no_amount.meaning` says that deals without an
amount count as zero, so the cleaned figure can only go up once they're filled in. Added after scoring showed the cleaned
forecast is 7 % *below* the truth because of those deals. It is a fixed sentence written by the code, not by the AI.

**A3, 6 Oct 2026: the number guard got stricter.** The pre-registration says every number in the note must appear in the
facts. Testing it with deliberately wrong notes showed a hole: deal names contain numbers ("300 seats"), so a made-up
"€300" would pass. Now euro amounts must match a euro amount in the facts, and percentages a percentage. The recorded AI
note passes both versions. A known limit stays and is tested: the guard checks that a number exists, not that it sits
next to the right name (two owners' counts swapped would pass). `workflow/test_number_guard.py` has all 9 cases.

**A4, 6 Oct 2026: n8n runs the checks itself, Python is the reference copy.** The plan was "Python core, n8n shell". But
n8n 2.x switches off its "Execute Command" step by default for security, and the official n8n Docker image has no Python.
So the checks run as visible n8n Code steps, written as a JavaScript copy of the Python. `workflow/compare_outboxes.py`
compares both versions' output files; see `n8n-checks.txt` (identical in every mode and on 5 other seeds).

**A5, 6 Oct 2026: one rounding rule for both languages.** An amount gap of exactly 11.25 % was written as 11.2 by Python
(round half to even) and 11.3 by n8n (round half up). Both now round halves up. Display only; no metric uses it.

**A6, 6 Oct 2026: the owner to-do messages and the would-send file were added to the outputs** (6-owner-messages.csv,
5-would-send.csv, which replaces a log that grew on every run). Outputs only; nothing scored reads them.
