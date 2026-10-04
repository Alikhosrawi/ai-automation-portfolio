# Amendments and clarifications to PREREGISTRATION.md

`PREREGISTRATION.md` is never edited. Anything below is dated and gives its reason.

## Clarifications written before any v2 result existed (2026-10-04, while writing the generator)
These fill gaps the pre-registration leaves open. None of them changes a rule, a parameter, the seed, a metric, a baseline or the scored weeks.
1. **Random streams.** Each part of the generator has its own random stream, seeded with the text "<seed>-<part>", for example "20261004-sick".
   So drawing, say, the sick weeks doesn't shift the noise in the bookings.
2. **Sickness vs vacation.** A sickness draw is drawn again if it lands on the same therapist's vacation week or if the two episodes share a week.
   The pre-registration says "no overlap" without saying with what; this reading covers both.
3. **Appointment days and times.** Each appointment gets an open day of its week at random (uniform), and its therapist's appointments that day get
   start times from 08:00 in 30-minute steps. Only the date and treatment are used by the agent. The day doesn't affect scoring, because use is
   spread evenly over the open days, as pre-registered.
4. **A loss bigger than the shelf** removes only what is there. A loss never counts as a stock-out: stock-outs are about use on open days.
5. **Recorded usage** for week w = consumption + loss + count error of the count before week w − count error of the count at the end of week w,
   not below 0. It does not depend on the policy (as pre-registered). The observed Friday count in the simulation = max(0, true shelf + that Friday's error).
