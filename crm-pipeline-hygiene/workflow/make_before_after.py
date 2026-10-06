"""Renders screenshots/02-before-export.png and 03-after-check.png from the real export and outbox rows.
Needs Playwright with Chromium (only for the pictures; the check itself needs neither)."""
import csv, html, json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
IDS = ["32287349317", "32291030631", "32158874439", "32162047647", "32120217853", "31999326915", "32244299145", "32247247361"]
deals = {r["Record ID"]: r for r in csv.DictReader(open(D("data", "export", "deals.csv"), encoding="utf-8"))}
flags = {}
for r in csv.DictReader(open(D("data", "outbox", "1-fix-list.csv"), encoding="utf-8")):
    flags.setdefault(r["record_id"], []).append(r)
review = list(csv.DictReader(open(D("data", "outbox", "2-duplicate-review.csv"), encoding="utf-8")))
facts = json.load(open(D("data", "outbox", "facts.json"), encoding="utf-8"))
note = open(D("data", "outbox", "4-monday-note.md"), encoding="utf-8").read().strip()
e = html.escape

def verdict_for(rid):
    if rid in flags:
        f = flags[rid][0]
        label = {"DUPLICATE": "Duplicate copy", "ZOMBIE": "No activity 60+ days", "NO_AMOUNT": "No amount"}.get(f["check"], f["check"])
        if f["check"] == "DUPLICATE":
            pair = next(r for r in review if r["copy_id"] == rid)
            why = f"Copy of {pair['original_id']}. " + ("Rule: same company, same name." if pair["decided_by"] == "rule" else f"AI: {pair['reason']}")
        else:
            why = f["detail"].capitalize() + "."
        return "flag", label, why
    for r in review:
        if rid in (r["copy_id"], r["original_id"]) and r["verdict"] == "DIFFERENT" and "Tidenhub" in r["original_deal"] and rid in ("32244299145", "32247247361"):
            return "ok", "Not a duplicate", "AI: " + next(x["reason"] for x in review if x["original_id"] == "32244299145" and x["copy_id"] == "32247247361")
    return "ok", "Looks fine", ""

CSS = """
:root{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--line:#e4e3df;--head:#f2f1ee;--flag:#eb6834;--flagbg:#fdf0ea;--ok:#2a78d6;--okbg:#eaf2fc}
*{box-sizing:border-box} body{margin:0;background:var(--bg);font:15px/1.4 Inter,system-ui,-apple-system,Segoe UI,sans-serif;color:var(--ink)}
.wrap{padding:28px 32px;width:1960px} h1{font-size:20px;margin:0 0 4px} .sub{color:var(--ink2);margin:0 0 18px}
table{border-collapse:collapse;width:100%;font-size:13.5px;background:#fff;border:1px solid var(--line)}
th{background:var(--head);text-align:left;font-weight:600;padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
td.nw{white-space:nowrap} td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top} td.num{text-align:right;font-variant-numeric:tabular-nums}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;color:var(--ink2)}
.stat{display:flex;gap:28px;margin:0 0 18px}.stat div{background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px 16px}
.stat b{display:block;font-size:24px}.stat span{color:var(--ink2);font-size:13px}
.chip{display:inline-block;border-radius:4px;padding:1px 7px;font-weight:600;font-size:12.5px;white-space:nowrap}
.flag .chip{background:var(--flagbg);color:#8a3210;border-left:3px solid var(--flag)} .ok .chip{background:var(--okbg);color:#174a85;border-left:3px solid var(--ok)}
tr.flag td{background:#fffaf7} .why{color:var(--ink2);font-size:12.5px;margin-top:3px;max-width:330px}
.grid{display:grid;grid-template-columns:minmax(0,1fr) 400px;gap:24px;align-items:start}
.note{background:#fff;border:1px solid var(--line);border-radius:8px;padding:16px 18px;white-space:pre-wrap;font-size:13.5px}
.note h2{font-size:14px;margin:0 0 8px;color:var(--ink2);font-weight:600}
"""
COLS = ["Record ID", "Deal Name", "Deal Stage", "Amount", "Close Date", "Last Activity Date", "Deal owner", "Associated Company (Primary)"]

def table(after):
    h = "".join(f"<th>{e(c)}</th>" for c in COLS) + ("<th>What the Monday check says</th>" if after else "")
    rows = []
    for rid in IDS:
        d = deals[rid]
        cls, label, why = verdict_for(rid) if after else ("", "", "")
        cells = []
        for c in COLS:
            v = d[c]
            if c == "Amount":
                cells.append(f"<td class='num'>{'' if not v else f'{int(v):,}'}</td>")
            elif c == "Record ID":
                cells.append(f"<td class='mono'>{e(v)}</td>")
            elif c in ("Close Date", "Last Activity Date", "Deal Stage", "Deal owner"):
                cells.append(f"<td class='nw'>{e(v)}</td>")
            else:
                cells.append(f"<td>{e(v)}</td>")
        if after:
            cells.append(f"<td><span class='chip'>{e(label)}</span>{f'<div class=why>{e(why)}</div>' if why else ''}</td>")
        rows.append(f"<tr class='{cls}'>{''.join(cells)}</tr>")
    return f"<table><tr>{h}</tr>{''.join(rows)}</table>"

before = f"""<div class=wrap><h1>Before: the HubSpot export on Monday morning</h1>
<p class=sub>deals.csv, 8 of 424 rows (fictional company, all names made up). Nothing here looks wrong at a glance.</p>
<div class=stat><div><b>{facts['q4_forecast_as_exported']}</b><span>Q4 weighted forecast, as exported</span></div>
<div><b>{facts['q4_open_deals']}</b><span>open deals closing in Q4</span></div></div>{table(False)}</div>"""
after = f"""<div class=wrap><h1>After: the same rows, and the note the Head of RevOps reads</h1>
<p class=sub>Flags from the rule checks and the AI duplicate judge. Nothing in HubSpot was changed; the note would be posted, nothing is sent.</p>
<div class=stat><div><b>{facts['q4_forecast_as_exported']} → {facts['q4_forecast_cleaned']}</b><span>Q4 weighted forecast, before → after cleaning</span></div>
<div><b>{facts['items_total']}</b><span>things to fix, split by owner</span></div></div>
<div class=grid><div>{table(True)}</div><div class=note><h2>#sales-leadership, Mon 07:30 (would post)</h2>{e(note)}</div></div></div>"""

with sync_playwright() as p:
    b = p.chromium.launch()
    for name, body, width in [("02-before-export.png", before.replace("width:1960px", ""), 2024), ("03-after-check.png", after, 2024)]:
        pg = b.new_page(viewport={"width": width, "height": 400}, device_scale_factor=2)
        pg.set_content(f"<!doctype html><meta charset=utf-8><style>{CSS}</style>{body}")
        pg.wait_for_timeout(300)
        pg.locator(".wrap").screenshot(path=D("screenshots", name))
        print(name)
    b.close()
