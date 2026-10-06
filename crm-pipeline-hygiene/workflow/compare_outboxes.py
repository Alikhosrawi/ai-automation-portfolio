"""Compare two outbox folders file by file: the n8n workflow's and the Python reference copy's.

  python3 compare_outboxes.py <n8n outbox> <python outbox>

CSV files are compared row by row and cell by cell (n8n and Python quote CSV slightly differently, so the bytes may
differ while the content is identical). facts.json is compared as data. The note and guard files as text.
Exit code 0 means every file matches.
"""
import csv
import json
import sys

FILES = ["1-fix-list.csv", "2-duplicate-review.csv", "3-forecast-bridge.csv", "4-monday-note.md", "4b-number-guard.txt",
         "5-would-send.csv", "6-owner-messages.csv", "facts.json"]


def rows(path):
    return [[c.strip() for c in r] for r in csv.reader(open(path, encoding="utf-8-sig", newline=""))]


def main(a, b):
    bad = 0
    for f in FILES:
        pa, pb = f"{a}/{f}", f"{b}/{f}"
        if f.endswith(".csv"):
            ra, rb = rows(pa), rows(pb)
            diffs = [(i, x, y) for i, (x, y) in enumerate(zip(ra, rb)) if x != y]
            same = not diffs and len(ra) == len(rb)
            detail = f"{len(ra) - 1} rows" if same else f"{len(ra)} vs {len(rb)} rows; first difference: {diffs[:1]}"
        elif f.endswith(".json"):
            same = json.load(open(pa, encoding="utf-8")) == json.load(open(pb, encoding="utf-8"))
            detail = "same data" if same else "data differs"
        else:
            ta, tb = open(pa, encoding="utf-8").read().strip(), open(pb, encoding="utf-8").read().strip()
            same = ta == tb
            detail = f"{len(ta.splitlines())} lines" if same else "text differs"
        bad += not same
        print(f"{'same' if same else 'DIFF'}  {f}: {detail}")
    print(f"\n{len(FILES) - bad} of {len(FILES)} files identical")
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
