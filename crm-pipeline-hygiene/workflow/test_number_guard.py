"""Feed the number guard notes that should pass and notes that should fail. Run: python3 test_number_guard.py"""
import json, os
from ai_steps import number_guard
from run_weekly import template_note

HERE = os.path.dirname(os.path.abspath(__file__))
facts = json.load(open(os.path.join(HERE, "..", "data", "outbox", "facts.json"), encoding="utf-8"))
note = open(os.path.join(HERE, "..", "data", "ai", "weekly-note.md"), encoding="utf-8").read()
cases = [
    ("the recorded AI note", note, True),
    ("the plain template note", template_note(facts), True),
    ("a rounded total (€345,000 instead of €345,040)", note.replace("€345,040", "€345,000"), False),
    ("a percentage the AI computed itself", note + "\nThat is 9.6% of the pipeline.", False),
    ("a euro amount borrowed from a deal name (300 seats)", note + "\nOne deal is worth €300.", False),
    ("a percentage that is a deal count in the facts (12%)", note.replace("16.2%", "12%") + " 12%", False),
    ("an owner count changed (12 -> 13)", note.replace("Jonas Example: 12", "Jonas Example: 13"), False),
    ("a made-up deal count", note + "\n31 deals look risky.", False),
    # a known limit: the guard checks that each number exists in the facts, not that it sits next to the right name
    ("KNOWN LIMIT: two owners' counts swapped (passes)", note.replace("Jonas Example: 12", "Jonas Example: 9").replace("Finn Example: 9", "Finn Example: 12"), True),
]
fails = 0
for name, text, should_pass in cases:
    problems = number_guard(text, facts)
    ok = (not problems) == should_pass
    fails += not ok
    print(f"{'ok ' if ok else 'BAD'} {'pass' if not problems else 'fail'}  {name}  {problems if problems else ''}")
print(f"\n{len(cases) - fails} of {len(cases)} cases as expected")
raise SystemExit(fails)
