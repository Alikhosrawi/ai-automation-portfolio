"""The two AI steps: the duplicate judge and the Monday note writer, plus the number guard.

Three modes, chosen with --ai:
  live    calls the AI Messages API with your own ANTHROPIC_API_KEY (model in AI_MODEL, default below)
  replay  uses the answers recorded in data/ai/ (what the demo ships with; no key needed)
  off     no AI: every candidate pair goes to a person, and the plain template note is used
"""
import csv
import json
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPTS = os.path.join(HERE, "..", "prompts")
DEFAULT_MODEL = os.environ.get("AI_MODEL", "claude-sonnet-5-5")

DEAL_FIELDS = ["Record ID", "Deal Name", "Deal Stage", "Amount", "Close Date", "Create Date", "Last Activity Date",
               "Deal owner", "Associated Company (Primary)"]
COMPANY_FIELDS = ["Record ID", "Company name", "Company Domain Name", "City"]


def _block(row, fields):
    return "\n".join(f"{f}: {row.get(f, '') or '(empty)'}" for f in fields)


def pair_id(p):
    return f"{p['original']['Record ID']}~{p['copy']['Record ID']}"


def judge_prompt(p):
    t = open(os.path.join(PROMPTS, "duplicate-judge.md"), encoding="utf-8").read()
    a, b = p["original"], p["copy"]
    return (t.replace("{deal_a}", _block(a, DEAL_FIELDS)).replace("{company_a}", _block(a["_company"], COMPANY_FIELDS))
             .replace("{deal_b}", _block(b, DEAL_FIELDS)).replace("{company_b}", _block(b["_company"], COMPANY_FIELDS)))


def note_prompt(facts):
    t = open(os.path.join(PROMPTS, "weekly-note.md"), encoding="utf-8").read()
    return t.replace("{facts_json}", json.dumps(facts, indent=2, ensure_ascii=False))


def call_ai(prompt, max_tokens=600):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("--ai live needs ANTHROPIC_API_KEY in the environment")
    body = json.dumps({"model": DEFAULT_MODEL, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    url = os.environ.get("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")
    req = urllib.request.Request(url, data=body, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.loads(r.read())
    return "".join(c.get("text", "") for c in out["content"]).strip()


def parse_verdict(text):
    line = text.strip().splitlines()[0] if text.strip() else ""
    m = re.match(r"^\s*(DUPLICATE|DIFFERENT|UNSURE)\s*\|\s*(.*)$", line)
    if not m:
        return "UNSURE", f"unreadable answer, sent to a person: {line[:60]}"
    return m.group(1), m.group(2).strip()


def judge_pairs(pairs, mode, recorded_path):
    """Returns {pair_id: (verdict, reason, source)}."""
    recorded = {}
    if mode == "replay" and os.path.exists(recorded_path):
        for r in csv.DictReader(open(recorded_path, encoding="utf-8")):
            recorded[r["pair_id"]] = r
    out = {}
    for p in pairs:
        pid = pair_id(p)
        if mode == "off":
            out[pid] = ("UNSURE", "AI step switched off: a person decides", "off")
        elif mode == "replay":
            r = recorded.get(pid)
            out[pid] = ((r["verdict"], r["reason"], f"recorded ({r['model']})") if r
                        else ("UNSURE", "no recorded answer for this pair: a person decides", "replay-missing"))
        else:
            v, why = parse_verdict(call_ai(judge_prompt(p), max_tokens=120))
            out[pid] = (v, why, DEFAULT_MODEL)
    return out


# ---- the number guard -------------------------------------------------------------------------------
NUM = re.compile(r"\d[\d,.]*\d|\d")
MONEY = re.compile(r"€\s?(\d[\d,.]*\d|\d)")
PCT = re.compile(r"(\d[\d,.]*\d|\d)\s?%")


def _norm(n):
    return n.rstrip(".").replace(",", "")


def numbers_in(text):
    """Every number in a text, normalised: '€1,234' -> '1234', '12.5%' -> '12.5'. Trailing dots dropped."""
    return {_norm(m) for m in NUM.findall(text)}


def number_guard(note, facts):
    """Every number in the note must appear in the facts. Euro amounts must match a euro amount in the facts and
    percentages a percentage, so '€300' can't pass just because a deal is called '300 seats'.
    Returns the list of numbers that fail."""
    fact_text = json.dumps(facts, indent=1, ensure_ascii=False)  # same text as JSON.stringify(facts, null, 1) in n8n
    allowed = numbers_in(fact_text) | {"4"}  # "Q4" is allowed
    money, pct = {_norm(m) for m in MONEY.findall(fact_text)}, {_norm(m) for m in PCT.findall(fact_text)}
    bad = {n for n in numbers_in(note) if n not in allowed}
    bad |= {f"€{_norm(m)}" for m in MONEY.findall(note) if _norm(m) not in money}
    bad |= {f"{_norm(m)}%" for m in PCT.findall(note) if _norm(m) not in pct}
    return sorted(bad)
